"""Tests for `gfwapiclient.resources.bulk_downloads.file.models.request`."""

from typing import Any, Dict

from gfwapiclient.resources.bulk_downloads.file.models.request import (
    BulkReportFileParams,
)


def test_bulk_report_file_request_params_serializes_all_fields(
    mock_raw_bulk_report_file_request_params: Dict[str, Any],
) -> None:
    """Test that `BulkReportFileParams` serializes all fields correctly."""
    bulk_report_file_request_params: BulkReportFileParams = BulkReportFileParams(
        **mock_raw_bulk_report_file_request_params
    )
    assert bulk_report_file_request_params.file is not None
    assert bulk_report_file_request_params.to_query_params() is not None
