import grpc

from app.grpc.generated.action import action_pb2
from app.grpc.generated.action import action_pb2_grpc


ACTION_SERVICE_ADDRESS = "action-service:50054"


class ActionClient:

    def __init__(self):
        self.channel = grpc.aio.insecure_channel(
            ACTION_SERVICE_ADDRESS
        )

        self.stub = (
            action_pb2_grpc.ActionInternalServiceStub(
                self.channel
            )
        )

    async def execute_action(
        self,
        workspace_id: str,
        connection_id: str,
        provider: str,
        action: str,
        config_json: str = "",
        input_data_json: str = "",
    ):
        request = action_pb2.ExecuteActionRequest(
            workspace_id=workspace_id,
            connection_id=connection_id,
            provider=provider,
            action=action,
            config_json=config_json,
            input_data_json=input_data_json,
        )

        return await self.stub.ExecuteAction(
            request
        )

    async def close(self):
        await self.channel.close()