import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from order_integration.models import OrderRequest

TRANSIENT_HTTP_ERRORS = (
    httpx.ConnectError,
    httpx.TimeoutException,
)


class DownstreamOrderClient:
    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._http_client = http_client

    @retry(
        retry=retry_if_exception_type(TRANSIENT_HTTP_ERRORS),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.1, min=0.1, max=1),
        reraise=True,
    )
    async def submit_order(
        self,
        order: OrderRequest,
        correlation_id: str,
    ) -> None:
        response = await self._http_client.post(
            "/orders",
            json=order.model_dump(mode="json"),
            headers={"X-Correlation-ID": correlation_id},
        )
        response.raise_for_status()