NYXON BOT - TERMUX SETUP
========================

1) Termux install/update:

   pkg update -y
   pkg upgrade -y
   pkg install python nano tmux -y

2) Is folder ko phone mein copy karke Termux mein open karo:

   cd ~/nagasaki-bot

3) Sabse easy first-time setup:

   chmod +x setup_termux.sh
   ./setup_termux.sh

   Ye script dependencies install karegi, Telegram Admin ID poochegi,
   tokens hidden input ke through poochegi aur bot start kar degi.

4) Manual setup karna ho to:

   pip install -r requirements.txt
   cp tokens.txt.example tokens.txt
   nano tokens.txt

   Har Telegram bot token alag line par likho.

5) Bot start karo:

   chmod +x start.sh
   ./start.sh

   Script admin ID poochegi. Telegram ki numeric user ID enter karo.

6) Background mein chalane ke liye:

   tmux new -s nyxon
   ./start.sh

   Session se bahar aane ke liye CTRL+B, phir D dabao.
   Wapas dekhne ke liye:

   tmux attach -t nyxon

7) Telegram group settings:

   @BotFather -> /mybots -> bot select -> Bot Settings ->
   Group Privacy -> Turn off

   Ye zaroori hai agar aap -ping, -start, -nc jaise hyphen commands
   group mein use karna chahte ho. Slash commands /ping aur /start
   privacy mode ke saath bhi receive ho sakte hain.

8) Group name/photo features ke liye bot ko group admin banao aur
   required permissions do.

9) Replit aur Termux dono par same token ek saath mat chalao.
   Warna Telegram "Conflict: terminated by other getUpdates request"
   error dega. Termux start karne se pehle Replit workflow stop karo.

10) Security:

   Purane exposed tokens ko @BotFather se revoke/regenerate karke hi
   tokens.txt mein naye tokens use karo.