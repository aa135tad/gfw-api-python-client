"""Tests for `gfwapiclient.resources.bulk_downloads.file.models.response`."""

from typing import Any, Dict, cast

from gfwapiclient.resources.bulk_downloads.file.models.response import (
    BulkReportFileItem,
    BulkReportFileResult,
)


def test_bulk_report_detail_item_deserializes_all_fields(
    mock_raw_bulk_report_file_item: Dict[str, Any],
) -> None:
    """Test that `BulkReportFileItem` deserializes all fields correctly."""
    bulk_report_file_item: BulkReportFileItem = BulkReportFileItem(
        **mock_raw_bulk_report_file_item
    )
    assert bulk_report_file_item.url is not None


def test_bulk_report_detail_result_deserializes_all_fields(
    mock_raw_bulk_report_file_item: Dict[str, Any],
) -> None:
    """Test that `BulkReportFileResult` deserializes all fields correctly."""
    data: BulkReportFileItem = BulkReportFileItem(**mock_raw_bulk_report_file_item)
    result = BulkReportFileResult(data=data)
    assert cast(BulkReportFileItem, result.data()) == data
