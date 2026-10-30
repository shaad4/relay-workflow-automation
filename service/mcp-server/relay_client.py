import httpx


class RelayClient:
    def __init__(self, base_url: str, access_token: str):
        self.base_url = base_url.rstrip("/")
        self.access_token = access_token

    async def list_workflows(self):
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{self.base_url}/workflows/",
                headers={
                    "Authorization": f"Bearer {self.access_token}"
                },
            )

            response.raise_for_status()
            return response.json()

    async def create_workflow(
        self,
        name: str,
        description: str = "",
    ):
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{self.base_url}/workflows/",
                headers={
                    "Authorization": f"Bearer {self.access_token}"
                },
                json={
                    "name": name,
                    "description": description,
                },
            )

            response.raise_for_status()
            return response.json()


    async def add_node(
        self,
        workflow_id: str,
        version: int,
        node_id: str,
        node_type: str,
        configuration: dict,
    ):
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{self.base_url}/workflows/{workflow_id}/versions/{version}/nodes/",
                headers={
                    "Authorization": f"Bearer {self.access_token}"
                },
                json={
                    "node_id": node_id,
                    "node_type": node_type,
                    "configuration": configuration,
                    "position_x": 250,
                    "position_y": 150,
                },
            )

            response.raise_for_status()
            return response.json()

    async def update_node(
        self,
        workflow_id: str,
        version: int,
        node_id: str,
        configuration: dict,
    ):
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.patch(
                f"{self.base_url}/workflows/{workflow_id}/versions/{version}/nodes/{node_id}/",
                headers={
                    "Authorization": f"Bearer {self.access_token}"
                },
                json={"configuration": configuration},
            )

            response.raise_for_status()
            return response.json()

    async def delete_node(
        self,
        workflow_id: str,
        version: int,
        node_id: str,
    ):
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.delete(
                f"{self.base_url}/workflows/{workflow_id}/versions/{version}/nodes/{node_id}/",
                headers={
                    "Authorization": f"Bearer {self.access_token}"
                },
            )

            response.raise_for_status()

            return {
                "success": True,
                "deleted_node_id": node_id,
            }

    async def add_edge(
        self,
        workflow_id: str,
        version: int,
        source_node_id: str,
        target_node_id: str,
    ):
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{self.base_url}/workflows/{workflow_id}/versions/{version}/edges/",
                headers={
                    "Authorization": f"Bearer {self.access_token}"
                },
                json={
                    "source_node_id": source_node_id,
                    "target_node_id": target_node_id,
                },
            )

            response.raise_for_status()
            return response.json()

    async def delete_edge(
        self,
        workflow_id: str,
        version: int,
        edge_id: str,
    ):
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.delete(
                f"{self.base_url}/workflows/{workflow_id}/versions/{version}/edges/{edge_id}/",
                headers={
                    "Authorization": f"Bearer {self.access_token}"
                },
            )

            response.raise_for_status()

            return {
                "success": True,
                "deleted_edge_id": edge_id,
            }


    async def validate_workflow(
        self,
        workflow_id: str,
        version: int,
    ):
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{self.base_url}/workflows/{workflow_id}/versions/{version}/validate/",
                headers={
                    "Authorization": f"Bearer {self.access_token}"
                },
            )

            response.raise_for_status()
            return response.json()

    async def publish_workflow(
        self,
        workflow_id: str,
        version: int,
    ):
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{self.base_url}/workflows/{workflow_id}/versions/{version}/publish/",
                headers={
                    "Authorization": f"Bearer {self.access_token}"
                },
            )

            response.raise_for_status()
            return response.json()

    async def deactivate_workflow(self, workflow_id: str):
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{self.base_url}/workflows/{workflow_id}/deactivate/",
                headers={
                    "Authorization": f"Bearer {self.access_token}"
                },
            )
            response.raise_for_status()
            return response.json()


    async def delete_workflow(self, workflow_id: str):
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.delete(
                f"{self.base_url}/workflows/{workflow_id}/",
                headers={
                    "Authorization": f"Bearer {self.access_token}"
                },
            )
            response.raise_for_status()

            return {
                "success": True,
                "deleted_workflow_id": workflow_id,
            }


    async def run_workflow(
        self,
        workflow_id: str,
        input_data: dict,
    ):
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{self.base_url}/workflows/{workflow_id}/run",
                headers={
                    "Authorization": f"Bearer {self.access_token}"
                },
                json={"input": input_data},
            )

            response.raise_for_status()
            return response.json()


    async def list_executions(self, page: int = 1):
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{self.base_url}/executions/",
                headers={
                    "Authorization": f"Bearer {self.access_token}"
                },
                params={
                    "page": page,
                    "page_size": 10,
                },
            )

            response.raise_for_status()
            return response.json()

    async def get_execution_steps(self, execution_id: str):
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{self.base_url}/executions/{execution_id}/steps/",
                headers={
                    "Authorization": f"Bearer {self.access_token}"
                },
            )

            response.raise_for_status()
            return response.json()