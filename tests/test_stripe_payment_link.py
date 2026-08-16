from __future__ import annotations

import pytest

from forge.integrations.stripe import (
    StripeCheckoutContractError,
    build_order_payment_link,
    order_id_from_checkout_session,
    validate_checkout_session,
)


def test_payment_link_carries_the_forge_order_reference() -> None:
    url = build_order_payment_link("https://buy.stripe.com/test_abc", "ord_customer_123")
    assert url == "https://buy.stripe.com/test_abc?client_reference_id=ord_customer_123"


def test_payment_link_preserves_existing_parameters() -> None:
    url = build_order_payment_link(
        "https://buy.stripe.com/test_abc?prefilled_email=buyer%40example.com",
        "ord_customer_123",
    )
    assert "prefilled_email=buyer%40example.com" in url
    assert "client_reference_id=ord_customer_123" in url


def test_payment_link_rejects_a_stripe_lookalike_host() -> None:
    with pytest.raises(StripeCheckoutContractError, match="STRIPE_PAYMENT_LINK_URL_INVALID"):
        build_order_payment_link(
            "https://buy.stripe.com.example.com/test_abc",
            "ord_customer_123",
        )


def test_checkout_uses_client_reference_id_when_metadata_is_absent() -> None:
    assert (
        order_id_from_checkout_session({"client_reference_id": "ord_customer_123"})
        == "ord_customer_123"
    )


def test_checkout_contract_accepts_the_350_dollar_payment_link() -> None:
    validate_checkout_session(
        {"payment_link": "plink_forge", "amount_total": 35000, "currency": "usd"},
        expected_payment_link_id="plink_forge",
        expected_amount_cents=35000,
    )


@pytest.mark.parametrize(
    ("session", "error"),
    [
        (
            {"payment_link": "plink_other", "amount_total": 35000, "currency": "usd"},
            "STRIPE_PAYMENT_LINK_MISMATCH",
        ),
        (
            {"payment_link": "plink_forge", "amount_total": 7500, "currency": "usd"},
            "STRIPE_AMOUNT_MISMATCH",
        ),
        (
            {"payment_link": "plink_forge", "amount_total": 35000, "currency": "krw"},
            "STRIPE_CURRENCY_MISMATCH",
        ),
    ],
)
def test_checkout_contract_rejects_wrong_payments(session: dict, error: str) -> None:
    with pytest.raises(StripeCheckoutContractError, match=error):
        validate_checkout_session(
            session,
            expected_payment_link_id="plink_forge",
            expected_amount_cents=35000,
        )
