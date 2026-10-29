"""Black-box journey through a running gateway, including asynchronous notification delivery."""

import argparse
import secrets
import time
import uuid

import httpx


def run(base_url):
    with httpx.Client(base_url=base_url, timeout=30) as client:

        def request(method, path, expected=200, **kwargs):
            response = client.request(method, path, **kwargs)
            assert response.status_code == expected, (
                f"{method} {path}: {response.status_code} {response.text}"
            )
            return response.json()

        assert client.get("/").status_code == 200
        credentials = {
            "email": f"smoke-{uuid.uuid4().hex[:12]}@example.test",
            "password": secrets.token_urlsafe(24),
        }
        request("POST", "/api/v1/auth/register", 201, json=credentials)
        token = request("POST", "/api/v1/auth/login", json=credentials)["access_token"]
        client.headers["Authorization"] = "Bearer " + token
        request("GET", "/api/v1/auth/me")
        products = request("GET", "/api/v1/products")["items"]
        chosen = next(p for p in products if request("GET", "/api/v1/inventory/" + p["id"])["available"] > 0)
        path = "/api/v1/inventory/" + chosen["id"]
        before = request("GET", path)["available"]
        body = {"items": [{"product_id": chosen["id"], "quantity": 1}], "payment_method": "decline"}
        decline_headers = {"Idempotency-Key": str(uuid.uuid4())}
        declined = request("POST", "/api/v1/orders", json=body, headers=decline_headers)
        assert declined["status"] == "declined"
        assert request("GET", path)["available"] == before
        body["payment_method"] = "approve"
        headers = {"Idempotency-Key": str(uuid.uuid4())}
        confirmed = request("POST", "/api/v1/orders", json=body, headers=headers)
        assert confirmed["status"] == "confirmed"
        assert request("POST", "/api/v1/orders", json=body, headers=headers) == confirmed
        assert request("GET", path)["available"] == before - 1
        assert len(request("GET", "/api/v1/orders")["items"]) == 2
        for _ in range(30):
            inbox = request("GET", "/api/v1/notifications")["items"]
            if any(item["order_id"] == confirmed["id"] for item in inbox):
                print(
                    "PASS: registration, login, catalog, decline/release, checkout, replay, history, notification"
                )
                print("Confirmed order:", confirmed["id"])
                return
            time.sleep(1)
        raise AssertionError("Confirmation notification did not arrive within 30 seconds")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8007")
    run(parser.parse_args().url)
