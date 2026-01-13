"""Tests for `gfwapiclient.resources.bulk_downloads.file.endpoints`."""

from typing import Any, Dict, cast

import httpx
import pytest
import respx

from gfwapiclient.exceptions.base import GFWAPIClientError
from gfwapiclient.http.client import HTTPClient
from gfwapiclient.resources.bulk_downloads.file.endpoints import (
    BulkReportFileEndPoint,
)
from gfwapiclient.resources.bulk_downloads.file.models.request import (
    BulkReportFileParams,
)
from gfwapiclient.resources.bulk_downloads.file.models.response import (
    BulkReportFileItem,
    BulkReportFileResult,
)

from ..conftest import bulk_report_id


@pytest.mark.asyncio
@pytest.mark.respx
async def test_bulk_report_file_endpoint_request_success(
    mock_http_client: HTTPClient,
    mock_raw_bulk_report_file_request_params: Dict[str, Any],
    mock_raw_bulk_report_file_item: Dict[str, Any],
    mock_responsex: respx.MockRouter,
) -> None:
    """Test `BulkReportFileEndPoint` request succeeds with a valid response."""
    mock_responsex.get(f"bulk-reports/{bulk_report_id}/download-file-url").respond(
        200, json=mock_raw_bulk_report_file_item
    )
    request_params: BulkReportFileParams = BulkReportFileParams(
        **mock_raw_bulk_report_file_request_params
    )
    endpoint: BulkReportFileEndPoint = BulkReportFileEndPoint(
        bulk_report_id=bulk_report_id,
        request_params=request_params,
        http_client=mock_http_client,
    )
    result: BulkReportFileResult = await endpoint.request()
    data = cast(BulkReportFileItem, result.data())
    assert isinstance(result, BulkReportFileResult)
    assert isinstance(data, BulkReportFileItem)


@pytest.mark.asyncio
@pytest.mark.respx
async def test_bulk_report_file_endpoint_request_failure(
    mock_http_client: HTTPClient,
    mock_raw_bulk_report_file_request_params: Dict[str, Any],
    mock_responsex: respx.MockRouter,
) -> None:
    """Test `BulkReportFileEndPoint` request fails with an invalid response."""
    mock_responsex.get(f"bulk-reports/{bulk_report_id}/download-file-url").mock(
        return_value=httpx.Response(status_code=400, json={"error": "Bad Request"})
    )
    request_params: BulkReportFileParams = BulkReportFileParams(
        **mock_raw_bulk_report_file_request_params
    )
    endpoint: BulkReportFileEndPoint = BulkReportFileEndPoint(
        bulk_report_id=bulk_report_id,
        request_params=request_params,
        http_client=mock_http_client,
    )
    with pytest.raises(GFWAPIClientError):
        await endpoint.request()
