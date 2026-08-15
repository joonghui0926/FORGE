import os
from fastapi import APIRouter, Header, HTTPException, Request, status
import stripe

router = APIRouter()


@router.post("/stripe", status_code=status.HTTP_200_OK)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(..., alias="stripe-signature"),
) -> dict:
    payload = await request.body()
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

    try:
        event = stripe.Webhook.construct_event(payload, stripe_signature, secret)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")

    event_type: str = event["type"]

    if event_type == "checkout.session.completed":
        # TODO: dedupe by provider event ID, transition order to PAID
        pass
    elif event_type == "payment_intent.payment_failed":
        # TODO: mark order payment failed
        pass

    return {"received": True}


@router.post("/terac", status_code=status.HTTP_200_OK)
async def terac_webhook(
    request: Request,
    x_terac_signature: str = Header(..., alias="x-terac-signature"),
) -> dict:
    # TODO: verify TERAC_WEBHOOK_SECRET HMAC, dedupe by provider event ID
    # TODO: handle submission events → create/update capture record
    raise HTTPException(status_code=501, detail="Not implemented")
