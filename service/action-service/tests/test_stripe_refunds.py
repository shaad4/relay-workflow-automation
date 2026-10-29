import asyncio
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import stripe
from app.connectors.stripe import StripeConnector


def refund(monkeypatch, amount, currency="usd", charged=10000, refunded=0):
    payment = SimpleNamespace(
        currency=currency,
        latest_charge=SimpleNamespace(amount=charged, amount_refunded=refunded),
    )
    retrieve = Mock(return_value=payment)
    create = Mock(return_value=SimpleNamespace(id="re_test", status="succeeded"))
    monkeypatch.setattr(stripe.PaymentIntent, "retrieve", retrieve)
    monkeypatch.setattr(stripe.Refund, "create", create)
    result = asyncio.run(
        StripeConnector().execute(
            "refund_payment",
            {"api_key": "sk_test"},
            {"payment_id": "pi_test", "amount": amount, "idempotency_key": "refund-test"},
        )
    )
    retrieve.assert_called_once_with("pi_test", expand=["latest_charge"], api_key="sk_test")
    return result, create


@pytest.mark.parametrize(
    "currency,amount,charged,refunded,units",
    [
        ("usd", "5.00", 1000, 0, 500),
        ("usd", "1.25", 1000, 0, 125),
        ("inr", "100.00", 20000, 0, 10000),
        ("jpy", "100", 200, 0, 100),
        ("usd", "5.00", 1000, 500, 500),
        ("usd", "10.00", 1000, 0, 1000),
        ("isk", "5", 1000, 0, 500),
        ("ugx", "5", 1000, 0, 500),
        ("huf", "5.25", 1000, 0, 525),
        ("twd", "5.25", 1000, 0, 525),
    ],
)
def test_refund_uses_payment_currency_and_remaining_balance(
    monkeypatch, currency, amount, charged, refunded, units
):
    result, create = refund(monkeypatch, amount, currency, charged, refunded)
    assert result == {
        "success": True,
        "refund_id": "re_test",
        "payment_id": "pi_test",
        "amount": float(amount),
        "status": "succeeded",
    }
    assert create.call_args.kwargs["amount"] == units
    assert create.call_args.kwargs["idempotency_key"] == "refund-test"


@pytest.mark.parametrize(
    "amount,currency,charged,refunded,message",
    [
        ("1.5", "jpy", 1000, 0, "fractional"),
        ("1.001", "usd", 1000, 0, "fractional"),
        ("0", "usd", 1000, 0, "greater than zero"),
        ("-1", "usd", 1000, 0, "greater than zero"),
        ("11", "usd", 1000, 0, "remaining refundable balance"),
        ("6", "usd", 1000, 500, "remaining refundable balance"),
        ("1.5", "isk", 1000, 0, "whole currency unit"),
        ("1", "xxx", 1000, 0, "Unsupported refund currency"),
    ],
)
def test_invalid_refund_does_not_call_stripe_create(
    monkeypatch, amount, currency, charged, refunded, message
):
    create = Mock()
    monkeypatch.setattr(
        stripe.PaymentIntent,
        "retrieve",
        Mock(
            return_value=SimpleNamespace(
                currency=currency,
                latest_charge=SimpleNamespace(amount=charged, amount_refunded=refunded),
            )
        ),
    )
    monkeypatch.setattr(stripe.Refund, "create", create)
    with pytest.raises(ValueError, match=message):
        asyncio.run(
            StripeConnector().execute(
                "refund_payment",
                {"api_key": "sk_test"},
                {"payment_id": "pi_test", "amount": amount, "idempotency_key": "refund-test"},
            )
        )
    create.assert_not_called()


@pytest.mark.parametrize("operation", ["retrieve", "create"])
def test_stripe_api_failure(monkeypatch, operation):
    monkeypatch.setattr(
        stripe.PaymentIntent,
        "retrieve",
        Mock(
            return_value=SimpleNamespace(
                currency="usd",
                latest_charge=SimpleNamespace(amount=1000, amount_refunded=0),
            )
        ),
    )
    monkeypatch.setattr(
        stripe.Refund, "create", Mock(return_value=SimpleNamespace(id="re", status="succeeded"))
    )
    target = stripe.PaymentIntent if operation == "retrieve" else stripe.Refund
    method = "retrieve" if operation == "retrieve" else "create"
    monkeypatch.setattr(target, method, Mock(side_effect=stripe.StripeError("API unavailable")))
    with pytest.raises(ValueError, match="API unavailable"):
        asyncio.run(
            StripeConnector().execute(
                "refund_payment",
                {"api_key": "sk_test"},
                {"payment_id": "pi_test", "amount": "1", "idempotency_key": "refund-test"},
            )
        )


@pytest.mark.parametrize("key", [None, "", " ", "x" * 256])
def test_refund_rejects_missing_or_invalid_idempotency_key(monkeypatch, key):
    retrieve = Mock()
    create = Mock()
    monkeypatch.setattr(stripe.PaymentIntent, "retrieve", retrieve)
    monkeypatch.setattr(stripe.Refund, "create", create)

    with pytest.raises(ValueError, match="idempotency key"):
        asyncio.run(
            StripeConnector().execute(
                "refund_payment",
                {"api_key": "sk_test"},
                {"payment_id": "pi_test", "amount": "1", "idempotency_key": key},
            )
        )

    retrieve.assert_not_called()
    create.assert_not_called()
