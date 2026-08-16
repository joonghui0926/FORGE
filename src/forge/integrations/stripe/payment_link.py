from __future__ import annotations

from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


class StripeCheckoutContractError(ValueError):
    pass


def build_order_payment_link(payment_link_url: str, order_id: str) -> str:
    """Attach a non-sensitive FORGE order ID using Stripe's supported URL contract."""

    if not order_id.startswith("ord_"):
        raise StripeCheckoutContractError("STRIPE_ORDER_ID_INVALID")
    parsed = urlsplit(payment_link_url.strip())
    if parsed.scheme != "https" or parsed.netloc != "buy.stripe.com":
        raise StripeCheckoutContractError("STRIPE_PAYMENT_LINK_URL_INVALID")
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["client_reference_id"] = order_id
    return urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment)
    )


def order_id_from_checkout_session(session: dict[str, Any]) -> str:
    metadata = session.get("metadata") or {}
    order_id = str(metadata.get("order_id") or session.get("client_reference_id") or "")
    if not order_id.startswith("ord_"):
        raise StripeCheckoutContractError("STRIPE_ORDER_ID_MISSING")
    return order_id


def validate_checkout_session(
    session: dict[str, Any],
    *,
    expected_payment_link_id: str | None,
    expected_amount_cents: int | None,
    expected_currency: str = "usd",
) -> None:
    payment_link_id = str(session.get("payment_link") or "")
    if expected_payment_link_id and payment_link_id != expected_payment_link_id:
        raise StripeCheckoutContractError("STRIPE_PAYMENT_LINK_MISMATCH")
    if expected_amount_cents is not None and int(session.get("amount_total") or -1) != int(
        expected_amount_cents
    ):
        raise StripeCheckoutContractError("STRIPE_AMOUNT_MISMATCH")
    if str(session.get("currency") or "").lower() != expected_currency.lower():
        raise StripeCheckoutContractError("STRIPE_CURRENCY_MISMATCH")
