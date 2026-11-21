"""第5回 宿題（発展）: Graphの意味順の並べ替え（案B）と、見出し→全文の2段階取得（案A）。

APIは呼ばない。質問の埋め込みの代わりに、検索DBに保存済みのページ埋め込みを使う。
"""

import json

from pydantic_ai.messages import ToolCallPart
from pydantic_ai.models.test import TestModel

from app import retrieval
from app.agent import HYBRID_INSTRUCTIONS, agent, summarize_pages
from app import tools

PAGES = {p["page_id"]: p for p in retrieval.load_pages()}
SEEDS = ["lec03-main-p039", "lec03-main-p040", "lec03-main-p038"]


def fake_search(monkeypatch, seeds=SEEDS, proxy="lec03-main-p039"):
    hits = [{**PAGES[s], "distance": 0.1 * i} for i, s in enumerate(seeds)]
    vector = retrieval.page_embeddings([proxy])[proxy]
    monkeypatch.setattr(retrieval, "search", lambda q: hits)
    monkeypatch.setattr(retrieval, "search_with_vector", lambda q, top_k=5: (hits[:top_k], vector))


def expanded_ids(result):
    return [c["page_id"] for c in result["expanded"]]


def test_id_order_picks_other_lectures_by_page_id(monkeypatch):
    fake_search(monkeypatch)
    ids = expanded_ids(retrieval.search_graph("メモリ", rank_by="id"))
    assert "lec03-main-p013" not in ids
    assert "lec01-main-p019" in ids  # 「メモリ」違い（GPUのメモリ）が文字順で先に来る


def test_semantic_order_reaches_p013(monkeypatch):
    fake_search(monkeypatch)
    result = retrieval.search_graph("メモリ", rank_by="semantic")
    ids = expanded_ids(result)
    assert "lec03-main-p013" in ids
    assert not any(i.startswith(("lec01", "lec02")) for i in ids)
    assert result["rank_by"] == "semantic"
    hops = [c["hops"] for c in result["expanded"]]
    assert hops == sorted(hops)  # hop数が少ない候補が先


def test_candidates_have_no_body(monkeypatch):
    fake_search(monkeypatch)
    candidates = retrieval.search_candidates("メモリ", top_k=3)
    assert [c["page_id"] for c in candidates] == SEEDS
    assert all("content" not in c and c["first_sentence"] for c in candidates)


def test_read_page_tool_returns_full_text_or_error():
    page = json.loads(tools.read_page("lec03-main-p013"))
    assert page["page"] == 13 and len(page["content"]) > 50
    assert "error" in json.loads(tools.read_page("no-such-page"))


def test_hybrid_mode_wires_two_tools(monkeypatch):
    fake_search(monkeypatch)
    model = TestModel(call_tools=["search_candidates", "read_page"])
    with agent.override(model=model, instructions=HYBRID_INSTRUCTIONS,
                        tools=[tools.search_candidates, tools.read_page]):
        result = agent.run_sync("メモリとは？")
    called = {p.tool_name for m in result.all_messages() for p in m.parts if isinstance(p, ToolCallPart)}
    assert called == {"search_candidates", "read_page"}


def test_trace_summary_lists_pages():
    content = json.dumps({"results": [{"lecture": 3, "page": 39}, {"lecture": 3, "page": 40,
                                       "retrieved_by": "neighbor"}]})
    assert summarize_pages(content) == "2件本文付き: 第3回p.39, 第3回p.40(隣)"
