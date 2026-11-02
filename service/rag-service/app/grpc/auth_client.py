import grpc

from app.config import grpc_target
from app.grpc.generated.auth import auth_pb2, auth_pb2_grpc

AUTH_GRPC_TARGET = grpc_target("AUTH_GRPC_URL", "auth-service:50051", "AUTH_GRPC_TARGET")


class AuthGrpcClient:
    def __init__(self):
        self.channel = grpc.aio.insecure_channel(AUTH_GRPC_TARGET)

        self.stub = auth_pb2_grpc.AuthInternalServiceStub(self.channel)

    async def validate_token(self, token: str):
        request = auth_pb2.ValidateTokenRequest(access_token=token)

        return await self.stub.ValidateToken(
            request,
            timeout=5,
        )

    async def close(self):
        await self.channel.close()
