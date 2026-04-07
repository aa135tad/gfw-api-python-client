"""研究查詢參數設定檔。

設計目標：
1) 保留兩種研究區域輸入方式：GFW EEZ Region ID / 自訂座標範圍。
2) 透過型別與驗證，提早攔截錯誤設定（例如日期反向、經緯度範圍錯誤）。
3) 保留既有常數名稱，降低對既有 step 腳本的影響。
"""

from __future__ import annotations

import os
from datetime import date

from pydantic import BaseModel
from pydantic import Field
from pydantic import model_validator


# ══════════════════════════════════════════
#  可編輯輸入區（研究者主要修改這裡）
# ══════════════════════════════════════════
# 格式：YYYY-MM-DD
DATE_START: str = "2025-12-27"  # 研究期間起點
DATE_END: str = "2026-01-02"  # 研究期間終點

# 研究區域輸入方式 A：GFW EEZ Region ID（4Wings 端點適用）
# 台灣 EEZ = 8321；塞內加爾 = 8371；阿根廷 = 8466；迦納 = 8400
# 不使用時請設為 None
REGION_EEZ_ID: int | None = None
REGION_EEZ_DATASET: str | None = None

# 研究區域輸入方式 B：自訂座標範圍（Events API Python 端過濾用）
# 1141230 PRC Military Exercise Northwest Zone（由 GeoJSON 邊界取 min/max）
LON_MIN: float | None = 120.066667
LON_MAX: float | None = 121.216667
LAT_MIN: float | None = 24.983333
LAT_MAX: float | None = 26.283333

# 【選項 B】作戰層：對應 AMTI AIS 研究範圍（建議論文驗證用）
# LON_MIN: float | None = 118.00
# LON_MAX: float | None = 118.55
# LAT_MIN: float | None = 24.20
# LAT_MAX: float | None = 24.70

# 【選項 C】核心層：禁止水域（最嚴格，資料筆數少但精確度最高）
# LON_MIN: float | None = 118.10
# LON_MAX: float | None = 118.45
# LAT_MIN: float | None = 24.30
# LAT_MAX: float | None = 24.60

# 區域識別標籤（用於輸出檔名與報告標題）
REGION_LABEL: str = "PRC_Military_Exercise_Northwest_Zone"


class DateWindow(BaseModel):
    """時間窗口設定。"""

    date_start: date
    date_end: date

    @model_validator(mode="after")
    def validate_date_order(self) -> "DateWindow":
        if self.date_end < self.date_start:
            raise ValueError("DATE_END 不可早於 DATE_START")
        return self


class EezRegion(BaseModel):
    """GFW EEZ 區域設定。"""

    region_id: int = Field(gt=0)
    dataset: str = Field(min_length=1)


class BoundingBox(BaseModel):
    """經緯度邊界框設定。"""

    lon_min: float
    lon_max: float
    lat_min: float
    lat_max: float

    @model_validator(mode="after")
    def validate_ranges(self) -> "BoundingBox":
        if not (-180 <= self.lon_min <= 180 and -180 <= self.lon_max <= 180):
            raise ValueError("經度需介於 -180 到 180")
        if not (-90 <= self.lat_min <= 90 and -90 <= self.lat_max <= 90):
            raise ValueError("緯度需介於 -90 到 90")
        if self.lon_min >= self.lon_max:
            raise ValueError("LON_MIN 必須小於 LON_MAX")
        if self.lat_min >= self.lat_max:
            raise ValueError("LAT_MIN 必須小於 LAT_MAX")
        return self


class QueryParams(BaseModel):
    """研究查詢參數主設定。"""

    date_window: DateWindow
    region_label: str = Field(min_length=1)
    eez_region: EezRegion | None = None
    bounding_box: BoundingBox | None = None

    @model_validator(mode="after")
    def validate_region_source(self) -> "QueryParams":
        if self.eez_region is None and self.bounding_box is None:
            raise ValueError("至少需提供一種研究區域：EEZ 或 Bounding Box")
        return self

    @property
    def output_dir(self) -> str:
        return os.path.join(
            "output",
            f"{self.region_label}_{self.date_window.date_start:%Y-%m}_{self.date_window.date_end:%Y-%m}",
        )


def _build_eez_region() -> EezRegion | None:
    if REGION_EEZ_ID is None and REGION_EEZ_DATASET is None:
        return None
    if REGION_EEZ_ID is None or REGION_EEZ_DATASET is None:
        raise ValueError("EEZ 設定需同時提供 REGION_EEZ_ID 與 REGION_EEZ_DATASET，或都設為 None")
    return EezRegion(region_id=REGION_EEZ_ID, dataset=REGION_EEZ_DATASET)


def _build_bounding_box() -> BoundingBox | None:
    values = [LON_MIN, LON_MAX, LAT_MIN, LAT_MAX]
    if all(v is None for v in values):
        return None
    if any(v is None for v in values):
        raise ValueError("Bounding Box 設定需同時提供 LON_MIN/LON_MAX/LAT_MIN/LAT_MAX，或都設為 None")
    return BoundingBox(
        lon_min=LON_MIN,
        lon_max=LON_MAX,
        lat_min=LAT_MIN,
        lat_max=LAT_MAX,
    )


# 單一設定物件：import 此檔時即完成型別轉換與驗證
QUERY_PARAMS = QueryParams(
    date_window=DateWindow(date_start=DATE_START, date_end=DATE_END),
    region_label=REGION_LABEL,
    eez_region=_build_eez_region(),
    bounding_box=_build_bounding_box(),
)


# ══════════════════════════════════════════
#  相容舊版常數輸出（讓既有 step 腳本可無痛沿用）
# ══════════════════════════════════════════
DATE_START = QUERY_PARAMS.date_window.date_start.isoformat()
DATE_END = QUERY_PARAMS.date_window.date_end.isoformat()

REGION_EEZ_ID = (
    QUERY_PARAMS.eez_region.region_id if QUERY_PARAMS.eez_region is not None else None
)
REGION_EEZ_DATASET = (
    QUERY_PARAMS.eez_region.dataset if QUERY_PARAMS.eez_region is not None else None
)

LON_MIN = QUERY_PARAMS.bounding_box.lon_min if QUERY_PARAMS.bounding_box is not None else None
LON_MAX = QUERY_PARAMS.bounding_box.lon_max if QUERY_PARAMS.bounding_box is not None else None
LAT_MIN = QUERY_PARAMS.bounding_box.lat_min if QUERY_PARAMS.bounding_box is not None else None
LAT_MAX = QUERY_PARAMS.bounding_box.lat_max if QUERY_PARAMS.bounding_box is not None else None

REGION_LABEL = QUERY_PARAMS.region_label
OUTPUT_DIR = QUERY_PARAMS.output_dir

# 下游可用這兩個旗標快速判斷目前啟用哪種區域條件
USE_EEZ_REGION = QUERY_PARAMS.eez_region is not None
USE_BOUNDING_BOX = QUERY_PARAMS.bounding_box is not None
