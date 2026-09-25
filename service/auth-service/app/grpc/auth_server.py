import jwt

from sqlalchemy import select

from app.core.jwt import decode_token
from app.db.database import AsyncSessionLocal
from app.models import User
from app.grpc.generated.auth import auth_pb2
from app.grpc.generated.auth import auth_pb2_grpc

class AuthInternalService(auth_pb2_grpc.AuthInternalServiceServicer):

    async def ValidateToken(self, request, context):
        try:
            payload = decode_token(request.access_token)

            if payload.get("type") != "access":
                return auth_pb2.ValidateTokenResponse(
                    valid=False,
                    user_id="",
                    workspace_id="",
                )

            user_id = payload.get("sub")
            workspace_id = payload.get("workspace_id")

            if not user_id or not workspace_id:
                return auth_pb2.ValidateTokenResponse(
                    valid=False,
                    user_id="",
                    workspace_id="",
                )

            return auth_pb2.ValidateTokenResponse(
                valid=True,
                user_id=user_id,
                workspace_id=workspace_id,
            )

        except jwt.InvalidTokenError:
            return auth_pb2.ValidateTokenResponse(
                valid=False,
                user_id="",
                workspace_id="",
            )

    async def ResolveWorkspace(self, request, context):
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).where(User.id == request.user_id)
            )

            user = result.scalar_one_or_none()

            if not user:
                return auth_pb2.ResolveWorkspaceResponse(
                    found=False,
                    workspace_id="",
                )

            return auth_pb2.ResolveWorkspaceResponse(
                found=True,
                workspace_id=str(user.workspace_id),
            )