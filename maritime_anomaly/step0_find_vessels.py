# step0_find_vessels.py
# 功能：用 4Wings Vessel Presence API 找台灣 EEZ 內活動的船隻
# 輸出：vessels.csv（含 vessel_id / mmsi / flag / 初步可疑標記）
# 對應：GFW API Workflows PDF Flow 1 Step 1

"""Step 0：識別研究區域內活動船隻。

流程摘要（給初學者）：
1) 載入查詢設定與 GFW Token。
2) 呼叫 4Wings API（先 Presence，必要時改用 Fishing Effort）。
3) 解析回傳資料並計算初步可疑分數。
4) 輸出 vessels.csv，供後續 Step 0b 與其他步驟使用。
"""

import os, time, requests, pandas as pd
from dotenv import load_dotenv
from query_params import (
    REGION_EEZ_ID,
    REGION_EEZ_DATASET,
    OUTPUT_DIR,
    DATE_START,
    DATE_END,
    REGION_LABEL,
    LON_MIN,
    LON_MAX,
    LAT_MIN,
    LAT_MAX,
    USE_EEZ_REGION,
    USE_BOUNDING_BOX,
)
from config import (GFW_API_BASE, VESSEL_PRESENCE_DATASET, FISHING_EFFORT_DATASET,
                    CHINA_FLAG_CODE, CHINA_MMSI_PREFIX, CCG_KNOWN_MMSIS, VESSEL_LIST_FILE)

load_dotenv()
TOKEN = os.getenv("GFW_TOKEN")
if not TOKEN:
    raise ValueError("找不到 GFW_TOKEN，請確認 .env 已設定")

HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


def _build_report_body() -> dict:
    """建立 4Wings report POST body（EEZ region 或 geojson polygon）。"""
    if USE_EEZ_REGION:
        return {"region": {"dataset": REGION_EEZ_DATASET, "id": REGION_EEZ_ID}}

    if USE_BOUNDING_BOX:
        return {
            "geojson": {
                "type": "Polygon",
                "coordinates": [[
                    [LON_MIN, LAT_MIN],
                    [LON_MAX, LAT_MIN],
                    [LON_MAX, LAT_MAX],
                    [LON_MIN, LAT_MAX],
                    [LON_MIN, LAT_MIN],
                ]],
            }
        }

    raise ValueError("查詢區域未設定：請設定 EEZ 或 Bounding Box")


def query_4wings(dataset: str) -> list:
    """查詢指定 4Wings dataset，並回傳扁平化後的船舶紀錄。"""
    url = (f"{GFW_API_BASE}/4wings/report"
           f"?spatial-resolution=LOW&temporal-resolution=ENTIRE"
           f"&group-by=VESSEL_ID&datasets[0]={dataset}"
           f"&date-range={DATE_START},{DATE_END}&format=JSON&spatial-aggregation=true")
    body = _build_report_body()
    resp = requests.post(url, json=body, headers=HEADERS, timeout=120)
    print(f"  [{dataset.split(':')[0].split('-')[-1]}] HTTP {resp.status_code}")
    if resp.status_code not in (200, 201):
        print(f"  {resp.text[:300]}")
        return []
    records = []
    for entry in resp.json().get("entries", []):
        for _, items in entry.items():
            if isinstance(items, list):
                records.extend(items)
    return records


def parse_records(records: list) -> pd.DataFrame:
    """轉換原始紀錄為 DataFrame，並建立初步 F3 可疑標記欄位。"""
    rows = []
    for r in records:
        rows.append({
            "vessel_id":   r.get("vesselId", ""),
            "mmsi":        str(r.get("mmsi", "")),
            "ship_name":   r.get("shipName", ""),
            "flag":        r.get("flag", ""),
            "vessel_type": r.get("vesselType", ""),
            "geartype":    r.get("geartype", ""),
            "hours":       r.get("hours", 0),
            "entry_ts":    r.get("entryTimestamp", ""),
            "exit_ts":     r.get("exitTimestamp", ""),
        })
    df = pd.DataFrame(rows).drop_duplicates(subset="vessel_id")
    # 初步 F3 可疑標記
    df["is_china_flag"] = df["flag"] == CHINA_FLAG_CODE
    df["is_china_mmsi"] = df["mmsi"].str.startswith(CHINA_MMSI_PREFIX)
    df["is_known_ccg"]  = df["mmsi"].isin(CCG_KNOWN_MMSIS)
    df["has_no_name"]   = df["ship_name"].isnull() | (df["ship_name"].str.strip() == "")
    df["suspicious_score"] = (
        df["is_china_flag"].astype(int) * 0.30 +
        df["is_china_mmsi"].astype(int) * 0.20 +
        df["is_known_ccg"].astype(int)  * 0.50 +
        df["has_no_name"].astype(int)   * 0.20
    ).clip(upper=1.0)
    return df.sort_values("suspicious_score", ascending=False).reset_index(drop=True)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, VESSEL_LIST_FILE)
    print("=" * 58)
    print(f"Step 0：識別 {REGION_LABEL} 活動船隻")
    print(f"  時間：{DATE_START} ~ {DATE_END}")
    if USE_EEZ_REGION:
        print(f"  區域來源：EEZ {REGION_EEZ_DATASET}:{REGION_EEZ_ID}")
    else:
        print(f"  區域來源：Bounding Box {LON_MIN},{LAT_MIN} -> {LON_MAX},{LAT_MAX}")
    print(f"  輸出：{out_path}")
    print("=" * 58)
    print("[流程 1/4] 讀取查詢條件並呼叫主要資料集（Vessel Presence）")

    # 優先查 Vessel Presence，備用查 Fishing Effort
    records = query_4wings(VESSEL_PRESENCE_DATASET)
    if not records:
        print("[流程 2/4] 主要資料集無資料，切換備援資料集（Fishing Effort）")
        print("  Presence 無資料，嘗試 Fishing Effort...")
        records = query_4wings(FISHING_EFFORT_DATASET)

    if not records:
        print("[流程 3/4] 兩種資料集都沒有回傳，結束本步驟")
        print("\n[注意] 兩個資料集均回傳 0 筆")
        print("  建議：將 DATE_END 延長至 2023-03-31 後重試")
        return

    print("[流程 3/4] 解析 API 回傳並計算初步可疑分數")
    df = parse_records(records)
    print("[流程 4/4] 輸出 vessels.csv 與摘要統計")
    df.to_csv(out_path, index=False, encoding="utf-8-sig")

    print(f"\n共取得 {len(df)} 艘　儲存至：{out_path}")
    print(f"  中國旗籍：{df['is_china_flag'].sum()} 艘")
    print(f"  已知 CCG：{df['is_known_ccg'].sum()} 艘")
    print(f"  無船名  ：{df['has_no_name'].sum()} 艘")
    show = ["mmsi","ship_name","flag","vessel_type","geartype","hours","suspicious_score"]
    print(df[[c for c in show if c in df.columns]].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
