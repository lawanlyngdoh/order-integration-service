from decimal import Decimal

import pytest
from pydantic import ValidationError

from order_integration.models import (
    OrderItem,
    OrderRequest,
    ShippingAddress,
)


def test_valid_order_contract() -> None:
    order = OrderRequest(
        order_id="ORD-1001",
        customer_id="CUS-2001",
        items=[
            OrderItem(
                sku="LAPTOP-01",
                quantity=2,
                unit_price=Decimal("999.99"),
            )
        ],
        shipping_address=ShippingAddress(
            line1="10 Enterprise Road",
            city="Shillong",
            postal_code="793001",
            country_code="IN",
        ),
    )

    assert order.order_id == "ORD-1001"
    assert order.items[0].quantity == 2
    assert order.shipping_address.country_code == "IN"


def test_order_item_rejects_zero_quantity() -> None:
    with pytest.raises(ValidationError):
        OrderItem.model_validate(
            {
                "sku": "LAPTOP-01",
                "quantity": 0,
                "unit_price": "999.99",
            }
        )


def test_address_rejects_invalid_country_code() -> None:
    with pytest.raises(ValidationError):
        ShippingAddress.model_validate(
            {
                "line1": "10 Enterprise Road",
                "city": "Shillong",
                "postal_code": "793001",
                "country_code": "India",
            }
        )