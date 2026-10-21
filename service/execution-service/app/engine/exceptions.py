class HumanApprovalRequired(Exception):
    def __init__(self, node_id: str):
        self.node_id = node_id
        super().__init__(
            f"Human approval required for node: {node_id}"
        )

class ActionExecutionFailed(Exception):
    def __init__(
        self,
        node_id: str,
        error: str,
        retryable: bool = False,
        status_code: int | None = None,
    ):
        self.node_id = node_id
        self.error = error
        self.retryable = retryable
        self.status_code = status_code

        super().__init__(
            f"Action node {node_id} failed: {error}"
        )

class RetryExhaustedError(Exception):
    def __init__(self, attempts_used: int):
        self.attempts_used = attempts_used
        super().__init__("Retry attempts exhausted")