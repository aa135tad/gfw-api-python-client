# run_pipeline.py
# 一鍵執行完整 pipeline
# 使用方式：python run_pipeline.py
# 若只想執行部分步驟：python run_pipeline.py --from step1

import subprocess, sys, argparse, time

STEPS = [
    ("step0",  "step0_find_vessels.py",    "4Wings 找台灣 EEZ 船隻"),
    ("step0b", "step0b_vessel_details.py", "Vessels API 取得身份細節"),
    ("step1",  "step1_fetch_gaps.py",      "Events API 拉取 Gap 事件"),
    ("step2",  "step2_score_f1f2f3.py",    "計算 F1/F2/F3 評分"),
    ("step3",  "step3_report.py",          "生成風險報告"),
]

STEP_KEYS = [key for key, _, _ in STEPS]

def run(script: str, label: str):
    print(f"\n{'='*62}")
    print(f"  執行：{label}  ({script})")
    print(f"{'='*62}")
    t0 = time.time()
    result = subprocess.run([sys.executable, script], check=True)
    print(f"  完成（{time.time()-t0:.1f}s）")
    return result.returncode


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--from",
        dest="from_step",
        default="step0",
        choices=STEP_KEYS,
        help="從哪個步驟開始（step0/step0b/step1/step2/step3）",
    )
    parser.add_argument(
        "--only",
        dest="only_step",
        default=None,
        choices=STEP_KEYS,
        help="只執行單一步驟",
    )
    args = parser.parse_args()

    active = False
    executed = 0
    for key, script, label in STEPS:
        try:
            if args.only_step:
                if key == args.only_step:
                    run(script, label)
                    executed += 1
                continue
            if key == args.from_step:
                active = True
            if active:
                run(script, label)
                executed += 1
        except subprocess.CalledProcessError as exc:
            print(f"\n[錯誤] 步驟失敗：{key} ({script})")
            print(f"  說明：{label}")
            print(f"  子程序退出碼：{exc.returncode}")
            print("  Pipeline 已中止，請先修正此步驟後再重試。")
            raise SystemExit(exc.returncode) from exc

    if executed == 0:
        print("\n[錯誤] 本次未執行任何步驟。")
        print("  請檢查 --from 或 --only 參數是否正確。")
        raise SystemExit(2)

    print(f"\n{'='*62}")
    print("  Pipeline 全部完成！請查看 output/ 資料夾")
    print(f"{'='*62}")
