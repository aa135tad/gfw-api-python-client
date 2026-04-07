# step3_report.py
# 功能：生成風險報告、統計摘要，供 Ch.5 驗證使用

"""Step 3：生成報告與摘要。

流程摘要（給初學者）：
1) 讀取 Step 2 產出的 scored_gaps.csv。
2) 篩選高風險事件（CRITICAL/HIGH）產生報告清單。
3) 彙整風險分布、平均分數與船旗統計。
4) 輸出 report.csv 與 summary.txt，供驗證與簡報使用。
"""

import os
import pandas as pd
from datetime import datetime
from query_params import OUTPUT_DIR, DATE_START, DATE_END, REGION_LABEL
from config import SCORED_FILE, REPORT_FILE, SUMMARY_FILE


def main():
    """讀取評分結果並輸出高風險清單與文字摘要。"""
    in_path  = os.path.join(OUTPUT_DIR, SCORED_FILE)
    rep_path = os.path.join(OUTPUT_DIR, REPORT_FILE)
    sum_path = os.path.join(OUTPUT_DIR, SUMMARY_FILE)

    print("=" * 58)
    print(f"Step 3：生成風險報告 [{REGION_LABEL}]")
    print("=" * 58)
    print("[流程 1/4] 讀取 Step 2 評分結果")

    if not os.path.exists(in_path):
        print(f"[錯誤] 找不到 {in_path}"); return

    df = pd.read_csv(in_path)

    print("[流程 2/4] 篩選高風險事件並輸出報告清單")
    # 高風險清單
    high = df[df["risk_level"].isin(["CRITICAL","HIGH"])]
    rep_cols = [c for c in ["ssvid","vessel_name","flag","start_time","end_time",
                             "duration_h","is_closed","start_lat","start_lon",
                             "f1_score","f2_score","f3_score","risk_score",
                             "risk_level","xai_reason"] if c in df.columns]
    high[rep_cols].to_csv(rep_path, index=False, encoding="utf-8-sig")

    print("[流程 3/4] 彙整統計摘要（風險分布、F1/F2/F3、船旗分布）")
    lvl = df["risk_level"].value_counts()
    closed = df[df["is_closed"]==True]["duration_h"].dropna()
    open_n = (df["is_closed"]==False).sum()

    txt = f"""
{'='*58}
  AIS Gap 異常分析報告
  研究區域：{REGION_LABEL}
  時間範圍：{DATE_START} ~ {DATE_END}
  產製時間：{datetime.now().strftime('%Y-%m-%d %H:%M')}
{'='*58}

【總體統計】
  分析事件總數：{len(df)} 筆
  平均靜默時間：{closed.mean():.1f} 小時（closed gap）
  Open Gap    ：{open_n} 筆（目標仍在靜默，需即時追蹤）

【風險等級分布】
  CRITICAL（極高）：{lvl.get('CRITICAL',0)} 筆
  HIGH    （高）  ：{lvl.get('HIGH',0)} 筆
  MEDIUM  （中）  ：{lvl.get('MEDIUM',0)} 筆
  LOW     （低）  ：{lvl.get('LOW',0)} 筆

【三維評分平均】
  F1（訊號中斷）   ：{df['f1_score'].mean():.3f}
  F2（地理敏感度） ：{df['f2_score'].mean():.3f}
  F3（身份一致性）：{df['f3_score'].mean():.3f}

【船旗國分布（前 8）】
{df['flag'].value_counts().head(8).to_string()}

【高風險前 5 名（供 Maritime MDA Space 驗證）】
"""
    top5 = df.head(5)[["ssvid","flag","duration_h","risk_score","risk_level","xai_reason"]]
    txt += top5.to_string(index=False)
    txt += f"\n\n詳細清單：{rep_path}\n"

    print("[流程 4/4] 輸出 summary.txt 並顯示結果")
    with open(sum_path, "w", encoding="utf-8") as f:
        f.write(txt)
    print(txt)


if __name__ == "__main__":
    main()
