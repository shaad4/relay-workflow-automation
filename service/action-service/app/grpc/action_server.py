import asyncio
import errno
import json
import os
import socket
from uuid import UUID

import httpx

from app.connectors.registry import connector_registry
from app.core.encryption import CredentialEncryption
from app.db.database import AsyncSessionLocal
from app.grpc.generated.action import action_pb2, action_pb2_grpc
from app.services.connection_service import get_connection

MAX_CONCURRENT_HTTP_REQUESTS = int(os.getenv("MAX_CONCURRENT_HTTP_REQUESTS", "10"))


class ActionInternalService(action_pb2_grpc.ActionInternalServiceServicer):
    def __init__(self):
        if MAX_CONCURRENT_HTTP_REQUESTS < 1:
            raise ValueError("MAX_CONCURRENT_HTTP_REQUESTS must be positive")

        self.http_semaphore = asyncio.Semaphore(MAX_CONCURRENT_HTTP_REQUESTS)

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

            # Decrypt credentials once.
            credential = None

            if connection.credential:
                encryption = CredentialEncryption()
                credential = encryption.decrypt(connection.credential)

            config = {}

            if request.config_json:
                config = json.loads(request.config_json)

            input_data = {}

            if request.input_data_json:
                input_data = json.loads(request.input_data_json)

            # Gmail OAuth2 authentication.
            if connection.auth_type == "oauth2":
                if credential:
                    config["refresh_token"] = credential

            # HTTP connector authentication.
            if connection.provider == "http":
                if connection.auth_type == "bearer":
                    if not credential:
                        raise ValueError("Credential is required for bearer authentication")

                    headers = input_data.get("headers") or {}

                    headers["Authorization"] = f"Bearer {credential}"

                    input_data["headers"] = headers

                elif connection.auth_type == "api_key_header":
                    if not credential:
                        raise ValueError("Credential is required for api_key_header authentication")

                    auth_header = (connection.config or {}).get("auth_header")

                    if not auth_header:
                        raise ValueError("config.auth_header is required for api_key_header")

                    headers = input_data.get("headers") or {}
                    headers[auth_header] = credential
                    input_data["headers"] = headers

                elif connection.auth_type == "api_key_query":
                    if not credential:
                        raise ValueError("Credential is required for api_key_query authentication")

                    auth_param = (connection.config or {}).get("auth_param")

                    if not auth_param:
                        raise ValueError("config.auth_param is required for api_key_query")

                    params = input_data.get("params") or {}
                    params[auth_param] = credential
                    input_data["params"] = params

            # Stripe connector authentication.
            if connection.provider == "stripe":
                if connection.auth_type != "api_key":
                    raise ValueError("Stripe connection requires api_key authentication")

                if not credential:
                    raise ValueError("Stripe API key is required")

                config["api_key"] = credential

            # Resolve connector.
            connector = connector_registry.get(connection.provider)

            # Limit only concurrent HTTP connector calls.
            if connection.provider == "http":
                async with self.http_semaphore:
                    result = await connector.execute(
                        action=request.action,
                        config=config,
                        input_data=input_data,
                    )

            else:
                result = await connector.execute(
                    action=request.action,
                    config=config,
                    input_data=input_data,
                )

            # Check HTTP-level success separately.
            if connection.provider == "http":
                if not result.get("success", False):
                    status_code = result.get("status_code")

                    return action_pb2.ExecuteActionResponse(
                        success=False,
                        result_json=json.dumps({"status_code": status_code}),
                        error=(f"HTTP request failed with status {status_code}"),
                    )

            return action_pb2.ExecuteActionResponse(
                success=True,
                result_json=json.dumps(result),
            )

        # HTTP request timeout.
        except httpx.TimeoutException as exc:
            if isinstance(exc, httpx.ConnectTimeout):
                error_code = "HTTP_CONNECT_TIMEOUT"

            elif isinstance(exc, httpx.ReadTimeout):
                error_code = "HTTP_READ_TIMEOUT"

            else:
                error_code = "HTTP_TIMEOUT"

            return action_pb2.ExecuteActionResponse(
                success=False,
                error="HTTP_TIMEOUT",
                result_json=json.dumps({"error_code": error_code}),
            )

        # HTTP connection failure.
        except httpx.ConnectError as exc:
            category = "HTTP_CONNECTION_ERROR"
            cause = exc
            seen = set()

            while cause is not None and id(cause) not in seen:
                seen.add(id(cause))

                if isinstance(cause, socket.gaierror):
                    category = "HTTP_DNS_FAILURE"
                    break

                if isinstance(cause, OSError) and cause.errno == errno.ECONNREFUSED:
                    category = "HTTP_CONNECTION_REFUSED"
                    break

                cause = cause.__cause__ or cause.__context__

            return action_pb2.ExecuteActionResponse(
                success=False,
                error="HTTP_CONNECTION_ERROR",
                result_json=json.dumps({"error_code": category}),
            )

        except json.JSONDecodeError:
            return action_pb2.ExecuteActionResponse(
                success=False,
                error="Invalid JSON payload",
            )

        except ValueError:
            return action_pb2.ExecuteActionResponse(
                success=False,
                error="Invalid action configuration or credentials",
            )

        except Exception:
            return action_pb2.ExecuteActionResponse(
                success=False,
                error="Action execution failed",
            )
