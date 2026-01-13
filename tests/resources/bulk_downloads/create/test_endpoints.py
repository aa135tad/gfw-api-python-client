"""Tests for `gfwapiclient.resources.bulk_downloads.create.endpoints`."""

from typing import Any, Dict, cast

import httpx
import pytest
import respx

from gfwapiclient.exceptions.base import GFWAPIClientError
from gfwapiclient.http.client import HTTPClient
from gfwapiclient.resources.bulk_downloads.create.endpoints import (
    BulkReportCreateEndPoint,
)
from gfwapiclient.resources.bulk_downloads.create.models.request import (
    BulkReportCreateBody,
)
from gfwapiclient.resources.bulk_downloads.create.models.response import (
    BulkReportCreateItem,
    BulkReportCreateResult,
)


@pytest.mark.asyncio
@pytest.mark.respx
async def test_bulk_report_create_endpoint_request_success(
    mock_http_client: HTTPClient,
    mock_raw_bulk_report_create_request_body: Dict[str, Any],
    mock_raw_bulk_report_item: Dict[str, Any],
    mock_responsex: respx.MockRouter,
) -> None:
    """Test `BulkReportCreateEndPoint` request succeeds with a valid response."""
    mock_responsex.post("/bulk-reports").respond(201, json=mock_raw_bulk_report_item)
    request_body: BulkReportCreateBody = BulkReportCreateBody(
        **mock_raw_bulk_report_create_request_body
    )
    endpoint: BulkReportCreateEndPoint = BulkReportCreateEndPoint(
        request_body=request_body,
        http_client=mock_http_client,
    )
    result: BulkReportCreateResult = await endpoint.request()
    data = cast(BulkReportCreateItem, result.data())
    assert isinstance(result, BulkReportCreateResult)
    assert isinstance(data, BulkReportCreateItem)


@pytest.mark.asyncio
@pytest.mark.respx
async def test_bulk_report_create_endpoint_request_failure(
    mock_http_client: HTTPClient,
    mock_raw_bulk_report_create_request_body: Dict[str, Any],
    mock_responsex: respx.MockRouter,
) -> None:
    """Test `BulkReportCreateEndPoint` request fails with an invalid response."""
    mock_responsex.post("/bulk-reports").mock(
        return_value=httpx.Response(status_code=400, json={"error": "Bad Request"})
    )
    request_body: BulkReportCreateBody = BulkReportCreateBody(
        **mock_raw_bulk_report_create_request_body
    )
    endpoint: BulkReportCreateEndPoint = BulkReportCreateEndPoint(
        request_body=request_body,
        http_client=mock_http_client,
    )
    with pytest.raises(GFWAPIClientError):
        await endpoint.request()
