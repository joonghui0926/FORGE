from __future__ import annotations

from hashlib import sha256
import json
import os
import secrets

from fastapi import APIRouter, Header, HTTPException, Request, status
import stripe

from ..db import get_conn
from ..webhook_security import verify_hmac_sha256
from ..workflow_client import WorkflowDispatchError, start_workflow_task


router = APIRouter()


def _new_id(prefix: str) -> str:
    return f"{prefix}{secrets.token_urlsafe(12)}"


def _record_event(provider: str, event_id: str, payload: dict) -> bool:
    with get_conn() as connection, connection.transaction():
        row = connection.execute(
            """
            INSERT INTO webhook_events (id, provider, provider_event_id, payload)
            VALUES (%s, %s, %s, %s::jsonb)
            ON CONFLICT (provider, provider_event_id) DO UPDATE SET
              payload = EXCLUDED.payload
            RETURNING processed_at
            """,
            (_new_id("wh_"), provider, event_id, json.dumps(payload)),
        ).fetchone()
    return row is not None and row[0] is None


def _mark_event_processed(provider: str, event_id: str) -> None:
    with get_conn() as connection:
        connection.execute(
            "UPDATE webhook_events SET processed_at = NOW() WHERE provider = %s AND provider_event_id = %s",
            (provider, event_id),
        )


@router.post("/stripe", status_code=status.HTTP_200_OK)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(..., alias="stripe-signature"),
) -> dict:
    body = await request.body()
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    try:
        event = stripe.Webhook.construct_event(body, stripe_signature, secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid Stripe webhook")

    event_id = str(event["id"])
    event_payload = event.to_dict_recursive()
    if not _record_event("stripe", event_id, event_payload):
        return {"received": True, "deduplicated": True}

    if event["type"] in {"checkout.session.completed", "checkout.session.async_payment_succeeded"}:
        session = event["data"]["object"]
        order_id = str(session.get("metadata", {}).get("order_id", ""))
        if not order_id.startswith("ord_"):
            raise HTTPException(status_code=422, detail="Stripe order_id metadata missing")
        with get_conn() as connection, connection.transaction():
            row = connection.execute(
                "SELECT state::text FROM dataset_orders WHERE id = %s FOR UPDATE", (order_id,)
            ).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Order not found")
            if row[0] == "DRAFT":
                connection.execute(
                    """
                    UPDATE dataset_orders
                    SET state = 'PAID', stripe_payment_intent = %s, updated_at = NOW()
                    WHERE id = %s
                    """,
                    (session.get("payment_intent") or session.get("id"), order_id),
                )
                connection.execute(
                    """
                    INSERT INTO audit_events
                      (entity_type, entity_id, action, actor, before_val, after_val, evidence)
                    VALUES ('dataset_order', %s, 'order_paid', 'stripe',
                            '{"state":"DRAFT"}'::jsonb, '{"state":"PAID"}'::jsonb,
                            %s::jsonb)
                    """,
                    (order_id, json.dumps({"stripe_event_id": event_id})),
                )
        try:
            run_id = start_workflow_task("order_paid", [order_id])
        except WorkflowDispatchError as error:
            raise HTTPException(status_code=503, detail=str(error))
        with get_conn() as connection:
            connection.execute(
                """
                INSERT INTO workflow_runs (id, order_id, status, current_step, render_root_run_id)
                VALUES (%s, %s, 'RUNNING', 'order_paid', %s)
                ON CONFLICT (order_id) DO UPDATE SET
                  status = 'RUNNING', current_step = 'order_paid',
                  render_root_run_id = EXCLUDED.render_root_run_id, updated_at = NOW()
                """,
                (_new_id("wfr_"), order_id, run_id),
            )
    elif event["type"] == "payment_intent.payment_failed":
        payment_intent = event["data"]["object"]
        order_id = str(payment_intent.get("metadata", {}).get("order_id", ""))
        if order_id:
            with get_conn() as connection:
                connection.execute(
                    "UPDATE dataset_orders SET state = 'FAILED', updated_at = NOW() WHERE id = %s",
                    (order_id,),
                )
    _mark_event_processed("stripe", event_id)
    return {"received": True}


@router.post("/terac", status_code=status.HTTP_200_OK)
async def terac_webhook(
    request: Request,
    x_terac_signature: str = Header(..., alias="x-terac-signature"),
) -> dict:
    body = await request.body()
    if not verify_hmac_sha256(os.getenv("TERAC_WEBHOOK_SECRET", ""), body, x_terac_signature):
        raise HTTPException(status_code=401, detail="Invalid Terac signature")
    payload = json.loads(body)
    event_id = str(payload.get("event_id") or sha256(body).hexdigest())
    if not _record_event("terac", event_id, payload):
        return {"received": True, "deduplicated": True}
    event_type = str(payload.get("type", ""))
    if event_type == "submission.batch_ready":
        order_id = str(payload.get("order_id", ""))
        capture_ids = list(payload.get("capture_ids", []))
        features = dict(payload.get("features", {}))
        if not order_id.startswith("ord_") or not capture_ids:
            raise HTTPException(status_code=422, detail="Terac batch payload incomplete")
        start_workflow_task("fast_pre_qc", [order_id, capture_ids, features])
    _mark_event_processed("terac", event_id)
    return {"received": True}


@router.post("/band-decision", status_code=status.HTTP_200_OK)
async def band_decision_webhook(
    request: Request,
    x_forge_band_signature: str = Header(..., alias="x-forge-band-signature"),
) -> dict:
    body = await request.body()
    if not verify_hmac_sha256(
        os.getenv("BAND_DECISION_WEBHOOK_SECRET", ""), body, x_forge_band_signature
    ):
        raise HTTPException(status_code=401, detail="Invalid Band bridge signature")
    payload = json.loads(body)
    correlation_id = str(payload.get("correlation_id", ""))
    decision = dict(payload.get("decision", {}))
    event_id = (
        f"{correlation_id}:{sha256(json.dumps(decision, sort_keys=True).encode()).hexdigest()}"
    )
    if not _record_event("band", event_id, payload):
        return {"received": True, "deduplicated": True}
    with get_conn() as connection, connection.transaction():
        row = connection.execute(
            """
            SELECT id, order_id, purpose, state FROM provider_requests
            WHERE provider = 'band' AND correlation_id = %s FOR UPDATE
            """,
            (correlation_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Band correlation not found")
        order_id, purpose = str(row[1]), str(row[2])
        if row[3] != "SUCCEEDED":
            connection.execute(
                """
                UPDATE provider_requests
                SET state = 'SUCCEEDED', response_payload = %s::jsonb, completed_at = NOW()
                WHERE id = %s
                """,
                (json.dumps(decision), row[0]),
            )
            connection.execute(
                """
                INSERT INTO decisions
                  (id, order_id, decision_type, reason_codes, evidence_artifact_ids,
                   payload, confidence, policy_version, requires_human_approval)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s)
                """,
                (
                    _new_id("dec_"),
                    order_id,
                    str(decision.get("route") or decision.get("decision_type") or purpose).upper(),
                    list(decision.get("reason_codes", [])),
                    list(decision.get("evidence_artifact_ids", [])),
                    json.dumps(decision),
                    float(decision.get("confidence", 0)),
                    str(decision.get("policy_version", "band-forge-v1")),
                    bool(decision.get("requires_human_approval", False)),
                ),
            )
    if purpose == "collection_plan":
        plan = decision.get("collection_plan")
        if not isinstance(plan, dict):
            raise HTTPException(status_code=422, detail="Band collection plan missing")
        run_id = start_workflow_task("create_terac_campaign", [order_id, plan])
    elif purpose == "quality_decision":
        run_id = start_workflow_task("apply_band_quality_decision", [order_id, decision])
    else:
        raise HTTPException(status_code=422, detail="Unsupported Band decision purpose")
    _mark_event_processed("band", event_id)
    return {"received": True, "task_run_id": run_id}
