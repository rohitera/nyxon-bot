#!/data/data/com.termux/files/usr/bin/bash

set -e
cd "$(dirname "$0")"

if [ ! -f "tokens.txt" ]; then
  echo "tokens.txt nahi mila."
  echo "Pehle ./setup_termux.sh chalao."
  exit 1
fi

if [ -z "${TELEGRAM_ADMIN_ID:-}" ]; then
  if [ -f "admin_id.txt" ]; then
    TELEGRAM_ADMIN_ID="$(tr -d '[:space:]' < admin_id.txt)"
  else
    printf "Apni Telegram numeric Admin ID enter karo: "
    read -r TELEGRAM_ADMIN_ID
    printf '%s\n' "$TELEGRAM_ADMIN_ID" > admin_id.txt
  fi
  export TELEGRAM_ADMIN_ID
fi

echo "NYXON BOT start ho raha hai..."
python bot.py