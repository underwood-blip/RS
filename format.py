"""Telegram 訊息排版。純文字，避免 Markdown 轉義問題。"""
import config
from query import pct

HELP = "\n".join([
    "RS Terminal 行情助手 — 只取 lazyrs.trade 公開資料",
    "",
    "指令：",
    "/market — 今日市場概況（跨市場強弱、指數、異動）",
    "/top [美股|港股|加密|外匯|商品|全部] [N] — 相對強弱排行",
    "/bottom [分頁] [N] — 最弱排行",
    "/sym <代號> — 個股/資產詳情",
    "/pulse — RS Pulse 異動榜",
    "/sector — 美股各板塊龍頭",
    "/compare <A> <B> — 兩檔對比",
    "/refresh — 強制重抓（清快取）",
    "",
    "也可直接打字問問題（例如「現在市場最強的是什麼？」），",
    "自由問答需要設定 LLM API Key。",
    "",
    config.DISCLAIMER,
])


def _line_rank(i, r):
    delta = r.get("rankDelta")
    d = ""
    if delta is not None:
        try:
            d = f" ({int(delta):+d})"
        except (TypeError, ValueError):
            d = ""
    return f"{i}. {r.get('name') or r.get('symbol')} [{r.get('symbol')}]  分數 {r.get('score'):.2f}{d}"


def overview(snap):
    home = snap.get("home") or {}
    cross = home.get("cross") or []
    lines = ["今日市場概況", ""]
    tiles = home.get("macro") or []
    if tiles:
        lines.append("指數 / 商品：")
        for t in tiles:
            lines.append(f"  {t['name']}  {t['price']}  1D {pct(t['d1'])}  5D {pct(t['d5'])}")
        lines.append("")
    if cross:
        ranked = sorted(cross, key=lambda r: r.get("score") or 0, reverse=True)
        lines.append("跨市場最強：")
        for r in ranked[:5]:
            lines.append(f"  {r['name']} [{r.get('symbol')}]  分數 {r.get('score'):.2f}  5D {pct(r.get('d5'))}")
        lines.append("跨市場最弱：")
        for r in ranked[-5:]:
            lines.append(f"  {r['name']} [{r.get('symbol')}]  分數 {r.get('score'):.2f}  5D {pct(r.get('d5'))}")
        lines.append("")
    p = home.get("pulse") or {}
    counts = p.get("counts") or []
    if counts:
        lines.append("RS Pulse：" + "，".join(f"{c['label']} {c['n']}" for c in counts))
    lines.append("")
    lines.append(f"更新時間 {snap.get('fetched_at')}")
    lines.append(config.DISCLAIMER)
    return "\n".join(lines)


def top_list(rows, title, label=""):
    if not rows:
        return f"{title}\n沒有資料。"
    lines = [title]
    for i, r in enumerate(rows, 1):
        lines.append(_line_rank(i, r))
        ex = r.get("excess") if isinstance(r.get("excess"), dict) else {}
        extra = []
        if ex:
            extra.append(f"超額 1D {pct(ex.get('d1'))} 5D {pct(ex.get('d5'))} 20D {pct(ex.get('d20'))}")
        if r.get("sectorName"):
            extra.append(f"板塊 {r['sectorName']}#{r.get('sectorRank')}/{r.get('sectorTotal')}")
        if extra:
            lines.append("    " + " | ".join(extra))
    lines.append("")
    lines.append(config.DISCLAIMER)
    return "\n".join(lines)


def symbol_hits(hits, query_text):
    if not hits:
        return f"找不到「{query_text}」。可用 /top 查看清單，或確認代號。"
    if len(hits) > 1:
        lines = [f"找到多個符合「{query_text}」的標的：", ""]
        for h in hits:
            lines.append(f"  [{h['symbol']}] {h['name']}（{h['tab']}）分數 {h.get('score')}")
        lines.append("")
        lines.append("請用 /sym <完整代號> 查看詳情。")
        return "\n".join(lines)
    return symbol_detail(hits[0])


def symbol_detail(h):
    lines = [f"{h.get('name')} [{h.get('symbol')}]"]
    if h.get("tab") and h["tab"] != "cross":
        lines.append(f"市場：{h['tab']}")
    if h.get("price") is not None:
        lines.append(f"價格：{h['price']}")
    lines.append(f"LazyRS 分數：{h.get('score')}（量能 {h.get('scoreVol')}）")
    if h.get("rankDelta") is not None:
        lines.append(f"名次變動：{h['rankDelta']:+d}" if isinstance(h["rankDelta"], (int, float)) else f"名次變動：{h['rankDelta']}")
    ex = h.get("excess") or {}
    if ex:
        lines.append(f"超額報酬：1D {pct(ex.get('d1'))}  5D {pct(ex.get('d5'))}  20D {pct(ex.get('d20'))}")
    if h.get("d60") is not None:
        lines.append(f"60D：{pct(h['d60'])}")
    if h.get("sectorName"):
        lines.append(f"板塊：{h['sectorName']}（第 {h.get('sectorRank')}/{h.get('sectorTotal')}）")
    if h.get("vsSector") is not None:
        lines.append(f"相對板塊強弱：{h['vsSector']:+.2f}")
    if h.get("hi20") is not None and h.get("lo20") is not None:
        lines.append(f"20D 區間：{h['lo20']} ~ {h['hi20']}")
    if h.get("streak"):
        lines.append(f"連續入榜：{h['streak']}")
    rs = h.get("rsLine")
    if rs:
        lines.append(f"rsLine 末 5 值：{', '.join(str(round(x, 3)) for x in rs[-5:])}")
    lines.append("")
    lines.append(config.DISCLAIMER)
    return "\n".join(lines)


def pulse_text(snap):
    p = snap.get("home", {}).get("pulse") or {}
    groups = p.get("groups") or []
    if not groups:
        return "目前沒有 Pulse 資料。"
    lines = ["RS Pulse 最新異動", ""]
    for g in groups:
        lines.append(f"【{g['title']}】共 {g['count']}")
        for i, it in enumerate(g["items"], 1):
            tail = it.get("excess") or it.get("hero") or it.get("streak") or ""
            lines.append(f"  {i}. {it.get('name')} [{it.get('ticker')}]  #{it.get('rank')} {it.get('move') or ''} {tail}")
        lines.append("")
    lines.append(f"更新時間 {snap.get('fetched_at')}")
    lines.append(config.DISCLAIMER)
    return "\n".join(lines)


def sector_text(rows):
    if not rows:
        return "沒有板塊龍頭資料。"
    lines = ["美股板塊龍頭（各板塊分數最高者，依板塊分數排序）", ""]
    for i, r in enumerate(rows, 1):
        sec = r.get("sectorName") or r.get("sectorSymbol")
        sscore = r.get("sectorScore")
        sscore = f"{sscore:.2f}" if isinstance(sscore, (int, float)) else "n/a"
        lines.append(f"{i}. {sec}（板塊分數 {sscore}）— 龍頭 {r.get('name')} [{r.get('symbol')}] "
                     f"分數 {r.get('score'):.2f}")
    lines.append("")
    lines.append(config.DISCLAIMER)
    return "\n".join(lines)


def compare_text(a, b):
    if not a or not b:
        return "兩者都需要找到才能比較。請用 /sym 確認代號。"
    lines = [f"{a['name']} [{a['symbol']}]  vs  {b['name']} [{b['symbol']}]", ""]

    def val(r, k):
        return r.get(k)

    rows = [
        ("LazyRS 分數", val(a, "score"), val(b, "score")),
        ("價格", val(a, "price"), val(b, "price")),
        ("超額 1D", pct((a.get("excess") or {}).get("d1")), pct((b.get("excess") or {}).get("d1"))),
        ("超額 5D", pct((a.get("excess") or {}).get("d5")), pct((b.get("excess") or {}).get("d5"))),
        ("超額 20D", pct((a.get("excess") or {}).get("d20")), pct((b.get("excess") or {}).get("d20"))),
        ("板塊", a.get("sectorName"), b.get("sectorName")),
    ]
    for name, x, y in rows:
        lines.append(f"{name}:  A={x}  B={y}")
    sa, sb = a.get("score") or 0, b.get("score") or 0
    stronger = a if sa >= sb else b
    lines.append("")
    lines.append(f"相對較強：{stronger['name']} [{stronger['symbol']}]")
    lines.append(config.DISCLAIMER)
    return "\n".join(lines)
