"""
Tradepedia Telegram Bot - Phase 2 Conversational Funnel
Auto-flow + delays + human-style conversation
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode, ChatAction
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

load_dotenv()

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("tradepedia_funnel_bot")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
FREE_CHANNEL_LINK = os.getenv("FREE_CHANNEL_LINK", "").strip()
BROKER_LINK = os.getenv("BROKER_LINK", "").strip()
APP_LINK = os.getenv("APP_LINK", "https://tradepedia.com/").strip()
IOS_APP = os.getenv("IOS_APP", "").strip()
ANDROID_APP = os.getenv("ANDROID_APP", "").strip()
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
CONTENT_FILE = Path(os.getenv("CONTENT_FILE", "content.json"))

if not BOT_TOKEN:
    raise RuntimeError("Missing BOT_TOKEN in .env")

DATA_DIR.mkdir(parents=True, exist_ok=True)
USER_STATE_FILE = DATA_DIR / "user_state.json"


DEFAULT_CONTENT = {
    "brand_name": "Tradepedia",
    "persona_name": "David",
    "recent_results": [
        {
            "image": "images/proof1.jpeg",
            "caption": "📊 Multi-year verified trading performance showing long-term profitability and consistency."
        },
        {
            "image": "images/proof2.jpeg",
            "caption": "📈 Recent live account results showing current execution and structured trade management."
        }
    ],
    "testimonials": [
        {
            "image": "images/proof3.jpeg",
            "caption": "🧾 Real client feedback showing confidence built through structured trading."
        }
    ],
    "onboarding_days": {
        "day1": "Welcome to the free journey. Watch how setups are structured.",
        "day2": "Focus on entry zone, stop loss, target, and patience. Don’t chase.",
        "day3": "Proof matters. Structure removes emotional trading.",
        "day4": "Consistency protects capital before chasing profit.",
        "day5": "Premium Access gives earlier timing, deeper analysis, and stronger execution.",
        "day6": "Discipline is your edge. Wait for clean setups.",
        "day7": "If free makes sense, Premium Access is the natural next step."
    }
}


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("Failed to load JSON")
        return default


def save_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def load_content() -> dict[str, Any]:
    if not CONTENT_FILE.exists():
        save_json(CONTENT_FILE, DEFAULT_CONTENT)
        return DEFAULT_CONTENT
    merged = DEFAULT_CONTENT.copy()
    merged.update(load_json(CONTENT_FILE, {}))
    return merged


CONTENT = load_content()


def get_user_state(context: ContextTypes.DEFAULT_TYPE) -> dict[str, Any]:
    context.user_data.setdefault("state", {})
    return context.user_data["state"]


def load_user_state_store() -> dict[str, Any]:
    return load_json(USER_STATE_FILE, {})


def save_user_state_store(store: dict[str, Any]) -> None:
    save_json(USER_STATE_FILE, store)


def free_join_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Join Free Signals Channel", url=FREE_CHANNEL_LINK)],
        [InlineKeyboardButton("I Joined", callback_data="after_free_join")],
    ])


def app_upgrade_markup() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("🚀 Unlock Premium Access", url=APP_LINK)]
    ]

    if IOS_APP:
        rows.append([InlineKeyboardButton("📱 Download iOS App", url=IOS_APP)])

    if ANDROID_APP:
        rows.append([InlineKeyboardButton("🤖 Download Android App", url=ANDROID_APP)])

    if BROKER_LINK:
        rows.append([InlineKeyboardButton("📈 XM Route: Unlock 6 Months", callback_data="broker_path")])

    rows.append([InlineKeyboardButton("Talk to us directly", callback_data="human_close")])
    return InlineKeyboardMarkup(rows)


def broker_markup() -> InlineKeyboardMarkup:
    rows = []

    if BROKER_LINK:
        rows.append([InlineKeyboardButton("📈 Open XM Account", url=BROKER_LINK)])

    rows.append([InlineKeyboardButton("Back to Premium Access", callback_data="premium_offer")])
    return InlineKeyboardMarkup(rows)


async def send_plain_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup,
        disable_web_page_preview=True,
    )


async def send_sequence(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    messages: list[dict[str, Any]],
) -> None:
    chat_id = update.effective_chat.id

    for msg in messages:
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        await asyncio.sleep(msg.get("delay", 2))

        if msg.get("type", "text") == "text":
            await context.bot.send_message(
                chat_id=chat_id,
                text=msg["text"],
                parse_mode=ParseMode.HTML,
                reply_markup=msg.get("reply_markup"),
                disable_web_page_preview=True,
            )

        elif msg.get("type") == "photo":
            image_path = Path(msg["path"])

            if not image_path.exists():
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"Missing image: {msg['path']}",
                )
                continue

            with image_path.open("rb") as photo:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=msg.get("caption", ""),
                )


async def send_results(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    for item in CONTENT["recent_results"]:
        image_path = Path(item["image"])
        caption = item.get("caption", "")

        if not image_path.exists():
            await send_plain_text(update, context, f"Missing result image: {item['image']}")
            continue

        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.UPLOAD_PHOTO,
        )
        await asyncio.sleep(1)

        with image_path.open("rb") as photo:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=photo,
                caption=caption,
            )


async def send_testimonials(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    for item in CONTENT["testimonials"]:
        image_path = Path(item["image"])
        caption = item.get("caption", "")

        if not image_path.exists():
            await send_plain_text(update, context, f"Missing testimonial image: {item['image']}")
            continue

        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.UPLOAD_PHOTO,
        )
        await asyncio.sleep(1)

        with image_path.open("rb") as photo:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=photo,
                caption=caption,
            )


async def send_performance_proof(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    messages = [
        {
            "text": "Before trusting anyone in trading, first verify they actually trade.",
            "delay": 2,
        },
        {
            "text": "And more importantly...",
            "delay": 2,
        },
        {
            "text": "<b>verify consistency over time.</b>",
            "delay": 2,
        },
        {
            "text": (
                "📊 <b>Multi-Year Verified Trading Performance</b>\n\n"
                "• 2023 Profit → $608,000+\n"
                "• 2024 Profit → $1.46M+\n"
                "• 2025 Profit → $1.18M+\n"
                "• 2026 YTD Profit → $929,000+"
            ),
            "delay": 2,
        },
        {
            "text": (
                "This proves:\n\n"
                "• long-term profitability\n"
                "• real trading activity\n"
                "• professional scale\n"
                "• consistency, not luck"
            ),
            "delay": 2,
        },
        {
            "text": "Anyone can show one lucky trade.\n\n<b>Very few can show years of consistency.</b>",
            "delay": 2,
            "reply_markup": InlineKeyboardMarkup([
                [InlineKeyboardButton("Show me recent live results", callback_data="next_results")]
            ]),
        },
    ]

    await send_sequence(update, context, messages)


def build_free_vs_premium_text() -> str:
    return (
        "📘 <b>Free vs Premium Access</b>\n\n"
        "<b>FREE SIGNAL EXAMPLE</b>\n"
        "Pair: XAUUSD\n"
        "Direction: Buy\n"
        "Entry Zone: 2328 - 2331\n"
        "TP: 2338\n"
        "SL: 2323\n"
        "Comment: clean level-based setup\n\n"
        "<b>PREMIUM ACCESS EXAMPLE</b>\n"
        "Pair: XAUUSD\n"
        "Bias: Bullish continuation after structure hold\n"
        "Entry Zone: 2328 - 2331\n"
        "Invalidation: close below 2323\n"
        "TP1: 2338\n"
        "TP2: 2344\n"
        "Reasoning: HTF alignment, liquidity sweep, demand reaction, execution structure included\n\n"
        "Free members see the setup.\n"
        "<b>Premium members get deeper structure, earlier positioning, and stronger execution context.</b>"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = get_user_state(context)
    state.clear()
    state["step"] = "entry"

    persona_name = CONTENT.get("persona_name", "David")

    messages = [
        {
            "text": "🎥 Watch this quickly before anything else...",
            "delay": 1,
        },
        {
            "text": f"Hey — I’m <b>{persona_name}</b>.",
            "delay": 2,
        },
        {
            "text": "I help traders follow structured setups instead of random signals.",
            "delay": 2,
        },
        {
            "text": "This is not about hype.",
            "delay": 2,
        },
        {
            "text": "It’s about timing, structure, proof, and consistency.",
            "delay": 2,
        },
        {
            "text": "<b>Quick question — have you traded before?</b>",
            "delay": 2,
            "reply_markup": InlineKeyboardMarkup([
                [InlineKeyboardButton("Beginner", callback_data="exp_beginner")],
                [InlineKeyboardButton("Some experience", callback_data="exp_mid")],
                [InlineKeyboardButton("Already using signals", callback_data="exp_signals")],
            ]),
        },
    ]

    await send_sequence(update, context, messages)


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start(update, context)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("/start /menu /status")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    step = get_user_state(context).get("step", "unknown")
    await update.message.reply_text(f"Current step: {step}")


async def schedule_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.job_queue:
        logger.warning("JobQueue unavailable. Onboarding scheduling skipped.")
        return

    user = update.effective_user
    chat = update.effective_chat

    if not user or not chat:
        return

    store = load_user_state_store()
    key = str(user.id)

    if store.get(key, {}).get("onboarding_scheduled"):
        return

    onboarding = CONTENT["onboarding_days"]
    days = ["day1", "day2", "day3", "day4", "day5", "day6", "day7"]

    for index, day_key in enumerate(days):
        when_seconds = index * 24 * 60 * 60

        context.job_queue.run_once(
            send_onboarding_message,
            when=when_seconds,
            data={
                "chat_id": chat.id,
                "text": onboarding[day_key],
                "day_num": index + 1,
            },
            name=f"onboarding_{user.id}_{day_key}",
        )

    store[key] = {"onboarding_scheduled": True}
    save_user_state_store(store)


async def send_onboarding_message(context: ContextTypes.DEFAULT_TYPE) -> None:
    job = context.job

    await context.bot.send_message(
        chat_id=job.data["chat_id"],
        text=f"📅 <b>Day {job.data['day_num']}</b>\n\n{job.data['text']}",
        parse_mode=ParseMode.HTML,
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query

    try:
        await query.answer()
    except Exception:
        pass

    state = get_user_state(context)
    data = query.data or ""

    if data == "restart":
        await start(update, context)
        return

    if data == "exp_beginner":
        state["experience"] = "beginner"
        state["step"] = "loss_question"

        messages = [
            {
                "text": "Got it — that’s actually a good place to start.",
                "delay": 1,
            },
            {
                "text": "Most beginners don’t lose because of the market.",
                "delay": 2,
            },
            {
                "text": "They lose because they follow signals blindly without understanding structure.",
                "delay": 2,
            },
            {
                "text": "Let me ask you something...",
                "delay": 2,
            },
            {
                "text": "<b>Have you ever lost money following signals before?</b>",
                "delay": 2,
                "reply_markup": InlineKeyboardMarkup([
                    [InlineKeyboardButton("Yes", callback_data="lost_yes")],
                    [InlineKeyboardButton("No", callback_data="lost_no")],
                ]),
            },
        ]

        await send_sequence(update, context, messages)
        return

    if data == "exp_mid":
        state["experience"] = "mid"
        state["step"] = "loss_question"

        messages = [
            {
                "text": "Good — then you’ll understand this quickly.",
                "delay": 1,
            },
            {
                "text": "The issue with most signal groups is poor timing.",
                "delay": 2,
            },
            {
                "text": "Late entries. No reasoning. No structure.",
                "delay": 2,
            },
            {
                "text": "<b>Have you lost money following signals before?</b>",
                "delay": 2,
                "reply_markup": InlineKeyboardMarkup([
                    [InlineKeyboardButton("Yes", callback_data="lost_yes")],
                    [InlineKeyboardButton("No", callback_data="lost_no")],
                ]),
            },
        ]

        await send_sequence(update, context, messages)
        return

    if data == "exp_signals":
        state["experience"] = "signals"
        state["step"] = "loss_question"

        messages = [
            {
                "text": "Let me guess — inconsistent results?",
                "delay": 1,
            },
            {
                "text": "That usually happens when entries are late and the reasoning is missing.",
                "delay": 2,
            },
            {
                "text": "Signals alone are not enough.",
                "delay": 2,
            },
            {
                "text": "<b>Have you lost money with other signal groups before?</b>",
                "delay": 2,
                "reply_markup": InlineKeyboardMarkup([
                    [InlineKeyboardButton("Yes", callback_data="lost_yes")],
                    [InlineKeyboardButton("No", callback_data="lost_no")],
                ]),
            },
        ]

        await send_sequence(update, context, messages)
        return

    if data == "lost_yes":
        state["pain"] = "yes"
        state["step"] = "performance_proof"

        messages = [
            {
                "text": "Yeah... that’s exactly why most traders come to us.",
                "delay": 2,
            },
            {
                "text": "Not because they’re new.",
                "delay": 2,
            },
            {
                "text": "But because they’ve already been burned by bad timing and low-quality signals.",
                "delay": 2,
            },
            {
                "text": "So before anything else...",
                "delay": 2,
            },
        ]

        await send_sequence(update, context, messages)
        await send_performance_proof(update, context)
        return

    if data == "lost_no":
        state["pain"] = "no"
        state["step"] = "performance_proof"

        messages = [
            {
                "text": "That’s good.",
                "delay": 1,
            },
            {
                "text": "It means you haven’t built too many bad habits yet.",
                "delay": 2,
            },
            {
                "text": "So the smartest thing now is to verify consistency before trusting anyone.",
                "delay": 2,
            },
        ]

        await send_sequence(update, context, messages)
        await send_performance_proof(update, context)
        return

    if data == "next_results":
        state["step"] = "results"

        messages = [
            {
                "text": "Now let me show you recent live account proof.",
                "delay": 2,
            }
        ]

        await send_sequence(update, context, messages)
        await send_results(update, context)

        messages = [
            {
                "text": "So now you’ve seen both:",
                "delay": 2,
            },
            {
                "text": "• multi-year consistency\n• recent live execution",
                "delay": 2,
            },
            {
                "text": "That’s the difference between marketing and real trading.",
                "delay": 2,
                "reply_markup": InlineKeyboardMarkup([
                    [InlineKeyboardButton("Show me real testimonials", callback_data="next_testimonials")]
                ]),
            },
        ]

        await send_sequence(update, context, messages)
        return

    if data == "next_testimonials":
        state["step"] = "testimonials"

        messages = [
            {
                "text": "Now look at what real users say.",
                "delay": 2,
            },
            {
                "text": "Not theory. Not hype.",
                "delay": 2,
            },
            {
                "text": "Real people seeing confidence through structure.",
                "delay": 2,
            },
        ]

        await send_sequence(update, context, messages)
        await send_testimonials(update, context)

        messages = [
            {
                "text": "Now let me show you what separates Free from Premium.",
                "delay": 2,
                "reply_markup": InlineKeyboardMarkup([
                    [InlineKeyboardButton("Continue", callback_data="next_explain")]
                ]),
            },
        ]

        await send_sequence(update, context, messages)
        return

    if data == "next_explain":
        state["step"] = "free_vs_premium"

        messages = [
            {
                "text": "Most groups give signals.",
                "delay": 2,
            },
            {
                "text": "Tradepedia gives structure.",
                "delay": 2,
            },
            {
                "text": "Free members see the setup.",
                "delay": 2,
            },
            {
                "text": "Premium members understand the reasoning, timing, and execution context.",
                "delay": 2,
            },
            {
                "text": build_free_vs_premium_text(),
                "delay": 2,
                "reply_markup": InlineKeyboardMarkup([
                    [InlineKeyboardButton("Start with free signals", callback_data="join_free")]
                ]),
            },
        ]

        await send_sequence(update, context, messages)
        return

    if data == "join_free":
        state["step"] = "join_free"

        messages = [
            {
                "text": "You do <b>not</b> need to jump into Premium immediately.",
                "delay": 2,
            },
            {
                "text": "The best move is simple:",
                "delay": 2,
            },
            {
                "text": "Join the free channel first.",
                "delay": 2,
            },
            {
                "text": "Watch how the setups are structured.",
                "delay": 2,
            },
            {
                "text": "Then you’ll understand why Premium exists.",
                "delay": 2,
                "reply_markup": free_join_markup(),
            },
        ]

        await send_sequence(update, context, messages)
        return

    if data == "after_free_join":
        state["step"] = "joined_free"
        await schedule_onboarding(update, context)

        messages = [
            {
                "text": "Good — that’s the right way to start.",
                "delay": 2,
            },
            {
                "text": "Watch the next few trades.",
                "delay": 2,
            },
            {
                "text": "Pay attention to structure, timing, and risk.",
                "delay": 2,
            },
            {
                "text": "That’s usually when serious traders understand why Premium Access exists.",
                "delay": 2,
            },
            {
                "text": "Ready to see what Premium includes?",
                "delay": 2,
                "reply_markup": InlineKeyboardMarkup([
                    [InlineKeyboardButton("Show me Premium Access", callback_data="premium_offer")]
                ]),
            },
        ]

        await send_sequence(update, context, messages)
        return

    if data == "premium_offer":
        state["step"] = "premium_offer"

        messages = [
            {
                "text": "🚀 <b>Unlock Tradepedia Premium Access</b>",
                "delay": 2,
            },
            {
                "text": (
                    "Premium Access unlocks:\n\n"
                    "• high-quality signals\n"
                    "• advanced market structure analysis\n"
                    "• early access to top trade setups\n"
                    "• full app features\n"
                    "• exclusive tools\n"
                    "• Inner Circle trading community"
                ),
                "delay": 2,
            },
            {
                "text": (
                    "Pricing:\n\n"
                    "• 1 Month — AED 199.99\n"
                    "• 6 Months — AED 999.99\n"
                    "• 12 Months — AED 1,799.99"
                ),
                "delay": 2,
            },
            {
                "text": (
                    "Alternative route:\n\n"
                    "Open XM account + deposit $250\n"
                    "→ unlock 6 months of Premium Access"
                ),
                "delay": 2,
            },
            {
                "text": "<b>This is not just a signal group.</b>\n\nThis is a full trading ecosystem.",
                "delay": 2,
                "reply_markup": app_upgrade_markup(),
            },
        ]

        await send_sequence(update, context, messages)
        return

    if data == "broker_path":
        state["step"] = "broker_path"

        messages = [
            {
                "text": "📈 <b>Alternative Premium Access Route</b>",
                "delay": 2,
            },
            {
                "text": "Open an XM account and deposit $250.",
                "delay": 2,
            },
            {
                "text": "That unlocks <b>6 months of Tradepedia Premium Access</b>.",
                "delay": 2,
                "reply_markup": broker_markup(),
            },
        ]

        await send_sequence(update, context, messages)
        return

    if data == "human_close":
        state["step"] = "human_close"

        messages = [
            {
                "text": "Perfect.",
                "delay": 1,
            },
            {
                "text": "If you want a direct handoff, we can continue the conversation personally from here.",
                "delay": 2,
            },
            {
                "text": "You can also go straight into the app and unlock Premium Access when ready.",
                "delay": 2,
                "reply_markup": InlineKeyboardMarkup([
                    [InlineKeyboardButton("Open Tradepedia App", url=APP_LINK)]
                ]),
            },
        ]

        await send_sequence(update, context, messages)
        return

    await send_plain_text(update, context, "Unknown action. Type /start to begin again.")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled exception", exc_info=context.error)


def build_app() -> Application:
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_error_handler(error_handler)

    return app


if __name__ == "__main__":
    logger.info("Bot starting...")
    build_app().run_polling(allowed_updates=Update.ALL_TYPES)