"""Tests for `gfwapiclient.resources.bulk_downloads.query.models.fixed_infrastructure_data.response`."""

from typing import Any, Dict, List, cast

from gfwapiclient.resources.bulk_downloads.query.models.fixed_infrastructure_data.response import (
    BulkFixedInfrastructureDataQueryItem,
    BulkFixedInfrastructureDataQueryResult,
)


def test_bulk_fixed_infrastructure_data_query_item_deserializes_all_fields(
    mock_raw_bulk_fixed_infrastructure_data_query_item: Dict[str, Any],
) -> None:
    """Test that `BulkFixedInfrastructureDataQueryItem` deserializes all fields correctly."""
    fixed_infrastructure_data_item: BulkFixedInfrastructureDataQueryItem = (
        BulkFixedInfrastructureDataQueryItem(
            **mock_raw_bulk_fixed_infrastructure_data_query_item
        )
    )
    assert fixed_infrastructure_data_item.detection_id is not None
    assert fixed_infrastructure_data_item.detection_date is not None
    assert fixed_infrastructure_data_item.structure_id is not None
    assert fixed_infrastructure_data_item.lon is not None
    assert fixed_infrastructure_data_item.lat is not None
    assert fixed_infrastructure_data_item.structure_start_date is not None
    assert fixed_infrastructure_data_item.structure_end_date is not None
    assert fixed_infrastructure_data_item.label is not None
    assert fixed_infrastructure_data_item.label_confidence is not None


def test_bulk_fixed_infrastructure_data_query_item_deserializes_empty_date_fields(
    mock_raw_bulk_fixed_infrastructure_data_query_item: Dict[str, Any],
) -> None:
    """Test that `BulkFixedInfrastructureDataQueryItem` deserializes empty date fields correctly."""
    fixed_infrastructure_data_item: BulkFixedInfrastructureDataQueryItem = (
        BulkFixedInfrastructureDataQueryItem(
            **{
                **mock_raw_bulk_fixed_infrastructure_data_query_item,
                "structure_start_date": " ",
                "structure_end_date": None,
            }
        )
    )
    assert fixed_infrastructure_data_item.detection_id is not None
    assert fixed_infrastructure_data_item.detection_date is not None
    assert fixed_infrastructure_data_item.structure_id is not None
    assert fixed_infrastructure_data_item.lon is not None
    assert fixed_infrastructure_data_item.lat is not None
    assert fixed_infrastructure_data_item.structure_start_date is None
    assert fixed_infrastructure_data_item.structure_end_date is None
    assert fixed_infrastructure_data_item.label is not None
    assert fixed_infrastructure_data_item.label_confidence is not None


def test_bulk_fixed_infrastructure_data_query_result_deserializes_all_fields(
    mock_raw_bulk_fixed_infrastructure_data_query_item: Dict[str, Any],
) -> None:
    """Test that `BulkFixedInfrastructureDataQueryResult` deserializes all fields correctly."""
    data: List[BulkFixedInfrastructureDataQueryItem] = [
        BulkFixedInfrastructureDataQueryItem(
            **mock_raw_bulk_fixed_infrastructure_data_query_item
        )
    ]
    result = BulkFixedInfrastructureDataQueryResult(data=data)
    assert cast(List[BulkFixedInfrastructureDataQueryItem], result.data()) == data
