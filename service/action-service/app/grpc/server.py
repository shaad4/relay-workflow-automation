import grpc

from app.grpc.action_server import ActionInternalService
from app.grpc.generated.action import action_pb2_grpc


async def start_grpc_server():
    server = grpc.aio.server()

    action_pb2_grpc.add_ActionInternalServiceServicer_to_server(
        ActionInternalService(),
        server,
    )

    server.add_insecure_port("[::]:50054")

    await server.start()

    return server