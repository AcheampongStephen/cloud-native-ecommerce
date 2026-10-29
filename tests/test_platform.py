from concurrent.futures import ThreadPoolExecutor

import httpx
import jwt
import pytest
from sqlalchemy import func, select

from commerce.basic_routes import accept_notification
from commerce.db import Outbox, Record
from commerce.security import check_password, hash_password, token_for

CHECKOUT = {"items": [{"product_id": "keyboard", "quantity": 2}], "payment_method": "approve"}


def checkout(clients, headers, body=None, key="checkout-test-key"):
    return clients["order"].post(
        "/api/v1/orders", json=body or CHECKOUT, headers={**headers, "Idempotency-Key": key}
    )


def test_password_hashes_are_salted():
    first, second = hash_password("long-password-here"), hash_password("long-password-here")
    assert first != second
    assert check_password("long-password-here", first)
    assert not check_password("wrong-password", first)


def test_health_and_catalog(platform):
    _, clients, _ = platform
    for name, client in clients.items():
        assert client.get("/health/live").json()["service"] == name
        assert client.get("/health/ready").status_code == 200
    assert clients["product"].get("/api/v1/products").json()["total"] == 6
    filtered = clients["product"].get("/api/v1/products?q=keyboard&category=Workspace").json()
    assert filtered["total"] == 1
    assert clients["product"].get("/api/v1/products/missing").status_code == 404
    assert clients["gateway"].get("/").status_code == 200


def test_identity_validation_and_roles(platform, customer):
    apps, clients, _ = platform
    headers, user_id = customer
    assert clients["identity"].get("/api/v1/auth/me", headers=headers).json()["id"] == user_id
    assert (
        clients["identity"]
        .post("/api/v1/auth/register", json={"email": "bad", "password": "short"})
        .status_code
        == 422
    )
    credentials = {"email": "customer@example.test", "password": "test-password-1234"}
    assert clients["identity"].post("/api/v1/auth/register", json=credentials).status_code == 409
    credentials["password"] = "wrong-password-1234"
    assert clients["identity"].post("/api/v1/auth/login", json=credentials).status_code == 401
    assert (
        clients["inventory"]
        .put("/api/v1/inventory/keyboard", json={"available": 10}, headers=headers)
        .status_code
        == 403
    )
    assert clients["order"].get("/api/v1/orders").status_code == 401
    forged = jwt.encode({"sub": user_id}, "forged-secret-" + "x" * 32, algorithm="HS256")
    assert (
        clients["order"].get("/api/v1/orders", headers={"Authorization": "Bearer " + forged}).status_code
        == 401
    )
    with apps["identity"].state.sessions() as session:
        row = session.get(Record, user_id)
        assert "test-password-1234" not in row.data["password_hash"]


def test_admin_catalog_and_stock(platform, customer):
    apps, clients, _ = platform
    _, user_id = customer
    with apps["identity"].state.sessions() as session, session.begin():
        row = session.get(Record, user_id)
        row.data = {**row.data, "role": "admin"}
        token = token_for(row, apps["identity"].state.settings.jwt_secret)
    headers = {"Authorization": "Bearer " + token}
    product = {"id": "new-product", "name": "New", "category": "Workspace", "price_cents": 500}
    assert (
        clients["product"].put("/api/v1/products/new-product", json=product, headers=headers).status_code
        == 200
    )
    assert (
        clients["inventory"]
        .put("/api/v1/inventory/new-product", json={"available": 7}, headers=headers)
        .status_code
        == 200
    )
    assert clients["inventory"].get("/api/v1/inventory/new-product").json()["available"] == 7


def test_checkout_idempotency_and_durable_notification(platform, customer):
    apps, clients, _ = platform
    headers, user_id = customer
    first = checkout(clients, headers)
    assert first.status_code == 200, first.text
    order = first.json()
    assert order["status"] == "confirmed"
    assert order["total_cents"] == 17800
    assert checkout(clients, headers).json() == order
    changed = {**CHECKOUT, "payment_method": "decline"}
    assert checkout(clients, headers, changed).status_code == 409
    assert clients["inventory"].get("/api/v1/inventory/keyboard").json()["available"] == 23
    with apps["order"].state.sessions() as session:
        events = session.scalars(select(Outbox)).all()
        assert len(events) == 1
        event = events[0].payload
    accept_notification(apps["notification"].state.sessions, event)
    accept_notification(apps["notification"].state.sessions, event)
    inbox = clients["notification"].get("/api/v1/notifications", headers=headers).json()["items"]
    assert len(inbox) == 1
    assert inbox[0]["order_id"] == order["id"]
    assert clients["order"].get("/api/v1/orders", headers=headers).json()["items"][0]["id"] == order["id"]


def test_decline_releases_stock(platform, customer):
    apps, clients, _ = platform
    headers, _ = customer
    response = checkout(clients, headers, {**CHECKOUT, "payment_method": "decline"})
    assert response.json()["status"] == "declined"
    assert checkout(clients, headers, {**CHECKOUT, "payment_method": "decline"}).json() == response.json()
    assert clients["inventory"].get("/api/v1/inventory/keyboard").json()["available"] == 25
    with apps["order"].state.sessions() as session:
        assert session.scalar(select(func.count()).select_from(Outbox)) == 0


def test_failed_multiline_reservation_rolls_back(platform, customer):
    _, clients, _ = platform
    headers, _ = customer
    body = {"items": [{"product_id": "bottle", "quantity": 1}, {"product_id": "keyboard", "quantity": 26}]}
    assert checkout(clients, headers, body).json()["status"] == "rejected"
    assert clients["inventory"].get("/api/v1/inventory/bottle").json()["available"] == 25


@pytest.mark.parametrize("stage", ["payment", "commit", "release"])
def test_lost_response_recovers_without_duplicate_side_effects(platform, customer, stage):
    apps, clients, original_transport = platform
    headers, _ = customer
    failed = False

    def fault(request):
        nonlocal failed
        result = original_transport.handle_request(request)
        target = (
            request.url.host == "payment" if stage == "payment" else request.url.path.endswith("/" + stage)
        )
        if target and not failed:
            failed = True
            raise httpx.ReadTimeout("Response lost after remote commit", request=request)
        return result

    apps["order"].state.client = httpx.Client(transport=httpx.MockTransport(fault))
    body = {**CHECKOUT, "payment_method": "decline" if stage == "release" else "approve"}
    assert checkout(clients, headers, body).status_code == 503
    assert clients["order"].get("/api/v1/orders", headers=headers).json()["items"][0]["status"] == "pending"
    recovered = checkout(clients, headers, body)
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["status"] == ("declined" if stage == "release" else "confirmed")
    assert clients["inventory"].get("/api/v1/inventory/keyboard").json()["available"] == (
        25 if stage == "release" else 23
    )
    with apps["payment"].state.sessions() as session:
        assert session.scalar(select(func.count()).select_from(Record)) == 1
    apps["order"].state.client.close()


def test_order_ownership(platform, customer):
    _, clients, _ = platform
    headers, _ = customer
    order = checkout(clients, headers).json()
    credentials = {"email": "other@example.test", "password": "another-password-123"}
    clients["identity"].post("/api/v1/auth/register", json=credentials)
    token = clients["identity"].post("/api/v1/auth/login", json=credentials).json()["access_token"]
    other = {"Authorization": "Bearer " + token}
    assert clients["order"].get("/api/v1/orders/" + order["id"], headers=other).status_code == 404
    assert clients["order"].get("/api/v1/orders", headers=other).json()["items"] == []


def test_concurrent_reservations_cannot_oversell(platform):
    apps, clients, _ = platform
    headers = {"X-Internal-Key": apps["inventory"].state.settings.internal_secret}

    def reserve(index):
        return (
            clients["inventory"]
            .post(
                f"/internal/reservations/concurrent-{index}",
                json={"items": [{"product_id": "keyboard", "quantity": 2}]},
                headers=headers,
            )
            .status_code
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(reserve, range(20)))
    assert results.count(200) == 12
    assert results.count(409) == 8
    assert clients["inventory"].get("/api/v1/inventory/keyboard").json()["available"] == 1


def test_internal_endpoints_and_validation(platform, customer):
    _, clients, _ = platform
    headers, _ = customer
    assert (
        clients["payment"]
        .post("/internal/payments/forged", json={"amount_cents": 100, "method": "approve"})
        .status_code
        == 403
    )
    duplicate = {"items": CHECKOUT["items"] * 2}
    assert checkout(clients, headers, duplicate).status_code == 422
    negative = {"items": [{"product_id": "keyboard", "quantity": -1}]}
    assert checkout(clients, headers, negative).status_code == 422
    assert clients["order"].post("/api/v1/orders", json=CHECKOUT, headers=headers).status_code == 422
