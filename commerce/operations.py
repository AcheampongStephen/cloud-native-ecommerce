from fastapi import Depends, HTTPException
from sqlalchemy import select, update

from commerce.db import Record, Stock, lock_transaction
from commerce.schemas import PaymentInput, Reservation, StockInput
from commerce.security import admin, internal


def inventory_routes(app):
    @app.get("/api/v1/inventory/{product_id}")
    def availability(product_id: str):
        with app.state.sessions() as session:
            row = session.get(Stock, product_id)
            if not row:
                raise HTTPException(404, "Stock item not found")
            return {"product_id": product_id, "available": row.available}

    @app.put("/api/v1/inventory/{product_id}", dependencies=[Depends(admin)])
    def set_stock(product_id: str, body: StockInput):
        with app.state.sessions() as session, session.begin():
            lock_transaction(session, "stock-admin")
            # Lock existing stock so a concurrent reservation cannot be overwritten mid-update.
            row = session.scalar(select(Stock).where(Stock.product_id == product_id).with_for_update())
            if row:
                row.available = body.available
            else:
                session.add(Stock(product_id=product_id, available=body.available))
        return {"product_id": product_id, **body.model_dump()}

    @app.post("/internal/reservations/{order_id}", dependencies=[Depends(internal)])
    def reserve(order_id: str, body: Reservation):
        items = sorted([item.model_dump() for item in body.items], key=lambda item: item["product_id"])
        if len({item["product_id"] for item in items}) != len(items):
            raise HTTPException(422, "Duplicate product lines")
        with app.state.sessions() as session, session.begin():
            lock_transaction(session, "reservation:" + order_id)
            row = session.get(Record, "reservation:" + order_id)
            if row:
                if row.data["items"] != items:
                    raise HTTPException(409, "Reservation payload differs")
                return row.data
            for item in items:
                changed = session.execute(
                    update(Stock)
                    .where(Stock.product_id == item["product_id"], Stock.available >= item["quantity"])
                    .values(available=Stock.available - item["quantity"])
                )
                if changed.rowcount != 1:
                    raise HTTPException(409, f"Insufficient stock for {item['product_id']}")
            data = {"items": items, "status": "reserved"}
            session.add(Record(id="reservation:" + order_id, kind="reservation", data=data))
            return data

    @app.post("/internal/reservations/{order_id}/{action}", dependencies=[Depends(internal)])
    def settle(order_id: str, action: str):
        if action not in ("commit", "release"):
            raise HTTPException(404, "Unknown reservation action")
        with app.state.sessions() as session, session.begin():
            lock_transaction(session, "reservation:" + order_id)
            row = session.get(Record, "reservation:" + order_id)
            if not row:
                raise HTTPException(404, "Reservation not found")
            target = "committed" if action == "commit" else "released"
            if row.data["status"] == target:
                return row.data
            if row.data["status"] != "reserved":
                raise HTTPException(409, "Reservation already settled differently")
            if action == "release":
                for item in row.data["items"]:
                    session.execute(
                        update(Stock)
                        .where(Stock.product_id == item["product_id"])
                        .values(available=Stock.available + item["quantity"])
                    )
            row.data = {**row.data, "status": target}
            return row.data


def payment_routes(app):
    @app.post("/internal/payments/{order_id}", dependencies=[Depends(internal)])
    def pay(order_id: str, body: PaymentInput):
        with app.state.sessions() as session, session.begin():
            lock_transaction(session, "payment:" + order_id)
            row = session.get(Record, "payment:" + order_id)
            if row:
                if row.data["request"] != body.model_dump():
                    raise HTTPException(409, "Payment payload differs")
                return row.data
            data = {
                "order_id": order_id,
                "request": body.model_dump(),
                "simulated": True,
                "status": "approved" if body.method == "approve" else "declined",
            }
            session.add(Record(id="payment:" + order_id, kind="payment", data=data))
            return data
