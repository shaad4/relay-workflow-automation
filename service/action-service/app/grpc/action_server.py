import json
from uuid import UUID

import grpc

from app.connectors.registry import connector_registry
from app.db.database import AsyncSessionLocal
from app.grpc.generated.action import action_pb2, action_pb2_grpc
from app.services.connection_service import get_connection


class ActionInternalService(
    action_pb2_grpc.ActionInternalServiceServicer
):

    async def ExecuteAction(
        self,
        request,
        context,
    ):
        try:
            workspace_id = UUID(request.workspace_id)
            connection_id = UUID(request.connection_id)

            async with AsyncSessionLocal() as session:
                connection = await get_connection(
                    connection_id=connection_id,
                    workspace_id=workspace_id,
                    session=session,
                )

            if connection is None:
                return action_pb2.ExecuteActionResponse(
                    success=False,
                    error="Connection not found",
                )

            config = {}

            if request.config_json:
                config = json.loads(request.config_json)

            input_data = {}

            if request.input_data_json:
                input_data = json.loads(request.input_data_json)

            if connection.auth_type == "oauth2":
                if connection.credential:
                    config["refresh_token"] = connection.credential

            if connection.provider == "http":
                if connection.auth_type == "bearer":
                    if not connection.credential:
                        raise ValueError(
                            "Credential is required for bearer authentication"
                        )

                    headers = input_data.get("headers") or {}
                    headers["Authorization"] = (
                        f"Bearer {connection.credential}"
                    )
                    input_data["headers"] = headers

                elif connection.auth_type == "api_key_header":
                    if not connection.credential:
                        raise ValueError(
                            "Credential is required for api_key_header authentication"
                        )

                    auth_header = (connection.config or {}).get("auth_header")

                    if not auth_header:
                        raise ValueError(
                            "config.auth_header is required for api_key_header"
                        )

                    headers = input_data.get("headers") or {}
                    headers[auth_header] = connection.credential
                    input_data["headers"] = headers

                elif connection.auth_type == "api_key_query":
                    if not connection.credential:
                        raise ValueError(
                            "Credential is required for api_key_query authentication"
                        )

                    auth_param = (connection.config or {}).get("auth_param")

                    if not auth_param:
                        raise ValueError(
                            "config.auth_param is required for api_key_query"
                        )

                    params = input_data.get("params") or {}
                    params[auth_param] = connection.credential
                    input_data["params"] = params

            if connection.provider == "stripe":
                if connection.auth_type != "api_key":
                    raise ValueError(
                        "Stripe connection requires api_key authentication"
                    )

                if not connection.credential:
                    raise ValueError(
                        "Stripe API key is required"
                    )

                config["api_key"] = connection.credential

            connector = connector_registry.get(
                connection.provider
            )

            result = await connector.execute(
                action=request.action,
                config=config,
                input_data=input_data,
            )

            return action_pb2.ExecuteActionResponse(
                success=True,
                result_json=json.dumps(result),
            )

        except ValueError as exc:
            return action_pb2.ExecuteActionResponse(
                success=False,
                error=str(exc),
            )

        except json.JSONDecodeError:
            return action_pb2.ExecuteActionResponse(
                success=False,
                error="Invalid JSON payload",
            )

        except Exception as exc:
            return action_pb2.ExecuteActionResponse(
                success=False,
                error=f"Action execution failed: {exc}",
            )