import hashlib
import uuid
from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select

from commerce.client import call
from commerce.db import Outbox, Record, lock_transaction
from commerce.schemas import Checkout
from commerce.security import user


def order_routes(app):
    @app.get("/api/v1/orders")
    def orders(claims=Depends(user)):
        with app.state.sessions() as session:
            rows = session.scalars(
                select(Record).where(Record.kind == "order", Record.owner == claims["sub"])
            ).all()
            return {
                "items": sorted([row.data for row in rows], key=lambda row: row["created_at"], reverse=True)
            }

    @app.get("/api/v1/orders/{order_id}")
    def order(order_id: str, claims=Depends(user)):
        with app.state.sessions() as session:
            row = session.get(Record, order_id)
            if not row or row.owner != claims["sub"]:
                raise HTTPException(404, "Order not found")
            return row.data

    @app.post("/api/v1/orders")
    def checkout(
        body: Checkout, claims=Depends(user), idempotency_key: str = Header(min_length=8, max_length=100)
    ):
        # User-scoped deterministic key; same key with a changed payload is rejected.
        order_id = hashlib.sha256(f"{claims['sub']}:{idempotency_key}".encode()).hexdigest()[:32]
        request = body.model_dump()
        with app.state.sessions() as session, session.begin():
            lock_transaction(session, "order:" + order_id)
            row = session.get(Record, order_id)
            if row:
                if row.data["request"] != request:
                    raise HTTPException(409, "Idempotency-Key already used with a different checkout")
                if row.data["status"] != "pending":
                    return row.data
            else:
                items = []
                for item in body.items:
                    product = call(app, "product", "GET", f"/api/v1/products/{item.product_id}")
                    items.append(
                        {**item.model_dump(), "name": product["name"], "price_cents": product["price_cents"]}
                    )
                data = {
                    "id": order_id,
                    "status": "pending",
                    "request": request,
                    "items": items,
                    "retry_key": idempotency_key,
                    "total_cents": sum(item["quantity"] * item["price_cents"] for item in items),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                row = Record(id=order_id, kind="order", owner=claims["sub"], data=data)
                session.add(row)

        # Persist pending before external effects. A crash or timeout leaves a resumable order.
        with app.state.sessions() as session, session.begin():
            lock_transaction(session, "order:" + order_id)
            row = session.get(Record, order_id, populate_existing=True)
            if row.data["status"] != "pending":
                return row.data
            data = dict(row.data)
            try:
                reservation = call(
                    app,
                    "inventory",
                    "POST",
                    f"/internal/reservations/{order_id}",
                    {"items": request["items"]},
                )
            except HTTPException as error:
                if error.status_code == 409:
                    row.data = {**data, "status": "rejected", "reason": error.detail}
                    return row.data
                raise
            if reservation["status"] == "released":
                row.data = {**data, "status": "declined"}
                return row.data
            payment = call(
                app,
                "payment",
                "POST",
                f"/internal/payments/{order_id}",
                {"amount_cents": data["total_cents"], "method": body.payment_method},
            )
            approved = payment["status"] == "approved"
            action = "commit" if approved else "release"
            call(app, "inventory", "POST", f"/internal/reservations/{order_id}/{action}")
            data["status"] = "confirmed" if approved else "declined"
            row.data = data
            if approved:
                event_id = str(uuid.uuid4())
                session.add(
                    Outbox(
                        id=event_id,
                        payload={
                            "id": event_id,
                            "type": "order.completed",
                            "order_id": order_id,
                            "user_id": row.owner,
                        },
                    )
                )
            return data
