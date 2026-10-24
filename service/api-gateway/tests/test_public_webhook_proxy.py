from types import SimpleNamespace
from unittest.mock import AsyncMock
import httpx
import pytest
from fastapi import HTTPException
from starlette.requests import Request
from app.routes.integrations import public_webhooks as hooks

@pytest.mark.parametrize('test_mode', [False,True])
async def test_webhook_proxy_preserves_payload_and_filters_headers(monkeypatch,test_mode):
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.request.return_value = httpx.Response(202, content=b'accepted', headers={'content-type':'text/plain','connection':'close','x-result':'yes'})
    monkeypatch.setattr(hooks.httpx,'AsyncClient',lambda:client)
    request = Request({'type':'http','method':'POST','path':'/hooks/token','query_string':b'a=1','headers':[(b'host',b'gateway'),(b'connection',b'close'),(b'x-signature',b'hmac')]}, receive=AsyncMock(return_value={'type':'http.request','body':b'{"event":1}'}))
    result = await (hooks.test_public_webhook if test_mode else hooks.receive_public_webhook)('token',request)
    assert result.status_code == 202 and result.body == b'accepted'
    assert result.headers['x-result'] == 'yes' and 'connection' not in result.headers
    kwargs = client.request.await_args.kwargs
    assert kwargs['content'] == b'{"event":1}'
    assert kwargs['headers'] == {'x-signature':'hmac'}
    assert kwargs['url'].endswith('/hooks/token/test' if test_mode else '/hooks/token')

@pytest.mark.parametrize('token',['','bad token','../secret','a/b'])
def test_invalid_webhook_token(token):
    with pytest.raises(HTTPException) as error:
        hooks.validate_webhook_token(token)
    assert error.value.status_code == 400
