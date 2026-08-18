import asyncio
import os
from pathlib import Path
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.constants import ChatType
from telegram.error import RetryAfter, TimedOut, NetworkError
import logging
import re
import random
from telegram.request import HTTPXRequest


BASE_DIR = Path(__file__).resolve().parent
TOKEN_FILE = BASE_DIR / "tokens.txt"
PROXY_FILE = BASE_DIR / "proxies.txt"

# SINGLE-FILE TERMUX CONFIG
# If you want to run only this bot.py without tokens.txt or environment
# variables, fill these two values locally before starting the bot.
LOCAL_OWNER_ID = ""
LOCAL_BOT_TOKENS = [
    # "PASTE_BOT_TOKEN_HERE",
]

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.WARNING
)

def _load_owner_id():
    raw_owner_id = (
        os.getenv("TELEGRAM_ADMIN_ID")
        or os.getenv("OWNER_ID")
        or LOCAL_OWNER_ID
    )
    if not raw_owner_id:
        raise RuntimeError(
            "Missing TELEGRAM_ADMIN_ID/OWNER_ID. Set it before starting the bot."
        )
    try:
        return int(raw_owner_id.strip())
    except ValueError as exc:
        raise RuntimeError("TELEGRAM_ADMIN_ID/OWNER_ID must be a numeric Telegram user ID.") from exc


def _load_tokens():
    """Load one token per line from tokens.txt or from environment variables.

    Keeping tokens outside the source file makes the bot safer to move to
    Termux and prevents accidental token leaks in backups or screenshots.
    """
    candidates = []
    candidates.extend(LOCAL_BOT_TOKENS)
    token_path = Path(os.getenv("TOKENS_FILE", str(TOKEN_FILE))).expanduser()
    if token_path.exists():
        candidates.extend(token_path.read_text(encoding="utf-8").splitlines())

    env_tokens = os.getenv("BOT_TOKENS", "")
    if env_tokens:
        candidates.extend(env_tokens.replace(",", "\n").splitlines())

    for index in range(1, 15):
        candidates.append(os.getenv(f"BOT_TOKEN_{index}", ""))

    candidates.append(os.getenv("TELEGRAM_BOT_TOKEN", ""))

    tokens = []
    for candidate in candidates:
        token = candidate.strip()
        if token and not token.startswith("#") and token not in tokens:
            tokens.append(token)
    return tokens


OWNER_ID = _load_owner_id()
BOT_TOKENS = _load_tokens()

if not BOT_TOKENS:
    raise RuntimeError(
        f"No Telegram bot tokens found. Add one token per line to {TOKEN_FILE.name} "
        "or set TELEGRAM_BOT_TOKEN/BOT_TOKENS."
    )

HEART_EMOJIS = ['❤️', '🧡', '💛', '💚', '💙', '💜', '🤎', '🖤', '🤍', '💘', '💝', '💖', '💗', '💓', '💞', '💌', '💕', '💟', '♥️', '❣️', '💔']

NC_MOON_MESSAGES = [
    "🌑 {target} 𝘛𝘌𝘙𝘐 मां 𝘋𝘈𝘕𝘐 𝘋𝘈𝘕𝘐𝘌𝘓𝘚><🌑",
    "🌔 {target} 𝘛𝘌𝘙𝘐 मां 𝘓𝘌𝘟𝘐 𝘓𝘜𝘕𝘈><🌔",
    "🌕 {target} 𝘛𝘌𝘙𝘐 मां 𝘗𝘙𝘐𝘠𝘈 𝘉𝘏𝘈𝘉𝘏𝘐><🌕",
    "🌖 {target} 𝘛𝘌𝘙𝘐 मां 𝘊𝘖𝘖𝘔𝘖𝘛𝘖𝘡𝘌><🌖",
    "🌗 {target}𝘛𝘌𝘙𝘐 मां 𝘔𝘐𝘈 𝘒𝘏𝘈𝘓𝘐𝘍𝘈><🌗",
    "🌘 {target} 𝘛𝘌𝘙𝘐 मां 𝘔𝘐𝘈 𝘙𝘖𝘚𝘌><🌘",
    "🌙 {target} 𝘛𝘌𝘙𝘐 मां 𝘋𝘐𝘙𝘛𝘠 𝘛𝘐𝘕𝘈><🌙",
]

NC_FLAG_MESSAGES = [
    "{target} 🇨🇳𝐌ᴀᴅᴀʀᴄʜᴏ𝐃🇨🇳",
    "{target} 🇨🇦𝐊ᴀɴᴊᴀ𝐑🇨🇦",
    "{target} 🇩🇪𝐑ᴀɴᴅ𝐈🇩🇪",
    "{target} 🇮🇳𝐇ᴀ𝐀ʀᴀᴍᴢᴀᴅᴀ🇮🇳",
    "{target} 🇮🇲𝐓ᴇʀɪᴍᴀᴀᴋɪ𝐂ʜᴜᴛ🇮🇲",
    "{target} 🇰🇵𝐁ɪᴛᴄʜ🇰🇵",
    "{target} 🇺🇸𝐂ʜᴜᴅᴋᴀ𝐃🇺🇸",
]

TIME_NC_MESSAGES = [
    " {target} Tɪᴍᴇ Is Oᴠᴇʀ 12:382:229",
    " {target} Tᴇʀɪ Mᴀᴀ Kᴀ Bʜᴏsᴅᴀ Sɪʟ Dᴜɴ 12:382:230",
    " {target} Tᴇʀᴀ Bᴀᴀᴘ NYXON BOT 12:382:231 ",
    " {target} Tᴇʀɪ Bᴇʜɴ Kɪ Cʜᴜᴛ Mᴇ Gʜᴀᴅɪ 12:382:232",
    " {target} Tɪᴍᴇ Tᴏ Dɪᴇ Mᴄ 12:382:233",
    "12:382:234 {target} Tᴇʀɪ Mᴀᴀ Cʜᴜᴅ Gᴀʏɪ ",
]

NC_CURLY_MESSAGES = [
    "{{ Tᴍᴋᴄ ! {target} Tᴍᴋᴄ ! }}",
    "{{-Tᴍᴋᴄ ! {target} Tᴍᴋᴄ !-}}",
    "{{★Tᴍᴋᴄ ! {target} Tᴍᴋᴄ !★}}",
    "{{🔥Tᴍᴋᴄ ! {target} Tᴍᴋᴄ !🔥}}",
    "{{🔱Tᴍᴋᴄ ! {target} Tᴍᴋᴄ !🔱}}",
    "{{✨Tᴍᴋᴄ ! {target} Tᴍᴋᴄ !✨}}",
    "{{🥀Tᴍᴋᴄ ! {target} Tᴍᴋᴄ !🥀}}",
]

DOTZKENG_MESSAGES = [
    "⚡ {target} DOTZ KENG ABU ⚡",
    "🔥 {target} Tᴇʀɪ Mᴀᴀ Kɪ Cʜᴜᴛ Mᴇ Aᴀɢ 🔥",
    "👑 {target} DOTZ KENG Bᴀᴀᴘ Hᴀɪ Tᴇʀᴀ 👑",
    "💀 {target} Kʜᴀᴍᴏsʜɪ Sᴇ Cʜᴜᴅ Jᴀ 💀",
    "💥 {target} DOTZ KENG Sᴇ Pᴀɴɢᴀ Mᴀᴛ Lᴇ 💥",
    "🚀 {target} Tᴇʀɪ Bᴇʜɴ Kɪ Cʜᴜᴛ Mᴇ Rᴏᴄᴋᴇᴛ 🚀",
    "🦾 {target} DOTZ KENG Pᴏᴡᴇʀ 🦾",
]

FLOWER_NC_MESSAGES = [
    "𝜗𝜚⋆₊🍁˚{target} Sʟᴜᴛ Mᴀᴀ ᴋᴇ Lᴀᴅᴋᴇ ",
    "𝜗𝜚⋆₊🌱˚{target} Sʟᴜᴛ Mᴀᴀ ᴋᴇ Lᴀᴅᴋᴇ ",
    "𝜗𝜚⋆₊🌿˚{target} Sʟᴜᴛ Mᴀᴀ ᴋᴇ Lᴀᴅᴋᴇ ",
    "𝜗𝜚⋆₊🍃˚{target} Sʟᴜᴛ Mᴀᴀ ᴋᴇ Lᴀᴅᴋᴇ ",
    "𝜗𝜚⋆₊☘️˚{target} Sʟᴜᴛ Mᴀᴀ ᴋᴇ Lᴀᴅᴋᴇ ",
    "𝜗𝜚⋆₊🍀˚{target} Sʟᴜᴛ Mᴀᴀ ᴋᴇ Lᴀᴅᴋᴇ ",
    "𝜗𝜚⋆₊🪴˚{target} Sʟᴜᴛ Mᴀᴀ ᴋᴇ Lᴀᴅᴋᴇ ",
]

UNAUTHORIZED_MESSAGE = "-Sᴜᴅᴏ Lᴇᴋᴇ Aᴀᴊᴀ Fʜɪʀ Kʀɪʏᴏ Cᴏᴍᴍᴀɴᴅ Tᴍᴋᴄ ⭐"

NAME_CHANGE_MESSAGES = [
    "{target} Cʜᴀᴘᴀʟ Kʜᴀ Mᴄ KsᴍK 🤢🤮🖕🏻🖕🏻",
    "{target} Gᴜʟᴀᴍ Kᴇ ʟᴀᴅᴋᴇ 121 Fʏᴛᴇʀ ʙᴀɴᴇɢᴀ Tᴍᴋᴄ 😂🔥🔥",
    "{target} Tᴇʀᴇ Mᴀᴀ ᴋɪ CHᴜᴛ ᴍ Sᴇ Bᴀᴅʙᴜ Aʀʜɪ Cʜᴜᴛ ᴋᴇsᴇ ᴍᴀʀᴜ ᴜsᴋɪ 🤮🤢",
    "{target} Sɪʟᴀɪ Wᴀʟʏ Kᴇ ʟᴀᴅᴋᴇ Tᴇʀɪ ᴍᴀᴀ Kᴀ ʙʜᴏsᴅᴀ Sɪʟ Dᴜ?? 🧵🧵",
    "{target} Tᴇʀɪ Mᴀᴀ Gʏᴍɴᴀsᴛɪᴄs 🤸🏻🤸🏻 Kʀᴛᴇ Kʀᴛᴇ Cʜᴜᴅɪ 🥵🔥",
    "{target} UᴛʜUᴛʜUTʜ Tᴇʀɪ ᴍᴀᴀ ᴋᴏ Wᴀᴅɪʏᴏɴ Mᴇɪ Cʜᴏᴅᴜᴜɴ 🤸🏻🔥😂",
    "{target} Tᴇʀɪ ᴍᴀᴀ Kᴇ ɴᴜᴅᴇs ᴋᴏ Vᴘs Eᴅɪᴛ ʙɴᴀ ᴅᴜ?? 👑🔥😂",
]

REPLY_MESSAGES = [
    "{target} Tᴇʀɪ ᴍᴀᴀ ɢᴜʟᴀᴍ ʜ ʙᴇᴛᴇ🐣",
    "{target} Cᴜᴅ Cᴜᴅ Cᴜᴅ -!🩴🔥",
    "Aʟᴏᴏ Kʜᴀᴋᴇ {target} Tᴇʀɪ ᴍᴏᴍ Cᴏᴍ Qᴜᴇᴇɴ 👑♥️",
    "{target} Hɪᴊᴅᴀ Tᴇʀᴇ Bᴀᴀᴘ ᴋɪ Cʜᴜᴛ🤳🏻👋🏻",
    "{target} Tᴇʀᴇ Bᴀᴀᴘ Kɪ ʙᴋʙ🔥✨",
    "{target} Tᴜ ᴋʀᴇɢᴀ Sᴘᴀᴍ Hᴀssɪ🔃💠",
    "{target} Tᴇʀɪ Bʜᴇɴ Cʜᴏᴅᴇ Dɪɴᴀsᴀᴜʀ🦖😈",
    "{target} Aᴛᴍᴋʙғᴛᴊɢ🖤🙊",
    "{target} Kᴜᴛɪʏᴀ Kᴇ ʟᴀᴅᴋᴇ🌷😭",
    "{target} Tᴇʀᴀ ʙᴀᴀᴘ Tᴇʀɪ ᴍᴀᴀ ᴄʜᴏᴅᴇ Bʙᴄ Bᴀɴᴋᴇ😨♥️",
    "{target} Sɪʟᴀɪ Wᴀʟʏ ᴋᴇ ʟᴀᴅᴋᴇ Tʀʏ Mᴀᴀ ᴋᴀ ʙʜᴏsᴅᴀ Sɪʟ ᴅᴜ? 💀🥵",
    "{target} Tʀʏ ᴍᴀᴀ ᴘᴀᴅʜᴇ Bᴏᴏᴋ Wᴏʜ Hᴏᴋᴇ ᴄʜᴜᴅᴇɢɪ Cᴏᴏᴋ 🥧🧑🏻‍🍳",
    "{target} Eᴠᴇʀʏᴛʜɪɴɢ Is Tᴇᴍᴘᴏʀᴀʀʏ Bᴜᴛ Tʀɪ Cʜᴜᴅᴀɪ Is ᴘᴇʀᴍᴀɴᴇɴᴛ 🦠🦷",
    "{target} ᴋᴀʜᴀ ᴛᴇ ʙʜᴀɢᴇɢᴀ Eᴋ ʀᴇʜᴘᴀᴛ ᴍ ᴛᴇʀᴀ Rᴀᴘᴇ ʜᴏᴊʏᴇɢᴀ Bʜᴇɴɢᴇ🦘🪽",
    "{target} Tᴇʀɪ Mᴀᴀ ᴘᴇsᴇ ᴋᴀᴍᴀᴛᴇ ᴋᴀᴍᴀᴛᴇ ɴᴀɴɢɪ Hᴜɪ 👩🏻‍⚕️👩🏻‍🎤",
    "{target} Tᴇʀɪ ᴍᴀᴀ ᴋᴏ Mᴇʀᴇ FᴀʀᴍHᴏᴜsᴇ P ʙʜᴇᴊᴅᴇ🥩🍏",
    "{target} Kᴜᴛɪʏᴀ Kᴇ ʙʜᴏsᴅᴇ Kɪ ᴀᴜʟᴀᴅ😈👋🏻",
    "{target} ʙᴏʟᴇ NYXON BOT Kɪ ᴊᴀɪ Hᴏ🕳️🔥",
    "{target} ʜɪᴊᴅᴀ ʜ ᴛᴜ ɢʀᴇᴇʙ💮🥀",
    "{target} ᴛᴇʀɪ ᴍᴀᴀ ʙᴏʟᴇ NYXON BOT अब्बू ʜᴀɪ ᴍᴇʀᴇ🩴🔥",
]

SPAM_MESSAGE_TEMPLATE = """{target} ˏˋ°•*⁀➷ 𝑳𝑼𝑵𝑫 𝑪𝑯𝑶𝑶𝑺 𝑲𝑬𝑵𝑰𝑵-𝑵𝒀𝑿𝑶𝑵 𝑩𝑶𝑻 𝑲𝑨 कुतिया के 🥂🌙{target} ˏˋ°•*⁀➷ 𝑳𝑼𝑵𝑫 𝑪𝑯𝑶𝑶𝑺 𝑲𝑬𝑵𝑰𝑵-𝑵𝒀𝑿𝑶𝑵 𝑩𝑶𝑻 𝑲𝑨 कुतिया के 🥂🌙{target} ˏˋ°•*⁀➷ 𝑳𝑼𝑵𝑫 𝑪𝑯𝑶𝑶𝑺 𝑲𝑬𝑵𝑰𝑵-𝑵𝒀𝑿𝑶𝑵 𝑩𝑶𝑻 𝑲𝑨 कुतिया के 🥂🌙{target} ˏˋ°•*⁀➷ 𝑳𝑼𝑵𝑫 𝑪𝑯𝑶𝑶𝑺 𝑲𝑬𝑵𝑰𝑵-𝑵𝒀𝑿𝑶𝑵 𝑩𝑶𝑻 𝑲𝑨 कुतिया के 🥂🌙{target} ˏˋ°•*⁀➷ 𝑳𝑼𝑵𝑫 𝑪𝑯𝑶𝑶𝑺 𝑲𝑬𝑵𝑰𝑵-𝑵𝒀𝑿𝑶𝑵 𝑩𝑶𝑻 𝑲𝑨 कुतिया के 🥂🌙"""

SPAM_MESSAGE_2 = """ {target} 𝐓𝐔𝐌 𝐓𝐀𝐀𝐓𝐓𝐎 𝐊𝐈 𝐌𝐊𝐁 𝐆𝐀𝐑𝐄𝐄𝐁𝐎_______________________________________________/⭐{target} 𝐓𝐔𝐌 𝐓𝐀𝐀𝐓𝐓𝐎 𝐊𝐈 𝐌𝐊𝐁 𝐆𝐀𝐑𝐄𝐄𝐁𝐎_______________________________________________/⭐{target} 𝐓𝐔𝐌 𝐓𝐀𝐀𝐓𝐓𝐎 𝐊𝐈 𝐌𝐊𝐁 𝐆𝐀𝐑𝐄𝐄𝐁𝐎_______________________________________________/⭐{target} 𝐓𝐔𝐌 𝐓𝐀𝐀𝐓𝐓𝐎 𝐊𝐈 𝐌𝐊𝐁 𝐆𝐀𝐑𝐄𝐄𝐁𝐎_______________________________________________/⭐{target} 𝐓𝐔𝐌 𝐓𝐀𝐀𝐓𝐓𝐎 𝐊𝐈 𝐌𝐊𝐁 𝐆𝐀𝐑𝐄𝐄𝐁𝐎_______________________________________________/⭐"""

SPAM_MESSAGE_3 = """ {target} CVR KR MC GAREEB 👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞👞"""


def extract_retry_after(error_str):
    match = re.search(r'retry after (\d+)', error_str.lower())
    if match:
        return int(match.group(1))
    return None


class BotInstance:
    def __init__(self, bot_number, owner_id):
        self.bot_number = bot_number
        self.owner_id = owner_id
        self.sudo_users = set()
        self.active_spam_tasks = {}
        self.active_name_change_tasks = {}
        self.active_ncmoon_tasks = {}
        self.active_ncflag_tasks = {}
        self.active_dotzkeng_tasks = {}
        self.active_curly_tasks = {}
        self.active_timenc_tasks = {}
        self.active_reply_tasks = {}
        self.active_reply_targets = {}
        self.active_react_chats = {}
        self.active_gc_tasks = {}
        self.pending_replies = {}
        self.chat_delays = {}
        self.chat_threads = {}
        self.locks = {}
        self.proxy = None
        self.proxies_list = []
        self._load_proxies()

    def _load_proxies(self):
        if PROXY_FILE.exists():
            with PROXY_FILE.open("r", encoding="utf-8") as f:
                self.proxies_list = [line.strip() for line in f if line.strip()]
            if self.proxies_list:
                self.proxy = random.choice(self.proxies_list)

    def get_lock(self, chat_id):
        if chat_id not in self.locks:
            self.locks[chat_id] = asyncio.Lock()
        return self.locks[chat_id]

    def is_owner(self, user_id):
        return user_id == self.owner_id or user_id in self.sudo_users

    async def check_owner(self, update):
        user_id = update.effective_user.id
        if not self.is_owner(user_id):
            try:
                await update.message.reply_text(UNAUTHORIZED_MESSAGE)
            except Exception:
                pass
            return False
        return True

    async def start(self, update, context):
        if not await self.check_owner(update):
            return
        help_text = f"""
- 𝐍𝐘𝐗𝐎𝐍 𝐁𝐎𝐓 ⭐

📑 | 𝐍ᴀᴍᴇ 𝐂ʜᴀɴɢᴇʀs
• -nc < target >
• -ncmoon < target >
• -ncemo < target >
• -flowernc < target >
• -ncflag < target >
• -timenc < target >
• -nccurly < target >
• -dotzkeng < target >

⚙️ | 𝐒ᴘᴀᴍ 𝐓ᴏᴏʟs
• -spam < target >
• -multispam < target >
• -reply < target >

💠 | 𝐆ᴄs 𝐏ғᴘ 𝐂ʜᴀɴɢᴇʀ
• -setgc [ reply photo with -setgc 1 or 2 ]
• -gc [ group image change loop ]

✳️ | 𝐄xᴛʀᴀ
• -start
• -sudo [ reply to message ]
• -ping
• -delay < 1-100 >
• -target < target >
• -threads < 1-50 >
• -refresh
• -ownrp [ reply to message ]
• -join < invite link >
• -proxy add/reload
• -react

🛡️ | 𝐒ᴛᴏᴘ 𝐂ᴏᴍᴍᴀɴᴅs
• -stopall
• -stopnc | -stopncmoon | -stopncflag
• -stopnccurly | -stopdotzkeng | -stoptimenc
• -stopspam | -stopreply

📌 | 𝐍ᴏᴛɪᴄᴇ
• ᴀʟʟ ᴀᴄᴛɪᴏɴs ʀᴜɴ ɪɴ ʟᴏᴏᴘs
• Bots Active: {len(BOT_TOKENS)}
• If -commands are not received in a group, disable Group Privacy in @BotFather or use /commands
"""
        await update.message.reply_text(help_text)

    async def refresh_command(self, update, context):
        if not await self.check_owner(update):
            return
        await update.message.reply_text(f"NYXON BOT {self.bot_number} is active and refreshed! ⚡")

    async def sudo_command(self, update, context):
        if update.effective_user.id != self.owner_id:
            return
        if not context.args and not update.message.reply_to_message:
            await update.message.reply_text("Usage: -sudo @username or reply to a message with -sudo")
            return
        user_to_sudo = None
        if update.message.reply_to_message:
            user_to_sudo = update.message.reply_to_message.from_user.id
        else:
            arg = context.args[0]
            if arg.startswith("@"):
                await update.message.reply_text("Please reply to the user's message with -sudo to grant sudo.")
                return
            else:
                try:
                    user_to_sudo = int(arg)
                except ValueError:
                    await update.message.reply_text("Invalid User ID.")
                    return
        if user_to_sudo:
            self.sudo_users.add(user_to_sudo)
            await update.message.reply_text(f"User {user_to_sudo} granted SUDO powers! ✅")

    async def ping_command(self, update, context):
        if not await self.check_owner(update):
            return
        import time
        start_time = time.time()
        sent_message = await update.message.reply_text("Pinging...")
        latency = (time.time() - start_time) * 1000
        await sent_message.edit_text(f"NYXON BOT {self.bot_number} Ping: {latency:.2f}ms ⚡")

    async def ownrp_command(self, update, context):
        if not await self.check_owner(update):
            return
        reply_to_message = update.message.reply_to_message
        if not reply_to_message:
            await update.message.reply_text("Please reply to a message with -ownrp to see details.")
            return
        target_user = reply_to_message.from_user
        target_name = target_user.first_name if target_user else "Unknown"
        target_id = target_user.id if target_user else "Unknown"
        target_username = f"@{target_user.username}" if target_user and target_user.username else "None"
        await update.message.reply_text(
            f"𓆩 𝐃𝐄𝐓𝐀𝐈𝐋𝐒 𓆪\n\n"
            f"OWNER ID: `{self.owner_id}`\n\n"
            f"TARGET NAME: `{target_name}`\nTARGET ID: `{target_id}`\nTARGET USERNAME: {target_username}\n\n"
            f"𝐍𝐘𝐗𝐎𝐍 𝐁𝐎𝐓 ⭐",
            parse_mode='Markdown'
        )

    async def join_command(self, update, context):
        if not await self.check_owner(update):
            return
        if not context.args:
            await update.message.reply_text("Usage: -join <invite_link_or_username>")
            return
        link = context.args[0]
        if "t.me/" in link:
            link = link.split("t.me/")[-1]
        if link.startswith("+"):
            link = link[1:]
        if link.startswith("@"):
            link = link[1:]
        print(f"[NYXON BOT {self.bot_number}] Attempting to join: {link}")
        try:
            await context.bot.join_chat(link)
        except Exception as e:
            print(f"[NYXON BOT {self.bot_number}] Join error: {e}")

    async def proxy_command(self, update, context):
        if not await self.check_owner(update):
            return
        if not context.args:
            status = f"Current Proxy: {self.proxy}" if self.proxy else "No proxy configured."
            await update.message.reply_text(f"{status}\nUsage: -proxy add <url> or -proxy reload")
            return
        cmd = context.args[0].lower()
        if cmd == "add" and len(context.args) > 1:
            proxy_url = context.args[1]
            with PROXY_FILE.open("a", encoding="utf-8") as f:
                f.write(f"{proxy_url}\n")
            self._load_proxies()
            await update.message.reply_text("Proxy added and reloaded! ✅")
        elif cmd == "reload":
            self._load_proxies()
            await update.message.reply_text(f"Proxies reloaded! Total: {len(self.proxies_list)} ✅")

    async def react_command(self, update, context):
        if not await self.check_owner(update):
            return
        chat_id = update.effective_chat.id
        if chat_id in self.active_react_chats:
            del self.active_react_chats[chat_id]
            await update.message.reply_text("Reactions disabled! ❌")
        else:
            self.active_react_chats[chat_id] = True
            await update.message.reply_text("Reactions enabled! 💀✅")

    async def delay_command(self, update, context):
        if not await self.check_owner(update):
            return
        if not context.args:
            await update.message.reply_text("Usage: -delay <seconds>")
            return
        try:
            delay = float(context.args[0])
            if delay < 0:
                await update.message.reply_text("Delay must be >= 0")
                return
            chat_id = update.effective_chat.id
            self.chat_delays[chat_id] = delay
            await update.message.reply_text(f"[NYXON BOT {self.bot_number}] Delay set to {delay}s")
        except ValueError:
            await update.message.reply_text("Invalid delay value!")

    async def threads_command(self, update, context):
        if not await self.check_owner(update):
            return
        if not context.args:
            await update.message.reply_text("Usage: -threads <number>")
            return
        try:
            threads = int(context.args[0])
            if threads < 1 or threads > 50:
                await update.message.reply_text("Threads must be between 1 and 50")
                return
            chat_id = update.effective_chat.id
            self.chat_threads[chat_id] = threads
            await update.message.reply_text(f"[NYXON BOT {self.bot_number}] Threads set to {threads}")
        except ValueError:
            await update.message.reply_text("Invalid threads value!")

    # ─── Name Change Loops ───────────────────────────────────────────────────

    async def name_change_loop(self, chat_id, base_name, context, worker_id=1):
        msg_index = 0
        success_count = 0
        print(f"[NYXON BOT {self.bot_number}] NC LOOP #{worker_id} started for {chat_id}")
        try:
            while True:
                delay = self.chat_delays.get(chat_id, 0)
                try:
                    display_name = NAME_CHANGE_MESSAGES[msg_index % len(NAME_CHANGE_MESSAGES)].format(target=base_name)
                    await context.bot.set_chat_title(chat_id=chat_id, title=display_name)
                    msg_index += 1
                    success_count += 1
                    await asyncio.sleep(max(delay, 0.1))
                except asyncio.CancelledError:
                    raise
                except RetryAfter as e:
                    wait_time = int(e.retry_after) if isinstance(e.retry_after, (int, float)) else e.retry_after.total_seconds()
                    await asyncio.sleep(wait_time + 1.0)
                except (TimedOut, NetworkError):
                    await asyncio.sleep(1.0)
                except Exception as e:
                    retry_after = extract_retry_after(str(e).lower())
                    await asyncio.sleep((retry_after + 1.0) if retry_after else 1.0)
                    msg_index += 1
        except asyncio.CancelledError:
            print(f"[NYXON BOT {self.bot_number}] NC LOOP #{worker_id} stopped after {success_count} changes")

    async def nc_moon_loop(self, chat_id, base_name, context, worker_id=1):
        msg_index = 0
        success_count = 0
        try:
            while True:
                delay = self.chat_delays.get(chat_id, 0)
                try:
                    display_name = NC_MOON_MESSAGES[msg_index % len(NC_MOON_MESSAGES)].format(target=base_name)
                    await context.bot.set_chat_title(chat_id=chat_id, title=display_name)
                    msg_index += 1
                    success_count += 1
                    await asyncio.sleep(max(delay, 0.05))
                except asyncio.CancelledError:
                    raise
                except RetryAfter as e:
                    wait_time = int(e.retry_after) if isinstance(e.retry_after, (int, float)) else e.retry_after.total_seconds()
                    await asyncio.sleep(wait_time + 0.1)
                except (TimedOut, NetworkError):
                    await asyncio.sleep(0.5)
                except Exception as e:
                    retry_after = extract_retry_after(str(e).lower())
                    await asyncio.sleep((retry_after + 0.1) if retry_after else 0.5)
                    msg_index += 1
        except asyncio.CancelledError:
            pass

    async def nc_flag_loop(self, chat_id, base_name, context, worker_id=1):
        msg_index = 0
        success_count = 0
        try:
            while True:
                delay = self.chat_delays.get(chat_id, 0)
                try:
                    display_name = NC_FLAG_MESSAGES[msg_index % len(NC_FLAG_MESSAGES)].format(target=base_name)
                    await context.bot.set_chat_title(chat_id=chat_id, title=display_name)
                    msg_index += 1
                    success_count += 1
                    await asyncio.sleep(max(delay, 0.05))
                except asyncio.CancelledError:
                    raise
                except RetryAfter as e:
                    wait_time = int(e.retry_after) if isinstance(e.retry_after, (int, float)) else e.retry_after.total_seconds()
                    await asyncio.sleep(wait_time + 0.1)
                except (TimedOut, NetworkError):
                    await asyncio.sleep(0.5)
                except Exception as e:
                    retry_after = extract_retry_after(str(e).lower())
                    await asyncio.sleep((retry_after + 0.1) if retry_after else 0.5)
                    msg_index += 1
        except asyncio.CancelledError:
            pass

    async def time_nc_loop(self, chat_id, base_name, context, worker_id=1):
        msg_index = 0
        success_count = 0
        try:
            while True:
                delay = self.chat_delays.get(chat_id, 0)
                try:
                    display_name = TIME_NC_MESSAGES[msg_index % len(TIME_NC_MESSAGES)].format(target=base_name)
                    await context.bot.set_chat_title(chat_id=chat_id, title=display_name)
                    msg_index += 1
                    success_count += 1
                    await asyncio.sleep(max(delay, 0.1))
                except asyncio.CancelledError:
                    raise
                except RetryAfter as e:
                    wait_time = int(e.retry_after) if isinstance(e.retry_after, (int, float)) else e.retry_after.total_seconds()
                    await asyncio.sleep(wait_time + 1.0)
                except Exception:
                    await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            pass

    async def nc_curly_loop(self, chat_id, base_name, context, worker_id=1):
        msg_index = 0
        try:
            while True:
                delay = self.chat_delays.get(chat_id, 0)
                try:
                    display_name = NC_CURLY_MESSAGES[msg_index % len(NC_CURLY_MESSAGES)].format(target=base_name)
                    await context.bot.set_chat_title(chat_id=chat_id, title=display_name)
                    msg_index += 1
                    await asyncio.sleep(max(delay, 0.05))
                except asyncio.CancelledError:
                    raise
                except RetryAfter as e:
                    wait_time = int(e.retry_after) if isinstance(e.retry_after, (int, float)) else e.retry_after.total_seconds()
                    await asyncio.sleep(wait_time + 0.1)
                except (TimedOut, NetworkError):
                    await asyncio.sleep(0.5)
                except Exception as e:
                    retry_after = extract_retry_after(str(e).lower())
                    await asyncio.sleep((retry_after + 0.1) if retry_after else 0.5)
                    msg_index += 1
        except asyncio.CancelledError:
            pass

    async def dotzkeng_loop(self, chat_id, base_name, context, worker_id=1):
        msg_index = 0
        try:
            while True:
                delay = self.chat_delays.get(chat_id, 0)
                try:
                    display_name = DOTZKENG_MESSAGES[msg_index % len(DOTZKENG_MESSAGES)].format(target=base_name)
                    await context.bot.set_chat_title(chat_id=chat_id, title=display_name)
                    msg_index += 1
                    await asyncio.sleep(max(delay, 0.05))
                except asyncio.CancelledError:
                    raise
                except RetryAfter as e:
                    wait_time = int(e.retry_after) if isinstance(e.retry_after, (int, float)) else e.retry_after.total_seconds()
                    await asyncio.sleep(wait_time + 0.1)
                except (TimedOut, NetworkError):
                    await asyncio.sleep(0.5)
                except Exception as e:
                    retry_after = extract_retry_after(str(e).lower())
                    await asyncio.sleep((retry_after + 0.1) if retry_after else 0.5)
                    msg_index += 1
        except asyncio.CancelledError:
            pass

    async def flower_nc_loop(self, chat_id, base_name, context):
        msg_index = 0
        try:
            while True:
                delay = self.chat_delays.get(chat_id, 0)
                try:
                    display_name = FLOWER_NC_MESSAGES[msg_index % len(FLOWER_NC_MESSAGES)].format(target=base_name)
                    await context.bot.set_chat_title(chat_id=chat_id, title=display_name)
                    msg_index += 1
                    await asyncio.sleep(max(delay, 0.05))
                except asyncio.CancelledError:
                    raise
                except RetryAfter as e:
                    wait_time = int(e.retry_after) if isinstance(e.retry_after, (int, float)) else e.retry_after.total_seconds()
                    await asyncio.sleep(wait_time + 0.1)
                except (TimedOut, NetworkError):
                    await asyncio.sleep(0.5)
                except Exception as e:
                    retry_after = extract_retry_after(str(e).lower())
                    await asyncio.sleep((retry_after + 0.1) if retry_after else 0.5)
                    msg_index += 1
        except asyncio.CancelledError:
            pass

    async def nc_emo_loop(self, chat_id, base_name, context):
        try:
            while True:
                delay = self.chat_delays.get(chat_id, 0)
                try:
                    emoji = random.choice(HEART_EMOJIS)
                    display_name = f"{emoji} {base_name} {emoji}"
                    await context.bot.set_chat_title(chat_id=chat_id, title=display_name)
                    await asyncio.sleep(max(delay, 0.05))
                except asyncio.CancelledError:
                    raise
                except RetryAfter as e:
                    wait_time = int(e.retry_after) if isinstance(e.retry_after, (int, float)) else e.retry_after.total_seconds()
                    await asyncio.sleep(wait_time + 0.1)
                except Exception:
                    await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            pass

    async def auto_name_loop(self, context, target_name):
        try:
            while True:
                try:
                    await context.bot.set_my_name(name=target_name)
                    await asyncio.sleep(60)
                except asyncio.CancelledError:
                    raise
                except RetryAfter as e:
                    wait_time = int(e.retry_after) if isinstance(e.retry_after, (int, float)) else e.retry_after.total_seconds()
                    await asyncio.sleep(wait_time + 1.0)
                except Exception:
                    await asyncio.sleep(10.0)
        except asyncio.CancelledError:
            pass

    # ─── Spam / Reply Loops ───────────────────────────────────────────────────

    async def spam_loop(self, chat_id, target_name, context, worker_id):
        success_count = 0
        templates = [SPAM_MESSAGE_TEMPLATE, SPAM_MESSAGE_2, SPAM_MESSAGE_3]
        try:
            while True:
                delay = self.chat_delays.get(chat_id, 0)
                jitter = delay * random.uniform(0.85, 1.15) if delay > 0 else random.uniform(0.1, 0.4)
                try:
                    template = templates[success_count % len(templates)]
                    await context.bot.send_message(chat_id=chat_id, text=template.format(target=target_name))
                    success_count += 1
                    await asyncio.sleep(jitter)
                except asyncio.CancelledError:
                    raise
                except RetryAfter as e:
                    wait_time = int(e.retry_after) if isinstance(e.retry_after, (int, float)) else e.retry_after.total_seconds()
                    await asyncio.sleep(wait_time + 1.0)
                except (TimedOut, NetworkError):
                    await asyncio.sleep(1.0)
                except Exception as e:
                    retry_after = extract_retry_after(str(e).lower())
                    await asyncio.sleep((retry_after + 1.0) if retry_after else 1.0)
        except asyncio.CancelledError:
            pass

    async def reply_loop(self, chat_id, target_name, context):
        try:
            while True:
                delay = self.chat_delays.get(chat_id, 0)
                if chat_id in self.pending_replies and self.pending_replies[chat_id]:
                    async with self.get_lock(chat_id):
                        messages_to_reply = self.pending_replies[chat_id].copy()
                        self.pending_replies[chat_id] = []
                    for msg_id in messages_to_reply:
                        try:
                            reply_msg = random.choice(REPLY_MESSAGES).format(target=target_name)
                            await context.bot.send_message(chat_id=chat_id, text=reply_msg, reply_to_message_id=msg_id)
                            await asyncio.sleep(max(delay, 0.05))
                        except asyncio.CancelledError:
                            raise
                        except RetryAfter as e:
                            wait_time = int(e.retry_after) if isinstance(e.retry_after, (int, float)) else e.retry_after.total_seconds()
                            await asyncio.sleep(wait_time + 0.1)
                        except Exception:
                            await asyncio.sleep(0.5)
                else:
                    await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass

    async def gc_loop(self, chat_id, context):
        image_paths = [
            BASE_DIR / "gc_image_1.png",
            BASE_DIR / "gc_image_2.png",
        ]
        msg_index = 0
        try:
            while True:
                delay = self.chat_delays.get(chat_id, 0)
                try:
                    available_images = [p for p in image_paths if os.path.exists(p)]
                    if available_images:
                        current_path = available_images[msg_index % len(available_images)]
                        with open(current_path, 'rb') as photo:
                            await context.bot.set_chat_photo(chat_id=chat_id, photo=photo)
                        msg_index += 1
                        await asyncio.sleep(max(delay, 2.0))
                    else:
                        await asyncio.sleep(5.0)
                except asyncio.CancelledError:
                    raise
                except RetryAfter as e:
                    wait_time = int(e.retry_after) if isinstance(e.retry_after, (int, float)) else e.retry_after.total_seconds()
                    await asyncio.sleep(wait_time + 1.0)
                except Exception as e:
                    print(f"[NYXON BOT {self.bot_number}] GC Error: {e}")
                    await asyncio.sleep(5.0)
        except asyncio.CancelledError:
            pass

    async def message_collector(self, update, context):
        msg = update.message or update.channel_post
        if not msg:
            return
        chat_id = update.effective_chat.id

        if chat_id in self.active_react_chats:
            try:
                await msg.react(reaction="💀")
            except Exception:
                try:
                    await context.bot.set_message_reaction(
                        chat_id=chat_id,
                        message_id=msg.message_id,
                        reaction=[{"type": "emoji", "emoji": "💀"}]
                    )
                except Exception:
                    pass

        if not msg.text:
            return

        text = msg.text.lower()
        if "taixochutiya" in text and update.message:
            await msg.reply_text("TAIXO Tᴇʀɪ ᴍᴏᴍ Cᴏᴍ Qᴜᴇᴇɴ 👑♥️")
            return

        if chat_id in self.active_reply_targets:
            msg_id = msg.message_id
            async with self.get_lock(chat_id):
                if chat_id not in self.pending_replies:
                    self.pending_replies[chat_id] = []
                self.pending_replies[chat_id].append(msg_id)

    # ─── Helper: cancel task list ─────────────────────────────────────────────

    async def _cancel_tasks(self, task_dict, chat_id):
        if chat_id in task_dict:
            tasks = task_dict[chat_id]
            if not isinstance(tasks, list):
                tasks = [tasks]
            for t in tasks:
                t.cancel()
            for t in tasks:
                try:
                    await t
                except asyncio.CancelledError:
                    pass
            del task_dict[chat_id]
            return True
        return False

    # ─── Command Handlers ─────────────────────────────────────────────────────

    async def nc_command(self, update, context):
        if not await self.check_owner(update): return
        chat = update.effective_chat
        if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await update.message.reply_text("This command only works in groups!"); return
        if not context.args:
            await update.message.reply_text("Usage: -nc <name>"); return
        base_name = " ".join(context.args)
        chat_id = chat.id
        await self._cancel_tasks(self.active_name_change_tasks, chat_id)
        num_threads = self.chat_threads.get(chat_id, 1)
        self.active_name_change_tasks[chat_id] = [asyncio.create_task(self.name_change_loop(chat_id, base_name, context, i+1)) for i in range(num_threads)]
        await update.message.reply_text(f"[NYXON BOT {self.bot_number}] ⚡ NC LOOP started with {num_threads} threads!")

    async def stop_nc_command(self, update, context):
        if not await self.check_owner(update): return
        chat_id = update.effective_chat.id
        stopped = await self._cancel_tasks(self.active_name_change_tasks, chat_id)
        await update.message.reply_text(f"[NYXON BOT {self.bot_number}] NC LOOP {'stopped! 🛑' if stopped else 'not running!'}")

    async def ncmoon_command(self, update, context):
        if not await self.check_owner(update): return
        chat = update.effective_chat
        if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await update.message.reply_text("This command only works in groups!"); return
        if not context.args:
            await update.message.reply_text("Usage: -ncmoon <name>"); return
        base_name = " ".join(context.args)
        chat_id = chat.id
        await self._cancel_tasks(self.active_ncmoon_tasks, chat_id)
        num_threads = self.chat_threads.get(chat_id, 1)
        self.active_ncmoon_tasks[chat_id] = [asyncio.create_task(self.nc_moon_loop(chat_id, base_name, context, i+1)) for i in range(num_threads)]
        await update.message.reply_text(f"[NYXON BOT {self.bot_number}] 🌙 NC MOON LOOP started with {num_threads} threads!")

    async def stop_ncmoon_command(self, update, context):
        if not await self.check_owner(update): return
        chat_id = update.effective_chat.id
        stopped = await self._cancel_tasks(self.active_ncmoon_tasks, chat_id)
        await update.message.reply_text(f"[NYXON BOT {self.bot_number}] NC MOON {'stopped! 🛑' if stopped else 'not running!'}")

    async def ncflag_command(self, update, context):
        if not await self.check_owner(update): return
        chat = update.effective_chat
        if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await update.message.reply_text("This command only works in groups!"); return
        if not context.args:
            await update.message.reply_text("Usage: -ncflag <name>"); return
        base_name = " ".join(context.args)
        chat_id = chat.id
        await self._cancel_tasks(self.active_ncflag_tasks, chat_id)
        num_threads = self.chat_threads.get(chat_id, 1)
        self.active_ncflag_tasks[chat_id] = [asyncio.create_task(self.nc_flag_loop(chat_id, base_name, context, i+1)) for i in range(num_threads)]
        await update.message.reply_text(f"[NYXON BOT {self.bot_number}] 🚩 NC FLAG LOOP started with {num_threads} threads!")

    async def stop_ncflag_command(self, update, context):
        if not await self.check_owner(update): return
        chat_id = update.effective_chat.id
        stopped = await self._cancel_tasks(self.active_ncflag_tasks, chat_id)
        await update.message.reply_text(f"[NYXON BOT {self.bot_number}] NC FLAG {'stopped! 🛑' if stopped else 'not running!'}")

    async def time_nc_command(self, update, context):
        if not await self.check_owner(update): return
        if not context.args:
            await update.message.reply_text("Usage: -timenc <target>"); return
        target = " ".join(context.args)
        chat_id = update.effective_chat.id
        await self._cancel_tasks(self.active_timenc_tasks, chat_id)
        num_threads = self.chat_threads.get(chat_id, 1)
        self.active_timenc_tasks[chat_id] = [asyncio.create_task(self.time_nc_loop(chat_id, target, context, i+1)) for i in range(num_threads)]
        await update.message.reply_text(f"[NYXON BOT {self.bot_number}] ⌚ TIME NC LOOP started with {num_threads} threads!")

    async def stop_time_nc(self, update, context):
        if not await self.check_owner(update): return
        chat_id = update.effective_chat.id
        stopped = await self._cancel_tasks(self.active_timenc_tasks, chat_id)
        await update.message.reply_text(f"[NYXON BOT {self.bot_number}] TIME NC {'stopped! 🛑' if stopped else 'not running!'}")

    async def nccurly_command(self, update, context):
        if not await self.check_owner(update): return
        chat = update.effective_chat
        if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await update.message.reply_text("This command only works in groups!"); return
        if not context.args:
            await update.message.reply_text("Usage: -nccurly <name>"); return
        target_name = " ".join(context.args)
        chat_id = chat.id
        await self._cancel_tasks(self.active_curly_tasks, chat_id)
        threads = self.chat_threads.get(chat_id, 1)
        self.active_curly_tasks[chat_id] = [asyncio.create_task(self.nc_curly_loop(chat_id, target_name, context, i+1)) for i in range(threads)]
        await update.message.reply_text(f"[NYXON BOT {self.bot_number}] 🌀 NC CURLY LOOP started with {threads} threads!")

    async def stop_nccurly_command(self, update, context):
        if not await self.check_owner(update): return
        chat_id = update.effective_chat.id
        stopped = await self._cancel_tasks(self.active_curly_tasks, chat_id)
        await update.message.reply_text(f"[NYXON BOT {self.bot_number}] NC CURLY {'stopped! 🛑' if stopped else 'not running!'}")

    async def dotzkeng_command(self, update, context):
        if not await self.check_owner(update): return
        chat = update.effective_chat
        if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await update.message.reply_text("This command only works in groups!"); return
        if not context.args:
            await update.message.reply_text("Usage: -dotzkeng <name>"); return
        base_name = " ".join(context.args)
        chat_id = chat.id
        await self._cancel_tasks(self.active_dotzkeng_tasks, chat_id)
        num_threads = self.chat_threads.get(chat_id, 1)
        self.active_dotzkeng_tasks[chat_id] = [asyncio.create_task(self.dotzkeng_loop(chat_id, base_name, context, i+1)) for i in range(num_threads)]
        await update.message.reply_text(f"[NYXON BOT {self.bot_number}] ⚡ DOTZKENG LOOP started with {num_threads} threads!")

    async def stop_dotzkeng_command(self, update, context):
        if not await self.check_owner(update): return
        chat_id = update.effective_chat.id
        stopped = await self._cancel_tasks(self.active_dotzkeng_tasks, chat_id)
        await update.message.reply_text(f"[NYXON BOT {self.bot_number}] DOTZKENG {'stopped! 🛑' if stopped else 'not running!'}")

    async def flower_nc_command(self, update, context):
        if not await self.check_owner(update): return
        chat = update.effective_chat
        if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await update.message.reply_text("This command only works in groups!"); return
        if not context.args:
            await update.message.reply_text("Usage: -flowernc <name>"); return
        base_name = " ".join(context.args)
        chat_id = chat.id
        await self._cancel_tasks(self.active_name_change_tasks, chat_id)
        task = asyncio.create_task(self.flower_nc_loop(chat_id, base_name, context))
        self.active_name_change_tasks[chat_id] = [task]
        await update.message.reply_text(f"[NYXON BOT {self.bot_number}] 🌸 FLOWER NC LOOP started!")

    async def nc_emo_command(self, update, context):
        if not await self.check_owner(update): return
        chat = update.effective_chat
        if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await update.message.reply_text("This command only works in groups!"); return
        if not context.args:
            await update.message.reply_text("Usage: -ncemo <name>"); return
        base_name = " ".join(context.args)
        chat_id = chat.id
        await self._cancel_tasks(self.active_name_change_tasks, chat_id)
        task = asyncio.create_task(self.nc_emo_loop(chat_id, base_name, context))
        self.active_name_change_tasks[chat_id] = [task]
        await update.message.reply_text(f"[NYXON BOT {self.bot_number}] ⚡ NC EMO LOOP started!")

    async def spam_command(self, update, context):
        if not await self.check_owner(update): return
        chat = update.effective_chat
        if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await update.message.reply_text("This command only works in groups!"); return
        if not context.args:
            await update.message.reply_text("Usage: -spam <target>"); return
        target_name = " ".join(context.args)
        chat_id = chat.id
        await self._cancel_tasks(self.active_spam_tasks, chat_id)
        num_threads = self.chat_threads.get(chat_id, 1)
        self.active_spam_tasks[chat_id] = [asyncio.create_task(self.spam_loop(chat_id, target_name, context, i+1)) for i in range(num_threads)]
        await update.message.reply_text(f"[NYXON BOT {self.bot_number}] 💣 SPAM LOOP started with {num_threads} threads!")

    async def stop_spam_command(self, update, context):
        if not await self.check_owner(update): return
        chat_id = update.effective_chat.id
        stopped = await self._cancel_tasks(self.active_spam_tasks, chat_id)
        await update.message.reply_text(f"[NYXON BOT {self.bot_number}] SPAM {'stopped! 🛑' if stopped else 'not running!'}")

    async def multispam_command(self, update, context):
        if not await self.check_owner(update): return
        if not context.args:
            await update.message.reply_text("Usage: -multispam <target>"); return
        target = " ".join(context.args)
        chat_id = update.effective_chat.id
        await update.message.reply_text(f"[NYXON BOT {self.bot_number}] 🚀 Multi-spam started for {target}!")
        num_threads = self.chat_threads.get(chat_id, 1)
        self.active_spam_tasks[chat_id] = [asyncio.create_task(self.spam_loop(chat_id, target, context, i)) for i in range(num_threads)]

    async def target_command(self, update, context):
        if not await self.check_owner(update): return
        chat = update.effective_chat
        if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await update.message.reply_text("This command only works in groups!"); return
        if not context.args:
            await update.message.reply_text("Usage: -target <name>"); return
        target_name = " ".join(context.args)
        chat_id = chat.id
        await self._cancel_tasks(self.active_name_change_tasks, chat_id)
        await self._cancel_tasks(self.active_spam_tasks, chat_id)
        num_threads = self.chat_threads.get(chat_id, 1)
        self.active_name_change_tasks[chat_id] = [asyncio.create_task(self.name_change_loop(chat_id, target_name, context, i+1)) for i in range(num_threads)]
        self.active_spam_tasks[chat_id] = [asyncio.create_task(self.spam_loop(chat_id, target_name, context, i+1)) for i in range(num_threads)]
        await update.message.reply_text(f"[NYXON BOT {self.bot_number}] 🎯 TARGET MODE: NC ({num_threads}) + SPAM ({num_threads}) = {num_threads*2} threads!")

    async def reply_command(self, update, context):
        if not await self.check_owner(update): return
        chat = update.effective_chat
        if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await update.message.reply_text("This command only works in groups!"); return
        if not context.args:
            await update.message.reply_text("Usage: -reply <target>"); return
        target_name = " ".join(context.args)
        chat_id = chat.id
        await self._cancel_tasks(self.active_reply_tasks, chat_id)
        self.active_reply_targets[chat_id] = target_name
        self.pending_replies[chat_id] = []
        task = asyncio.create_task(self.reply_loop(chat_id, target_name, context))
        self.active_reply_tasks[chat_id] = task
        await update.message.reply_text(f"[NYXON BOT {self.bot_number}] 💬 REPLY LOOP activated!")

    async def stop_reply_command(self, update, context):
        if not await self.check_owner(update): return
        chat_id = update.effective_chat.id
        stopped = await self._cancel_tasks(self.active_reply_tasks, chat_id)
        self.active_reply_targets.pop(chat_id, None)
        self.pending_replies.pop(chat_id, None)
        await update.message.reply_text(f"[NYXON BOT {self.bot_number}] REPLY {'stopped! 🛑' if stopped else 'not running!'}")

    async def gc_command(self, update, context):
        if not await self.check_owner(update): return
        chat = update.effective_chat
        if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await update.message.reply_text("This command only works in groups!"); return
        chat_id = chat.id
        task = asyncio.create_task(self.gc_loop(chat_id, context))
        self.active_gc_tasks[chat_id] = task
        await update.message.reply_text(f"[NYXON BOT {self.bot_number}] 🖼️ GC IMAGE LOOP started!")

    async def set_gc_command(self, update, context):
        if not await self.check_owner(update): return
        message = update.message
        photo = None
        if message.reply_to_message and message.reply_to_message.photo:
            photo = message.reply_to_message.photo[-1]
        elif message.photo:
            photo = message.photo[-1]
        if not photo:
            await update.message.reply_text("Reply to a photo with -setgc [1 or 2]"); return
        slot = "1"
        if context.args and context.args[0] in ["1", "2"]:
            slot = context.args[0]
        filename = BASE_DIR / f"gc_image_{slot}.png"
        file = await context.bot.get_file(photo.file_id)
        await file.download_to_drive(filename)
        await update.message.reply_text(f"Group image saved to Slot {slot}! ✅ Use -gc to start.")

    async def auto_name_command(self, update, context):
        if not await self.check_owner(update): return
        target_name = " ".join(context.args) if context.args else "BOT"
        chat_id = update.effective_chat.id
        await self._cancel_tasks(self.active_name_change_tasks, chat_id)
        task = asyncio.create_task(self.auto_name_loop(context, target_name))
        self.active_name_change_tasks[chat_id] = [task]
        await update.message.reply_text(f"Auto name change loop started for {target_name}! 🔄")

    async def stop_auto_name(self, update, context):
        if not await self.check_owner(update): return
        chat_id = update.effective_chat.id
        stopped = await self._cancel_tasks(self.active_name_change_tasks, chat_id)
        await update.message.reply_text(f"Auto name change {'stopped! 🛑' if stopped else 'not running!'}")

    async def stop_all_command(self, update, context):
        if not await self.check_owner(update): return
        chat_id = update.effective_chat.id
        stopped = []

        for task_dict, label in [
            (self.active_name_change_tasks, "NC"),
            (self.active_ncmoon_tasks, "NC Moon"),
            (self.active_ncflag_tasks, "NC Flag"),
            (self.active_dotzkeng_tasks, "Dotzkeng"),
            (self.active_curly_tasks, "NC Curly"),
            (self.active_timenc_tasks, "Time NC"),
            (self.active_spam_tasks, "Spam"),
        ]:
            if await self._cancel_tasks(task_dict, chat_id):
                stopped.append(label)

        if await self._cancel_tasks(self.active_reply_tasks, chat_id):
            stopped.append("Reply")
            self.active_reply_targets.pop(chat_id, None)
            self.pending_replies.pop(chat_id, None)

        if await self._cancel_tasks(self.active_gc_tasks, chat_id):
            stopped.append("GC")

        if stopped:
            await update.message.reply_text(f"[NYXON BOT {self.bot_number}] Stopped: {', '.join(stopped)} ✅")
        else:
            await update.message.reply_text(f"[NYXON BOT {self.bot_number}] No active loops to stop!")


async def run_bot(token, bot_number, owner_id):
    max_retries = 30
    retry_delay = 15

    proxies = []
    if PROXY_FILE.exists():
        try:
            with PROXY_FILE.open("r", encoding="utf-8") as f:
                proxies = [line.strip() for line in f if line.strip()]
        except Exception:
            pass

    for attempt in range(max_retries):
        bot_instance = BotInstance(bot_number, owner_id)

        proxy_url = None
        if proxies:
            proxy_url = proxies[(bot_number - 1) % len(proxies)]
            bot_instance.proxy = proxy_url

        request = None
        if proxy_url:
            request = HTTPXRequest(proxy_url=proxy_url)

        builder = Application.builder().token(token)
        if request:
            builder.request(request)
        application = builder.build()

        bi = bot_instance

        application.add_handler(CommandHandler("start", bi.start))
        application.add_handler(CommandHandler("nc", bi.nc_command))
        application.add_handler(CommandHandler("stopnc", bi.stop_nc_command))
        application.add_handler(CommandHandler("ncemo", bi.nc_emo_command))
        application.add_handler(CommandHandler("ncmoon", bi.ncmoon_command))
        application.add_handler(CommandHandler("stopncmoon", bi.stop_ncmoon_command))
        application.add_handler(CommandHandler("ncflag", bi.ncflag_command))
        application.add_handler(CommandHandler("stopncflag", bi.stop_ncflag_command))
        application.add_handler(CommandHandler("nccurly", bi.nccurly_command))
        application.add_handler(CommandHandler("stopnccurly", bi.stop_nccurly_command))
        application.add_handler(CommandHandler("dotzkeng", bi.dotzkeng_command))
        application.add_handler(CommandHandler("stopdotzkeng", bi.stop_dotzkeng_command))
        application.add_handler(CommandHandler("flowernc", bi.flower_nc_command))
        application.add_handler(CommandHandler("timenc", bi.time_nc_command))
        application.add_handler(CommandHandler("stoptimenc", bi.stop_time_nc))
        application.add_handler(CommandHandler("spam", bi.spam_command))
        application.add_handler(CommandHandler("stopspam", bi.stop_spam_command))
        application.add_handler(CommandHandler("multispam", bi.multispam_command))
        application.add_handler(CommandHandler("target", bi.target_command))
        application.add_handler(CommandHandler("reply", bi.reply_command))
        application.add_handler(CommandHandler("stopreply", bi.stop_reply_command))
        application.add_handler(CommandHandler("delay", bi.delay_command))
        application.add_handler(CommandHandler("threads", bi.threads_command))
        application.add_handler(CommandHandler("stopall", bi.stop_all_command))
        application.add_handler(CommandHandler("gc", bi.gc_command))
        application.add_handler(CommandHandler("setgc", bi.set_gc_command))
        application.add_handler(CommandHandler("ping", bi.ping_command))
        application.add_handler(CommandHandler("sudo", bi.sudo_command))
        application.add_handler(CommandHandler("proxy", bi.proxy_command))
        application.add_handler(CommandHandler("join", bi.join_command))
        application.add_handler(CommandHandler("refresh", bi.refresh_command))
        application.add_handler(CommandHandler("react", bi.react_command))
        application.add_handler(CommandHandler("ownrp", bi.ownrp_command))

        async def prefix_handler(update, context, _bi=bi):
            if not update.message or not update.message.text:
                await _bi.message_collector(update, context)
                return
            text = update.message.text.strip()
            if not text.startswith('-'):
                await _bi.message_collector(update, context)
                return
            parts = text[1:].split(maxsplit=1)
            if not parts or not parts[0]:
                return
            command = parts[0].lower().split("@", 1)[0]
            context.args = parts[1].split() if len(parts) > 1 else []

            cmd_map = {
                "start": _bi.start,
                "nc": _bi.nc_command, "stopnc": _bi.stop_nc_command,
                "ncemo": _bi.nc_emo_command, "stopncemo": _bi.stop_nc_command,
                "ncmoon": _bi.ncmoon_command, "stopncmoon": _bi.stop_ncmoon_command,
                "ncflag": _bi.ncflag_command, "stopncflag": _bi.stop_ncflag_command,
                "nccurly": _bi.nccurly_command, "stopnccurly": _bi.stop_nccurly_command,
                "dotzkeng": _bi.dotzkeng_command, "stopdotzkeng": _bi.stop_dotzkeng_command,
                "flowernc": _bi.flower_nc_command,
                "timenc": _bi.time_nc_command, "stoptimenc": _bi.stop_time_nc,
                "spam": _bi.spam_command, "stopspam": _bi.stop_spam_command,
                "multispam": _bi.multispam_command,
                "target": _bi.target_command,
                "reply": _bi.reply_command, "stopreply": _bi.stop_reply_command,
                "delay": _bi.delay_command,
                "threads": _bi.threads_command,
                "stopall": _bi.stop_all_command,
                "gc": _bi.gc_command, "setgc": _bi.set_gc_command,
                "ping": _bi.ping_command,
                "sudo": _bi.sudo_command,
                "proxy": _bi.proxy_command,
                "join": _bi.join_command,
                "refresh": _bi.refresh_command,
                "react": _bi.react_command,
                "ownrp": _bi.ownrp_command,
                "autoname": _bi.auto_name_command, "stopautoname": _bi.stop_auto_name,
            }

            if command in cmd_map:
                await cmd_map[command](update, context)
            elif _bi.is_owner(update.effective_user.id):
                await update.message.reply_text(
                    "Unknown command. Use -start to see the available commands."
                )

        async def error_handler(update, context):
            error = context.error
            print(
                f"[NYXON BOT {bot_number}] Handler error: "
                f"{type(error).__name__}: {error}"
            )

        # Prefix commands (-ping) are normal text messages, while slash
        # commands (/ping) are handled by CommandHandler above.
        application.add_handler(
            MessageHandler(filters.TEXT & (~filters.COMMAND), prefix_handler)
        )
        application.add_error_handler(error_handler)

        try:
            await application.initialize()
            await application.start()
            if application.updater:
                await asyncio.sleep(0.1)
                await application.updater.start_polling(drop_pending_updates=True)

            print(f"NYXON BOT {bot_number} started successfully!")

            while True:
                await asyncio.sleep(3600)

        except Exception as e:
            error_str = str(e).lower()
            if "conflict" in error_str:
                print(f"NYXON BOT {bot_number} conflict (attempt {attempt + 1}/{max_retries}), retrying in {retry_delay}s...")
                try:
                    if application.updater:
                        await application.updater.stop()
                    await application.stop()
                    await application.shutdown()
                except Exception:
                    pass
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay + 15, 300)
                continue
            else:
                print(f"NYXON BOT {bot_number} error: {e}")
                break
        finally:
            try:
                if application.updater:
                    await application.updater.stop()
                await application.stop()
                await application.shutdown()
            except Exception:
                pass
        break
    else:
        print(f"NYXON BOT {bot_number} failed after {max_retries} attempts")


async def main():
    print(f"Starting {len(BOT_TOKENS)} bots for owner ID: {OWNER_ID}")
    print("NYXON BOT - All actions run in LOOPS!")

    tasks = []
    for i, token in enumerate(BOT_TOKENS, 1):
        task = asyncio.create_task(run_bot(token, i, OWNER_ID))
        tasks.append(task)
        await asyncio.sleep(0.05)

    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        print("\nShutting down all bots...")


if __name__ == "__main__":
    asyncio.run(main())
