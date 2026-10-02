import grpc

from app.grpc.generated.auth import auth_pb2
from app.grpc.generated.auth import auth_pb2_grpc


AUTH_GRPC_URL = "auth-service:50051"


class AuthGrpcClient:
    def __init__(self):
        self.channel = grpc.aio.insecure_channel(AUTH_GRPC_URL)
        self.stub = auth_pb2_grpc.AuthInternalServiceStub(self.channel)

    async def validate_token(self, access_token: str):
        request = auth_pb2.ValidateTokenRequest(
            access_token=access_token,
        )

        return await self.stub.ValidateToken(request)

    async def resolve_workspace(self, user_id: str):
        request = auth_pb2.ResolveWorkspaceRequest(
            user_id=user_id,
        )

        return await self.stub.ResolveWorkspace(request)

    async def close(self):
        await self.channel.close()