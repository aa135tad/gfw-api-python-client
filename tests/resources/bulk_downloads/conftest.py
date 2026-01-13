"""Test configurations for `gfwapiclient.resources.bulk_downloads`."""

from typing import Any, Callable, Dict, Final

import pytest


bulk_report_id: Final[str] = "adbb9b62-5c08-4142-82e0-b2b575f3e058"
region_dataset: Final[str] = "public-eez-areas"
region_id: Final[int] = 8466
geometry: Final[Dict[str, Any]] = {
    "type": "Polygon",
    "coordinates": [
        [
            [-180.0, -85.0511287798066],
            [-180.0, 0.0],
            [0.0, 0.0],
            [0.0, -85.0511287798066],
            [-180.0, -85.0511287798066],
        ]
    ],
}


@pytest.fixture
def mock_raw_bulk_report_item(
    load_json_fixture: Callable[[str], Dict[str, Any]],
) -> Dict[str, Any]:
    """Fixture for a mock raw bulk report item.

    This fixture loads sample JSON data representing a single
    `BulkReportItem` from a fixture file.

    Returns:
        Dict[str, Any]:
            Raw `BulkReportItem` sample data as a dictionary.
    """
    raw_bulk_report_item: Dict[str, Any] = load_json_fixture(
        "bulk_downloads/bulk_report_item.json"
    )
    return raw_bulk_report_item


@pytest.fixture
def mock_raw_bulk_report_create_request_body(
    load_json_fixture: Callable[[str], Dict[str, Any]],
) -> Dict[str, Any]:
    """Fixture for mock raw bulk report create request body.

    Returns:
        Dict[str, Any]:
            Raw `BulkReportCreateBody` sample data as dictionary.
    """
    raw_bulk_report_create_request_body: Dict[str, Any] = load_json_fixture(
        "bulk_downloads/bulk_report_create_request_body.json"
    )
    return raw_bulk_report_create_request_body


@pytest.fixture
def mock_raw_bulk_report_list_request_params(
    load_json_fixture: Callable[[str], Dict[str, Any]],
) -> Dict[str, Any]:
    """Fixture for mock raw bulk report list request parameters.

    Returns:
        Dict[str, Any]:
            Raw `BulkReportListParams` sample data as dictionary.
    """
    raw_bulk_report_list_request_params: Dict[str, Any] = load_json_fixture(
        "bulk_downloads/bulk_report_list_request_params.json"
    )
    return raw_bulk_report_list_request_params


@pytest.fixture
def mock_raw_bulk_report_file_request_params(
    load_json_fixture: Callable[[str], Dict[str, Any]],
) -> Dict[str, Any]:
    """Fixture for mock raw bulk report file request parameters.

    Returns:
        Dict[str, Any]:
            Raw `BulkReportFileParams` sample data as dictionary.
    """
    raw_bulk_report_file_request_params: Dict[str, Any] = load_json_fixture(
        "bulk_downloads/bulk_report_file_request_params.json"
    )
    return raw_bulk_report_file_request_params


@pytest.fixture
def mock_raw_bulk_report_file_item(
    load_json_fixture: Callable[[str], Dict[str, Any]],
) -> Dict[str, Any]:
    """Fixture for a mock raw bulk report file item.

    This fixture loads sample JSON data representing a single
    `BulkReportFileItem` from a fixture file.

    Returns:
        Dict[str, Any]:
            Raw `BulkReportFileItem` sample data as a dictionary.
    """
    raw_bulk_report_file_item: Dict[str, Any] = load_json_fixture(
        "bulk_downloads/bulk_report_file_item.json"
    )
    return raw_bulk_report_file_item


@pytest.fixture
def mock_raw_bulk_report_query_request_params(
    load_json_fixture: Callable[[str], Dict[str, Any]],
) -> Dict[str, Any]:
    """Fixture for mock raw bulk report query request parameters.

    Returns:
        Dict[str, Any]:
            Raw `BulkReportQueryParams` sample data as dictionary.
    """
    raw_bulk_report_query_request_params: Dict[str, Any] = load_json_fixture(
        "bulk_downloads/bulk_report_query_request_params.json"
    )
    return raw_bulk_report_query_request_params


@pytest.fixture
def mock_raw_bulk_fixed_infrastructure_data_query_item(
    load_json_fixture: Callable[[str], Dict[str, Any]],
) -> Dict[str, Any]:
    """Fixture for a mock raw bulk fixed infrastructure data query item.

    This fixture loads sample JSON data representing a single
    `FixedInfrastructureDataItem` from a fixture file.

    Returns:
        Dict[str, Any]:
            Raw `BulkFixedInfrastructureDataQueryItem` sample data as a dictionary.
    """
    raw_bulk_fixed_infrastructure_data_query_item: Dict[str, Any] = load_json_fixture(
        "bulk_downloads/bulk_fixed_infrastructure_data_query_item.json"
    )
    return raw_bulk_fixed_infrastructure_data_query_item
