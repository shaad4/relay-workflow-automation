
"""Safe failure descriptions. This module never makes retry decisions."""

import json

import grpc

from app.ai.exceptions import (
    AIAuthenticationError,
    AIRateLimitError,
    AITimeoutError,
    AIServiceUnavailableError,
    AIResponseError,
    AIDecisionValidationError,
)
from app.engine.exceptions import ActionExecutionFailed


HTTP = {
    400: (
        "BAD_REQUEST",
        "Check the request parameters.",
    ),
    401: (
        "UNAUTHORIZED",
        "Check the API credentials in the connection.",
    ),
    403: (
        "FORBIDDEN",
        "Check the connection's access permissions.",
    ),
    404: (
        "NOT_FOUND",
        "Check the endpoint URL.",
    ),
    408: (
        "TIMEOUT",
        "Check the external API availability.",
    ),
    429: (
        "RATE_LIMITED",
        "Wait before retrying and check the API usage limits.",
    ),
    500: (
        "SERVER_ERROR",
        "Check the external service availability.",
    ),
    502: (
        "BAD_GATEWAY",
        "Try again after the external service recovers.",
    ),
    503: (
        "SERVICE_UNAVAILABLE",
        "Wait for the external API to recover, then use Replay Execution to retry the failed step. Replay remains subject to safety checks.",
    ),
    504: (
        "GATEWAY_TIMEOUT",
        "Try again after the external service recovers.",
    ),
}


TRANSPORT = {
    "HTTP_TIMEOUT": "The HTTP request timed out.",
    "HTTP_CONNECT_TIMEOUT": (
        "The connection to the external API timed out."
    ),
    "HTTP_READ_TIMEOUT": (
        "The external API took too long to respond."
    ),
    "HTTP_CONNECTION_REFUSED": (
        "The external API refused the connection."
    ),
    "HTTP_DNS_FAILURE": (
        "The external API hostname could not be resolved."
    ),
    "HTTP_CONNECTION_ERROR": (
        "Relay could not connect to the external API."
    ),
}


AI = [
    (
        AIDecisionValidationError,
        "AI_OUTPUT_VALIDATION_FAILED",
        "The AI response did not match the required structure.",
        False,
        "Review the output schema and node configuration.",
    ),
    (
        AIAuthenticationError,
        "AI_AUTHENTICATION_FAILED",
        "AI provider authentication failed.",
        False,
        "Check the AI connection credentials and permissions.",
    ),
    (
        AIRateLimitError,
        "AI_RATE_LIMITED",
        "The AI provider rate limit was exceeded.",
        True,
        "Wait before retrying or check your provider usage limits.",
    ),
    (
        AITimeoutError,
        "AI_TIMEOUT",
        "The AI provider request timed out.",
        True,
        "Try again later or review the request size.",
    ),
    (
        AIServiceUnavailableError,
        "AI_SERVICE_UNAVAILABLE",
        "The AI provider is temporarily unavailable.",
        True,
        "Check the provider availability and try again later.",
    ),
    (
        AIResponseError,
        "AI_INVALID_RESPONSE",
        "The AI provider returned an invalid response.",
        False,
        "Review the model and output configuration.",
    ),
]


def action_failure(
    node_id,
    response,
    *,
    retryable=False,
    attempts_used=1,
):
    """Read only allowlisted metadata from the existing gRPC envelope."""

    try:
        payload = json.loads(response.result_json or "{}")

        status = payload.get("status_code")
        category = payload.get("error_code")

    except (ValueError, TypeError, AttributeError):
        status = None
        category = None

    exc = ActionExecutionFailed(
        node_id,
        response.error or "Action execution failed",
        retryable,
        status,
    )

    exc.error_code = (
        category
        if category in TRANSPORT
        else (
            response.error
            if response.error in TRANSPORT
            else None
        )
    )

    exc.attempts_used = attempts_used

    return exc


def classify_error(
    exc,
    node_id=None,
    node_type=None,
):
    node_id = node_id or getattr(
        exc,
        "node_id",
        None,
    )

    node_type = node_type or getattr(
        exc,
        "failed_node_type",
        None,
    )

    attempts = getattr(
        exc,
        "attempts_used",
        1,
    )

    attempts = (
        attempts
        if type(attempts) is int and attempts > 0
        else 1
    )

    code = "EXECUTION_FAILED"
    message = "Node execution failed."
    temporary = False
    suggestion = (
        "Review the failed node configuration before trying again."
    )

    status = getattr(
        exc,
        "status_code",
        None,
    )

    status = (
        status
        if type(status) is int and 100 <= status <= 599
        else None
    )

    # Classify action failures.
    if isinstance(exc, ActionExecutionFailed):
        code = "ACTION_FAILED"
        message = "Action execution failed."

        if node_type == "action.http_request":

            if status is not None:
                suffix, suggestion = HTTP.get(
                    status,
                    (
                        "ERROR",
                        "Review the endpoint and external service documentation.",
                    ),
                )

                code = "HTTP_" + suffix
                message = (
                    f"The external API returned HTTP {status}."
                )

            elif getattr(exc, "error_code", None) in TRANSPORT:
                code = exc.error_code
                message = TRANSPORT[code]

                suggestion = (
                    "Check the endpoint and network availability "
                    "before trying again."
                )

            temporary = bool(exc.retryable)

    # Classify AI provider failures.
    for (
        kind,
        ai_code,
        ai_message,
        ai_temporary,
        ai_suggestion,
    ) in AI:

        if isinstance(exc, kind):
            code = ai_code
            message = ai_message
            temporary = ai_temporary
            suggestion = ai_suggestion
            break

    # Classify invalid AI node configurations.
    if (
        node_type
        and node_type.startswith("ai.")
        and isinstance(exc, ValueError)
    ):
        code = "AI_INVALID_CONFIGURATION"
        message = "The AI node configuration is invalid."

        suggestion = (
            "Review the provider, model, input mappings, "
            "and output configuration."
        )

    # Classify RAG retrieval failures.
    if node_type and "rag" in node_type:
        cause = exc
        seen = set()

        while (
            cause is not None
            and id(cause) not in seen
        ):
            seen.add(id(cause))

            if isinstance(cause, grpc.RpcError):
                mappings = {
                    grpc.StatusCode.UNAVAILABLE: (
                        "RAG_UNAVAILABLE",
                        "The retrieval service is unavailable.",
                        True,
                    ),
                    grpc.StatusCode.DEADLINE_EXCEEDED: (
                        "RAG_TIMEOUT",
                        "The retrieval request timed out.",
                        True,
                    ),
                    grpc.StatusCode.NOT_FOUND: (
                        "RAG_KNOWLEDGE_BASE_NOT_FOUND",
                        "The knowledge base was not found.",
                        False,
                    ),
                    grpc.StatusCode.INVALID_ARGUMENT: (
                        "RAG_INVALID_QUERY",
                        "The retrieval request is invalid.",
                        False,
                    ),
                    grpc.StatusCode.PERMISSION_DENIED: (
                        "RAG_PERMISSION_DENIED",
                        "Access to the knowledge base was denied.",
                        False,
                    ),
                }

                code, message, temporary = mappings.get(
                    cause.code(),
                    (
                        "RAG_FAILED",
                        "Knowledge retrieval failed.",
                        False,
                    ),
                )

                suggestion = (
                    "Try again after the retrieval service recovers."
                    if temporary
                    else (
                        "Check knowledge base access "
                        "and retrieval configuration."
                    )
                )

                break

            cause = cause.__cause__

        else:
            if isinstance(exc, ValueError):
                code = "RAG_INVALID_CONFIGURATION"
                message = "The retrieval configuration is invalid."

                suggestion = (
                    "Check the knowledge base, query, "
                    "and result limit."
                )

                if str(exc) in {
                    "RAG query cannot be empty",
                    "RAG query cannot exceed 2000 characters",
                    "RAG query must be a string",
                    "RAG query contains unresolved expressions",
                }:
                    code = "RAG_INVALID_QUERY"
                    message = (
                        "The retrieval query is empty or too long."
                    )

    # Determine whether the failure is temporary.
    is_temporary = temporary

    if node_type == "action.http_request":
        is_temporary = (
            status in {408, 429, 500, 502, 503, 504}
            or code in TRANSPORT
        )

    from app.engine.retry import MAX_ATTEMPTS

    # Reporting only: the retry helper remains the sole retry-policy owner.
    # Build the sanitized error response.
    result = {
        "temporary": is_temporary,
        "code": code,
        "message": message,
        "retryable": temporary,
        "attempts_used": attempts,
        "automatic_retries_exhausted": temporary and attempts >= MAX_ATTEMPTS,
        "suggestion": suggestion,
    }

    if node_id:
        result["node_id"] = node_id

    if node_type:
        result["node_type"] = node_type

    if (
        status is not None
        and node_type == "action.http_request"
    ):
        result["status_code"] = status

    return result
