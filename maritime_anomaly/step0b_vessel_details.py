# step0b_vessel_details.py
# 功能：對 vessels.csv 的每艘船查詢 Vessels API 取得完整身份
# 輸出：vessel_details.csv（含 F3 異常欄位）
# 對應：GFW API Workflows PDF Flow 1 Step 2

"""Step 0b：船舶身份補全。

流程摘要（給初學者）：
1) 讀取 Step 0 產出的船舶清單。
2) 逐艘呼叫 Vessels API 查詢身份資料。
3) 解析 Registry / AIS 欄位並建立 F3 異常指標。
4) 輸出 vessel_details.csv 供下一步分析使用。
"""

import os, time, requests, pandas as pd
from dotenv import load_dotenv
from query_params import OUTPUT_DIR, REGION_LABEL
from config import (GFW_API_BASE, VESSEL_IDENTITY_DATASET, MAX_RETRIES, RETRY_WAIT,
                    VESSEL_LIST_FILE, VESSEL_DETAIL_FILE, CHINA_FLAG_CODE)

BATCH_SIZE = 100

load_dotenv()
TOKEN = os.getenv("GFW_TOKEN")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
SESSION = requests.Session()


def _build_vessel_params(vessel_ids: list[str]) -> list[tuple[str, str]]:
    params: list[tuple[str, str]] = [
        ("datasets[0]", VESSEL_IDENTITY_DATASET),
        ("includes[0]", "POTENTIAL_RELATED_SELF_REPORTED_INFO"),
    ]
    params.extend((f"ids[{index}]", vessel_id) for index, vessel_id in enumerate(vessel_ids))
    return params


def fetch_details(vessel_ids: list[str]) -> list[dict]:
    """向 Vessels API 批次取得多艘船的原始身份資料。"""
    url = f"{GFW_API_BASE}/vessels"
    params = _build_vessel_params(vessel_ids)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = SESSION.get(url, params=params, headers=HEADERS, timeout=120)
            if resp.status_code == 429:
                wait_seconds = 30 * attempt
                print(f"    [429 速率限制] 等 {wait_seconds}s...")
                time.sleep(wait_seconds)
                continue
            if resp.status_code not in (200, 201):
                print(f"    [錯誤] HTTP {resp.status_code}: {resp.text[:300]}")
                return [{} for _ in vessel_ids]
            entries = resp.json().get("entries", [])
            if not entries:
                return [{} for _ in vessel_ids]
            if len(entries) != len(vessel_ids):
                print(
                    f"    [注意] 批次回傳 {len(entries)} 筆，請求 {len(vessel_ids)} 筆，"
                    "將依序配對可用結果"
                )
            padded_entries = list(entries[: len(vessel_ids)])
            if len(padded_entries) < len(vessel_ids):
                padded_entries.extend({} for _ in range(len(vessel_ids) - len(padded_entries)))
            return padded_entries
        except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout) as exc:
            etype = "斷線" if "Connection" in type(exc).__name__ else "逾時"
            print(f"    [{etype}] 第{attempt}/{MAX_RETRIES}次，等{RETRY_WAIT}s...")
            if attempt == MAX_RETRIES:
                return [{} for _ in vessel_ids]
            time.sleep(RETRY_WAIT)


def parse_detail(vessel_id: str, d: dict) -> dict:
    """將巢狀 API 回傳轉成平坦欄位，並計算 F3 異常指標。"""
    if not d:
        return {"vessel_id": vessel_id, "parse_error": True}
    reg_list = d.get("registryInfo", [])
    ais_list = d.get("selfReportedInfo", [])
    owners   = d.get("registryOwners", [])
    reg = reg_list[0] if reg_list else {}
    ais = ais_list[0] if ais_list else {}

    mmsi_set = {r.get("ssvid","") for r in ais_list if r.get("ssvid")}
    reg_flag, ais_flag = reg.get("flag",""), ais.get("flag","")
    reg_name, ais_name = reg.get("shipname",""), ais.get("shipname","") or ""

    return {
        "vessel_id":          vessel_id,
        # Registry
        "registry_count":     d.get("registryInfoTotalRecords", 0),
        "reg_mmsi":           reg.get("ssvid",""),
        "reg_flag":           reg_flag,
        "reg_name":           reg_name,
        "reg_imo":            reg.get("imo",""),
        "reg_geartype":       str(reg.get("geartypes",[])),
        "reg_owner":          owners[0].get("name","") if owners else "",
        # AIS 自報
        "ais_mmsi":           ais.get("ssvid",""),
        "ais_flag":           ais_flag,
        "ais_name":           ais_name,
        "ais_match_fields":   ais.get("matchFields",""),
        "ais_msg_count":      ais.get("messagesCounter", 0),
        # F3 異常指標
        "no_registry":        d.get("registryInfoTotalRecords",0) == 0,
        "flag_mismatch":      bool(reg_flag and ais_flag and reg_flag != ais_flag),
        "name_mismatch":      bool(reg_name and ais_name and reg_name.upper() != ais_name.upper()),
        "no_match":           ais.get("matchFields","") == "NO_MATCH",
        "no_shipname":        not ais_name.strip(),
        "mmsi_history_count": len(mmsi_set),
        "mmsi_history":       str(sorted(mmsi_set)),
    }


def main():
    in_path  = os.path.join(OUTPUT_DIR, VESSEL_LIST_FILE)
    out_path = os.path.join(OUTPUT_DIR, VESSEL_DETAIL_FILE)
    print("=" * 58)
    print(f"Step 0b：查詢 Vessels API 身份資訊 [{REGION_LABEL}]")
    print("=" * 58)
    print("[流程 1/4] 檢查 Step 0 輸入檔是否存在")

    if not os.path.exists(in_path):
        print(f"[錯誤] 找不到 {in_path}，請先執行 step0_find_vessels.py")
        return

    print("[流程 2/4] 讀取船舶清單並整理唯一 vessel_id")
    df_in = pd.read_csv(in_path)
    ids   = [v for v in df_in["vessel_id"].dropna().unique() if str(v).strip()]
    print(f"  待查詢：{len(ids)} 艘　結果儲存至：{out_path}")

    print("[流程 3/4] 批次查詢 API、解析欄位並建立 F3 異常指標")
    results = []
    total_batches = (len(ids) + BATCH_SIZE - 1) // BATCH_SIZE
    for batch_index, start in enumerate(range(0, len(ids), BATCH_SIZE), 1):
        batch_ids = [str(v) for v in ids[start:start + BATCH_SIZE]]
        raw_items = fetch_details(batch_ids)

        for vid, raw in zip(batch_ids, raw_items):
            parsed = parse_detail(vid, raw)
            results.append(parsed)

        print(f"  [批次 {batch_index}/{total_batches}] 完成 {len(batch_ids)} 艘")

    print("[流程 4/4] 輸出明細 CSV 並列印統計摘要")
    df = pd.DataFrame(results)
    df.to_csv(out_path, index=False, encoding="utf-8-sig")

    print(f"\n完成　{len(df)} 艘")
    print(f"  無 Registry 記錄  ：{df['no_registry'].sum()}")
    print(f"  旗籍不符          ：{df['flag_mismatch'].sum()}")
    print(f"  NO_MATCH          ：{df['no_match'].sum()}")
    print(f"  多 MMSI 歷史(≥2)  ：{(df['mmsi_history_count']>=2).sum()}")


if __name__ == "__main__":
    main()
