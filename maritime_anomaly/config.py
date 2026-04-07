"""固定技術參數與評分規則設定檔。

設計目標：
1) 以 Pydantic 提供型別與驗證，提早攔截錯誤設定。
2) 保留舊版常數名稱，讓既有 step 腳本可持續運作。
3) 將可調整參數集中於檔案上半部，降低維護成本。
"""

from __future__ import annotations

from math import isclose
from typing import Literal

from pydantic import BaseModel
from pydantic import Field
from pydantic import model_validator


# ══════════════════════════════════════════
#  可編輯輸入區（研究者通常只需修改這裡）
# ══════════════════════════════════════════

# GFW API 技術設定
GFW_API_BASE = "https://gateway.api.globalfishingwatch.org/v3"
API_PAGE_SIZE = 99  # 每頁筆數（GFW 建議不超過 99）
REQUEST_DELAY = 0  # 每次請求間隔秒數（避免觸發速率限制）
MAX_RETRIES = 5  # 連線失敗最大重試次數
RETRY_WAIT = 15  # 重試等待秒數
CHECKPOINT_FREQ = 20  # 每 N 頁存一次中間結果

# GFW Dataset 名稱
FISHING_EFFORT_DATASET = "public-global-fishing-effort:latest"
VESSEL_PRESENCE_DATASET = "public-global-presence:latest"
VESSEL_IDENTITY_DATASET = "public-global-vessel-identity:latest"
GAPS_DATASET = "public-global-gaps-events:latest"
PORT_VISITS_DATASET = "public-global-port-visits-events:latest"
ENCOUNTERS_DATASET = "public-global-encounters-events:latest"

# F1：AIS 訊號中斷評分規則
MIN_GAP_HOURS = 6  # 低於此值的 gap 不納入分析
F1_RULES = [
    (6, 12, 0.3),
    (12, 24, 0.6),
    (24, 72, 0.8),
    (72, float("inf"), 1.0),
]
F1_OPEN_GAP_SCORE = 0.9  # open gap（仍在靜默）強制給分

# F2：地理敏感度加權
F2_EEZ_BASE_WEIGHT = 0.70  # EEZ 內基礎分
F2_SENSITIVE_ZONES = [
    [119.0, 122.0, 22.0, 26.0, 0.85],
    [121.5, 125.0, 24.0, 26.5, 0.90],
    [119.0, 120.5, 23.5, 25.0, 0.95],
]

# F3：身份一致性規則（各項加分，合計由主流程負責上限控制）
MMSI_VALID_LENGTH = 9
CHINA_MMSI_PREFIX = "413"
CHINA_FLAG_CODE = "CHN"
F3_SCORE_RULES = {
    "invalid_mmsi_length": 0.40,
    "no_registry": 0.35,
    "no_flag": 0.30,
    "no_shipname": 0.25,
    "no_match": 0.30,
    "flag_mismatch": 0.35,
    "name_mismatch": 0.30,
    "china_mmsi_prefix": 0.20,
    "multi_mmsi_history": 0.25,
    "known_ccg": 0.50,
}
CCG_KNOWN_MMSIS = [
    "413703450",
    "413703240",
    "413800380",
]

# 評分聚合（加權平均）
SCORE_WEIGHTS = {"f1": 0.45, "f2": 0.30, "f3": 0.25}
RISK_THRESHOLDS = {
    "CRITICAL": 0.75,
    "HIGH": 0.55,
    "MEDIUM": 0.35,
    "LOW": 0.00,
}

# 輸出檔名（基底；前綴由 OUTPUT_DIR 決定）
VESSEL_LIST_FILE = "vessels.csv"
VESSEL_DETAIL_FILE = "vessel_details.csv"
RAW_GAPS_FILE = "raw_gaps.csv"
RAW_GAPS_CKPT = "raw_gaps_checkpoint.csv"
SCORED_FILE = "scored_gaps.csv"
REPORT_FILE = "risk_report.csv"
SUMMARY_FILE = "summary.txt"


class ApiSettings(BaseModel):
    gfw_api_base: str = Field(min_length=1)
    api_page_size: int = Field(ge=1, le=99)
    request_delay: int = Field(ge=0)
    max_retries: int = Field(ge=0)
    retry_wait: int = Field(ge=0)
    checkpoint_freq: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_base_url(self) -> "ApiSettings":
        if not self.gfw_api_base.startswith(("http://", "https://")):
            raise ValueError("GFW_API_BASE 必須為有效 URL（http 或 https）")
        return self


class DatasetSettings(BaseModel):
    fishing_effort_dataset: str = Field(min_length=1)
    vessel_presence_dataset: str = Field(min_length=1)
    vessel_identity_dataset: str = Field(min_length=1)
    gaps_dataset: str = Field(min_length=1)
    port_visits_dataset: str = Field(min_length=1)
    encounters_dataset: str = Field(min_length=1)


class F1Rule(BaseModel):
    gap_hours_min: float = Field(ge=0)
    gap_hours_max: float
    score: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_range(self) -> "F1Rule":
        if self.gap_hours_max <= self.gap_hours_min:
            raise ValueError("F1 規則需滿足下限 < 上限")
        return self


class F1Settings(BaseModel):
    min_gap_hours: float = Field(ge=0)
    rules: list[F1Rule]
    open_gap_score: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_rules(self) -> "F1Settings":
        if not self.rules:
            raise ValueError("F1_RULES 不可為空")
        if self.rules[0].gap_hours_min < self.min_gap_hours:
            raise ValueError("F1_RULES 第一段下限不可小於 MIN_GAP_HOURS")
        for prev, curr in zip(self.rules, self.rules[1:]):
            if curr.gap_hours_min < prev.gap_hours_max:
                raise ValueError("F1_RULES 區間不可重疊，請依序排列")
        return self


class SensitiveZone(BaseModel):
    lon_min: float
    lon_max: float
    lat_min: float
    lat_max: float
    weight: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_geo_range(self) -> "SensitiveZone":
        if not (-180 <= self.lon_min <= 180 and -180 <= self.lon_max <= 180):
            raise ValueError("F2_SENSITIVE_ZONES 經度需介於 -180 到 180")
        if not (-90 <= self.lat_min <= 90 and -90 <= self.lat_max <= 90):
            raise ValueError("F2_SENSITIVE_ZONES 緯度需介於 -90 到 90")
        if self.lon_min >= self.lon_max:
            raise ValueError("F2_SENSITIVE_ZONES 需滿足 lon_min < lon_max")
        if self.lat_min >= self.lat_max:
            raise ValueError("F2_SENSITIVE_ZONES 需滿足 lat_min < lat_max")
        return self


class F2Settings(BaseModel):
    eez_base_weight: float = Field(ge=0, le=1)
    sensitive_zones: list[SensitiveZone]


class F3Settings(BaseModel):
    mmsi_valid_length: int = Field(ge=1)
    china_mmsi_prefix: str = Field(min_length=1)
    china_flag_code: str = Field(min_length=1)
    score_rules: dict[str, float]
    ccg_known_mmsis: list[str]

    @model_validator(mode="after")
    def validate_scores(self) -> "F3Settings":
        if not self.score_rules:
            raise ValueError("F3_SCORE_RULES 不可為空")
        for key, value in self.score_rules.items():
            if not (0 <= value <= 1):
                raise ValueError(f"F3_SCORE_RULES[{key}] 需介於 0 到 1")
        return self


class ScoringSettings(BaseModel):
    score_weights: dict[Literal["f1", "f2", "f3"], float]
    risk_thresholds: dict[Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"], float]

    @model_validator(mode="after")
    def validate_scoring(self) -> "ScoringSettings":
        total = sum(self.score_weights.values())
        if not isclose(total, 1.0, rel_tol=0, abs_tol=1e-9):
            raise ValueError("SCORE_WEIGHTS 加總需為 1.0")

        for key, value in self.score_weights.items():
            if not (0 <= value <= 1):
                raise ValueError(f"SCORE_WEIGHTS[{key}] 需介於 0 到 1")

        critical = self.risk_thresholds["CRITICAL"]
        high = self.risk_thresholds["HIGH"]
        medium = self.risk_thresholds["MEDIUM"]
        low = self.risk_thresholds["LOW"]
        if not (1 >= critical >= high >= medium >= low >= 0):
            raise ValueError("RISK_THRESHOLDS 需滿足 CRITICAL >= HIGH >= MEDIUM >= LOW，且介於 0 到 1")
        return self


class OutputFiles(BaseModel):
    vessel_list_file: str = Field(min_length=1)
    vessel_detail_file: str = Field(min_length=1)
    raw_gaps_file: str = Field(min_length=1)
    raw_gaps_ckpt: str = Field(min_length=1)
    scored_file: str = Field(min_length=1)
    report_file: str = Field(min_length=1)
    summary_file: str = Field(min_length=1)


class MaritimeAnomalyConfig(BaseModel):
    api: ApiSettings
    datasets: DatasetSettings
    f1: F1Settings
    f2: F2Settings
    f3: F3Settings
    scoring: ScoringSettings
    output_files: OutputFiles


def _build_f1_rules() -> list[F1Rule]:
    built: list[F1Rule] = []
    for rule in F1_RULES:
        if len(rule) != 3:
            raise ValueError("F1_RULES 每筆需為 (下限, 上限, 評分)")
        built.append(
            F1Rule(
                gap_hours_min=float(rule[0]),
                gap_hours_max=float(rule[1]),
                score=float(rule[2]),
            )
        )
    return built


def _build_sensitive_zones() -> list[SensitiveZone]:
    built: list[SensitiveZone] = []
    for zone in F2_SENSITIVE_ZONES:
        if len(zone) != 5:
            raise ValueError("F2_SENSITIVE_ZONES 每筆需為 [lon_min, lon_max, lat_min, lat_max, weight]")
        built.append(
            SensitiveZone(
                lon_min=float(zone[0]),
                lon_max=float(zone[1]),
                lat_min=float(zone[2]),
                lat_max=float(zone[3]),
                weight=float(zone[4]),
            )
        )
    return built


CONFIG = MaritimeAnomalyConfig(
    api=ApiSettings(
        gfw_api_base=GFW_API_BASE,
        api_page_size=API_PAGE_SIZE,
        request_delay=REQUEST_DELAY,
        max_retries=MAX_RETRIES,
        retry_wait=RETRY_WAIT,
        checkpoint_freq=CHECKPOINT_FREQ,
    ),
    datasets=DatasetSettings(
        fishing_effort_dataset=FISHING_EFFORT_DATASET,
        vessel_presence_dataset=VESSEL_PRESENCE_DATASET,
        vessel_identity_dataset=VESSEL_IDENTITY_DATASET,
        gaps_dataset=GAPS_DATASET,
        port_visits_dataset=PORT_VISITS_DATASET,
        encounters_dataset=ENCOUNTERS_DATASET,
    ),
    f1=F1Settings(
        min_gap_hours=float(MIN_GAP_HOURS),
        rules=_build_f1_rules(),
        open_gap_score=F1_OPEN_GAP_SCORE,
    ),
    f2=F2Settings(
        eez_base_weight=F2_EEZ_BASE_WEIGHT,
        sensitive_zones=_build_sensitive_zones(),
    ),
    f3=F3Settings(
        mmsi_valid_length=MMSI_VALID_LENGTH,
        china_mmsi_prefix=CHINA_MMSI_PREFIX,
        china_flag_code=CHINA_FLAG_CODE,
        score_rules=F3_SCORE_RULES,
        ccg_known_mmsis=CCG_KNOWN_MMSIS,
    ),
    scoring=ScoringSettings(
        score_weights=SCORE_WEIGHTS,
        risk_thresholds=RISK_THRESHOLDS,
    ),
    output_files=OutputFiles(
        vessel_list_file=VESSEL_LIST_FILE,
        vessel_detail_file=VESSEL_DETAIL_FILE,
        raw_gaps_file=RAW_GAPS_FILE,
        raw_gaps_ckpt=RAW_GAPS_CKPT,
        scored_file=SCORED_FILE,
        report_file=REPORT_FILE,
        summary_file=SUMMARY_FILE,
    ),
)


# ══════════════════════════════════════════
#  相容舊版常數輸出（保持舊腳本可用）
# ══════════════════════════════════════════
GFW_API_BASE = CONFIG.api.gfw_api_base
API_PAGE_SIZE = CONFIG.api.api_page_size
REQUEST_DELAY = CONFIG.api.request_delay
MAX_RETRIES = CONFIG.api.max_retries
RETRY_WAIT = CONFIG.api.retry_wait
CHECKPOINT_FREQ = CONFIG.api.checkpoint_freq

FISHING_EFFORT_DATASET = CONFIG.datasets.fishing_effort_dataset
VESSEL_PRESENCE_DATASET = CONFIG.datasets.vessel_presence_dataset
VESSEL_IDENTITY_DATASET = CONFIG.datasets.vessel_identity_dataset
GAPS_DATASET = CONFIG.datasets.gaps_dataset
PORT_VISITS_DATASET = CONFIG.datasets.port_visits_dataset
ENCOUNTERS_DATASET = CONFIG.datasets.encounters_dataset

MIN_GAP_HOURS = CONFIG.f1.min_gap_hours
F1_RULES = [
    (rule.gap_hours_min, rule.gap_hours_max, rule.score)
    for rule in CONFIG.f1.rules
]
F1_OPEN_GAP_SCORE = CONFIG.f1.open_gap_score

F2_EEZ_BASE_WEIGHT = CONFIG.f2.eez_base_weight
F2_SENSITIVE_ZONES = [
    [zone.lon_min, zone.lon_max, zone.lat_min, zone.lat_max, zone.weight]
    for zone in CONFIG.f2.sensitive_zones
]

MMSI_VALID_LENGTH = CONFIG.f3.mmsi_valid_length
CHINA_MMSI_PREFIX = CONFIG.f3.china_mmsi_prefix
CHINA_FLAG_CODE = CONFIG.f3.china_flag_code
F3_SCORE_RULES = dict(CONFIG.f3.score_rules)
CCG_KNOWN_MMSIS = list(CONFIG.f3.ccg_known_mmsis)

SCORE_WEIGHTS = dict(CONFIG.scoring.score_weights)
RISK_THRESHOLDS = dict(CONFIG.scoring.risk_thresholds)

VESSEL_LIST_FILE = CONFIG.output_files.vessel_list_file
VESSEL_DETAIL_FILE = CONFIG.output_files.vessel_detail_file
RAW_GAPS_FILE = CONFIG.output_files.raw_gaps_file
RAW_GAPS_CKPT = CONFIG.output_files.raw_gaps_ckpt
SCORED_FILE = CONFIG.output_files.scored_file
REPORT_FILE = CONFIG.output_files.report_file
SUMMARY_FILE = CONFIG.output_files.summary_file
