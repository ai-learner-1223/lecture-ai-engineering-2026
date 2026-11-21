"""第5回 宿題（実装）: 前後ページの付加。"""

from app.retrieval import expand_neighbors


def page(doc, n):
    return {"page_id": f"{doc}-p{n:03d}", "document_id": doc, "page": n, "content": f"{doc} {n}"}


PAGES = [page("lec01-main", n) for n in range(1, 6)] + [page("lec02-main", n) for n in range(1, 6)]


def ids(results):
    return [r["page_id"] for r in results]


def test_window0_is_plain_search():
    hits = [{**page("lec01-main", 3), "distance": 0.1}]
    assert ids(expand_neighbors(hits, 0, PAGES)) == ["lec01-main-p003"]


def test_adds_prev_and_next_in_page_order():
    hits = [{**page("lec01-main", 3), "distance": 0.1}]
    out = expand_neighbors(hits, 1, PAGES)
    assert ids(out) == ["lec01-main-p002", "lec01-main-p003", "lec01-main-p004"]
    assert out[0]["retrieved_by"] == "neighbor" and out[0]["neighbor_of"] == "lec01-main-p003"
    assert "distance" not in out[0]


def test_does_not_cross_documents():
    hits = [{**page("lec01-main", 5), "distance": 0.1}, {**page("lec02-main", 1), "distance": 0.2}]
    assert ids(expand_neighbors(hits, 1, PAGES)) == [
        "lec01-main-p004", "lec01-main-p005", "lec02-main-p001", "lec02-main-p002"]


def test_no_duplicates_and_hits_stay_hits():
    hits = [{**page("lec01-main", 2), "distance": 0.1}, {**page("lec01-main", 3), "distance": 0.2}]
    out = expand_neighbors(hits, 1, PAGES)
    assert ids(out) == ["lec01-main-p001", "lec01-main-p002", "lec01-main-p003", "lec01-main-p004"]
    assert [r["retrieved_by"] for r in out] == ["neighbor", "search", "search", "neighbor"]
