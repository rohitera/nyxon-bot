#!/data/data/com.termux/files/usr/bin/bash

set -e
cd "$(dirname "$0")"

echo "NYXON BOT - Termux first-time setup"
echo "===================================="

if ! command -v python >/dev/null 2>&1; then
  echo "Python install ho raha hai..."
  pkg install python -y
fi

echo "Dependencies install ho rahi hain..."
python -m pip install -r requirements.txt

printf "Apni Telegram numeric Admin ID enter karo: "
read -r admin_id
if ! [[ "$admin_id" =~ ^[0-9]+$ ]]; then
  echo "Admin ID sirf numbers mein honi chahiye."
  exit 1
fi
printf '%s\n' "$admin_id" > admin_id.txt

echo
echo "Ab BotFather ke bot tokens enter karo."
echo "Har token hidden rahega. Blank enter karke token input finish karo."
: > tokens.txt
while true; do
  printf "Bot token (blank = finish): "
  IFS= read -r -s token
  echo
  if [ -z "$token" ]; then
    break
  fi
  printf '%s\n' "$token" >> tokens.txt
done

if [ ! -s tokens.txt ]; then
  echo "Koi token add nahi hua. Setup cancel."
  rm -f tokens.txt
  exit 1
fi

chmod +x start.sh setup_termux.sh
echo
echo "Setup complete. Bot start ho raha hai..."
./start.sh