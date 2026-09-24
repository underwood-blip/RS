"""自然語言問答：以抓取到的資料做 grounding，支援 Gemini 與 OpenAI 相容端點。

沒有 API Key 或模型失敗時，降級為規則式應答（關鍵字路由 + 確定性查詢）。
"""
import json
import ssl
import urllib.error
import urllib.request

import config
import format as fmt
import query

_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE

SYSTEM = (
    "你是 RS Terminal 行情數據助手。只能根據下方提供的即時數據回答，"
    "用繁體中文、250 字以內、條列清楚。不要編造數據或新聞，"
    "數據不足時直接說無法判斷。不做投資建議。"
)


def _post_gemini(prompt):
    url = f"{config.LLM_BASE_URL}/models/{config.LLM_MODEL}:generateContent"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 800},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": config.LLM_API_KEY},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=config.LLM_TIMEOUT, context=_CTX) as resp:
        data = json.loads(resp.read().decode("utf-8", "ignore"))
    return data["candidates"][0]["content"]["parts"][0]["text"]


def _post_openai(prompt):
    url = f"{config.LLM_BASE_URL}/chat/completions"
    body = {
        "model": config.LLM_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {config.LLM_API_KEY}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=config.LLM_TIMEOUT, context=_CTX) as resp:
        data = json.loads(resp.read().decode("utf-8", "ignore"))
    return data["choices"][0]["message"]["content"]


def build_context(snap, question=""):
    """組出精簡的數據摘要，控制 token 用量。"""
    parts = []
    tiles = query.macro_tiles(snap)
    if tiles:
        parts.append("指數/商品：" + "；".join(
            f"{t['name']} {t['price']} 1D {query.pct(t['d1'])} 5D {query.pct(t['d5'])}" for t in tiles))
    cross = (snap.get("home") or {}).get("cross") or []
    if cross:
        ranked = sorted(cross, key=lambda r: r.get("score") or 0, reverse=True)
        parts.append("跨市場最強：" + "；".join(
            f"{r['name']}({r.get('symbol')}) 分數{r.get('score'):.2f} 5D {query.pct(r.get('d5'))}"
            for r in ranked[:6]))
        parts.append("跨市場最弱：" + "；".join(
            f"{r['name']}({r.get('symbol')}) 分數{r.get('score'):.2f} 5D {query.pct(r.get('d5'))}"
            for r in ranked[-6:]))
    p = snap.get("home", {}).get("pulse") or {}
    if p.get("groups"):
        seg = []
        for g in p["groups"]:
            names = ", ".join(f"{i.get('ticker')}({i.get('name')})" for i in g["items"][:5])
            seg.append(f"{g['title']}：{names}")
        parts.append("RS Pulse：" + "；".join(seg))
    for tab, data in (snap.get("tabs") or {}).items():
        rows = [r for r in data["rows"] if r.get("score") is not None]
        rows.sort(key=lambda r: r["score"], reverse=True)
        parts.append(f"{data['label']}前5：" + "；".join(
            f"{r.get('name')}({r.get('symbol')}) {r.get('score'):.2f}" for r in rows[:5]))
    # 若問題點名某標的，補上詳情
    hits = query.find_symbols_in_text(snap, question, limit=1)
    if hits:
        h = hits[0]
        parts.append(f"查詢標的 {h['symbol']}：分數 {h.get('score')}，超額 {h.get('excess')}，"
                     f"板塊 {h.get('sectorName')}，rsLine 末值 {(h.get('rsLine') or [None])[-1]}")
    return "\n".join(parts)


def _ask(prompt):
    if config.LLM_PROVIDER == "openai":
        return _post_openai(prompt)
    return _post_gemini(prompt)


def rule_answer(question, snap):
    q = (question or "").strip()
    hits = query.find_symbols_in_text(snap, q, limit=5)
    if hits:
        return fmt.symbol_hits(hits, q)
    if any(k in q for k in ("pulse", "異動", "走強", "走弱", "領先")):
        return fmt.pulse_text(snap)
    if any(k in q for k in ("板塊", "sector")):
        return fmt.sector_text(query.sector_leaders(snap))
    if any(k in q for k in ("最強", "top", "排行", "強勢")):
        return fmt.top_list(query.top(snap, None, 10), "相對強弱排行（全部）")
    if any(k in q for k in ("最弱", "bottom", "弱勢")):
        return fmt.top_list(query.top(snap, None, 10, reverse=False), "最弱排行（全部）")
    return fmt.overview(snap)


def answer(question, snap, use_llm=True):
    if not use_llm or not config.LLM_API_KEY:
        return [rule_answer(question, snap)]
    context = build_context(snap, question)
    prompt = f"{SYSTEM}\n\n=== 即時數據 ===\n{context}\n\n=== 用戶問題 ===\n{question}"
    try:
        text = _ask(prompt).strip()
        if not text:
            raise RuntimeError("empty response")
        return [text]
    except Exception as e:  # noqa: BLE001
        note = f"（模型暫時不可用：{str(e)[:120]}，以下為規則輸出）\n"
        return [note + rule_answer(question, snap)]
