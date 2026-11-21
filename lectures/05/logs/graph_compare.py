from app.retrieval import search_graph
qs = ["コンパクション セッション 長期メモリ", "コンパクション セッション 長期メモリ 第3回",
      "コンパクション セッション メモリ 長期メモリ 日々のメモ", "メモリ"]
for q in qs:
    for mode in ("id", "semantic"):
        r = search_graph(q, rank_by=mode)
        ex = [f"{'' if c['lecture']==3 else '第%d回' % c['lecture']}p{c['page']}" for c in r["expanded"]]
        print(f"[{mode:8}] {q} | 入口 {[p['page'] for p in r['seeds']]} | 候補 {ex} | p13 {'○' if any(c['page_id']=='lec03-main-p013' for c in r['seeds']+r['expanded']) else '×'}")
