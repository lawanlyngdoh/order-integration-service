from decimal import Decimal

import httpx
import pytest
import respx

from order_integration.client import DownstreamOrderClient
from order_integration.models import OrderItem, OrderRequest, ShippingAddress


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def order_request() -> OrderRequest:
    return OrderRequest(
        order_id="ORD-1001",
        customer_id="CUS-2001",
        items=[
            OrderItem(
                sku="LAPTOP-01",
                quantity=1,
                unit_price=Decimal("999.99"),
            )
        ],
        shipping_address=ShippingAddress(
            line1="1 Integration Street",
            city="Shillong",
            postal_code="793001",
            country_code="IN",
        ),
    )


@pytest.mark.anyio
async def test_submit_order_successfully(order_request: OrderRequest) -> None:
    with respx.mock:
        route = respx.post("https://downstream.example.test/orders").mock(
            return_value=httpx.Response(202)
        )

        async with httpx.AsyncClient(base_url="https://downstream.example.test") as http_client:
            client = DownstreamOrderClient(http_client)

            await client.submit_order(
                order_request,
                correlation_id="correlation-123",
            )

        assert route.called
        assert route.calls.last.request.headers["X-Correlation-ID"] == ("correlation-123")


@pytest.mark.anyio
async def test_retry_after_temporary_connection_failure(
    order_request: OrderRequest,
) -> None:
    with respx.mock:
        route = respx.post("https://downstream.example.test/orders").mock(
            side_effect=[
                httpx.ConnectError("Temporary connection failure"),
                httpx.Response(202),
            ]
        )

        async with httpx.AsyncClient(base_url="https://downstream.example.test") as http_client:
            client = DownstreamOrderClient(http_client)

            await client.submit_order(
                order_request,
                correlation_id="correlation-456",
            )

        assert route.call_count == 2


@pytest.mark.anyio
async def test_rejected_order_is_not_retried(
    order_request: OrderRequest,
) -> None:
    with respx.mock:
        route = respx.post("https://downstream.example.test/orders").mock(
            return_value=httpx.Response(400)
        )

        async with httpx.AsyncClient(base_url="https://downstream.example.test") as http_client:
            client = DownstreamOrderClient(http_client)

            with pytest.raises(httpx.HTTPStatusError):
                await client.submit_order(
                    order_request,
                    correlation_id="correlation-789",
                )

        assert route.call_count == 1
