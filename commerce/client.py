import httpx
from fastapi import HTTPException


def call(app, service, method, path, body=None):
    try:
        response = app.state.client.request(
            method,
            app.state.settings.urls[service] + path,
            json=body,
            headers={"x-internal-key": app.state.settings.internal_secret},
            timeout=5,
        )
    except httpx.RequestError:
        raise HTTPException(503, f"{service} unavailable; retry with the same Idempotency-Key") from None
    if response.status_code >= 400:
        if response.status_code >= 500:
            raise HTTPException(503, f"{service} unavailable; retry with the same Idempotency-Key")
        raise HTTPException(
            response.status_code, response.json().get("detail", "Dependency rejected request")
        )
    return response.json()
