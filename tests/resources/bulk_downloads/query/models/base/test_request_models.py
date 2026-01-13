"""Tests for `gfwapiclient.resources.bulk_downloads.query.models.base.request`."""

from typing import Any, Dict

from gfwapiclient.resources.bulk_downloads.query.models.base.request import (
    BulkReportQueryParams,
)


def test_bulk_report_query_request_params_serializes_all_fields(
    mock_raw_bulk_report_query_request_params: Dict[str, Any],
) -> None:
    """Test that `BulkReportQueryParams` serializes all fields correctly."""
    bulk_report_query_params: BulkReportQueryParams = BulkReportQueryParams(
        **mock_raw_bulk_report_query_request_params
    )
    assert bulk_report_query_params.limit is not None
    assert bulk_report_query_params.offset is not None
    assert bulk_report_query_params.sort is not None
    assert bulk_report_query_params.includes is not None
    assert bulk_report_query_params.to_query_params() is not None
