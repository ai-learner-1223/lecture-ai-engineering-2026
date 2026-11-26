# 第6回 解答

## 演習

- STEP 1 のツールの名前：glossary_search_glossary
- STEP 2 の [tool call]：glossary_search_glossary({'query': '3レベル'})
- STEP 3 の [tool call]：fetch_fetch({'url': 'https://modelcontextprotocol.io/'})
- STEP 4 の [tool call]：aws_aws___search_documentation({'search_phrase': 'Amazon S3 バージョニング 概要', 'topics': ['general']})
- 気づき・疑問：
  - 設定ファイルに数行足すだけで、エージェントのコードを変えずに Web 取得や AWS 検索ができるようになった。`--list-tools` の表示でも、command は手元で起動、url は外部に接続、と区別されていた。
  - fetch の説明文に「インターネットにアクセスできるようになった」という、モデルへの指示のような文があった。サーバーの説明文はそのままモデルに渡るので、提供元を確認してから足す必要があると実感した。
  - aws を足す前に同じ質問をしたら、モデルは fetch で AWS のページを直接取りに行った。手持ちのツールで代わりを探す。
  - STEP 4 では、日本語で検索して外れると、英語で検索し直していた。一方で指示文の「必ず用語集を確認」「関係する回を示す」に従い、根拠のない「第1回」を書き足していた。講座専用の指示文が、範囲外の質問では回答をゆがめる。
  - 入力トークンが STEP 2 の 715 から、STEP 3 で 2,230、STEP 4 で 15,959 に増えた。ツールの説明と結果がすべてモデルに渡るので、サーバーを足すほど1回の質問が重くなる。
<!-- [tool call] の行は、表示された行をそのまま貼り付けてください。終わらなかった STEP は、空欄のままでかまいません。 -->


## 宿題

<!-- 基礎・実装・発展のどれか1つに取り組めば完了です。 -->

- 取り組んだレベル：基礎 / 実装 / 発展（3つすべて）

### 基礎：get_lecture_summary を公開する

- やったこと：`app/mcp_server.py` の TODO の下に `server.tool()(tools.get_lecture_summary)` を1行足した。エージェント側（`app/mcp_agent.py`、`app/mcp_servers.json`）は変えていない。
- 結果：
  - `git status` で変更は `app/mcp_server.py` だけだった
  - `--list-tools` に `glossary_get_lecture_summary` が増えた
  - 「第2回では何を学びますか？」の [tool call]：`glossary_get_lecture_summary({'lecture': 2})`。回答は第2回の要点（ファインチューニングとLoRA）に沿っていた
  - `uv run pytest -q` は 21 passed
- 気づき・疑問：エージェントは起動のたびにサーバーへツール一覧を問い合わせるので、サーバー側の1行だけでエージェントのできることが増える。逆に言えば、接続先のサーバーが変わると、エージェントのコードを変えていなくても振る舞いが変わる。外部サーバーの版を固定する（演習の `==2026.11.11`）意味がここにある。なお `data/lectures/` には第5回の要点がない。

### 実装：make_quiz を MCP で公開し、範囲外を扱う

- やったこと：
  - `app/tools.py` に `make_quiz(lecture: int)` を追加し、`app/mcp_server.py` で公開した（ツール名は `glossary_make_quiz`）
  - 範囲外を2種類に分け、どちらも JSON で `error`・`available_lectures`・`hint` を返すようにした
    - 回の番号として不正（0 以下）
    - 番号は正しいが、用語集にその回の用語がない（第5回、第99回）
  - `tests/test_tools.py` に正常系と範囲外のテストを2つ追加した（23 passed）
- 結果：
  - [tool call]：`glossary_make_quiz({'lecture': 99})`
  - [tool return]：`{"error": "第99回の用語は用語集にないため、確認問題を作れません。", "available_lectures": [1, 2, 3, 4, 6], "hint": "…どの回にするか利用者に確認してください。"}`
  - Gemini は別の回で勝手に作らず、作れる回（第1〜4回・第6回）を示して「どの回の問題をご希望ですか？」と聞き返した。モデル応答は2回
  - 比較のため、別のサーバーで返し方を変えて試した（Gemini の代わりに、決まった引数でツールを呼ぶ FunctionModel で確認）

    | 方式 | trace の表示 | モデルが受け取った内容 |
    |---|---|---|
    | 文字列で返す（採用） | `[tool return]` | 自分で書いた JSON がそのまま届く |
    | `ValueError` を投げる | `[tool error]` | `Error executing tool …` だけ。自分のメッセージは届かない |
    | `ToolError` を投げる | `[tool error]` | `Error executing tool …: 第99回の用語は…` が届く |
    | 引数の型で範囲を付ける（`Field(ge=1, le=6)`） | `[tool error]` | pydantic の英語の検証エラーが届く |

    `[tool error]` の3つには、末尾に `Fix the errors and try again.` が付く。
- 気づき・疑問：
  - MCP サーバーは、想定外の例外の中身をクライアントに渡さない。内部の情報を漏らさないための作りだが、そのため `raise ValueError("…")` と丁寧に書いても、モデルには何も伝わらない。モデルに読ませたい失敗は、返り値で返すか `ToolError` を投げる必要がある。
  - エラー扱いにすると「直して呼び直せ」と促されるので、モデルが勝手に別の回で呼び直すおそれがある。「第99回はない」は利用者の判断が要る場面なので、返り値で知らせて `hint` に「利用者に確認して」と書いた。実際に Gemini はそのとおり聞き返した。呼び直しで直せる失敗（型の誤りなど）はエラー扱い、利用者の判断が要る失敗は返り値、と分けるのがよさそう。

### 発展：Claude Code の MCP 設定と比べる

- 調べた日：2026-11-26
- 参照した公式ドキュメント：
  - https://code.claude.com/docs/en/mcp
  - https://code.claude.com/docs/en/mcp-quickstart
- やったこと：Claude Code の MCP サーバーの設定方法を公式ドキュメントで調べ、演習の `app/mcp_servers.json` と比べた。

  | 観点 | 演習（`app/mcp_servers.json`） | Claude Code |
  |---|---|---|
  | 設定を書く場所 | `app/mcp_servers.json` | local（既定）：`~/.claude.json` の、そのプロジェクトの項目の下／project：プロジェクト直下の `.mcp.json`／user：`~/.claude.json`。`claude mcp add` コマンドでも書き込める |
  | コマンドで起動 | `"command"` ＋ `"args"` | 同じ `"command"` ＋ `"args"`（＋`"env"`）。`type` がない項目は stdio として読まれる。コマンドなら `claude mcp add <名前> -- <コマンド> [引数…]` |
  | URL で接続 | `"url"` だけ | `"type": "http"` ＋ `"url"`。`"headers"` で認証ヘッダーを付けられる。コマンドなら `claude mcp add --transport http <名前> <URL>` |
  | 有効になる範囲 | このリポジトリのエージェントだけ | local：自分だけ・このプロジェクトだけ／project：`.mcp.json` をコミットすれば clone した全員／user：自分の全プロジェクト。同じ名前は local → project → user の順に優先される |

- 結果：
  - 外側の `"mcpServers"` の形は同じなので、`glossary` と `fetch` はそのまま `.mcp.json` に移せる
  - いちばん大きな違いは URL の書き方。演習の `"aws": {"url": "…"}` をそのまま写すと、`type` がないので stdio として読まれ、設定の誤りになる。`"type": "http"` を足す必要がある
  - Claude Code には演習にない仕組みがある
    - `.mcp.json` のサーバーは、使う前に利用者の承認を求める（任意のプログラムを起動できるため）
    - `${VAR}` で環境変数を展開できるので、API キーを設定ファイルに直接書かずに済む
- 気づき・疑問：演習のエージェントは、`mcp_servers.json` に書かれたものを確認なしで起動・接続する。演習の補足（提供元とリスクを確認してから足す）を、仕組みとして求めているのが Claude Code の承認だと理解した。演習の STEP 3 で fetch の説明文にモデルへの指示のような文があったことからも、この確認は大事だと思う。設定方法は変わることがあるので、上の内容は調べた日時点のもの。
