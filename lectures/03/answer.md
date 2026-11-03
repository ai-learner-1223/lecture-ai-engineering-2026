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
  - `adk run` には `--trace` に相当する表示がないため、`adk web`（ブラウザの開発画面）で確認した。Events に `search_glossary("LoRA")` と `search_glossary("QLoRA")` が1回の応答で並列に呼ばれ、結果を受けて回答が生成される流れが表示され、演習の Pydantic AI 版（requests=2, tool_calls=2）と同じ呼ばれ方だった。ただし Codespaces では、ADK 2.x の DNS リバインディング対策で JS が 403 になり画面が真っ黒になったため、`--allow_origins "*"` を付けて起動する必要があった（URL を1つ許可するだけでは不十分だった）。

### 追加で取り組んだもの：基礎（INSTRUCTIONS・docstring を1か所ずつ変えて比較）

比較の基準（変更なし）：「LoRAとQLoRAの違いは？」で `search_glossary('LoRA')`・`search_glossary('QLoRA')` の2回、`requests=2, tool_calls=2`、末尾に「関係する回：第2回」。

- 実験1：`search_glossary` の docstring「query には調べたい用語を1つだけ入れる」を「まとめて入れる（例: "LoRA QLoRA"）」に変更
  - 結果：`search_glossary({'query': 'LoRA QLoRA'})` の1回にまとまった（`tool_calls` 2→1、`requests` は2のまま）。ツールを直接呼ぶと、まとめたクエリでも LoRA・QLoRA の両方の定義が返っており、回答の内容は同等だった。
  - 気づき：docstring の例が、そのまま引数の形に反映された。このツールは部分一致で複数語を拾えるので「1つずつ」は必須ではなかったが、完全一致の検索などではまとめると取りこぼす可能性がある。
- 実験2：`INSTRUCTIONS` から「必ず search_glossary で用語集を確認する」の行を削除
  - 結果：「3レベル」でも「LoRAとQLoRA」でも、削除前と同じように検索してから答えた。
  - 気づき：`search_glossary` の docstring にも「答える前に使うこと」と書いてあり、指示が2か所に重なっていたため、片方を消しても効果が残った。末尾の回の表記は「（関連回：第1回）」「（第2回）」のように揺れた。
- 実験3：`INSTRUCTIONS` の「回答の最後に、関係する回（第N回）を示す」を「回答の最後に、内容の理解を確かめる確認問題を1問出す」に変更
  - 結果：「関係する回」の行が消え、末尾に確認問題が付いた（出力トークン 167→256）。ただし `make_quiz` は呼ばれず、モデルが検索結果から自分で問題を作った。
  - 気づき：指示にツール名が無く、`make_quiz` は回の番号からランダムに用語を選ぶ作りなので、質問の話題に合った問題を出すにはモデルが自分で書くほうを選んだと考えられる。ツールを使わせたいなら、指示にツール名と使う場面を書く必要がある。

### 追加で取り組んだもの：実装（承認付きの save_learning_log）

- やったこと：
  - `app/tools.py` に `save_learning_log(title, content)` を作り、`learning_log/` に「日時_題名.md」で保存するようにした。
  - `app/agent.py` で `agent.tool_plain(tools.save_learning_log, requires_approval=True)` と登録し、`output_type=[str, DeferredToolRequests]` を指定した。
  - CLI では、結果が `DeferredToolRequests` の間、`approvals` の各呼び出しのツール名と引数を表示して `[y/N]` で聞き、y なら `True`、それ以外は `ToolDenied` を `DeferredToolResults` に入れ、`message_history=result.all_messages()` と一緒に `run_sync` で再実行するようにした。
- 結果：
  - 最初の版では止まらなかった。trace を見ると `save_learning_log` は呼ばれておらず、モデルが回答の最後で「学習ログに保存しますか？」と自分で聞いて終わっていた。docstring に「実行の前に利用者の承認を求める」と書いたため、承認を会話で取るものと解釈したと考えられる。
  - docstring と INSTRUCTIONS を「確認はプログラムが自動で行うので、会話で確認を求めずに直接呼ぶ」に直すと、`[approval] save_learning_log …` で実行が止まり、title と content が表示された。
  - y：`learning_log/20261103-064610_LoRAとQLoRAの違い.md` が保存され、モデルは「保存しました」と伝えて回答を終えた。
  - n：ツールの結果として「利用者が実行を許可しませんでした。」がモデルに返り、ファイルは作られなかった。モデルは過学習の説明を返して終わった。
- 気づき・疑問：
  - 承認の仕組みがあっても、docstring の一文で「モデルが自分で確認する」方向に流れてツールが呼ばれなくなった。基礎の実験と同じく、説明文がふるまいを左右する。
  - 再開後の `[usage]` は requests=1 で、再開した実行の分しか数えていない。1回目（検索→保存の依頼）の requests=2 と合わせると、実際は計3回 LLM を呼んでいる。
  - 拒否したとき、モデルは「保存しなかった」ことに触れなかった。`ToolDenied` のメッセージに「保存しなかったことを利用者に伝える」と書き足すと改善できそう。
  - モデルが content の先頭に見出しを書いてきて、ツールの付ける見出しと二重になった。モデルへの指示ではなく、ツール側で「content が # で始まるなら見出しを足さない」ようにして防いだ。

### 追加で取り組んだもの：発展（b）Pi を Codespaces で動かす

- やったこと：`npm install -g --ignore-scripts @earendil-works/pi-coding-agent` で入れ、`pi --model gemini-3.1-flash-lite` で起動して「app/tools.py を読んで、どんなツールが定義されているか説明して」と聞いた。インストール先の `dist/core/system-prompt.js` を読み、システムプロンプトの組み立て方を自分の `INSTRUCTIONS` と比べた。
- 結果：
  - 起動時に fd・ripgrep を確認なしで自分でダウンロードした。質問には `read app/tools.py:1-2000` を確認なしで実行し、`save_learning_log` を含む4つのツールを正しく説明した（入力 約4.1k トークン、出力 403 トークン）。
  - 既定のモデルは gemini-3.1-pro-preview で、無料枠の上限が 0 のため 429 になった。Codespaces のブラウザ上のターミナルではモデル選択の画面が操作しにくく、起動オプション `--model` で指定した。
  - Pi のシステムプロンプトは固定文ではなく、preamble（役割）・tools（ツール一覧と説明）・rules（ツール構成に応じた規則と「簡潔に」「パスを示す」）・docs（Pi 自身の文書の場所）・project_context（AGENTS.md などの差し込み）・skills・cwd の部品をタグで区切って組み立てる作りだった。
- 比較：
  - Pi にあって自分のに無いもの：本文中のツール一覧、作業フォルダやプロジェクト指示などの環境情報、出力の一般規則、ツール構成や拡張で変わる可変の構成。
  - 自分のにあって Pi に無いもの：用語集に無いことは断定しないという根拠の規則、答える前に必ず調べる順序、最後に関係する回を示す形式、宿題の答えを書かないという教育上の制約。汎用のコーディングエージェントと、用途を絞ったエージェントの違いが出た。
  - どちらにも無いもの：確認を求める規則。Pi は確認なしで動き、自分のエージェントは確認をプロンプトではなく `requires_approval=True`（プログラム）で行っている。実装の宿題で、docstring に「承認を求める」と書くとモデルが自分で聞いてツールを呼ばなくなったこととあわせて、安全のための確認はプロンプトより仕組みで担うほうが確実だと分かった。
