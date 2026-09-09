import json
import logging
import os
import random
import re
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.constants import ChatMemberStatus
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID_RAW = os.getenv("OWNER_ID")
TARGET_CHAT_ID_RAW = os.getenv("TARGET_CHAT_ID")

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN is missing. Add BOT_TOKEN=your_token to .env"
    )

if not OWNER_ID_RAW:
    raise RuntimeError(
        "OWNER_ID is missing. Add OWNER_ID=your_telegram_id to .env"
    )

try:
    OWNER_ID = int(OWNER_ID_RAW)
except ValueError:
    raise RuntimeError("OWNER_ID must be a valid Telegram numeric ID.")

# TARGET_CHAT_ID is optional.
# If it is not in .env, the bot can be registered from the group
# using /setgroup.
TARGET_CHAT_ID: Optional[int] = None

if TARGET_CHAT_ID_RAW:
    try:
        TARGET_CHAT_ID = int(TARGET_CHAT_ID_RAW)
    except ValueError:
        raise RuntimeError(
            "TARGET_CHAT_ID must be a valid Telegram chat ID."
        )


CONFIG_FILE = Path("config.json")

DEFAULT_INTERVAL = 45
DEFAULT_DELETE_AFTER = 8

DEFAULT_MESSAGES = [
    "🔴 WE ARE LIVE NOW — JOIN THE CALL!",
    "🎙️ LIVE SESSION IS ON — COME THROUGH NOW!",
    "🚨 WE'RE LIVE — DON'T MISS THE SESSION!",
    "📈 LIVE TRADING SESSION IS ACTIVE — JOIN US!",
    "🔥 WE ARE LIVE RIGHT NOW — GET IN THE CALL!",
    "👀 IF YOU'RE IN THE GROUP, COME JOIN THE LIVE!",
    "🟣 APEXTRADE AI IS LIVE — JOIN THE SESSION!",
    "🚨 LIVE NOW — COME IN BEFORE WE GET STARTED!",


    # NEWLY ADDED MESSAGES

    "⚠️ WE ARE NOW LIVE ⚠️",

    "LIVE SESSION ONGOING JOIN NOW❗️❗️❗️❗️❗️ ",

    "COME HERE NOW ❗️❗️ JOIN THE LIVE 🔥 ",

    "🔴 WE ARE LIVE! JOIN THE LIVE SESSION NOW !!🔥",

    " TODAY'S GIVEAWAY 🎁 WILL BE $50(70k) FOR NEW LUCKY MEMBERS 🚀🔥",

    "YOU WERE MENTIONED!",

    "YOU WERE MENTIONED TWICE",

    "DON’T MISS THIS OPPORTUNITY",

    "LIVE TRADING SESSION WILL BEGIN SOON ‼️ JOIN THE LIVE NOW❗️❗️❗️❗️❗️",

    "ACT NOW, ACT FAST, BE A WINNER 🏆",

    "ApexTrade AI invites you to join- the live Call.",

    "🎉🎁 $500 GIVEAWAY FOR 10 NEW MEMBERS 🎉🎁\n\nJOIN THE LIVE NOW❗️❗️❗️❗️❗️❗️",

    "🔥 TAKE ACTION RIGHT NOW ‼️",

    "ApexTrade AI Mentioned you 🫵",

    "$50 each for 10 people on this live 🔥🔥🔥🔥🔥🔥",

    "🔴🔴 All new members/traders\nGet in the live stream 👇👇👇",

    "You have been mentioned 🫵 Join The Live Now ‼️",

    "APEXTRADE AI MENTIONED YOU 👇👇👇🫵",

    "🔥⚠️ TAKE ACTION NOW 🔥⚠️",

    "🚨 APEXTRADE AI MENTIONED YOU! 🫵\nYes, YOU. Get into the live session now! 🟣",

    "JOIN THE LIVE STREAM NOW‼️",

    "🔴 WE ARE NOW LIVE! 🔴\nStop scrolling and get inside the session. 📊🚀",

    "📢 NEW MEMBERS, JOIN THE LIVE NOW 🔥",

    "🔥 THE LIVE SESSION HAS STARTED 📊\nDon’t watch the replay when you can be here LIVE👇",

    "🎁 GIVEAWAY TIME! Who’s inside the live already? 👀🟣 Get in before we start picking winners!",

    "If you’re not inside the live yet, this is your reminder.🚨 JOIN NOW 🚨",

    "🔥 WE’RE ACTIVE ON LIVE SESSION",

    "📢 ALL NEW MEMBERS! JOIN THE LIVE NOW 🔥",

    "🚨🚨 APEXTRADE AI MENTIONED YOU! 🫵",

    "JOIN THE LIVE NOW! 🚨 🏆 WINNERS ARE BEING ANNOUNCED! ",
]


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# ============================================================
# CONFIG / DATABASE
# ============================================================

def merge_default_messages(settings: dict[str, Any]) -> None:
    """Keep existing custom messages and add newly shipped defaults."""
    messages = settings.get("messages")

    if not isinstance(messages, list):
        messages = []

    settings["messages"] = messages + [
        message
        for message in DEFAULT_MESSAGES
        if message not in messages
    ]


def load_config() -> dict[str, Any]:
    if not CONFIG_FILE.exists():
        data = {
            "default_interval": DEFAULT_INTERVAL,
            "default_delete_after": DEFAULT_DELETE_AFTER,
            "target_chat_id": TARGET_CHAT_ID,
            "settings": {
                "interval": DEFAULT_INTERVAL,
                "delete_after": DEFAULT_DELETE_AFTER,
                "messages": DEFAULT_MESSAGES.copy(),
                "live": False,
            },
        }

        save_config(data)
        return data

    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)

        data.setdefault(
            "default_interval",
            DEFAULT_INTERVAL,
        )

        data.setdefault(
            "default_delete_after",
            DEFAULT_DELETE_AFTER,
        )

        # An explicitly configured environment value is authoritative.
        # This keeps config.json synchronized when TARGET_CHAT_ID changes.
        if TARGET_CHAT_ID_RAW:
            data["target_chat_id"] = TARGET_CHAT_ID
        else:
            data.setdefault("target_chat_id", None)

        if data.get("target_chat_id") != TARGET_CHAT_ID and TARGET_CHAT_ID_RAW:
            save_config(data)

        data.setdefault("settings", {})

        settings = data["settings"]

        settings.setdefault(
            "interval",
            data["default_interval"],
        )

        settings.setdefault(
            "delete_after",
            data["default_delete_after"],
        )

        settings.setdefault(
            "messages",
            DEFAULT_MESSAGES.copy(),
        )

        merge_default_messages(settings)

        settings.setdefault("live", False)

        return data

    except (json.JSONDecodeError, OSError):
        logger.exception("Unable to load config.json.")

        return {
            "default_interval": DEFAULT_INTERVAL,
            "default_delete_after": DEFAULT_DELETE_AFTER,
            "target_chat_id": TARGET_CHAT_ID,
            "settings": {
                "interval": DEFAULT_INTERVAL,
                "delete_after": DEFAULT_DELETE_AFTER,
                "messages": DEFAULT_MESSAGES.copy(),
                "live": False,
            },
        }


def save_config(data: dict[str, Any]) -> None:
    temp_file = CONFIG_FILE.with_suffix(".tmp")

    with temp_file.open("w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            indent=4,
            ensure_ascii=False,
        )

    temp_file.replace(CONFIG_FILE)


config = load_config()


# ============================================================
# TARGET GROUP
# ============================================================

def get_target_chat_id() -> Optional[int]:
    """
    Returns the configured target group ID.
    """
    value = config.get("target_chat_id")

    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def set_target_chat_id(chat_id: int) -> None:
    config["target_chat_id"] = chat_id
    save_config(config)


def get_settings() -> dict[str, Any]:
    """
    Global settings for the target group.
    """
    settings = config.setdefault("settings", {})

    settings.setdefault(
        "interval",
        config.get(
            "default_interval",
            DEFAULT_INTERVAL,
        ),
    )

    settings.setdefault(
        "delete_after",
        config.get(
            "default_delete_after",
            DEFAULT_DELETE_AFTER,
        ),
    )

    settings.setdefault(
        "messages",
        DEFAULT_MESSAGES.copy(),
    )

    merge_default_messages(settings)

    settings.setdefault(
        "live",
        False,
    )

    return settings


# ============================================================
# OWNER CHECK
# ============================================================

def is_owner(user_id: Optional[int]) -> bool:
    if user_id is None:
        return False

    return user_id == OWNER_ID


async def owner_only(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:

    user = update.effective_user

    if user and is_owner(user.id):
        return True

    if update.callback_query:
        await update.callback_query.answer(
            "⛔ Owner only.",
            show_alert=True,
        )

    elif update.message:
        await update.message.reply_text(
            "⛔ You are not authorized to control this bot."
        )

    return False


# ============================================================
# BOT ADMIN CHECK
# ============================================================

async def bot_is_admin(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
) -> bool:

    try:
        me = await context.bot.get_me()

        member = await context.bot.get_chat_member(
            chat_id=chat_id,
            user_id=me.id,
        )

        return member.status in (
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        )

    except TelegramError as exc:
        logger.error(
            "Could not check bot admin status: %s",
            exc,
        )

        return False


# ============================================================
# TIME HELPERS
# ============================================================

def parse_duration(text: str) -> Optional[int]:
    """
    Parse a duration such as '45s', '5m', '1h', '30',
    '10 min' or '2hours'.

    Returns total seconds, or None if the format
    is not understood.
    """

    match = re.fullmatch(
        r"\s*(\d+)\s*([a-zA-Z]{0,7})\s*",
        text,
    )

    if not match:
        return None

    value = int(match.group(1))

    unit = match.group(2).lower()

    if unit in (
        "",
        "s",
        "sec",
        "secs",
        "second",
        "seconds",
    ):
        multiplier = 1

    elif unit in (
        "m",
        "min",
        "mins",
        "minute",
        "minutes",
    ):
        multiplier = 60

    elif unit in (
        "h",
        "hr",
        "hrs",
        "hour",
        "hours",
    ):
        multiplier = 3600

    else:
        return None

    return value * multiplier


def format_duration(seconds: int) -> str:

    if seconds % 3600 == 0:
        hours = seconds // 3600
        plural = "s" if hours != 1 else ""
        return f"{hours} hour{plural}"

    if seconds % 60 == 0:
        minutes = seconds // 60
        plural = "s" if minutes != 1 else ""
        return f"{minutes} minute{plural}"

    return f"{seconds} seconds"


# ============================================================
# KEYBOARDS
# ============================================================

def main_keyboard(
    settings: dict[str, Any],
) -> InlineKeyboardMarkup:

    live = settings["live"]

    if live:
        live_button = InlineKeyboardButton(
            "⏹ STOP LIVE",
            callback_data="live_stop",
        )
    else:
        live_button = InlineKeyboardButton(
            "🔴 START LIVE",
            callback_data="live_start",
        )

    keyboard = [
        [
            live_button,
        ],

        [
            InlineKeyboardButton(
                "⏱ INTERVAL",
                callback_data="menu_interval",
            ),
            InlineKeyboardButton(
                "🗑 DELETE AFTER",
                callback_data="menu_delete",
            ),
        ],

        [
            InlineKeyboardButton(
                "💬 MESSAGES",
                callback_data="menu_messages",
            ),
        ],

        [
            InlineKeyboardButton(
                "🎯 TARGET GROUP",
                callback_data="menu_target",
            ),
        ],

        [
            InlineKeyboardButton(
                "📊 STATUS",
                callback_data="menu_status",
            ),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


def back_keyboard() -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "◀️ BACK",
                    callback_data="menu_main",
                )
            ]
        ]
    )


def interval_keyboard() -> InlineKeyboardMarkup:

    values = [
        (5, "5 seconds"),
        (20, "20 seconds"),
        (30, "30 seconds"),
        (45, "45 seconds"),
        (60, "60 seconds"),
        (90, "90 seconds"),
        (120, "2 minutes"),
    ]

    keyboard = []

    for seconds, label in values:
        keyboard.append(
            [
                InlineKeyboardButton(
                    label,
                    callback_data=f"interval_{seconds}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                "✏️ CUSTOM TIME",
                callback_data="interval_custom",
            )
        ]
    )

    keyboard.append(
        [
            InlineKeyboardButton(
                "◀️ BACK",
                callback_data="menu_main",
            )
        ]
    )

    return InlineKeyboardMarkup(keyboard)


def delete_keyboard() -> InlineKeyboardMarkup:

    values = [
        (5, "5 seconds"),
        (20, "20 seconds"),
        (30, "30 seconds"),
        (45, "45 seconds"),
        (60, "60 seconds"),
        (90, "90 seconds"),
        (120, "2 minutes"),
    ]

    keyboard = []

    for seconds, label in values:
        keyboard.append(
            [
                InlineKeyboardButton(
                    label,
                    callback_data=f"delete_{seconds}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                "✏️ CUSTOM TIME",
                callback_data="delete_custom",
            )
        ]
    )

    keyboard.append(
        [
            InlineKeyboardButton(
                "◀️ BACK",
                callback_data="menu_main",
            )
        ]
    )

    return InlineKeyboardMarkup(keyboard)


def messages_keyboard() -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "👁 VIEW MESSAGES",
                    callback_data="messages_view",
                )
            ],

            [
                InlineKeyboardButton(
                    "➕ ADD MESSAGE",
                    callback_data="messages_add",
                )
            ],

            [
                InlineKeyboardButton(
                    "🗑 REMOVE MESSAGE",
                    callback_data="messages_delete",
                )
            ],

            [
                InlineKeyboardButton(
                    "◀️ BACK",
                    callback_data="menu_main",
                )
            ],
        ]
    )


def target_keyboard() -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📍 USE THIS GROUP",
                    callback_data="target_register_current",
                )
            ],

            [
                InlineKeyboardButton(
                    "🔄 REFRESH",
                    callback_data="menu_target",
                )
            ],

            [
                InlineKeyboardButton(
                    "◀️ BACK",
                    callback_data="menu_main",
                )
            ],
        ]
    )


# ============================================================
# PANEL TEXT
# ============================================================

def panel_text(
    settings: dict[str, Any],
) -> str:

    if settings["live"]:
        status = "🔴 LIVE"
    else:
        status = "⚪ OFF"

    target_chat_id = get_target_chat_id()

    if target_chat_id:
        target = str(target_chat_id)
    else:
        target = "❌ Not configured"

    return (
        "🟣 LIVE ALERT BOT\n\n"
        f"Status: {status}\n\n"
        f"🎯 Target Group: {target}\n"
        f"⏱ Interval: "
        f"{format_duration(settings['interval'])}\n"
        f"🗑 Delete after: "
        f"{format_duration(settings['delete_after'])}\n"
        f"💬 Alert messages: "
        f"{len(settings['messages'])}\n\n"
        "Use the buttons below to control the bot."
    )


# ============================================================
# /START
# ============================================================

async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    if not await owner_only(update, context):
        return

    settings = get_settings()

    if not update.message:
        return

    await update.message.reply_text(
        panel_text(settings),
        reply_markup=main_keyboard(settings),
    )


# ============================================================
# /PANEL
# ============================================================

async def panel_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    if not await owner_only(update, context):
        return

    if not update.message:
        return

    settings = get_settings()

    await update.message.reply_text(
        panel_text(settings),
        reply_markup=main_keyboard(settings),
    )


# ============================================================
# /SETGROUP
# ============================================================

async def setgroup_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Run /setgroup inside the target group once.

    Only OWNER_ID can register the group.
    """

    if not await owner_only(update, context):
        return

    chat = update.effective_chat
    message = update.effective_message

    if not chat or not message:
        return

    if chat.type not in (
        "group",
        "supergroup",
        "channel",
    ):
        await message.reply_text(
            "❌ Use /setgroup inside the Telegram group "
            "or channel where you want the live alerts."
        )
        return

    # Verify that the bot itself is an admin.
    if not await bot_is_admin(
        context,
        chat.id,
    ):
        await message.reply_text(
            "❌ I am not an admin here.\n\n"
            "Make me an administrator and give me "
            "permission to send and delete messages."
        )
        return

    set_target_chat_id(chat.id)

    settings = get_settings()

    await message.reply_text(
        "✅ TARGET GROUP SAVED!\n\n"
        f"Group/Channel: {chat.title or 'Unnamed chat'}\n"
        f"Chat ID: {chat.id}\n\n"
        "You can now control the live alerts from "
        "your private chat with the bot using /panel.",
        reply_markup=main_keyboard(settings),
    )


# ============================================================
# LIVE JOB
# ============================================================

def live_job_name() -> str:
    return "live_alert_bot"


async def live_alert_job(
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    job = context.job

    if job is None:
        return

    target_chat_id = get_target_chat_id()

    if target_chat_id is None:
        logger.warning(
            "No target group configured."
        )
        return

    settings = get_settings()

    if not settings["live"]:
        return

    messages = settings["messages"]

    if not messages:
        logger.warning(
            "No alert messages configured."
        )
        return

    # Prevent the exact same message from being selected
    # twice consecutively.
    previous_message = None

    if job.data:
        previous_message = job.data.get(
            "previous_message"
        )

    available = [
        message
        for message in messages
        if message != previous_message
    ]

    if not available:
        available = messages

    text = random.choice(available)

    if job.data is None:
        job.data = {}

    job.data["previous_message"] = text

    try:

        sent = await context.bot.send_message(
            chat_id=target_chat_id,
            text=text,
            disable_web_page_preview=True,
        )

        logger.info(
            "Live alert sent to %s",
            target_chat_id,
        )

        # Schedule automatic deletion.
        context.job_queue.run_once(
            delete_alert_job,
            when=settings["delete_after"],
            data={
                "chat_id": target_chat_id,
                "message_id": sent.message_id,
            },
            name=(
                f"delete_"
                f"{target_chat_id}_"
                f"{sent.message_id}"
            ),
        )

    except TelegramError as exc:

        logger.error(
            "Failed to send live alert: %s",
            exc,
        )


# ============================================================
# DELETE ALERT
# ============================================================

async def delete_alert_job(
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    job = context.job

    if job is None or not job.data:
        return

    chat_id = job.data["chat_id"]
    message_id = job.data["message_id"]

    try:

        await context.bot.delete_message(
            chat_id=chat_id,
            message_id=message_id,
        )

        logger.info(
            "Deleted alert %s from %s",
            message_id,
            chat_id,
        )

    except TelegramError as exc:

        logger.warning(
            "Could not delete message %s: %s",
            message_id,
            exc,
        )


# ============================================================
# START LIVE
# ============================================================

async def start_live(
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:

    target_chat_id = get_target_chat_id()

    if target_chat_id is None:
        return False

    settings = get_settings()

    settings["live"] = True
    save_config(config)

    # Remove old repeating live jobs.
    existing_jobs = context.job_queue.get_jobs_by_name(
        live_job_name()
    )

    for job in existing_jobs:
        job.schedule_removal()

    job_data = {
        "previous_message": None,
    }

    # Send first alert immediately.
    context.job_queue.run_once(
        live_alert_job,
        when=0,
        data=job_data,
        name=f"{live_job_name()}_initial",
    )

    # Continue at selected interval.
    context.job_queue.run_repeating(
        live_alert_job,
        interval=settings["interval"],
        first=settings["interval"],
        data=job_data,
        name=live_job_name(),
    )

    return True


# ============================================================
# STOP LIVE
# ============================================================

async def stop_live(
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    settings = get_settings()

    settings["live"] = False
    save_config(config)

    jobs = context.job_queue.get_jobs_by_name(
        live_job_name()
    )

    for job in jobs:
        job.schedule_removal()


# ============================================================
# CALLBACK HANDLER
# ============================================================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    query = update.callback_query

    if not query:
        return

    if not await owner_only(update, context):
        return

    await query.answer()

    data = query.data

    settings = get_settings()

    # ========================================================
    # MAIN MENU
    # ========================================================

    if data == "menu_main":

        await query.edit_message_text(
            panel_text(settings),
            reply_markup=main_keyboard(settings),
        )

        return

    # ========================================================
    # START LIVE
    # ========================================================

    if data == "live_start":

        target_chat_id = get_target_chat_id()

        if target_chat_id is None:

            await query.edit_message_text(
                "❌ NO TARGET GROUP\n\n"
                "The bot doesn't know which group "
                "to send the live alerts to.\n\n"
                "Go into your target group and send:\n"
                "/setgroup",
                reply_markup=back_keyboard(),
            )

            return

        # Make sure bot is still admin.
        if not await bot_is_admin(
            context,
            target_chat_id,
        ):

            await query.edit_message_text(
                "❌ BOT IS NOT ADMIN\n\n"
                "I need to be an administrator in "
                "the target group with permission to "
                "send and delete messages.",
                reply_markup=back_keyboard(),
            )

            return

        started = await start_live(context)

        if not started:

            await query.edit_message_text(
                "❌ Could not start live mode.",
                reply_markup=back_keyboard(),
            )

            return

        settings = get_settings()

        await query.edit_message_text(
            "🔴 LIVE MODE STARTED!\n\n"
            f"⏱ Every "
            f"{format_duration(settings['interval'])}\n"
            f"🗑 Delete after "
            f"{format_duration(settings['delete_after'])}\n\n"
            "The bot is now sending live alerts "
            "to the target group.",
            reply_markup=main_keyboard(settings),
        )

        return

    # ========================================================
    # STOP LIVE
    # ========================================================

    if data == "live_stop":

        await stop_live(context)

        settings = get_settings()

        await query.edit_message_text(
            "⏹ LIVE MODE STOPPED.\n\n"
            "No more live alerts will be sent.",
            reply_markup=main_keyboard(settings),
        )

        return

    # ========================================================
    # INTERVAL MENU
    # ========================================================

    if data == "menu_interval":

        await query.edit_message_text(
            "⏱ POSTING INTERVAL\n\n"
            "Choose how often the bot sends "
            "a live alert, or set a custom time.\n\n"
            "⚠️ Intervals under 10 seconds can "
            "hit Telegram flood limits.",
            reply_markup=interval_keyboard(),
        )

        return

    # ========================================================
    # CUSTOM INTERVAL
    # ========================================================

    if data == "interval_custom":

        context.user_data["awaiting_input"] = "interval"

        await query.edit_message_text(
            "✏️ CUSTOM INTERVAL\n\n"
            "Send the interval as a number with "
            "a unit:\n\n"
            "• seconds — 30s or just 30\n"
            "• minutes — 5m or 10min\n"
            "• hours — 1h or 2hours\n\n"
            "Examples: 45s, 2m, 1h\n"
            "Maximum: 24h\n\n"
            "Send /cancel to abort.",
            reply_markup=back_keyboard(),
        )

        return

    # ========================================================
    # INTERVAL SET
    # ========================================================

    if data.startswith("interval_"):

        seconds = int(
            data.split("_")[1]
        )

        settings["interval"] = seconds

        save_config(config)

        # If live, restart the repeating job.
        if settings["live"]:

            jobs = context.job_queue.get_jobs_by_name(
                live_job_name()
            )

            for job in jobs:
                job.schedule_removal()

            context.job_queue.run_repeating(
                live_alert_job,
                interval=seconds,
                first=seconds,
                data={
                    "previous_message": None,
                },
                name=live_job_name(),
            )

        await query.edit_message_text(
            "✅ INTERVAL UPDATED\n\n"
            f"Alerts will now be sent every "
            f"{format_duration(seconds)}.",
            reply_markup=main_keyboard(settings),
        )

        return

    # ========================================================
    # DELETE MENU
    # ========================================================

    if data == "menu_delete":

        await query.edit_message_text(
            "🗑 DELETE AFTER\n\n"
            "Choose how long each alert remains "
            "visible, or set a custom time:",
            reply_markup=delete_keyboard(),
        )

        return

    # ========================================================
    # CUSTOM DELETE AFTER
    # ========================================================

    if data == "delete_custom":

        context.user_data["awaiting_input"] = (
            "delete_after"
        )

        await query.edit_message_text(
            "✏️ CUSTOM DELETE TIME\n\n"
            "Send how long each alert should "
            "stay visible, as a number with "
            "a unit:\n\n"
            "• seconds — 10s or just 10\n"
            "• minutes — 5m or 10min\n"
            "• hours — 1h or 2hours\n\n"
            "Examples: 15s, 1m, 1h\n"
            "Maximum: 24h\n\n"
            "Send /cancel to abort.",
            reply_markup=back_keyboard(),
        )

        return

    # ========================================================
    # DELETE SET
    # ========================================================

    if data.startswith("delete_"):

        seconds = int(
            data.split("_")[1]
        )

        settings["delete_after"] = seconds

        save_config(config)

        await query.edit_message_text(
            "✅ DELETE DELAY UPDATED\n\n"
            f"Messages will now be deleted "
            f"after {format_duration(seconds)}.",
            reply_markup=main_keyboard(settings),
        )

        return

    # ========================================================
    # MESSAGES MENU
    # ========================================================

    if data == "menu_messages":

        await query.edit_message_text(
            "💬 ALERT MESSAGES\n\n"
            f"Currently configured: "
            f"{len(settings['messages'])}\n\n"
            "The bot randomly selects messages "
            "from this list.",
            reply_markup=messages_keyboard(),
        )

        return

    # ========================================================
    # VIEW MESSAGES
    # ========================================================

    if data == "messages_view":

        messages = settings["messages"]

        if not messages:

            text = "📝 No alert messages configured."

        else:

            text = "📝 ALERT MESSAGES\n\n"

            for index, message in enumerate(
                messages,
                start=1,
            ):

                text += (
                    f"{index}. {message}\n\n"
                )

        await query.edit_message_text(
            text,
            reply_markup=back_keyboard(),
        )

        return

    # ========================================================
    # ADD MESSAGE
    # ========================================================

    if data == "messages_add":

        context.user_data["awaiting_message"] = True

        await query.edit_message_text(
            "➕ ADD ALERT MESSAGE\n\n"
            "Send the message you want the bot "
            "to use.\n\n"
            "Example:\n"
            "🔴 WE ARE LIVE NOW — JOIN THE CALL!\n\n"
            "Send /cancel if you change your mind.",
            reply_markup=back_keyboard(),
        )

        return

    # ========================================================
    # DELETE MESSAGE MENU
    # ========================================================

    if data == "messages_delete":

        messages = settings["messages"]

        if not messages:

            await query.edit_message_text(
                "🗑 There are no messages to remove.",
                reply_markup=back_keyboard(),
            )

            return

        keyboard = []

        for index, message in enumerate(
            messages,
            start=1,
        ):

            label = message[:35]

            if len(message) > 35:
                label += "..."

            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"🗑 {index}. {label}",
                        callback_data=f"remove_{index}",
                    )
                ]
            )

        keyboard.append(
            [
                InlineKeyboardButton(
                    "◀️ BACK",
                    callback_data="menu_messages",
                )
            ]
        )

        await query.edit_message_text(
            "🗑 REMOVE ALERT MESSAGE\n\n"
            "Select the message you want to remove:",
            reply_markup=InlineKeyboardMarkup(
                keyboard
            ),
        )

        return

    # ========================================================
    # REMOVE MESSAGE
    # ========================================================

    if data.startswith("remove_"):

        index = int(
            data.split("_")[1]
        )

        messages = settings["messages"]

        if index < 1 or index > len(messages):

            await query.answer(
                "Message no longer exists.",
                show_alert=True,
            )

            return

        removed = messages.pop(index - 1)

        save_config(config)

        await query.edit_message_text(
            "🗑 MESSAGE REMOVED\n\n"
            f"{removed}",
            reply_markup=messages_keyboard(),
        )

        return

    # ========================================================
    # TARGET GROUP
    # ========================================================

    if data == "menu_target":

        target_chat_id = get_target_chat_id()

        if target_chat_id:

            try:

                chat = await context.bot.get_chat(
                    target_chat_id
                )

                group_name = (
                    chat.title
                    or chat.username
                    or str(target_chat_id)
                )

                text = (
                    "🎯 TARGET GROUP\n\n"
                    f"Group: {group_name}\n"
                    f"Chat ID: {target_chat_id}\n\n"
                    "To change the target group, "
                    "go into the new group and send:\n\n"
                    "/setgroup"
                )

            except TelegramError:

                text = (
                    "🎯 TARGET GROUP\n\n"
                    f"Chat ID: {target_chat_id}\n\n"
                    "I couldn't retrieve the group "
                    "information right now.\n\n"
                    "To change the target group, "
                    "use /setgroup in the new group."
                )

        else:

            text = (
                "🎯 TARGET GROUP\n\n"
                "❌ No target group configured.\n\n"
                "Go into the group where you want "
                "the alerts and send:\n\n"
                "/setgroup"
            )

        await query.edit_message_text(
            text,
            reply_markup=target_keyboard(),
        )

        return

    # ========================================================
    # REGISTER CURRENT GROUP
    # ========================================================

    if data == "target_register_current":

        await query.answer(
            "Use /setgroup inside the target group.",
            show_alert=True,
        )

        return

    # ========================================================
    # STATUS
    # ========================================================

    if data == "menu_status":

        status = (
            "🔴 LIVE"
            if settings["live"]
            else "⚪ OFF"
        )

        target_chat_id = get_target_chat_id()

        if target_chat_id:

            try:

                chat = await context.bot.get_chat(
                    target_chat_id
                )

                group_name = (
                    chat.title
                    or chat.username
                    or str(target_chat_id)
                )

            except TelegramError:

                group_name = str(target_chat_id)

        else:

            group_name = "❌ Not configured"

        await query.edit_message_text(
            "📊 BOT STATUS\n\n"
            f"Status: {status}\n\n"
            f"🎯 Target: {group_name}\n"
            f"⏱ Interval: "
            f"{format_duration(settings['interval'])}\n"
            f"🗑 Delete after: "
            f"{format_duration(settings['delete_after'])}\n"
            f"💬 Messages: "
            f"{len(settings['messages'])}",
            reply_markup=back_keyboard(),
        )

        return


# ============================================================
# RECEIVE NEW MESSAGE
# ============================================================

async def receive_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    if not update.message:
        return

    text = (update.message.text or "").strip()

    # --------------------------------------------------------
    # CUSTOM TIME INPUT (interval / delete_after)
    # --------------------------------------------------------

    awaiting = context.user_data.get("awaiting_input")

    if awaiting in ("interval", "delete_after"):

        if not await owner_only(update, context):
            return

        seconds = parse_duration(text)

        if seconds is None or not 1 <= seconds <= 86400:

            await update.message.reply_text(
                "❌ Invalid time.\n\n"
                "Use a number with a unit:\n"
                "• seconds — 30s or just 30\n"
                "• minutes — 5m or 10min\n"
                "• hours — 1h or 2hours\n\n"
                "Maximum: 24h\n"
                "Send /cancel to abort.",
                reply_markup=back_keyboard(),
            )

            return

        settings = get_settings()

        label = format_duration(seconds)

        if awaiting == "interval":

            settings["interval"] = seconds

            # If live, restart the repeating job.
            if settings["live"]:

                jobs = (
                    context.job_queue.get_jobs_by_name(
                        live_job_name()
                    )
                )

                for job in jobs:
                    job.schedule_removal()

                context.job_queue.run_repeating(
                    live_alert_job,
                    interval=seconds,
                    first=seconds,
                    data={
                        "previous_message": None,
                    },
                    name=live_job_name(),
                )

            save_config(config)
            context.user_data["awaiting_input"] = None

            await update.message.reply_text(
                "✅ INTERVAL UPDATED\n\n"
                f"Alerts will now be sent every "
                f"{label}.",
                reply_markup=main_keyboard(settings),
            )

            return

        settings["delete_after"] = seconds

        save_config(config)
        context.user_data["awaiting_input"] = None

        await update.message.reply_text(
            "✅ DELETE DELAY UPDATED\n\n"
            f"Messages will now be deleted "
            f"after {label}.",
            reply_markup=main_keyboard(settings),
        )

        return

    # --------------------------------------------------------
    # NEW ALERT MESSAGE INPUT
    # --------------------------------------------------------

    if not context.user_data.get(
        "awaiting_message",
        False,
    ):
        return

    if not await owner_only(update, context):
        return

    message = text

    if not message:
        return

    if len(message) > 4096:

        await update.message.reply_text(
            "❌ Telegram messages cannot exceed "
            "4096 characters."
        )

        return

    settings = get_settings()

    settings["messages"].append(message)

    save_config(config)

    context.user_data["awaiting_message"] = False
    context.user_data["awaiting_input"] = None

    await update.message.reply_text(
        "✅ ALERT MESSAGE ADDED!\n\n"
        f"Total messages: "
        f"{len(settings['messages'])}",
        reply_markup=main_keyboard(settings),
    )


# ============================================================
# CANCEL MESSAGE INPUT
# ============================================================

async def cancel_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    if not await owner_only(update, context):
        return

    context.user_data["awaiting_message"] = False

    settings = get_settings()

    if update.message:

        await update.message.reply_text(
            "❌ Message input cancelled.",
            reply_markup=main_keyboard(settings),
        )


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    logger.error(
        "Unhandled exception:",
        exc_info=context.error,
    )


# ============================================================
# BOT STARTUP
# ============================================================

async def post_init(
    application: Application,
) -> None:

    await application.bot.set_my_commands(
        [
            (
                "start",
                "Open control panel",
            ),
            (
                "panel",
                "Open live alert control panel",
            ),
            (
                "setgroup",
                "Set this group as target",
            ),
            (
                "cancel",
                "Cancel current action",
            ),
        ]
    )

    logger.info(
        "Live Alert Bot started."
    )

    logger.info(
        "Owner ID: %s",
        OWNER_ID,
    )

    target = get_target_chat_id()

    if target:
        logger.info(
            "Target group: %s",
            target,
        )
    else:
        logger.info(
            "No target group configured yet."
        )


# ============================================================
# CHANNEL POST ROUTER
# ============================================================

async def channel_post_router(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Handles posts made inside a channel.

    IMPORTANT:
    Commands posted inside a channel never reach CommandHandler.
    In python-telegram-bot v20+, MessageHandler receives channel
    posts automatically, so we route them here instead.
    """

    post = update.effective_message

    if not post or not post.text:
        return

    # Strip a possible @BotUsername suffix, e.g. /setgroup@MyBot
    command = post.text.strip().split()[0].split("@")[0].lower()

    if command == "/setgroup":
        await setgroup_command(update, context)


# ============================================================
# MAIN
# ============================================================


def main() -> None:

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # --------------------------------------------------------
    # COMMANDS
    # --------------------------------------------------------

    application.add_handler(
        CommandHandler(
            "start",
            start_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "panel",
            panel_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "setgroup",
            setgroup_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "cancel",
            cancel_command,
        )
    )

    # --------------------------------------------------------
    # CHANNEL POSTS (needed for /setgroup inside a channel)
    # --------------------------------------------------------

    application.add_handler(
        MessageHandler(
            filters.ChatType.CHANNEL & filters.TEXT,
            channel_post_router,
        )
    )

    # --------------------------------------------------------
    # BUTTONS
    # --------------------------------------------------------

    application.add_handler(
        CallbackQueryHandler(
            button_handler
        )
    )

    # --------------------------------------------------------
    # MESSAGE INPUT
    # --------------------------------------------------------

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            receive_message,
        )
    )

    # --------------------------------------------------------
    # ERROR HANDLER
    # --------------------------------------------------------

    application.add_error_handler(
        error_handler
    )

    logger.info(
        "Starting Telegram polling..."
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()
