# NYXON BOT

Telegram bot prepared for Termux and Railway deployment.

## Railway deployment

1. Deploy this repository on Railway.
2. Add these Railway Variables:
   - `TELEGRAM_ADMIN_ID` — your numeric Telegram user ID
   - `BOT_TOKEN_1` through `BOT_TOKEN_15` — one token per variable

Alternatively, use `BOT_TOKENS` with one or more bot tokens separated by commas or new lines.

Railway uses `python bot.py` as the start command.

Never commit real Telegram tokens, admin IDs, `tokens.txt`, or `.env` files.

## Termux

```bash
python -m pip install -r requirements.txt
bash setup_termux.sh
```

For custom hyphen commands such as `-ping` in groups, disable Group Privacy in BotFather. Slash commands such as `/ping` remain the reliable fallback.