import grpc

from app.grpc.generated.integration import webhook_lifecycle_pb2_grpc
from app.grpc.webhook_lifecycle_server import IntegrationInternalService


async def start_grpc_server():
    server = grpc.aio.server()
    webhook_lifecycle_pb2_grpc.add_IntegrationInternalServiceServicer_to_server(
        IntegrationInternalService(),
        server,
    )
    server.add_insecure_port("[::]:50053")
    await server.start()
    return server
