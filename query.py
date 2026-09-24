"""確定性查詢引擎：在抓取到的快照上做篩選、排序、查找。"""
import config
import fetcher


def _norm(symbol):
    return fetcher.strip_symbol(symbol).upper()


def all_rows(snap):
    """攤平所有分頁的 rows，附上 tab 標籤。"""
    out = []
    for tab, data in (snap.get("tabs") or {}).items():
        for r in data.get("rows") or []:
            r = dict(r)
            r["_tab"] = tab
            r["_label"] = data.get("label", config.TABS.get(tab, tab))
            out.append(r)
    return out


def find_symbols(snap, query, limit=8):
    """在跨市場與所有分頁中尋找符合代號或名稱的標的。"""
    q = (query or "").strip().upper()
    if not q:
        return []
    hits, seen = [], set()

    def consider(row, tab_label, cross=False):
        sym = _norm(row.get("symbol"))
        name = (row.get("name") or "")
        bare = sym.split(".")[0]
        matched = (
            q == sym or q == bare or sym.startswith(q + ".")
            or q in name.upper()
        )
        if not matched:
            return
        key = sym
        if key in seen:
            return
        seen.add(key)
        ex = row.get("excess")
        hits.append({
            "symbol": sym, "raw_symbol": row.get("symbol"), "name": name,
            "tab": "cross" if cross else tab_label, "price": row.get("price"),
            "score": row.get("score"), "scoreVol": row.get("scoreVol"),
            "excess": ex if isinstance(ex, dict) else None,
            "d1": row.get("d1"), "d5": row.get("d5"),
            "d20": row.get("d20"), "d60": row.get("d60"),
            "rankDelta": row.get("rankDelta") or row.get("rankDelta5d"),
            "vsSector": row.get("vsSector"), "sectorName": row.get("sectorName"),
            "sectorRank": row.get("sectorRank"), "sectorTotal": row.get("sectorTotal"),
            "hi20": row.get("hi20"), "lo20": row.get("lo20"),
            "streak": row.get("streak"), "rsLine": row.get("rsLine"),
        })

    for r in (snap.get("home") or {}).get("cross") or []:
        consider(r, "cross", cross=True)
    for r in all_rows(snap):
        consider(r, r["_label"])
    # 精確代號優先
    hits.sort(key=lambda h: (0 if h["symbol"].split(".")[0] == q else 1, -abs(h.get("score") or 0)))
    return hits[:limit]


def find_symbols_in_text(snap, text, limit=8):
    """從自然語言句子中抽出可能的代號/名稱並查找（供問答用）。"""
    import re
    hits, seen = [], set()
    for tok in re.findall(r"[A-Za-z0-9.\-]{2,}", (text or "").upper()):
        for h in find_symbols(snap, tok, limit=4):
            if h["symbol"] not in seen:
                seen.add(h["symbol"])
                hits.append(h)
    return hits[:limit]


def has_any_symbol(snap):
    return bool(all_rows(snap) or (snap.get("home") or {}).get("cross"))


def top(snap, tab=None, n=10, reverse=True):
    rows = all_rows(snap)
    if tab and tab != "all":
        rows = [r for r in rows if r["_tab"] == tab]
    rows = [r for r in rows if r.get("score") is not None]
    rows.sort(key=lambda r: r["score"], reverse=reverse)
    return rows[:n]


def cross_top(snap, n=8, reverse=True):
    rows = list((snap.get("home") or {}).get("cross") or [])
    rows.sort(key=lambda r: r.get("score") or 0, reverse=reverse)
    return rows[:n]


def macro_tiles(snap):
    return (snap.get("home") or {}).get("macro") or []


def pulse(snap):
    return (snap.get("home") or {}).get("pulse") or {"counts": [], "groups": []}


def sector_leaders(snap, n=15):
    """美股各板塊中分數最高的龍頭股（每個板塊取一檔），依板塊分數排序。

    注意：row 的 sectorRank 是「該板塊在所有板塊中的排名」，並非個股在板塊內的排名，
    因此這裡以 sectorSymbol 分組、取組內最高分。
    """
    rows = [r for r in all_rows(snap) if r["_tab"] == "stocks" and r.get("sectorSymbol")]
    best = {}
    for r in rows:
        key = r.get("sectorSymbol")
        if key not in best or (r.get("score") or -1e9) > (best[key].get("score") or -1e9):
            best[key] = r
    out = list(best.values())
    out.sort(key=lambda r: (r.get("sectorScore") if r.get("sectorScore") is not None
                            else (r.get("score") or 0)), reverse=True)
    return out[:n]


def parse_tab_arg(arg):
    a = (arg or "").strip().lower()
    alias = {
        "us": "stocks", "美股": "stocks", "stock": "stocks",
        "hk": "hkstocks", "港股": "hkstocks",
        "crypto": "crypto", "加密": "crypto", "幣": "crypto",
        "fx": "fx", "外匯": "fx", "forex": "fx",
        "commodities": "commodities", "商品": "commodities", "大宗": "commodities",
        "全部": "all", "all": "all",
    }
    return alias.get(a, a if a in config.TABS else None)


def pct(v, digits=2):
    if v is None:
        return "n/a"
    try:
        return f"{v:+.{digits}f}%"
    except (TypeError, ValueError):
        return "n/a"
