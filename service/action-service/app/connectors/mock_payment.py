from uuid import uuid4

from app.connectors.base import Connector


class MockPaymentConnector(Connector):

    async def execute(
        self,
        action: str,
        config: dict,
        input_data: dict,
    ) -> dict:

        if action != "refund_payment":
            raise ValueError(
                f"Unsupported payment action: {action}"
            )

        payment_id = input_data.get("payment_id")
        amount = input_data.get("amount")

        if not payment_id:
            raise ValueError("Payment ID is required")

        if amount is None:
            raise ValueError("Refund amount is required")

        refund_id = str(uuid4())

        return {
            "success": True,
            "refund_id": refund_id,
            "payment_id": payment_id,
            "amount": amount,
            "status": "refunded",
        }
    