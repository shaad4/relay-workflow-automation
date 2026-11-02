from urllib.parse import quote

from relay_session import RelaySession


def path_segment(value):
    value = str(value)
    if (
        value in {"", ".", ".."}
        or any(c in value for c in "/\\%?#")
        or any(ord(c) < 32 for c in value)
    ):
        raise ValueError("Invalid resource identifier")
    return quote(value, safe="")


class RelayClient:
    def __init__(self, session: RelaySession):
        self.session = session

    async def get_node_schema(self, node_type: str | None = None):
        response = await self.session.request(
            "GET", "/workflows/node-types/", params={"node_type": node_type} if node_type else {}
        )
        return response.json()

    async def validate_workflow_definition(self, nodes, edges, sample_input=None):
        response = await self.session.request(
            "POST",
            "/workflows/validate-definition/",
            json={"nodes": nodes, "edges": edges, "sample_input": sample_input},
        )
        return response.json()

    async def list_ai_models(self, connection_id: str):
        response = await self.session.get(f"/ai/connections/{path_segment(connection_id)}/models/")
        return {
            "connection_id": connection_id,
            "models": [
                {"id": model["id"], "name": model.get("name", model["id"])}
                for model in response.json()["models"]
            ],
        }

    # Connection Discovery

    async def _list_connections(self, path: str, provider: str | None):
        response = await self.session.get(path)
        connections = response.json()
        provider = provider.strip().casefold() if provider else ""
        if provider:
            connections = [
                connection
                for connection in connections
                if connection["provider"].casefold() == provider
            ]
        return connections

    async def list_connections(self, provider: str | None = None):
        connections = await self._list_connections("/connections/", provider)
        results = []
        for connection in connections:
            # Config can contain credentials. Only expose the Gmail account label.
            email = None
            if connection["provider"].casefold() == "gmail":
                email = (connection.get("config") or {}).get("email")
            results.append(
                {
                    "id": connection["id"],
                    "name": connection["name"],
                    "provider": connection["provider"],
                    "auth_type": connection["auth_type"],
                    "email": email if isinstance(email, str) else None,
                    "status": "configured",
                }
            )
        return results

    async def list_ai_provider_connections(self, provider: str | None = None):
        connections = await self._list_connections("/ai/connections/", provider)
        # Use an allowlist for both transports, even if the upstream schema expands.
        return [
            {key: connection[key] for key in ("id", "name", "provider", "status")}
            for connection in connections
        ]

    # Workflow Management

    async def list_workflows(self):
        response = await self.session.get("/workflows/")
        return response.json()

    async def create_workflow(
        self,
        name: str,
        description: str = "",
    ):
        response = await self.session.request(
            "POST",
            "/workflows/",
            json={
                "name": name,
                "description": description,
            },
        )
        return response.json()

    async def deactivate_workflow(self, workflow_id: str):
        response = await self.session.request(
            "POST",
            f"/workflows/{path_segment(workflow_id)}/deactivate/",
        )
        return response.json()

    async def delete_workflow(self, workflow_id: str):
        await self.session.request(
            "DELETE",
            f"/workflows/{path_segment(workflow_id)}/",
        )
        return {
            "success": True,
            "deleted_workflow_id": workflow_id,
        }

    # Node Management

    async def add_node(
        self,
        workflow_id: str,
        version: int,
        node_id: str,
        node_type: str,
        configuration: dict,
    ):
        response = await self.session.request(
            "POST",
            f"/workflows/{path_segment(workflow_id)}/versions/{version}/nodes/",
            json={
                "node_id": node_id,
                "node_type": node_type,
                "configuration": configuration,
                "position_x": 250,
                "position_y": 150,
            },
        )
        return response.json()

    async def update_node(
        self,
        workflow_id: str,
        version: int,
        node_id: str,
        configuration: dict,
    ):
        response = await self.session.request(
            "PATCH",
            f"/workflows/{path_segment(workflow_id)}/versions/{version}/nodes/{path_segment(node_id)}/",
            json={
                "configuration": configuration,
            },
        )
        return response.json()

    async def delete_node(
        self,
        workflow_id: str,
        version: int,
        node_id: str,
    ):
        await self.session.request(
            "DELETE",
            f"/workflows/{path_segment(workflow_id)}/versions/{version}/nodes/{path_segment(node_id)}/",
        )
        return {
            "success": True,
            "deleted_node_id": node_id,
        }

    # Edge Management

    async def add_edge(
        self,
        workflow_id: str,
        version: int,
        source_node_id: str,
        target_node_id: str,
        condition: str | None = None,
    ):
        response = await self.session.request(
            "POST",
            f"/workflows/{path_segment(workflow_id)}/versions/{version}/edges/",
            json={
                "source_node_id": source_node_id,
                "target_node_id": target_node_id,
                "condition": condition,
            },
        )
        return response.json()

    async def delete_edge(
        self,
        workflow_id: str,
        version: int,
        edge_id: str,
    ):
        await self.session.request(
            "DELETE",
            f"/workflows/{path_segment(workflow_id)}/versions/{version}/edges/{path_segment(edge_id)}/",
        )
        return {
            "success": True,
            "deleted_edge_id": edge_id,
        }

    # Validation and Publishing

    async def validate_workflow(
        self,
        workflow_id: str,
        version: int,
    ):
        response = await self.session.request(
            "POST",
            f"/workflows/{path_segment(workflow_id)}/versions/{version}/validate/",
        )
        return response.json()

    async def publish_workflow(
        self,
        workflow_id: str,
        version: int,
    ):
        response = await self.session.request(
            "POST",
            f"/workflows/{path_segment(workflow_id)}/versions/{version}/publish/",
        )
        return response.json()

    # Workflow Execution

    async def run_workflow(
        self,
        workflow_id: str,
        input_data: dict,
    ):
        response = await self.session.request(
            "POST",
            f"/workflows/{path_segment(workflow_id)}/run",
            json={
                "input": input_data,
            },
        )
        return response.json()

    # Execution History

    async def list_executions(self, page: int = 1):
        response = await self.session.request(
            "GET",
            "/executions/",
            params={
                "page": page,
                "page_size": 10,
            },
        )
        return response.json()

    async def get_execution_steps(self, execution_id: str):
        response = await self.session.request(
            "GET",
            f"/executions/{path_segment(execution_id)}/steps/",
        )
        return response.json()
