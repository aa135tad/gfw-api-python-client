"""Tests for `gfwapiclient.resources.bulk_downloads.list.endpoints`."""

from typing import Any, Dict, List, cast

import httpx
import pytest
import respx

from gfwapiclient.exceptions.base import GFWAPIClientError
from gfwapiclient.exceptions.validation import ResultValidationError
from gfwapiclient.http.client import HTTPClient
from gfwapiclient.resources.bulk_downloads.list.endpoints import (
    BulkReportListEndPoint,
)
from gfwapiclient.resources.bulk_downloads.list.models.request import (
    BulkReportListParams,
)
from gfwapiclient.resources.bulk_downloads.list.models.response import (
    BulkReportListItem,
    BulkReportListResult,
)


@pytest.mark.asyncio
@pytest.mark.respx
async def test_bulk_report_list_endpoint_request_success(
    mock_http_client: HTTPClient,
    mock_raw_bulk_report_list_request_params: Dict[str, Any],
    mock_raw_bulk_report_item: Dict[str, Any],
    mock_responsex: respx.MockRouter,
) -> None:
    """Test `BulkReportListEndPoint` request succeeds with a valid response."""
    mock_responsex.get("/bulk-reports").respond(
        200, json={"entries": [mock_raw_bulk_report_item, {}]}
    )
    request_params: BulkReportListParams = BulkReportListParams(
        **mock_raw_bulk_report_list_request_params
    )
    endpoint: BulkReportListEndPoint = BulkReportListEndPoint(
        request_params=request_params,
        http_client=mock_http_client,
    )
    result: BulkReportListResult = await endpoint.request()
    data: List[BulkReportListItem] = cast(List[BulkReportListItem], result.data())
    assert isinstance(result, BulkReportListResult)
    assert isinstance(data[0], BulkReportListItem)


@pytest.mark.asyncio
@pytest.mark.respx
async def test_bulk_report_list_endpoint_invalid_response_body_failure(
    mock_http_client: HTTPClient,
    mock_raw_bulk_report_list_request_params: Dict[str, Any],
    mock_raw_bulk_report_item: Dict[str, Any],
    mock_responsex: respx.MockRouter,
) -> None:
    """Test `BulkReportListEndPoint` request fails with an invalid response body."""
    mock_responsex.get("/bulk-reports").respond(200, json=[mock_raw_bulk_report_item])
    request_params: BulkReportListParams = BulkReportListParams(
        **mock_raw_bulk_report_list_request_params
    )
    endpoint: BulkReportListEndPoint = BulkReportListEndPoint(
        request_params=request_params,
        http_client=mock_http_client,
    )
    with pytest.raises(ResultValidationError):
        await endpoint.request()


@pytest.mark.asyncio
@pytest.mark.respx
async def test_bulk_report_list_endpoint_request_failure(
    mock_http_client: HTTPClient,
    mock_raw_bulk_report_list_request_params: Dict[str, Any],
    mock_responsex: respx.MockRouter,
) -> None:
    """Test `BulkReportListEndPoint` request fails with an invalid response."""
    mock_responsex.get("/bulk-reports").mock(
        return_value=httpx.Response(status_code=400, json={"error": "Bad Request"})
    )
    request_params: BulkReportListParams = BulkReportListParams(
        **mock_raw_bulk_report_list_request_params
    )
    endpoint: BulkReportListEndPoint = BulkReportListEndPoint(
        request_params=request_params,
        http_client=mock_http_client,
    )
    with pytest.raises(GFWAPIClientError):
        await endpoint.request()
