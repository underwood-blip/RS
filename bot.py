"""Telegram 長輪詢機器人（標準庫，零第三方依賴）。"""
import json
import ssl
import time
import urllib.parse
import urllib.request

import config
import fetcher
import format as fmt
import llm
import query

_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE


class Telegram:
    def __init__(self, token=None):
        self.token = token or config.TELEGRAM_TOKEN

    def api(self, method, **params):
        url = f"https://api.telegram.org/bot{self.token}/{method}"
        data = urllib.parse.urlencode(params).encode("utf-8")
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=config.HTTP_TIMEOUT + 30, context=_CTX) as resp:
            return json.loads(resp.read().decode("utf-8", "ignore"))

    def send(self, chat_id, text):
        # Telegram 單則上限 4096 字
        for i in range(0, len(text), 4000):
            self.api("sendMessage", chat_id=chat_id, text=text[i:i + 4000],
                     disable_web_page_preview="true")

    def get_updates(self, offset=None, timeout=30):
        params = {"timeout": timeout}
        if offset is not None:
            params["offset"] = offset
        return self.api("getUpdates", **params)


class Engine:
    def __init__(self, use_llm=True):
        self.use_llm = use_llm
        self._snap = None

    def snapshot(self, force=False, tabs=None):
        if force or self._snap is None:
            self._snap = fetcher.snapshot(force=force, tabs=tabs)
            return self._snap
        if tabs == [] and self._snap.get("home"):
            return self._snap
        if tabs and not all(t in (self._snap.get("tabs") or {}) for t in tabs):
            extra = fetcher.snapshot(force=False, tabs=tabs)
            self._snap.setdefault("tabs", {}).update(extra.get("tabs") or {})
            self._snap.setdefault("home", extra.get("home") or self._snap.get("home"))
        return self._snap


class RateLimiter:
    def __init__(self, per_minute=None):
        self.per_minute = per_minute or config.RATE_LIMIT_PER_MIN
        self.hits = {}

    def allow(self, user_id):
        now = time.time()
        bucket = [t for t in self.hits.get(user_id, []) if now - t < 60]
        if len(bucket) >= self.per_minute:
            self.hits[user_id] = bucket
            return False
        bucket.append(now)
        self.hits[user_id] = bucket
        return True


def _parse_top_args(args, default_n=10):
    """支援 /top、/top 美股、/top 美股 10、/top 10。"""
    tab, n = None, default_n
    for a in args:
        if a.isdigit():
            n = max(1, min(50, int(a)))
        else:
            maybe = query.parse_tab_arg(a)
            if maybe:
                tab = maybe
    return tab, n


def handle(engine, text, limiter=None, user_id=0):
    text = (text or "").strip()
    if limiter and not limiter.allow(user_id):
        return ["查詢過於頻繁，請稍後再試。"]
    if not text:
        return [fmt.HELP]

    if text.startswith("/"):
        parts = text.split()
        cmd = parts[0].split("@")[0].lower()
        args = parts[1:]
        try:
            if cmd in ("/start", "/help"):
                return [fmt.HELP]
            if cmd == "/market":
                return [fmt.overview(engine.snapshot(tabs=[]))]
            if cmd == "/refresh":
                snap = engine.snapshot(force=True)
                errs = snap.get("errors") or {}
                note = f"，失敗分頁 {len(errs)}" if errs else ""
                return [f"已重新抓取，更新時間 {snap.get('fetched_at')}{note}。"]
            if cmd == "/top":
                tab, n = _parse_top_args(args)
                snap = engine.snapshot()
                rows = query.top(snap, tab, n)
                title = f"相對強弱排行 - {config.TABS.get(tab, '全部')}（前 {n}）"
                return [fmt.top_list(rows, title)]
            if cmd == "/bottom":
                tab, n = _parse_top_args(args)
                snap = engine.snapshot()
                rows = query.top(snap, tab, n, reverse=False)
                title = f"最弱排行 - {config.TABS.get(tab, '全部')}（前 {n}）"
                return [fmt.top_list(rows, title)]
            if cmd == "/sym":
                if not args:
                    return ["用法：/sym NVDA"]
                snap = engine.snapshot()
                hits = query.find_symbols(snap, " ".join(args), limit=8)
                return [fmt.symbol_hits(hits, " ".join(args))]
            if cmd == "/pulse":
                return [fmt.pulse_text(engine.snapshot())]
            if cmd == "/sector":
                return [fmt.sector_text(query.sector_leaders(engine.snapshot()))]
            if cmd == "/compare":
                if len(args) < 2:
                    return ["用法：/compare NVDA AMD"]
                snap = engine.snapshot()
                a = query.find_symbols(snap, args[0], limit=1)
                b = query.find_symbols(snap, args[1], limit=1)
                return [fmt.compare_text(a[0] if a else None, b[0] if b else None)]
            return [f"未知指令 {cmd}\n\n{fmt.HELP}"]
        except fetcher.FetchError as e:
            return [f"抓取失敗，請稍後再試。\n{str(e)[:200]}"]
        except Exception as e:  # noqa: BLE001
            return [f"處理失敗：{str(e)[:200]}"]

    snap = engine.snapshot()
    return llm.answer(text, snap, use_llm=engine.use_llm)


def run():
    missing = config.validate()
    if missing:
        raise SystemExit("缺少設定：" + ", ".join(missing))
    engine = Engine(use_llm=config.llm_enabled())
    limiter = RateLimiter()
    tg = Telegram()
    try:
        print("deleteWebhook", tg.api("deleteWebhook", drop_pending_updates="true"), flush=True)
    except Exception as e:  # noqa: BLE001
        print("deleteWebhook error:", e, flush=True)
    offset = None
    mode = "LLM+規則" if config.llm_enabled() else "純規則"
    print(f"lazyrs-tg-bot started（問答模式：{mode}）", flush=True)
    while True:
        try:
            upd = tg.get_updates(offset=offset, timeout=30)
        except Exception as e:  # noqa: BLE001
            print("getUpdates error:", e)
            time.sleep(5)
            continue
        for item in upd.get("result") or []:
            offset = item["update_id"] + 1
            msg = item.get("message") or {}
            chat = msg.get("chat") or {}
            user = msg.get("from") or {}
            text = msg.get("text")
            chat_id = chat.get("id")
            if not chat_id or not text:
                continue
            for out in handle(engine, text, limiter, user.get("id") or chat_id):
                try:
                    tg.send(chat_id, out)
                except Exception as e:  # noqa: BLE001
                    print("send error:", e)


if __name__ == "__main__":
    run()
