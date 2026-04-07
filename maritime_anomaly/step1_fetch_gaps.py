# step1_fetch_gaps.py  （整合版 v7）
# 功能：拉取 AIS gap 事件，Python 端以座標過濾台灣周邊
# 修正歷程：v1-v6 解決 422/timeout/速率限制/geometry不支援問題
# v7：整合 query_params，輸出目錄自動對應研究設定

"""Step 1：拉取 AIS Gap 事件。

流程摘要（給初學者）：
1) 依查詢時間向 Events API 分頁抓取 GAP 事件。
2) 在 Python 端用研究座標框做地理過濾。
3) 解析事件欄位並保留符合條件的紀錄。
4) 定期輸出 checkpoint，最後輸出 raw_gaps.csv。
"""

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests
from datetime import datetime
from dotenv import load_dotenv
from query_params import (
    LON_MIN,
    LON_MAX,
    LAT_MIN,
    LAT_MAX,
    OUTPUT_DIR,
    DATE_START,
    DATE_END,
    REGION_LABEL,
    REGION_EEZ_ID,
    REGION_EEZ_DATASET,
    USE_EEZ_REGION,
    USE_BOUNDING_BOX,
)
from config import (GFW_API_BASE, GAPS_DATASET, API_PAGE_SIZE, REQUEST_DELAY,
                    MAX_RETRIES, RETRY_WAIT, CHECKPOINT_FREQ, MIN_GAP_HOURS,
                    RAW_GAPS_FILE, RAW_GAPS_CKPT)

load_dotenv()
TOKEN = os.getenv("GFW_TOKEN")
if not TOKEN:
    raise ValueError("找不到 GFW_TOKEN")
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
MAX_WORKERS = 4


def in_area(lat, lon) -> bool:
    """判斷事件起點是否落在研究座標範圍內。"""
    try:
        return LAT_MIN <= float(lat) <= LAT_MAX and LON_MIN <= float(lon) <= LON_MAX
    except (TypeError, ValueError):
        return False


def build_events_body() -> dict:
    """建立 Events API 請求 body，依目前區域來源自動加上 region。"""
    body = {
        "datasets": [GAPS_DATASET],
        "types": ["GAP"],
        "startDate": DATE_START,
        "endDate": DATE_END,
    }
    if USE_EEZ_REGION:
        body["region"] = {"dataset": REGION_EEZ_DATASET, "id": REGION_EEZ_ID}
    return body


def fetch_page(offset: int) -> dict:
    """抓取指定 offset 的單頁 GAP 事件，含重試與速率限制處理。"""
    url  = f"{GFW_API_BASE}/events?limit={API_PAGE_SIZE}&offset={offset}"
    body = build_events_body()
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(url, json=body, headers=HEADERS, timeout=120)
            if resp.status_code == 429:
                w = 30 * attempt
                print(f"    [429 速率限制] 等 {w}s...")
                time.sleep(w); continue
            if resp.status_code not in (200, 201):
                print(f"    [錯誤] HTTP {resp.status_code}: {resp.text[:300]}")
                resp.raise_for_status()
            return resp.json()
        except (requests.exceptions.ConnectionError,
                requests.exceptions.ReadTimeout) as e:
            etype = "斷線" if "Connection" in type(e).__name__ else "逾時"
            print(f"    [{etype}] 第{attempt}/{MAX_RETRIES}次，等{RETRY_WAIT}s...")
            if attempt == MAX_RETRIES: raise
            time.sleep(RETRY_WAIT)


def parse_event(ev: dict) -> dict:
    """將單筆 GAP 事件轉為分析用平坦欄位。"""
    g  = ev.get("gap",{})      or {}
    v  = ev.get("vessel",{})   or {}
    p  = ev.get("position",{}) or {}
    r  = ev.get("regions",{})  or {}
    ds = ev.get("distances",{}) or {}
    ts, te = ev.get("start",""), ev.get("end","")
    dur, closed = None, False
    if ts and te:
        for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"):
            try:
                dur = (datetime.strptime(te,fmt)-datetime.strptime(ts,fmt)).total_seconds()/3600
                closed = True; break
            except ValueError: continue
    return {
        "event_id": ev.get("id",""), "ssvid": v.get("ssvid",""),
        "vessel_name": v.get("name",""), "flag": v.get("flag",""),
        "start_time": ts, "end_time": te,
        "duration_h": dur, "is_closed": closed,
        "start_lat": p.get("lat"), "start_lon": p.get("lon"),
        "eez_ids": str(r.get("eez",[])),
        "distance_from_shore_km": ds.get("startDistanceFromShoreKm"),
        "implied_speed_knots": g.get("impliedSpeedKnots"),
        "positions_before": g.get("positionsBefore", 0),
    }


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out   = os.path.join(OUTPUT_DIR, RAW_GAPS_FILE)
    ckpt  = os.path.join(OUTPUT_DIR, RAW_GAPS_CKPT)

    print("=" * 62)
    print(f"Step 1：拉取 AIS Gap 事件 [{REGION_LABEL}]")
    print(f"  時間：{DATE_START} ~ {DATE_END}")
    if USE_EEZ_REGION:
        print(f"  區域來源：EEZ {REGION_EEZ_DATASET}:{REGION_EEZ_ID}")
    if USE_BOUNDING_BOX:
        print(f"  座標過濾：{LON_MIN}-{LON_MAX}°E / {LAT_MIN}-{LAT_MAX}°N")
    print(f"  輸出：{out}")
    print("=" * 62)
    print("[流程 1/4] 依時間條件分頁抓取 GAP 事件")

    first_page = fetch_page(0)
    total = first_page.get("total", 0)
    est = (total + API_PAGE_SIZE - 1) // API_PAGE_SIZE
    print(f"  [第   1頁] offset=0       進度=...  ← 全球總筆數：{total:,}（約{est}頁）")
    if total == 0:
        print("[錯誤] total=0，請確認 Token 與 dataset 名稱")
        return

    print("[流程 2/4] 在 Python 端進行研究區域座標過濾")

    pages: list[tuple[int, dict]] = [(0, first_page)]
    offsets = list(range(API_PAGE_SIZE, total, API_PAGE_SIZE))
    if offsets:
        print(f"  [平行抓取] 已排定 {len(offsets)} 頁，workers={MAX_WORKERS}")
        completed = 0
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_map = {executor.submit(fetch_page, offset): offset for offset in offsets}
            for future in as_completed(future_map):
                offset = future_map[future]
                pages.append((offset, future.result()))
                completed += 1
                if completed % 10 == 0 or completed == len(offsets):
                    print(f"  [平行抓取] 已完成 {completed}/{len(offsets)} 頁")

    pages.sort(key=lambda item: item[0])
    events = []
    for page_index, (offset, data) in enumerate(pages, 1):
        pct = f"{offset / total * 100:.1f}%" if total else "..."
        if page_index > 1:
            print(f"  [第{page_index:>4}頁] offset={offset:<7} 進度={pct}")

        entries = data.get("entries", [])
        if not entries:
            continue

        hit = 0
        for ev in entries:
            p = parse_event(ev)
            if USE_BOUNDING_BOX and not in_area(p["start_lat"], p["start_lon"]):
                continue
            if not p["is_closed"] or (p["duration_h"] and p["duration_h"] >= MIN_GAP_HOURS):
                events.append(p)
                hit += 1

        if hit:
            print(f"         命中 {hit} 筆（累計：{len(events)}）")

        if page_index % CHECKPOINT_FREQ == 0 and events:
            if page_index == CHECKPOINT_FREQ:
                print("[流程 3/4] 定期輸出 checkpoint，避免長流程中斷遺失")
            pd.DataFrame(events).to_csv(ckpt, index=False, encoding="utf-8-sig")
            print(f"  [Checkpoint] {len(events)} 筆 → {ckpt}")

    print(f"\n  全部 {total:,} 筆處理完畢。")

    df = pd.DataFrame(events)
    print("[流程 4/4] 輸出最終 raw_gaps.csv 並列印摘要統計")
    df.to_csv(out, index=False, encoding="utf-8-sig")
    if os.path.exists(ckpt): os.remove(ckpt)

    print(f"\n{'='*62}")
    print(f"完成　{len(df)} 筆 gap 事件　→ {out}")
    if df.empty: print("[注意] 0 筆，建議擴大時間窗口"); return

    show = ["ssvid","flag","duration_h","is_closed","start_lat","start_lon"]
    print(df[[c for c in show if c in df.columns]].head(10).to_string(index=False))
    closed = df[df["is_closed"]==True]["duration_h"].dropna()
    print(f"\n  open gap：{(df['is_closed']==False).sum()}  closed：{(df['is_closed']==True).sum()}")
    if len(closed):
        print(f"  平均靜默：{closed.mean():.1f}h  最長：{closed.max():.1f}h")
    print(df["flag"].value_counts().head(8).to_string())


if __name__ == "__main__":
    main()
