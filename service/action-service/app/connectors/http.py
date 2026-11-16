import json

import httpx

from app.connectors.base import Connector


class HTTPConnector(Connector):
    async def execute(
        self,
        action: str,
        config: dict,
        input_data: dict,
    ) -> dict:

        if action != "request":
            raise ValueError(f"Unsupported HTTP action: {action}")

        method = input_data.get("method", "GET").upper()
        url = input_data.get("url")

        if not url:
            raise ValueError("HTTP request URL is required")

        headers = input_data.get("headers")
        params = input_data.get("params")
        body = input_data.get("body")

        # Workflow editors can supply JSON object/array text. Decode once to
        # avoid httpx double-encoding it. Preserve other body types unchanged.
        if isinstance(body, str):
            content_type = next(
                (value for key, value in (headers or {}).items()
                 if key.lower() == "content-type"),
                "",
            )
            if content_type.split(";", 1)[0].strip().lower() == "application/json":
                try:
                    decoded = json.loads(body)
                except json.JSONDecodeError:
                    pass
                else:
                    if isinstance(decoded, (dict, list)):
                        body = decoded

        async with httpx.AsyncClient(timeout=config.get("timeout", 10)) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=body,
            )

        try:
            response_data = response.json()
        except ValueError:
            response_data = response.text

        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": response_data,
            "success": response.is_success,
        }
