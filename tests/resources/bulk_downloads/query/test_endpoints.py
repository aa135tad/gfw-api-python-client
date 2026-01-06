"""Tests for `gfwapiclient.resources.bulk_downloads.query.endpoints`."""

from typing import Any, Dict, List, cast

import httpx
import pytest
import respx

from gfwapiclient.exceptions.base import GFWAPIClientError
from gfwapiclient.exceptions.validation import ResultValidationError
from gfwapiclient.http.client import HTTPClient
from gfwapiclient.resources.bulk_downloads.query.endpoints import (
    BulkFixedInfrastructureDataQueryEndPoint,
)
from gfwapiclient.resources.bulk_downloads.query.models.base.request import (
    BulkReportQueryParams,
)
from gfwapiclient.resources.bulk_downloads.query.models.fixed_infrastructure_data.response import (
    BulkFixedInfrastructureDataQueryItem,
    BulkFixedInfrastructureDataQueryResult,
)

from ..conftest import bulk_report_id


@pytest.mark.asyncio
@pytest.mark.respx
async def test_bulk_fixed_infrastructure_data_query_endpoint_request_success(
    mock_http_client: HTTPClient,
    mock_raw_bulk_report_query_request_params: Dict[str, Any],
    mock_raw_bulk_fixed_infrastructure_data_query_item: Dict[str, Any],
    mock_responsex: respx.MockRouter,
) -> None:
    """Test `BulkFixedInfrastructureDataQueryEndPoint` request succeeds with a valid response."""
    mock_responsex.get(f"bulk-reports/{bulk_report_id}/query").respond(
        200, json={"entries": [mock_raw_bulk_fixed_infrastructure_data_query_item, {}]}
    )
    request_params: BulkReportQueryParams = BulkReportQueryParams(
        **mock_raw_bulk_report_query_request_params
    )
    endpoint: BulkFixedInfrastructureDataQueryEndPoint = (
        BulkFixedInfrastructureDataQueryEndPoint(
            bulk_report_id=bulk_report_id,
            request_params=request_params,
            http_client=mock_http_client,
        )
    )
    result: BulkFixedInfrastructureDataQueryResult = await endpoint.request()
    data: List[BulkFixedInfrastructureDataQueryItem] = cast(
        List[BulkFixedInfrastructureDataQueryItem], result.data()
    )
    assert isinstance(result, BulkFixedInfrastructureDataQueryResult)
    assert isinstance(data[0], BulkFixedInfrastructureDataQueryItem)


@pytest.mark.asyncio
@pytest.mark.respx
async def test_bulk_fixed_infrastructure_data_query_endpoint_invalid_response_body_failure(
    mock_http_client: HTTPClient,
    mock_raw_bulk_report_query_request_params: Dict[str, Any],
    mock_raw_bulk_fixed_infrastructure_data_query_item: Dict[str, Any],
    mock_responsex: respx.MockRouter,
) -> None:
    """Test `BulkFixedInfrastructureDataQueryEndPoint` request fails with an invalid response body."""
    mock_responsex.get(f"bulk-reports/{bulk_report_id}/query").respond(
        200, json=[mock_raw_bulk_fixed_infrastructure_data_query_item]
    )
    request_params: BulkReportQueryParams = BulkReportQueryParams(
        **mock_raw_bulk_report_query_request_params
    )
    endpoint: BulkFixedInfrastructureDataQueryEndPoint = (
        BulkFixedInfrastructureDataQueryEndPoint(
            bulk_report_id=bulk_report_id,
            request_params=request_params,
            http_client=mock_http_client,
        )
    )
    with pytest.raises(ResultValidationError):
        await endpoint.request()


@pytest.mark.asyncio
@pytest.mark.respx
async def test_bulk_fixed_infrastructure_data_query_endpoint_request_failure(
    mock_http_client: HTTPClient,
    mock_raw_bulk_report_query_request_params: Dict[str, Any],
    mock_responsex: respx.MockRouter,
) -> None:
    """Test `BulkFixedInfrastructureDataQueryEndPoint` request fails with an invalid response."""
    mock_responsex.get(f"bulk-reports/{bulk_report_id}/query").mock(
        return_value=httpx.Response(status_code=400, json={"error": "Bad Request"})
    )
    request_params: BulkReportQueryParams = BulkReportQueryParams(
        **mock_raw_bulk_report_query_request_params
    )
    endpoint: BulkFixedInfrastructureDataQueryEndPoint = (
        BulkFixedInfrastructureDataQueryEndPoint(
            bulk_report_id=bulk_report_id,
            request_params=request_params,
            http_client=mock_http_client,
        )
    )
    with pytest.raises(GFWAPIClientError):
        await endpoint.request()
