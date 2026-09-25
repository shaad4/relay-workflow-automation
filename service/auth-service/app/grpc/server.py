import grpc

from app.grpc.auth_server import AuthInternalService
from app.grpc.generated.auth import auth_pb2_grpc


async def start_grpc_server():
    server = grpc.aio.server()

    auth_pb2_grpc.add_AuthInternalServiceServicer_to_server(
        AuthInternalService(),
        server,
    )

    server.add_insecure_port("[::]:50051")

    await server.start()

    return server