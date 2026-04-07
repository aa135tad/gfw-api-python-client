# step2_score_f1f2f3.py
# 功能：合併 gap 事件與船隻身份資料，計算 F1/F2/F3 及風險評分
# 輸出：scored_gaps.csv

"""Step 2：F1/F2/F3 風險評分。

流程摘要（給初學者）：
1) 讀取 Step 1 產出的 gap 事件。
2) 嘗試合併 Step 0b 的船舶身份明細。
3) 逐筆計算 F1/F2/F3，並聚合成總風險分數。
4) 輸出 scored_gaps.csv，附風險等級與解釋文字。
"""

import os
import numpy as np
import pandas as pd
from query_params import (
    OUTPUT_DIR,
    LON_MIN,
    LON_MAX,
    LAT_MIN,
    LAT_MAX,
    REGION_LABEL,
    USE_BOUNDING_BOX,
    USE_EEZ_REGION,
)
from config import (F1_RULES, F1_OPEN_GAP_SCORE, F2_EEZ_BASE_WEIGHT, F2_SENSITIVE_ZONES,
                    F3_SCORE_RULES, MMSI_VALID_LENGTH, CHINA_MMSI_PREFIX, CCG_KNOWN_MMSIS,
                    SCORE_WEIGHTS, RISK_THRESHOLDS,
                    RAW_GAPS_FILE, VESSEL_DETAIL_FILE, SCORED_FILE)


# ── F1 ──────────────────────────────────────────────────────────
def score_f1(row: pd.Series) -> float:
    """根據 gap 靜默時長（或 open gap）計算 F1 分數。"""
    if not row.get("is_closed", True):
        return F1_OPEN_GAP_SCORE
    dur = row.get("duration_h")
    if dur is None or (isinstance(dur, float) and np.isnan(dur)):
        return 0.0
    for lo, hi, score in F1_RULES:
        if lo <= dur < hi:
            return score
    return 0.0


# ── F2 ──────────────────────────────────────────────────────────
def score_f2(row: pd.Series) -> float:
    """根據事件座標落點與敏感區設定計算 F2 分數。"""
    if not USE_BOUNDING_BOX:
        # EEZ-only 模式下不做座標框判斷，直接給基礎區域權重。
        return min(F2_EEZ_BASE_WEIGHT, 1.0)

    lat, lon = row.get("start_lat"), row.get("start_lon")
    if lat is None or lon is None:
        return 0.0
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        return 0.0
    if not (LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX):
        return 0.0
    base = F2_EEZ_BASE_WEIGHT
    for lmin, lmax, tmin, tmax, w in F2_SENSITIVE_ZONES:
        if lmin <= lon <= lmax and tmin <= lat <= tmax:
            base = max(base, w)
    return min(base, 1.0)


# ── F3 ──────────────────────────────────────────────────────────
def score_f3(row: pd.Series) -> float:
    """根據身份一致性異常指標計算 F3 分數。"""
    ssvid = str(row.get("ssvid","")).strip()
    score = 0.0
    if ssvid and len(ssvid) != MMSI_VALID_LENGTH:
        score += F3_SCORE_RULES["invalid_mmsi_length"]
    if row.get("no_registry", False):
        score += F3_SCORE_RULES["no_registry"]
    flag = str(row.get("flag","") or "").strip()
    if not flag or flag.lower() in ("nan","none",""):
        score += F3_SCORE_RULES["no_flag"]
    if row.get("no_shipname", False):
        score += F3_SCORE_RULES["no_shipname"]
    if row.get("no_match", False):
        score += F3_SCORE_RULES["no_match"]
    if row.get("flag_mismatch", False):
        score += F3_SCORE_RULES["flag_mismatch"]
    if row.get("name_mismatch", False):
        score += F3_SCORE_RULES["name_mismatch"]
    if ssvid.startswith(CHINA_MMSI_PREFIX):
        score += F3_SCORE_RULES["china_mmsi_prefix"]
    if row.get("mmsi_history_count", 0) >= 2:
        score += F3_SCORE_RULES["multi_mmsi_history"]
    if ssvid in CCG_KNOWN_MMSIS:
        score += F3_SCORE_RULES["known_ccg"]
    return min(score, 1.0)


# ── 聚合 ─────────────────────────────────────────────────────────
def risk_score(f1, f2, f3) -> float:
    """用設定權重將 F1/F2/F3 聚合成總風險分數。"""
    w = SCORE_WEIGHTS
    return round(w["f1"]*f1 + w["f2"]*f2 + w["f3"]*f3, 4)


def risk_level(score: float) -> str:
    """依門檻將總風險分數映射為等級。"""
    for level, thr in RISK_THRESHOLDS.items():
        if score >= thr:
            return level
    return "LOW"


def xai_reason(row: pd.Series) -> str:
    """輸出人類可讀的風險解釋字串（XAI）。"""
    parts = []
    f1, f2, f3 = row["f1_score"], row["f2_score"], row["f3_score"]
    if not row.get("is_closed", True):
        parts.append("F1:目標仍在AIS靜默(open gap)")
    elif f1 >= 0.8:
        parts.append(f"F1:長時靜默{row.get('duration_h',0):.0f}h(>24h)")
    elif f1 >= 0.6:
        parts.append(f"F1:異常靜默{row.get('duration_h',0):.0f}h(12-24h)")
    if f2 >= 0.90:
        parts.append("F2:位於極高敏感水域(金馬附近)")
    elif f2 >= 0.80:
        parts.append("F2:位於高敏感水域(台海中線/東北航道)")
    else:
        parts.append("F2:位於研究區域")
    if f3 >= 0.5:
        parts.append("F3:多項身份異常(無registry/no_match/多MMSI)")
    elif f3 >= 0.3:
        parts.append("F3:身份可疑(無船旗或船名)")
    elif f3 >= 0.2:
        parts.append("F3:中國MMSI前綴")
    return " | ".join(parts) if parts else "-"


def main():
    gaps_path   = os.path.join(OUTPUT_DIR, RAW_GAPS_FILE)
    detail_path = os.path.join(OUTPUT_DIR, VESSEL_DETAIL_FILE)
    out_path    = os.path.join(OUTPUT_DIR, SCORED_FILE)

    print("=" * 58)
    print(f"Step 2：計算 F1/F2/F3 評分 [{REGION_LABEL}]")
    if USE_EEZ_REGION and not USE_BOUNDING_BOX:
        print("  區域來源：EEZ 模式（F2 使用基礎區域權重）")
    elif USE_BOUNDING_BOX:
        print(f"  區域來源：Bounding Box {LON_MIN},{LAT_MIN} -> {LON_MAX},{LAT_MAX}")
    print("=" * 58)
    print("[流程 1/4] 讀取 Step 1 的 gap 事件資料")

    if not os.path.exists(gaps_path):
        print(f"[錯誤] 找不到 {gaps_path}"); return
    df = pd.read_csv(gaps_path)
    print(f"  Gap 事件：{len(df)} 筆")

    print("[流程 2/4] 合併 Step 0b 身份資料（若存在）")
    # 合併船隻身份（若有 vessel_details.csv）
    if os.path.exists(detail_path):
        df_det = pd.read_csv(detail_path)
        df = df.merge(df_det, on=None, left_on="ssvid", right_on="ais_mmsi", how="left")
        print(f"  合併 vessel_details 完成（共 {len(df)} 筆）")
    else:
        print(f"  [注意] 找不到 {detail_path}，F3 僅用 gap 資料中的欄位計算")

    print("[流程 3/4] 計算 F1/F2/F3、總風險分數、風險等級與解釋")
    df["f1_score"]   = df.apply(score_f1, axis=1)
    df["f2_score"]   = df.apply(score_f2, axis=1)
    df["f3_score"]   = df.apply(score_f3, axis=1)
    df["risk_score"] = df.apply(lambda r: risk_score(r.f1_score, r.f2_score, r.f3_score), axis=1)
    df["risk_level"] = df["risk_score"].apply(risk_level)
    df["xai_reason"] = df.apply(xai_reason, axis=1)

    df = df.sort_values("risk_score", ascending=False).reset_index(drop=True)
    print("[流程 4/4] 依風險排序後輸出 scored_gaps.csv 並列印摘要")
    df.to_csv(out_path, index=False, encoding="utf-8-sig")

    print(f"\n完成　→ {out_path}")
    lvl = df["risk_level"].value_counts()
    for l in ["CRITICAL","HIGH","MEDIUM","LOW"]:
        print(f"  {l:<10}：{lvl.get(l,0)} 筆")
    print(f"\n前 5 筆高風險：")
    show = ["ssvid","flag","duration_h","f1_score","f2_score","f3_score","risk_score","risk_level"]
    print(df[[c for c in show if c in df.columns]].head(5).to_string(index=False))


if __name__ == "__main__":
    main()
