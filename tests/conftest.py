import os
import uuid

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from commerce.app import create_app
from commerce.catalog import PRODUCTS
from commerce.config import SERVICES, Settings
from commerce.db import Record, Stock
from commerce.manage import migrate


@pytest.fixture
def platform(tmp_path, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-" + "x" * 40)
    monkeypatch.setenv("INTERNAL_SECRET", "test-internal-secret-" + "x" * 40)
    apps, clients, schemas = {}, {}, []
    postgres_url = os.getenv("TEST_POSTGRES_URL")
    admin_engine = create_engine(postgres_url) if postgres_url else None

    def dispatch(request):
        client = clients[request.url.host]
        response = client.request(
            request.method, request.url.raw_path.decode(), content=request.content, headers=request.headers
        )
        return httpx.Response(response.status_code, json=response.json())

    transport = httpx.MockTransport(dispatch)
    network = httpx.Client(transport=transport)
    for service in SERVICES:
        url = f"sqlite:///{(tmp_path / (service + '.db')).as_posix()}"
        if postgres_url:
            schema = "test_" + uuid.uuid4().hex
            with admin_engine.begin() as connection:
                connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            schemas.append(schema)
            url = (
                make_url(postgres_url)
                .update_query_dict({"options": f"-csearch_path={schema}"})
                .render_as_string(hide_password=False)
            )
        settings = Settings(
            service,
            url,
            os.environ["JWT_SECRET"],
            os.environ["INTERNAL_SECRET"],
            urls={name: f"http://{name}" for name in SERVICES},
        )
        migrate(settings)
        app = create_app(settings, client=network)
        apps[service] = app
        clients[service] = TestClient(app)
    with apps["product"].state.sessions() as session, session.begin():
        for product in PRODUCTS:
            session.add(Record(id="product:" + product["id"], kind="product", data=product))
    with apps["inventory"].state.sessions() as session, session.begin():
        for product in PRODUCTS:
            session.add(Stock(product_id=product["id"], available=25))
    yield apps, clients, transport
    for client in clients.values():
        client.close()
    network.close()
    for app in apps.values():
        app.state.engine.dispose()
    if admin_engine:
        with admin_engine.begin() as connection:
            for schema in schemas:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin_engine.dispose()


@pytest.fixture
def customer(platform):
    _, clients, _ = platform
    body = {"email": "customer@example.test", "password": "test-password-1234"}
    registered = clients["identity"].post("/api/v1/auth/register", json=body)
    assert registered.status_code == 201
    token = clients["identity"].post("/api/v1/auth/login", json=body).json()["access_token"]
    return {"Authorization": "Bearer " + token}, registered.json()["id"]
