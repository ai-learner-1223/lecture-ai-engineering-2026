"""第2回 宿題（発展）: 用語集から SFT 用の Q&A データ（JSONL）を作る。

使い方:
    # 元の形式（平文の定義を答える。system なし、2 テンプレート × 58 語 = 116 件）
    uv run python scripts/make_sft_dataset.py > glossary_sft.jsonl

    # 発展の本実験で使う形式（演習と同じ JSON 1 行・needs_review 付き、用語集に無い語の負例入り）
    uv run python scripts/make_sft_dataset.py --json > glossary_sft.jsonl

できたファイルを Colab にアップロードし、LoRA 学習のデータとして使う。
質問の言い回しを増やす、別名でも質問を作る、検証用に一部を分ける、などを工夫してみよう。

--json の設計（演習の FAQ 実験に揃える）:
- 出力は {"answer": <定義文>, "needs_review": false} の JSON 1 行。
- 用語集に無い語（TRAIN_NEGATIVES）には「この用語集には記載がありません。運営に確認が必要です。」
  と needs_review: true を教える。評価で使う「用語集に無い語」とは重ならないようにしてある。
- 学習に使う聞き方は TEMPLATES_JSON の 3 つだけ。評価の「言い回しを変えた質問」は
  別名・逆引き・口語など、ここに無い聞き方で作る（学習で見た文を評価に出さない）。
- 用語集の本文はプロンプトに入れない（closed-book）。「学習で知識を入れる」ことを試すため。
"""

import argparse
import json
import sys
from pathlib import Path

GLOSSARY = Path(__file__).resolve().parent.parent / "data" / "glossary.json"
TEMPLATES = ["「{term}」とは何ですか？", "{term}について簡単に説明してください。"]

# --json で使うもの
TEMPLATES_JSON = TEMPLATES + ["{term}の意味を教えてください。"]
SYSTEM = (
    "あなたは AI エンジニアリング講座（AIE2026）の用語集の回答係です。必ず JSON 1 行で答えてください。"
    "形式: {\"answer\": 文字列, \"needs_review\": 真偽値}。"
    "用語集に載っている用語なら定義を answer に書き、needs_review を false にします。"
    "用語集に記載が無い用語は answer に『確認が必要』と書き、needs_review を true にします。"
)
NOT_FOUND_ANSWER = "この用語集には記載がありません。運営に確認が必要です。"
# 学習用の負例（用語集に無い語）。評価用の「用語集に無い語」とは別の語にする
TRAIN_NEGATIVES = [
    "ベクトルデータベース", "チャンク分割", "リランキング", "強化学習", "推論モデル", "思考の連鎖（CoT）",
    "top-p サンプリング", "ビームサーチ", "LangChain", "Docker", "継続事前学習", "知識グラフ",
]


def load_terms() -> list[dict]:
    return json.loads(GLOSSARY.read_text(encoding="utf-8"))["terms"]


def chat(user: str, assistant: str, system: str | None = None) -> dict:
    messages = [{"role": "system", "content": system}] if system else []
    messages += [{"role": "user", "content": user}, {"role": "assistant", "content": assistant}]
    return {"messages": messages}


def plain_records(terms: list[dict]):
    for t in terms:
        for template in TEMPLATES:
            yield chat(template.format(term=t["term"]), t["definition"])


def json_records(terms: list[dict]):
    names = {t["term"] for t in terms} | {a for t in terms for a in t["aliases"]}
    clash = [n for n in TRAIN_NEGATIVES if n in names]
    assert not clash, f"負例が用語集の語と重なっています: {clash}"
    for t in terms:
        target = json.dumps({"answer": t["definition"], "needs_review": False}, ensure_ascii=False)
        for template in TEMPLATES_JSON:
            yield chat(template.format(term=t["term"]), target, SYSTEM)
    target = json.dumps({"answer": NOT_FOUND_ANSWER, "needs_review": True}, ensure_ascii=False)
    for term in TRAIN_NEGATIVES:
        for template in TEMPLATES_JSON:
            yield chat(template.format(term=term), target, SYSTEM)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true", help="JSON 1 行・needs_review 付き・負例入りの形式で出力する")
    args = parser.parse_args()
    terms = load_terms()
    records = json_records(terms) if args.json else plain_records(terms)
    n = 0
    for record in records:
        sys.stdout.write(json.dumps(record, ensure_ascii=False) + "\n")
        n += 1
    print(f"{n} 件を出力しました", file=sys.stderr)


if __name__ == "__main__":
    main()
