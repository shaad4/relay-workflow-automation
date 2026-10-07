from decimal import Decimal, InvalidOperation
from typing import Any

import stripe

from app.connectors.base import Connector


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

        if amount_decimal <= 0:
            raise ValueError("Refund amount must be greater than zero")

        # Stripe expects amounts in the currency's smallest unit.
        # Example: 12.50 USD -> 1250 cents.
        amount_smallest_unit = int(amount_decimal * 100)

        try:
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