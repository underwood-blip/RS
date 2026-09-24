# 手动上传到 GitHub

目标仓库（空仓）：https://github.com/underwood-blip/RS

不要上传 `.env`（里面有 Telegram Token 和 LLM Key）。仓库里只用 `.env.example`。

压缩包：当前工作区 `/RS-upload.zip`  
解压后应看到：`README.md`、`bot.py`、`.gitignore`、`.env.example`、`tests/` 等。

---

## 方法 A：网页拖拽（最简单）

1. 解压 `RS-upload.zip` 到任意文件夹（例如桌面的 `RS`）。
2. 打开 https://github.com/underwood-blip/RS
3. 点 **Add file** → **Upload files**
4. 把解压出来的**全部内容**拖进页面（含隐藏文件 `.gitignore`、`.env.example`）。
   - Windows 资源管理器：先在「查看」里打开「隐藏的项目」
   - macOS Finder：`Command + Shift + .` 显示隐藏文件
5. Commit message 填：`feat: Telegram bot for lazyrs.trade public market data`
6. 选 **Commit directly to the main branch**
7. 点 **Commit changes**
8. 打开仓库确认没有 `.env`，应有 `.gitignore` 和 `.env.example`

---

## 方法 B：本机 Git 推送

```bash
# 解压压缩包
unzip RS-upload.zip -d RS
cd RS

# 确认没有 .env
ls -la

git init
git add .
git status
```

`git status` 里不能出现 `.env`。然后：

```bash
git commit -m "feat: Telegram bot for lazyrs.trade public market data"
git branch -M main
git remote add origin https://github.com/underwood-blip/RS.git
git push -u origin main
```

若远程已有网页提交，先 `git pull origin main --rebase` 再 push。

---

## 克隆后本地运行

```bash
git clone https://github.com/underwood-blip/RS.git
cd RS
cp .env.example .env
```

编辑 `.env`，填入：

- `USER_TG_BOT_TOKEN`
- `USER_TG_ADMIN_CHAT_ID`（可选，启动时发上线通知）
- `USER_LLM_API_KEY` / `USER_LLM_PROVIDER` / `USER_LLM_MODEL` / `USER_LLM_BASE_URL`（自由问答才需要）

```bash
set -a && . ./.env && set +a
python3 bot.py
```

测试：

```bash
python3 -m unittest discover -s tests -t .
```

数据缓存 120 秒。启动时会 `deleteWebhook`，避免和长轮询冲突。
