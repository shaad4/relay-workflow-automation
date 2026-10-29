import grpc

from app.config import grpc_bind_address
from app.grpc.generated.integration import webhook_lifecycle_pb2_grpc
from app.grpc.webhook_lifecycle_server import IntegrationInternalService


async def start_grpc_server():
    server = grpc.aio.server()
    webhook_lifecycle_pb2_grpc.add_IntegrationInternalServiceServicer_to_server(
        IntegrationInternalService(),
        server,
    )
    port = server.add_insecure_port(grpc_bind_address(50053))
    if port == 0:
        raise RuntimeError("Failed to bind internal gRPC port")
    await server.start()
    return server
