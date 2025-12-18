"""Global Fishing Watch (GFW) API Python Client - Get All Bulk Reports Response Models."""

from typing import List, Type

from gfwapiclient.http.models import Result
from gfwapiclient.resources.bulk_downloads.base.models.response import BulkReportItem


__all__ = ["BulkReportListItem", "BulkReportListResult"]


class BulkReportListItem(BulkReportItem):
    """Result item for the Get All Bulk Reports API endpoint.

    Represents metadata and status of the previously created bulk report.

    For more details on the Get All Bulk Reports API endpoint supported
    response bodies, please refer to the official Global Fishing Watch API
    documentation:

    See: https://globalfishingwatch.org/our-apis/documentation#get-all-bulk-reports-by-user

    See: https://globalfishingwatch.org/our-apis/documentation#bulk-reports-get-http-response

    See: https://globalfishingwatch.org/our-apis/documentation#bulk-report-object-schema
    """

    pass


class BulkReportListResult(Result[BulkReportListItem]):
    """Result for the Get All Bulk Reports API endpoint.

    For more details on the Get All Bulk Reports API endpoint supported
    response bodies, please refer to the official Global Fishing Watch API
    documentation:

    See: https://globalfishingwatch.org/our-apis/documentation#get-all-bulk-reports-by-user

    Attributes:
        _result_item_class (Type[BulkReportListItem]):
            The model used for individual result items.

        _data (BulkReportListItem):
            The bulk report item returned in the response.
    """

    _result_item_class: Type[BulkReportListItem]
    _data: List[BulkReportListItem]

    def __init__(self, data: List[BulkReportListItem]) -> None:
        """Initializes a new `BulkReportListResult`.

        Args:
            data (List[BulkReportListItem]):
                The list of bulk report items.
        """
        super().__init__(data=data)
