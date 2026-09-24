# lazyrs-tg-bot

Telegram 机器人：抓取 [lazyrs.trade](https://lazyrs.trade/) 公开分页，用命令或自然语言查市场行情。

只读大众版（美股 / 港股 / 加密 / 外汇 / 商品）。会员页不抓。零第三方依赖。

## 指令

- `/market` 今日概况
- `/top [美股|港股|加密|外汇|商品] [N]`
- `/bottom ...`
- `/sym NVDA`
- `/pulse` 异动
- `/sector` 板块龙头
- `/compare A B`
- `/refresh`
- 自由文本：有 LLM Key 时用模型回答，否则走规则匹配

## 启动

```bash
cp .env.example .env
# 填 USER_TG_BOT_TOKEN；自由问答再填 USER_LLM_API_KEY
set -a && . ./.env && set +a
python3 bot.py
```

测试：`python3 -m unittest discover -s tests -t .`

数据缓存 120 秒，避免对源站高频请求。
