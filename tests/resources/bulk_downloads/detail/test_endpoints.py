"""Tests for `gfwapiclient.resources.bulk_downloads.detail.endpoints`."""

from typing import Any, Dict, cast

import httpx
import pytest
import respx

from gfwapiclient.exceptions.base import GFWAPIClientError
from gfwapiclient.http.client import HTTPClient
from gfwapiclient.resources.bulk_downloads.detail.endpoints import (
    BulkReportDetailEndPoint,
)
from gfwapiclient.resources.bulk_downloads.detail.models.response import (
    BulkReportDetailItem,
    BulkReportDetailResult,
)

from ..conftest import bulk_report_id


@pytest.mark.asyncio
@pytest.mark.respx
async def test_bulk_report_detail_endpoint_request_success(
    mock_http_client: HTTPClient,
    mock_raw_bulk_report_item: Dict[str, Any],
    mock_responsex: respx.MockRouter,
) -> None:
    """Test `BulkReportDetailEndPoint` request succeeds with a valid response."""
    mock_responsex.get(f"/bulk-reports/{bulk_report_id}").respond(
        200, json=mock_raw_bulk_report_item
    )
    endpoint: BulkReportDetailEndPoint = BulkReportDetailEndPoint(
        bulk_report_id=bulk_report_id,
        http_client=mock_http_client,
    )
    result: BulkReportDetailResult = await endpoint.request()
    data = cast(BulkReportDetailItem, result.data())
    assert isinstance(result, BulkReportDetailResult)
    assert isinstance(data, BulkReportDetailItem)


@pytest.mark.asyncio
@pytest.mark.respx
async def test_bulk_report_detail_endpoint_request_failure(
    mock_http_client: HTTPClient,
    mock_responsex: respx.MockRouter,
) -> None:
    """Test `BulkReportDetailEndPoint` request fails with an invalid response."""
    mock_responsex.get(f"/bulk-reports/{bulk_report_id}").mock(
        return_value=httpx.Response(status_code=400, json={"error": "Bad Request"})
    )
    endpoint: BulkReportDetailEndPoint = BulkReportDetailEndPoint(
        bulk_report_id=bulk_report_id,
        http_client=mock_http_client,
    )
    with pytest.raises(GFWAPIClientError):
        await endpoint.request()
