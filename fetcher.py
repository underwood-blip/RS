"""抓取並解析 lazyrs.trade 的公開資料。

資料以 Next.js RSC 形式內嵌在頁面 HTML 的 self.__next_f.push 中，
本模組還原該負載後取出結構化 props（rows / counts / macro tiles）。
只取公開分頁，不繞過會員限制。
"""
import gzip
import json
import re
import ssl
import time
import urllib.request
from datetime import datetime, timezone

import cache
import config

_CTX = ssl.create_default_context()
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
_CACHE = cache.TTLCache(config.CACHE_TTL)

_PUSH_RE = re.compile(r"self\.__next_f\.push\(\[1,(.*?)\]\)", re.S)


class FetchError(RuntimeError):
    pass


def _get(url):
    last = None
    for attempt in range(config.HTTP_RETRIES + 1):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": _UA, "Accept": "text/html,application/json"}
            )
            with urllib.request.urlopen(req, timeout=config.HTTP_TIMEOUT, context=_CTX) as resp:
                raw = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                return raw.decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            last = e
            if attempt < config.HTTP_RETRIES:
                time.sleep(1.5 * (attempt + 1))
    raise FetchError(f"GET {url} failed: {last}")


def _flight(html):
    """把 RSC push 片段還原成連續字串。"""
    out = []
    for m in _PUSH_RE.finditer(html):
        chunk = m.group(1)
        try:
            out.append(json.loads(chunk))
        except Exception:  # noqa: BLE001
            out.append(chunk)
    return "".join(out)


def _json_array_at(text, start):
    """從 text[start] 的 '[' 起做括號配對，回傳平衡的 JSON 陣列字串。"""
    if start >= len(text) or text[start] != "[":
        return None
    depth = 0
    i = start
    while i < len(text):
        c = text[i]
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
        elif c == '"':
            i += 1
            while i < len(text) and text[i] != '"':
                if text[i] == "\\":
                    i += 1
                i += 1
        i += 1
    return None


def _rows_arrays(flight):
    arrays = []
    for m in re.finditer(r'"rows":\[', flight):
        raw = _json_array_at(flight, m.end() - 1)
        if raw is None:
            continue
        try:
            arrays.append(json.loads(raw))
        except Exception:  # noqa: BLE001
            continue
    return arrays


def strip_symbol(symbol):
    """'LB:SMH.US' -> 'SMH.US'，'BN:BTCUSDT' -> 'BTCUSDT'。"""
    if symbol and ":" in symbol:
        return symbol.split(":", 1)[1]
    return symbol or ""


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _num(text):
    if text is None:
        return None
    try:
        return float(str(text).replace(",", "").replace("%", "").strip())
    except ValueError:
        return None


# ---------------- 分頁排行榜 ----------------

def fetch_tab(tab):
    """抓取單一公開分頁，回傳 {"tab","label","rows","fetched_at"}。"""
    if tab not in config.TABS:
        raise ValueError(f"未知分頁：{tab}（可用：{','.join(config.TABS)}）")

    def produce():
        url = f"{config.LAZYRS_BASE_URL}/?tab={tab}"
        flight = _flight(_get(url))
        arrays = _rows_arrays(flight)
        if not arrays:
            raise FetchError(f"{tab} 找不到 rows 資料")
        # 分頁 rows 帶 scoreVol / excess 欄位；取最大者
        rows = max(arrays, key=len)
        return {"tab": tab, "label": config.TABS[tab], "rows": rows, "fetched_at": _now()}

    return _CACHE.get_or_set(f"tab:{tab}", produce)


def parse_macro_tiles(flight):
    """解析首頁頂部指數條（macro-tile）。"""
    tiles = []
    marks = list(re.finditer(r'"([A-Z]{2,4}:[A-Z0-9.]+)",\{"className":"macro-tile"', flight))
    for idx, m in enumerate(marks):
        end = marks[idx + 1].start() if idx + 1 < len(marks) else len(flight)
        seg = flight[m.end():min(end, m.end() + 1500)]
        label = re.search(r'"muted","style":\{[^}]*\},"children":"([^"]+)"', seg)
        price = re.search(r'"fontSize":14[^}]*\},"children":"([0-9.,]+)"', seg)
        rets = re.findall(r'"children":\["(1D|5D) ",.*?"children":\["([+-]?[0-9.]+)","%"', seg)
        ret = {k: _num(v) for k, v in rets}
        tiles.append({
            "symbol": strip_symbol(m.group(1)),
            "raw_symbol": m.group(1),
            "name": label.group(1) if label else None,
            "price": _num(price.group(1)) if price else None,
            "d1": ret.get("1D"),
            "d5": ret.get("5D"),
        })
    return tiles


def parse_pulse(flight):
    """解析首頁 RS Pulse（突然走強 / 持續領先 / 走弱警示）。"""
    counts = None
    m = re.search(r'"counts":(\[[^\]]*\])', flight)
    if m:
        try:
            counts = json.loads(m.group(1))
        except Exception:  # noqa: BLE001
            counts = None

    headers = list(re.finditer(
        r'"title":"([^"]+)","count":(\d+),"hidden":(\d+),"toneName":"([^"]+)"', flight))
    groups = []
    for idx, h in enumerate(headers):
        start = h.start()
        end = headers[idx + 1].start() if idx + 1 < len(headers) else min(len(flight), start + 26000)
        seg = flight[start:end]
        items = []
        li_iter = list(re.finditer(r'\["\$","li","([^"]+)",\{', seg))
        for k, li in enumerate(li_iter):
            end = li_iter[k + 1].start() if k + 1 < len(li_iter) else min(len(seg), li.start() + 2500)
            chunk = seg[li.start():end]
            tick = re.search(
                r'"home-pulse-ticker","data-no-translate":true,"title":"[^"]*","children":"([^"]+)"',
                chunk)
            name = re.search(r'"home-pulse-name[^}]*"children":"([^"]*)"', chunk)
            rank = re.search(r'"children":\["#",\s*(\d+)\]', chunk)
            move = re.search(r'"children":"([↑↓]\d+)"', chunk)
            excess = re.search(
                r'"className":"num (?:up|down|muted)","data-no-translate":true,"children":"([+-]?[0-9.]+%)"',
                chunk)
            hero = re.search(r'"home-pulse-hero[^"]*","data-no-translate":true,"children":\["([+-]?[0-9.]+%)"',
                             chunk)
            streak = re.search(r'"children":"(\d+日)"', chunk)
            items.append({
                "key": li.group(1),
                "ticker": tick.group(1) if tick else None,
                "name": name.group(1) if name else None,
                "rank": int(rank.group(1)) if rank else None,
                "move": move.group(1) if move else None,
                "excess": excess.group(1) if excess else None,
                "hero": hero.group(1) if hero else None,
                "streak": streak.group(1) if streak else None,
            })
        groups.append({"title": h.group(1), "count": int(h.group(2)), "items": items})
    return {"counts": counts, "groups": groups}


def fetch_home():
    """抓取首頁：跨市場排名 + 指數條 + Pulse。"""
    def produce():
        flight = _flight(_get(config.LAZYRS_BASE_URL + "/"))
        arrays = _rows_arrays(flight)
        cross = []
        for rows in arrays:
            if rows and "rankDelta5d" in rows[0]:
                cross = rows
                break
        if not cross and arrays:
            cross = max(arrays, key=len)
        return {
            "cross": cross,
            "macro": parse_macro_tiles(flight),
            "pulse": parse_pulse(flight),
            "fetched_at": _now(),
        }

    return _CACHE.get_or_set("home", produce)


def snapshot(tabs=None, force=False):
    """回傳跨市場 + 指定分頁的合併快照。單一分頁失敗不影響整體。"""
    if force:
        _CACHE.clear()
    home = fetch_home()
    tabs = tabs or list(config.TABS)
    tab_data, errors = {}, {}
    for tab in tabs:
        try:
            tab_data[tab] = fetch_tab(tab)
        except Exception as e:  # noqa: BLE001
            errors[tab] = str(e)
    return {"home": home, "tabs": tab_data, "errors": errors, "fetched_at": _now()}
