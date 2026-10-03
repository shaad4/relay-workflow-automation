from app.connectors.base import Connector


class GmailConnector(Connector):

    async def execute(
        self,
        action: str,
        config: dict,
        input_data: dict,
    ) -> dict:

        if action != "send_email":
            raise ValueError(f"Unsupported Gmail action: {action}")

        # Gmail API implementation will be added next.
        raise NotImplementedError("Gmail connector is not implemented yet")