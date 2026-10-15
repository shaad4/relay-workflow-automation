from decimal import Decimal, InvalidOperation
from typing import Any

import stripe

from app.connectors.base import Connector


ZERO_DECIMAL_CURRENCIES = {
    "bif", "clp", "djf", "gnf", "jpy", "kmf", "krw", "mga", "pyg",
    "rwf", "vnd", "vuv", "xaf", "xof", "xpf",
}
TWO_DECIMAL_CURRENCIES = {"usd", "inr", "huf", "twd"}
WHOLE_AMOUNT_TWO_DECIMAL_CURRENCIES = {"isk", "ugx"}


class StripeConnector(Connector):

    async def execute(
        self,
        action: str,
        config: dict[str, Any],
        input_data: dict[str, Any],
    ) -> dict[str, Any]:

        if action != "refund_payment":
            raise ValueError(
                f"Unsupported Stripe action: {action}"
            )

        api_key = config.get("api_key")
        payment_id = input_data.get("payment_id")
        amount = input_data.get("amount")

        if not api_key:
            raise ValueError("Stripe API key is required")

        if not payment_id:
            raise ValueError("Payment ID is required")

        if amount is None:
            raise ValueError("Refund amount is required")

        try:
            amount_decimal = Decimal(str(amount))
        except (InvalidOperation, ValueError):
            raise ValueError("Refund amount must be a valid number")

        if not amount_decimal.is_finite() or amount_decimal <= 0:
            raise ValueError("Refund amount must be greater than zero")

        try:
            payment = stripe.PaymentIntent.retrieve(
                payment_id, expand=["latest_charge"], api_key=api_key,
            )
            currency = payment.currency.lower()
            charge = payment.latest_charge
            if not charge or isinstance(charge, str):
                raise ValueError("Payment has no refundable charge")
            if currency not in (ZERO_DECIMAL_CURRENCIES | TWO_DECIMAL_CURRENCIES | WHOLE_AMOUNT_TWO_DECIMAL_CURRENCIES):
                raise ValueError(f"Unsupported refund currency: {currency}")
            if currency in WHOLE_AMOUNT_TWO_DECIMAL_CURRENCIES and amount_decimal != amount_decimal.to_integral_value():
                raise ValueError("Refund amount must be a whole currency unit")
            multiplier = 1 if currency in ZERO_DECIMAL_CURRENCIES else 100
            units = amount_decimal * multiplier
            if units != units.to_integral_value():
                raise ValueError("Refund amount has invalid fractional units")
            amount_smallest_unit = int(units)
            remaining = charge.amount - charge.amount_refunded
            if amount_smallest_unit > remaining or remaining <= 0:
                raise ValueError("Refund amount exceeds remaining refundable balance")

            refund = stripe.Refund.create(
                payment_intent=payment_id,
                amount=amount_smallest_unit,
                api_key=api_key,
            )

        except stripe.StripeError as exc:
            message = (
                getattr(exc, "user_message", None)
                or str(exc)
                or "Stripe refund failed"
            )

            raise ValueError(message) from exc

        return {
            "success": True,
            "refund_id": refund.id,
            "payment_id": payment_id,
            "amount": float(amount_decimal),
            "status": refund.status,
        }
