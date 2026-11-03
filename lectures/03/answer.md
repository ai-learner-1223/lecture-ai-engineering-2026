# 第3回 解答

## 演習

- 第1回（素のLLM）とエージェントの回答の違い：
  同じ質問「AIE2026の講座の宿題にある『3レベル』とは何ですか？」で比べた。app.ask は講座のことを知らず、「初級・中級・上級」「AI活用レベル」など一般論を2通り推測し、資料の確認を勧めて終わった。app.agent は用語集（homework-levels）を検索し、「基礎・実装・発展の3段階で、どれか1つで完了、原則採点しない」と定義どおりに答え、最後に「関係する回：第1回」を付けた。
- `--trace` で見えたツール呼び出し（ツール名と引数）：
  質問「LoRAとQLoRAの違いは？」で、`search_glossary({'query': 'LoRA'})` と `search_glossary({'query': 'QLoRA'})` の2回。docstring の「query には調べたい用語を1つだけ入れる」に従い、用語ごとに別々に検索していた。
- 1つの質問での LLM 呼び出し回数（`requests`）：
  `requests=2, tool_calls=2`。1回目の呼び出しで2つの検索を並列に依頼し、2回目で検索結果を使って回答を生成した。
- 追加したツールと、docstring に書いた説明：
  `make_quiz(lecture: int)`。docstring は「指定した回の用語から1つを選び、確認問題と答えを返す。『第2回の確認問題を出して』のように、復習用の問題を求められたときに使う。lecture には回の番号を整数で入れる。返り値は question と answer を含む JSON。利用者が答えるまで answer は見せない。」とした。「第2回の内容から確認問題を1問出して」で `make_quiz({'lecture': 2})` が呼ばれ（`requests=2, tool_calls=1`）、「過学習」の問題が出題された。ツールは答えも返したが、モデルは docstring に従って答えを伏せて出題した。用語が無い回（lecture=0）ではエラーメッセージを返すようにし、`pytest` は 11 passed。

## 宿題

- 取り組んだレベル：発展（a）ADK で作り直す
- やったこと：
  `adk_agent/glossary_agent/` に `agent.py` と `__init__.py` を作り、演習と同じ `INSTRUCTIONS` と3つのツール（`search_glossary`・`get_lecture_summary`・`make_quiz`）を ADK の `Agent` に渡した。`PYTHONPATH=. uv run --with google-adk adk run adk_agent/glossary_agent` で起動し（モデルは gemini-3.5-flash-lite）、演習と同じ3つの質問を投げた。
- 結果：
  - 「3レベル」：基礎・実装・発展のどれか1つで完了、原則採点しない、関係する回：第1回。Pydantic AI 版とほぼ同じ回答。
  - 「LoRAとQLoRAの違い」：用語集の定義に沿った説明で、関係する回：第2回。こちらも同等。
  - 「第2回の確認問題」：「事前学習」の意味を問う問題を出し、答えは伏せた（演習では「過学習」。make_quiz が random.choice で選ぶため毎回変わる）。
  - 書き方の違い：Pydantic AI は `Agent(instructions=...)` を作ってから `agent.tool_plain(関数)` で1つずつ登録し、自前の CLI（`app/agent.py`）から `run_sync` で実行する。ADK は `Agent(name=..., model=..., instruction=..., tools=[関数, ...])` とコンストラクタにまとめて渡し、`root_agent` という変数名と `__init__.py` の規約で `adk run` がエージェントを見つけて対話 CLI を提供する。どちらも関数の docstring と型ヒントからツールの説明を自動で作る点は同じ。
- 気づき・疑問：
  - 指示とツールの docstring が同じなら、フレームワークを変えても回答やふるまいはほぼ変わらなかった。ふるまいを決めているのはフレームワークより指示と docstring だと分かった。
  - `adk run` は会話の履歴を保ったまま続く対話形式で、1問ごとに終わる `app.agent` と違う。途中で誤って入力した文も履歴に残る。
  - `adk run` には `--trace` に相当する表示がなく、どのツールが何回呼ばれたかが画面からは分からない。確認するには `adk web` のイベント表示などを使う必要がありそう。
