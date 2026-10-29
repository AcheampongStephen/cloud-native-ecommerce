import hashlib
import uuid

from fastapi import Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from commerce.db import Record, lock_transaction
from commerce.schemas import Credentials, ProductInput
from commerce.security import admin, check_password, hash_password, token_for, user


def identity_routes(app):
    @app.post("/api/v1/auth/register", status_code=201)
    def register(body: Credentials):
        key = "user:" + hashlib.sha256(body.email.encode()).hexdigest()
        with app.state.sessions() as session, session.begin():
            row = Record(
                id=key,
                kind="user",
                data={"email": body.email, "password_hash": hash_password(body.password), "role": "customer"},
            )
            session.add(row)
            try:
                session.flush()
            except IntegrityError:
                raise HTTPException(409, "Email already registered") from None
            return {"id": key, "email": body.email, "role": "customer"}

    @app.post("/api/v1/auth/login")
    def login(body: Credentials):
        key = "user:" + hashlib.sha256(body.email.encode()).hexdigest()
        with app.state.sessions() as session:
            row = session.get(Record, key)
            # Do comparable password work even for an unknown account.
            encoded = row.data["password_hash"] if row else app.state.dummy_password
            valid = check_password(body.password, encoded)
            if not row or not valid:
                raise HTTPException(401, "Invalid credentials")
            return {
                "access_token": token_for(row, app.state.settings.jwt_secret),
                "token_type": "bearer",
                "expires_in": 1800,
            }

    @app.get("/api/v1/auth/me")
    def me(claims=Depends(user)):
        with app.state.sessions() as session:
            row = session.get(Record, claims["sub"])
            if not row:
                raise HTTPException(401, "Account no longer exists")
            return {"id": row.id, "email": row.data["email"], "role": row.data["role"]}


def product_routes(app):
    @app.get("/api/v1/products")
    def products(
        q: str = Query("", max_length=120),
        category: str = Query("", max_length=60),
        offset: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=100),
    ):
        with app.state.sessions() as session:
            rows = session.scalars(select(Record).where(Record.kind == "product").order_by(Record.id)).all()
            values = [
                row.data
                for row in rows
                if q.casefold() in row.data["name"].casefold()
                and (not category or row.data["category"] == category)
            ]
            return {"items": values[offset : offset + limit], "total": len(values)}

    @app.get("/api/v1/products/{product_id}")
    def product(product_id: str):
        with app.state.sessions() as session:
            row = session.get(Record, "product:" + product_id)
            if not row:
                raise HTTPException(404, "Product not found")
            return row.data

    @app.put("/api/v1/products/{product_id}", dependencies=[Depends(admin)])
    def save_product(product_id: str, body: ProductInput):
        if product_id != body.id:
            raise HTTPException(422, "Path and product id differ")
        with app.state.sessions() as session, session.begin():
            lock_transaction(session, "product:" + product_id)
            session.merge(Record(id="product:" + product_id, kind="product", data=body.model_dump()))
        return body.model_dump()


def notification_routes(app):
    @app.get("/api/v1/notifications")
    def notifications(claims=Depends(user)):
        with app.state.sessions() as session:
            rows = session.scalars(
                select(Record).where(Record.kind == "notification", Record.owner == claims["sub"])
            ).all()
            return {"items": [dict(id=row.id, **row.data) for row in rows]}


def accept_notification(sessions, event):
    if event.get("type") != "order.completed" or not all(k in event for k in ("id", "user_id", "order_id")):
        raise ValueError("Unsupported event")
    with sessions() as session, session.begin():
        lock_transaction(session, "event:" + event["id"])
        key = "notification:" + event["id"]
        if not session.get(Record, key):
            session.add(
                Record(
                    id=key,
                    kind="notification",
                    owner=event["user_id"],
                    data={
                        "order_id": event["order_id"],
                        "message": "Your order is confirmed. Thanks for shopping with us!",
                        "adapter": "local-inbox",
                        "delivery_id": str(uuid.uuid4()),
                    },
                )
            )
