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
    ):
        self.node_id = node_id
        self.error = error

        super().__init__(
            f"Action node {node_id} failed: {error}"
        )