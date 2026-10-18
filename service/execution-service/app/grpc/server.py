import grpc

from app.grpc.generated.execution import approval_lifecycle_pb2_grpc
from app.grpc.execution_server import ExecutionInternalService


async def start_grpc_server():
    server = grpc.aio.server()
    approval_lifecycle_pb2_grpc.add_ExecutionInternalServiceServicer_to_server(
        ExecutionInternalService(), server,
    )
    server.add_insecure_port("[::]:50055")
    await server.start()
    return server
