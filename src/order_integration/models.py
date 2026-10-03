from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class OrderItem(StrictModel):
    sku: str = Field(
        min_length=1,
        max_length=50,
        pattern=r"^[A-Z0-9][A-Z0-9_-]*$",
    )
    quantity: int = Field(ge=1, le=100)
    unit_price: Decimal = Field(
        gt=0,
        max_digits=12,
        decimal_places=2,
    )


class ShippingAddress(StrictModel):
    line1: str = Field(min_length=1, max_length=200)
    city: str = Field(min_length=1, max_length=100)
    postal_code: str = Field(min_length=1, max_length=20)
    country_code: str = Field(pattern=r"^[A-Z]{2}$")


class OrderRequest(StrictModel):
    order_id: str = Field(min_length=3, max_length=64)
    customer_id: str = Field(min_length=3, max_length=64)
    items: list[OrderItem] = Field(min_length=1, max_length=50)
    shipping_address: ShippingAddress


class OrderAccepted(StrictModel):
    order_id: str
    correlation_id: str
    status: Literal["accepted"] = "accepted"
