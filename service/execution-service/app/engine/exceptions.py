class HumanApprovalRequired(Exception):
    def __init__(self, node_id: str):
        self.node_id = node_id
        super().__init__(
            f"Human approval required for node: {node_id}"
        )