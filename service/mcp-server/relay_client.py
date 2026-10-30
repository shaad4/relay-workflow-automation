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

    