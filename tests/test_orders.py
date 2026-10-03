from collections.abc import Iterator
from uuid import UUID

import httpx
import pytest
from fastapi.testclient import TestClient

from order_integration.main import app, get_downstream_client
from order_integration.models import OrderRequest


class StubDownstreamOrderClient:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.submissions: list[tuple[OrderRequest, str]] = []

    async def submit_order(
        self,
        order: OrderRequest,
        correlation_id: str,
    ) -> None:
        if self.error is not None:
            raise self.error

        self.submissions.append((order, correlation_id))


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> Iterator[None]:
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def order_payload() -> dict[str, object]:
    return {
        "order_id": "ORD-1001",
        "customer_id": "CUS-2001",
        "items": [
            {
                "sku": "LAPTOP-01",
                "quantity": 1,
                "unit_price": "999.99",
            }
        ],
        "shipping_address": {
            "line1": "1 Integration Street",
            "city": "Shillong",
            "postal_code": "793001",
            "country_code": "IN",
        },
    }


def test_accepts_order_and_propagates_correlation_id(
    order_payload: dict[str, object],
) -> None:
    stub = StubDownstreamOrderClient()
    app.dependency_overrides[get_downstream_client] = lambda: stub

    with TestClient(app) as client:
        response = client.post(
            "/orders",
            json=order_payload,
            headers={"X-Correlation-ID": "correlation-123"},
        )

    assert response.status_code == 202
    assert response.json() == {
        "order_id": "ORD-1001",
        "correlation_id": "correlation-123",
        "status": "accepted",
    }
    assert response.headers["X-Correlation-ID"] == "correlation-123"
    assert stub.submissions[0][1] == "correlation-123"


def test_generates_correlation_id_when_missing(
    order_payload: dict[str, object],
) -> None:
    stub = StubDownstreamOrderClient()
    app.dependency_overrides[get_downstream_client] = lambda: stub

    with TestClient(app) as client:
        response = client.post("/orders", json=order_payload)

    assert response.status_code == 202
    UUID(response.json()["correlation_id"])


def test_returns_503_when_downstream_is_unavailable(
    order_payload: dict[str, object],
) -> None:
    request = httpx.Request(
        "POST",
        "https://downstream.example.test/orders",
    )
    error = httpx.ConnectError(
        "Connection failed",
        request=request,
    )
    stub = StubDownstreamOrderClient(error)
    app.dependency_overrides[get_downstream_client] = lambda: stub

    with TestClient(app) as client:
        response = client.post("/orders", json=order_payload)

    assert response.status_code == 503
    assert response.json() == {"detail": "Downstream order service is unavailable"}
    assert "X-Correlation-ID" in response.headers


def test_returns_502_when_downstream_rejects_order(
    order_payload: dict[str, object],
) -> None:
    request = httpx.Request(
        "POST",
        "https://downstream.example.test/orders",
    )
    error = httpx.HTTPStatusError(
        "Order rejected",
        request=request,
        response=httpx.Response(400, request=request),
    )
    stub = StubDownstreamOrderClient(error)
    app.dependency_overrides[get_downstream_client] = lambda: stub

    with TestClient(app) as client:
        response = client.post("/orders", json=order_payload)

    assert response.status_code == 502
    assert response.json() == {"detail": "Downstream order service rejected the order"}
