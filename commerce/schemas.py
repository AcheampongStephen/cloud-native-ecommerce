from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Identifier = Annotated[str, Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Credentials(Input):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=12, max_length=128)

    @field_validator("email")
    @classmethod
    def email_shape(cls, value):
        value = value.strip().lower()
        if "@" not in value or "." not in value.rsplit("@", 1)[-1] or any(c.isspace() for c in value):
            raise ValueError("A valid email address is required")
        return value


class ProductInput(Input):
    id: Identifier
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    category: str = Field(min_length=1, max_length=60)
    price_cents: int = Field(strict=True, gt=0, le=100_000_000)
    emoji: str = Field(default="📦", max_length=12)


class Item(Input):
    product_id: Identifier
    quantity: int = Field(strict=True, ge=1, le=100)


class Checkout(Input):
    items: list[Item] = Field(min_length=1, max_length=30)
    payment_method: Literal["approve", "decline"] = "approve"

    @field_validator("items")
    @classmethod
    def unique_items(cls, items):
        if len({item.product_id for item in items}) != len(items):
            raise ValueError("Combine duplicate product lines")
        return sorted(items, key=lambda item: item.product_id)


class Reservation(Input):
    items: list[Item] = Field(min_length=1, max_length=30)


class PaymentInput(Input):
    amount_cents: int = Field(strict=True, gt=0, le=300_000_000_000)
    method: Literal["approve", "decline"]


class StockInput(Input):
    available: int = Field(strict=True, ge=0, le=1_000_000)
