import grpc

from app.config import grpc_bind_address
from app.grpc.action_server import ActionInternalService
from app.grpc.generated.action import action_pb2_grpc


async def start_grpc_server():
    server = grpc.aio.server()

    action_pb2_grpc.add_ActionInternalServiceServicer_to_server(
        ActionInternalService(),
        server,
    )

    port = server.add_insecure_port(grpc_bind_address(50054))
    if port == 0:
        raise RuntimeError("Failed to bind internal gRPC port")

    await server.start()

    return server
