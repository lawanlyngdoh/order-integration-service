import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, cast
from uuid import uuid4

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status

from order_integration.client import DownstreamOrderClient
from order_integration.models import OrderAccepted, OrderRequest


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    base_url = os.environ.get(
        "DOWNSTREAM_ORDER_URL",
        "http://localhost:8081",
    )

    async with httpx.AsyncClient(
        base_url=base_url,
        timeout=httpx.Timeout(5.0),
    ) as http_client:
        application.state.downstream_order_client = DownstreamOrderClient(http_client)
        yield


app = FastAPI(
    title="Order Integration Service",
    version="0.1.0",
    lifespan=lifespan,
)


def get_downstream_client(request: Request) -> DownstreamOrderClient:
    return cast(
        DownstreamOrderClient,
        request.app.state.downstream_order_client,
    )


@app.get("/health/live")
def liveness() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready")
def readiness() -> dict[str, str]:
    return {"status": "ready"}


@app.post(
    "/orders",
    response_model=OrderAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_order(
    order: OrderRequest,
    response: Response,
    downstream_client: Annotated[
        DownstreamOrderClient,
        Depends(get_downstream_client),
    ],
    correlation_id: Annotated[
        str | None,
        Header(alias="X-Correlation-ID"),
    ] = None,
) -> OrderAccepted:
    request_id = correlation_id or str(uuid4())

    try:
        await downstream_client.submit_order(order, request_id)
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Downstream order service is unavailable",
            headers={"X-Correlation-ID": request_id},
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Downstream order service rejected the order",
            headers={"X-Correlation-ID": request_id},
        ) from exc

    response.headers["X-Correlation-ID"] = request_id

    return OrderAccepted(
        order_id=order.order_id,
        correlation_id=request_id,
    )
