"""第1回 宿題（発展）: 応答時間とトークン数を計測し、モデル・質問で比較する。

使い方（リポジトリのルートで）:
    uv run python -m scripts.measure_lec01 --dry-run   # 実行計画だけ表示（APIは呼ばない）
    uv run python -m scripts.measure_lec01             # 全モデルで計測
    uv run python -m scripts.measure_lec01 --models gemini-3.8-flash  # 一部のモデルだけ

結果（追記されていく）:
    lectures/01/results.csv    1リクエスト1行の計測結果
    lectures/01/responses.md   回答本文（回答の違いの比較用）
"""

import argparse
import csv
import statistics
import time
from pathlib import Path

from google import genai
from google.genai import errors

from app.config import get_api_key

# モデルごとの繰り返し回数と、リクエスト間の待ち時間（秒）
# 待ち時間は無料枠の毎分上限（lite: 15回/分、flash: 5回/分）を超えないように設定
PLAN = {
    "gemini-3.5-flash-lite": {"repeats": 3, "wait": 5},
    "gemini-3.8-flash": {"repeats": 1, "wait": 15},
}

QUESTIONS = {
    "short": "日本の首都はどこですか？一言で答えてください。",
    "general": "LoRA とは何ですか？",
    "course": "AIE2026の講座の宿題にある「3レベル」とは何ですか？",
}

OUT_DIR = Path("lectures/01")
FIELDS = ["timestamp", "model", "question_id", "run", "status", "latency_s",
          "input_tokens", "output_tokens", "thoughts_tokens", "total_tokens"]


def run_once(client, model: str, question: str) -> dict:
    """1回呼び出して、応答時間とトークン数を返す。エラーもそのまま記録する。"""
    start = time.perf_counter()
    try:
        response = client.models.generate_content(model=model, contents=question)
    except errors.APIError as e:
        return {"status": f"error {e.code}", "latency_s": round(time.perf_counter() - start, 2),
                "text": str(e.message)}
    latency = time.perf_counter() - start
    u = response.usage_metadata
    return {
        "status": "ok",
        "latency_s": round(latency, 2),
        "input_tokens": u.prompt_token_count if u else None,
        "output_tokens": u.candidates_token_count if u else None,
        "thoughts_tokens": (u.thoughts_token_count or 0) if u else None,
        "total_tokens": u.total_token_count if u else None,
        "text": response.text or "",
    }


def summarize(rows: list[dict]) -> None:
    """モデル×質問ごとに平均を取り、answer.md に貼れる表で表示する。"""
    print("\n| モデル | 質問 | 成功/試行 | 平均応答時間(s) | 平均入力 | 平均出力 | 平均思考 | 出力速度(tok/s) |")
    print("|---|---|---|---|---|---|---|---|")
    for model, qid in dict.fromkeys((r["model"], r["question_id"]) for r in rows):
        group = [r for r in rows if r["model"] == model and r["question_id"] == qid]
        ok = [r for r in group if r["status"] == "ok"]
        if not ok:
            errs = ", ".join(r["status"] for r in group)
            print(f"| {model} | {qid} | 0/{len(group)} | - | - | - | - | - ({errs}) |")
            continue
        mean = lambda key: statistics.mean((r[key] or 0) for r in ok)
        speed = statistics.mean(((r["output_tokens"] or 0) + (r["thoughts_tokens"] or 0)) / r["latency_s"]
                                for r in ok)
        print(f"| {model} | {qid} | {len(ok)}/{len(group)} | {mean('latency_s'):.2f} | "
              f"{mean('input_tokens'):.0f} | {mean('output_tokens'):.0f} | "
              f"{mean('thoughts_tokens'):.0f} | {speed:.0f} |")


def main() -> None:
    parser = argparse.ArgumentParser(description="応答時間とトークン数の計測")
    parser.add_argument("--models", nargs="+", default=list(PLAN), help="計測するモデル")
    parser.add_argument("--dry-run", action="store_true", help="計画だけ表示する")
    args = parser.parse_args()

    total = sum(PLAN[m]["repeats"] * len(QUESTIONS) for m in args.models)
    print(f"[計画] モデル {args.models} / 質問 {len(QUESTIONS)}種 / 合計 {total} リクエスト")
    if args.dry_run:
        return

    client = genai.Client(api_key=get_api_key())
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path, md_path = OUT_DIR / "results.csv", OUT_DIR / "responses.md"
    new_csv = not csv_path.exists()
    rows = []

    with csv_path.open("a", newline="", encoding="utf-8") as fcsv, \
         md_path.open("a", encoding="utf-8") as fmd:
        writer = csv.DictWriter(fcsv, fieldnames=FIELDS, extrasaction="ignore")
        if new_csv:
            writer.writeheader()
        for model in args.models:
            cfg = PLAN[model]
            for qid, question in QUESTIONS.items():
                for run in range(1, cfg["repeats"] + 1):
                    r = run_once(client, model, question)
                    r.update(timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                             model=model, question_id=qid, run=run)
                    rows.append(r)
                    writer.writerow(r)
                    fmd.write(f"## {r['timestamp']} / {model} / {qid} / run {run} ({r['status']})\n\n"
                              f"{r['text']}\n\n")
                    print(f"{model:24s} {qid:8s} run{run}  {r['status']:10s} "
                          f"{r['latency_s']:6.2f}s  in={r.get('input_tokens')} "
                          f"out={r.get('output_tokens')} think={r.get('thoughts_tokens')}")
                    time.sleep(cfg["wait"])

    summarize(rows)
    print(f"\n[保存] {csv_path} / {md_path}")


if __name__ == "__main__":
    main()