"""第1回: 素のLLMに1回だけ質問するスクリプト。

使い方:
    uv run python -m app.ask "LoRAとは何ですか？"
    uv run python -m app.ask            # 質問を省略すると、講座に固有の質問をする

ツールも会話履歴も持たない「素の」呼び出し。
講座に固有のことを聞くと、「分からない」と答えるか、一般論でもっともらしく答える
（講座の実際とは違う）ことを確かめよう。
（第3回で、用語集を検索できるエージェントにして改善する）
"""

import argparse

from google import genai
from google.genai import errors

from app.config import MODEL, api_error_message, get_api_key

# 講座に固有の質問。正しい答えは data/glossary.json の homework-levels にある
DEFAULT_QUESTION = "AIE2026の講座の宿題にある「3レベル」とは何ですか？"


def ask(question: str) -> str:
    client = genai.Client(api_key=get_api_key())
    response = client.models.generate_content(model=MODEL, contents=question)

    # TODO(第1回 演習): response.usage_metadata から
    #   入力トークン数と出力トークン数を表示してみよう（Copilotに頼んでよい）
    # 第1回 演習: トークン数を表示する
    usage = response.usage_metadata
    if usage is not None:
        print(f"[入力トークン] {usage.prompt_token_count}")
        print(f"[出力トークン] {usage.candidates_token_count}")
        # 思考（thinking）を行うモデルでは、思考分のトークンも別に数えられる
        if usage.thoughts_token_count:
            print(f"[思考トークン] {usage.thoughts_token_count}")
        print(f"[合計トークン] {usage.total_token_count}\n")
        
    return response.text

def chat() -> None:
    """第1回 宿題（実装）: 会話履歴を保ったまま、続けて質問できるチャットループ。"""
    client = genai.Client(api_key=get_api_key())
    session = client.chats.create(model=MODEL)  # このセッションが履歴を保持する
    print(f"[model] {MODEL}")
    print("会話モードです。終了するには exit と入力するか、何も入力せずに Enter を押してください。")

    while True:
        try:
            question = input("\n[あなた] ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if question in ("", "exit", "quit"):
            break
        try:
            response = session.send_message(question)  # 履歴＋今回の質問をまとめて送る
        except errors.APIError as e:
            print(api_error_message(e.code, e.message))
            continue
        print(f"\n[Gemini] {response.text}")
        usage = response.usage_metadata
        if usage is not None:
            turns = len(session.get_history()) // 2
            print(f"  （{turns}往復目 / 入力 {usage.prompt_token_count} / 出力 {usage.candidates_token_count} トークン）")
    print("会話を終了しました。")

def main() -> None:
    parser = argparse.ArgumentParser(description="素のLLMに質問する")
    parser.add_argument("question", nargs="?", default=DEFAULT_QUESTION)
    parser.add_argument("--chat", action="store_true", help="会話履歴を保って続けて質問する")
    args = parser.parse_args()

    if args.chat:
        chat()
        return

    print(f"[model] {MODEL}")
    print(f"[質問] {args.question}\n")
    try:
        print(ask(args.question))
    except errors.APIError as e:
        print(api_error_message(e.code, e.message))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
