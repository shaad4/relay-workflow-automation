import grpc

from app.config import grpc_bind_address
from app.grpc.auth_server import AuthInternalService
from app.grpc.generated.auth import auth_pb2_grpc


async def start_grpc_server():
    server = grpc.aio.server()

    auth_pb2_grpc.add_AuthInternalServiceServicer_to_server(
        AuthInternalService(),
        server,
    )

    port = server.add_insecure_port(grpc_bind_address(50051))
    if port == 0:
        raise RuntimeError("Failed to bind internal gRPC port")

    await server.start()

    return server
