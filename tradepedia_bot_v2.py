"""
Tradepedia Telegram Bot - Phase 2 Conversational Funnel
Main journey:
Telegram Free Signals -> Trust -> App Registration -> Premium Access
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
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
VIP_CHANNEL_LINK = os.getenv("VIP_CHANNEL_LINK", "").strip()  # optional supporting benefit
BROKER_LINK = os.getenv("BROKER_LINK", "").strip()            # XM / broker route
APP_LINK = os.getenv("APP_LINK", "http://www.tradepedia.com").strip()
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))

ADMIN_IDS = {
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}

CONTENT_FILE = Path(os.getenv("CONTENT_FILE", "content.json"))

if not BOT_TOKEN:
    raise RuntimeError("Missing BOT_TOKEN in environment variables.")

DATA_DIR.mkdir(parents=True, exist_ok=True)
USER_STATE_FILE = DATA_DIR / "user_state.json"


DEFAULT_CONTENT = {
    "brand_name": "Tradepedia",
    "persona_name": "David",
    "welcome_hook": "I help traders with structured signals, cleaner entries, and better decision-making.",
    "entry_message": (
        "This is not one of those random signal groups that throws entries at you with no structure.\n\n"
        "Before I show you anything, I just want to understand where you are."
    ),
    "recent_results": [
        {
            "image": "images/results.png",
            "caption": "📊 Recent live account results showing structured execution, defined entries, and clean profit-taking."
        }
    ],
    "testimonials": [
        {
            "image": "images/reviews.png",
            "caption": "🧾 Real user feedback showing the value of structure, discipline, and consistency."
        }
    ],
    "free_signal_example": (
        "FREE SIGNAL EXAMPLE\n"
        "Pair: XAUUSD\n"
        "Direction: Buy\n"
        "Entry Zone: 2328 - 2331\n"
        "TP: 2338\n"
        "SL: 2323\n"
        "Comment: clean level-based setup"
    ),
    "premium_signal_example": (
        "PREMIUM ACCESS EXAMPLE\n"
        "Pair: XAUUSD\n"
        "Bias: Bullish continuation after structure hold\n"
        "Entry Zone: 2328 - 2331\n"
        "Invalidation: close below 2323\n"
        "TP1: 2338\n"
        "TP2: 2344\n"
        "Reasoning: HTF alignment, liquidity sweep, demand reaction, execution structure included"
    ),
    "premium_positioning": [
        "Free members see the setup. Premium members understand the reasoning.",
        "Free helps you observe. Premium helps you position earlier and with more clarity.",
        "Premium is built for traders who want stronger analysis, better timing, and higher-quality setups."
    ],
    "urgency_lines": [
        "The difference is usually not effort — it is timing and structure.",
        "Serious traders do not wait for random entries. They position with clarity.",
        "When the move is obvious to everyone, the best entries are usually gone."
    ],
    "performance_proof_intro": (
        "Before trusting anyone in trading, first verify they actually trade — and verify consistency over time."
    ),
    "onboarding_days": {
        "day1": "Welcome to the free journey. Start by observing the structure and how setups are presented.",
        "day2": "How to use signals: focus on entry zone, stop loss, target, and patience. Don’t chase.",
        "day3": "Proof matters. Review the results and notice how structure removes emotional trading.",
        "day4": "Trust comes from consistency. Good systems protect capital before they chase profit.",
        "day5": "Premium Access is not just more signals — it is earlier timing, deeper analysis, and stronger execution.",
        "day6": "Reminder: discipline is your edge. Wait for clean setups and protect your downside.",
        "day7": "If the free structure has made sense to you, Premium Access is the natural next step."
    }
}


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("Failed to load %s", path)
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


def load_user_state_store() -> dict[str, Any]:
    return load_json(USER_STATE_FILE, {})


def save_user_state_store(store: dict[str, Any]) -> None:
    save_json(USER_STATE_FILE, store)


def get_user_state(context: ContextTypes.DEFAULT_TYPE) -> dict[str, Any]:
    context.user_data.setdefault("state", {})
    return context.user_data["state"]


def free_join_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Join Free Signals Channel", url=FREE_CHANNEL_LINK)],
            [InlineKeyboardButton("I Joined", callback_data="after_free_join")],
        ]
    )


def app_upgrade_markup() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("🚀 Unlock Tradepedia Premium Access", url=APP_LINK)],
    ]
    if BROKER_LINK:
        rows.append([InlineKeyboardButton("📈 Open XM Account + Unlock 6 Months", callback_data="broker_path")])
    rows.append([InlineKeyboardButton("Talk to us directly", callback_data="human_close")])
    return InlineKeyboardMarkup(rows)


def broker_markup() -> InlineKeyboardMarkup:
    rows = []
    if BROKER_LINK:
        rows.append([InlineKeyboardButton("Open XM Account", url=BROKER_LINK)])
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


async def send_results(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    for item in CONTENT["recent_results"]:
        image_path = Path(item["image"])
        caption = item.get("caption", "")

        if not image_path.exists():
            await send_plain_text(update, context, f"Missing result image: {item['image']}")
            continue

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

        with image_path.open("rb") as photo:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=photo,
                caption=caption,
            )


async def send_performance_proof(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    intro = CONTENT.get(
        "performance_proof_intro",
        "Before trusting anyone in trading, first verify they actually trade — and verify consistency over time.",
    )

    text = (
        f"{intro}\n\n"
        "<b>Multi-Year Verified Trading Performance</b>\n\n"
        "• 2023 Profit → $608,000+\n"
        "• 2024 Profit → $1.46M+\n"
        "• 2025 Profit → $1.18M+\n"
        "• 2026 YTD Profit → $929,000+\n\n"
        "This proves:\n"
        "• long-term profitability\n"
        "• real trading activity\n"
        "• professional scale\n"
        "• consistency, not luck\n\n"
        "Anyone can show one trade.\n"
        "<b>Very few can show years of consistency.</b>"
    )

    await send_plain_text(
        update,
        context,
        text,
        InlineKeyboardMarkup([[InlineKeyboardButton("Show me recent live results", callback_data="next_results")]]),
    )


def build_free_vs_premium_text() -> str:
    return (
        "📘 <b>Free vs Premium Access</b>\n\n"
        f"<b>{CONTENT['free_signal_example'].splitlines()[0]}</b>\n"
        + "\n".join(CONTENT["free_signal_example"].splitlines()[1:])
        + "\n\n"
        f"<b>{CONTENT['premium_signal_example'].splitlines()[0]}</b>\n"
        + "\n".join(CONTENT["premium_signal_example"].splitlines()[1:])
        + "\n\n"
        "Free members see the setup.\n"
        "<b>Premium members get deeper structure, earlier positioning, and stronger execution context.</b>"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = get_user_state(context)
    state.clear()
    state["step"] = "entry"

    persona_name = CONTENT.get("persona_name", "David")
    welcome_hook = CONTENT.get("welcome_hook", "")
    entry_message = CONTENT.get("entry_message", "")

    await send_plain_text(
        update,
        context,
        f"Hey — I’m <b>{persona_name}</b>.\n\n"
        f"{welcome_hook}\n\n"
        f"{entry_message}\n\n"
        "<b>Have you traded before?</b>",
        InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Beginner", callback_data="exp_beginner")],
                [InlineKeyboardButton("Some experience", callback_data="exp_mid")],
                [InlineKeyboardButton("Already using signals", callback_data="exp_signals")],
            ]
        ),
    )


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
            data={"chat_id": chat.id, "text": onboarding[day_key], "day_num": index + 1},
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

    if data == "exp_beginner":
        state["experience"] = "beginner"
        state["step"] = "loss_question"

        await send_plain_text(
            update,
            context,
            "Got it — that’s actually a good place to start.\n\n"
            "Most beginners lose money because they follow signals blindly without understanding structure.\n\n"
            "<b>Be honest — have you ever lost money following signals before?</b>",
            InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("Yes", callback_data="lost_yes")],
                    [InlineKeyboardButton("No", callback_data="lost_no")],
                ]
            ),
        )
        return

    if data == "exp_mid":
        state["experience"] = "mid"
        state["step"] = "loss_question"

        await send_plain_text(
            update,
            context,
            "Good — then you’ll understand this quickly.\n\n"
            "The issue with most signal groups is poor timing, late entries, and no real structure.\n\n"
            "<b>Have you lost money following signals before?</b>",
            InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("Yes", callback_data="lost_yes")],
                    [InlineKeyboardButton("No", callback_data="lost_no")],
                ]
            ),
        )
        return

    if data == "exp_signals":
        state["experience"] = "signals"
        state["step"] = "loss_question"

        await send_plain_text(
            update,
            context,
            "Let me guess — inconsistent results?\n\n"
            "That usually happens when entries are late and the reasoning is missing.\n\n"
            "<b>Have you lost money with other signal groups before?</b>",
            InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("Yes", callback_data="lost_yes")],
                    [InlineKeyboardButton("No", callback_data="lost_no")],
                ]
            ),
        )
        return

    if data == "lost_yes":
        state["pain"] = "yes"
        state["step"] = "performance_proof"

        await send_plain_text(
            update,
            context,
            "That’s exactly why most traders come to us.\n\n"
            "Not because they’re new — but because they’ve already been burned by bad timing and low-quality signal groups."
        )
        await send_performance_proof(update, context)
        return

    if data == "lost_no":
        state["pain"] = "no"
        state["step"] = "performance_proof"

        await send_plain_text(
            update,
            context,
            "That’s good — it means you haven’t built too many bad habits yet.\n\n"
            "So the smartest thing now is to verify real consistency before trusting anyone."
        )
        await send_performance_proof(update, context)
        return

    if data == "next_results":
        state["step"] = "results"

        await send_results(update, context)
        await send_plain_text(
            update,
            context,
            "These are recent live account results.\n\n"
            "So now you’ve seen both:\n"
            "• multi-year consistency\n"
            "• recent live execution\n\n"
            "That’s the difference between marketing and real trading.",
            InlineKeyboardMarkup([[InlineKeyboardButton("Show me real testimonials", callback_data="next_testimonials")]]),
        )
        return

    if data == "next_testimonials":
        state["step"] = "testimonials"

        await send_testimonials(update, context)
        await send_plain_text(
            update,
            context,
            "These are real users seeing what happens when structure replaces guesswork.",
            InlineKeyboardMarkup([[InlineKeyboardButton("What’s the difference between free and premium?", callback_data="next_explain")]]),
        )
        return

    if data == "next_explain":
        state["step"] = "free_vs_premium"

        await send_plain_text(
            update,
            context,
            "The difference is simple:\n\n"
            "Most groups give signals.\n"
            "<b>Tradepedia gives structure, timing, and a full premium ecosystem.</b>"
        )
        await send_plain_text(
            update,
            context,
            build_free_vs_premium_text(),
            InlineKeyboardMarkup([[InlineKeyboardButton("Start with free signals", callback_data="join_free")]]),
        )
        return

    if data == "join_free":
        state["step"] = "join_free"

        await send_plain_text(
            update,
            context,
            "You do <b>not</b> need to jump into Premium immediately.\n\n"
            "Best move is to join the free signals channel first, observe the structure, and build trust properly.",
            free_join_markup(),
        )
        return

    if data == "after_free_join":
        state["step"] = "joined_free"
        await schedule_onboarding(update, context)

        await send_plain_text(
            update,
            context,
            "Good — that’s the right way to start.\n\n"
            "Watch how the next few setups are structured.\n\n"
            "That’s usually when serious traders understand why Premium Access exists.",
            InlineKeyboardMarkup([[InlineKeyboardButton("What does Premium Access include?", callback_data="premium_offer")]]),
        )
        return

    if data == "premium_offer":
        state["step"] = "premium_offer"

        premium_lines = "\n".join([f"• {x}" for x in CONTENT["premium_positioning"]])
        urgency_lines = "\n".join([f"• {x}" for x in CONTENT["urgency_lines"]])

        await send_plain_text(
            update,
            context,
            "🚀 <b>Unlock Tradepedia Premium Access</b>\n\n"
            "Premium Access includes:\n"
            "• premium signals\n"
            "• HTF alignment + structure\n"
            "• premium analysis\n"
            "• earlier access than free users\n"
            "• better quality setups\n"
            "• app access\n"
            "• premium tools\n"
            "• Inner Circle community\n\n"
            f"{premium_lines}\n\n"
            "Pricing:\n"
            "• 1 Month — AED 199.99\n"
            "• 6 Months — AED 999.99\n"
            "• 12 Months — AED 1,799.99\n\n"
            "Alternative path:\n"
            "• Open XM account + deposit $250\n"
            "• Unlock 6 months of Premium Access\n\n"
            "Why traders move up:\n"
            f"{urgency_lines}",
            app_upgrade_markup(),
        )
        return

    if data == "broker_path":
        state["step"] = "broker_path"

        await send_plain_text(
            update,
            context,
            "📈 <b>Alternative Premium Access Route</b>\n\n"
            "If you prefer, you can open an XM account, deposit $250, and unlock <b>6 months of Tradepedia Premium Access</b>.",
            broker_markup(),
        )
        return

    if data == "human_close":
        state["step"] = "human_close"

        await send_plain_text(
            update,
            context,
            "Perfect — if you want a direct handoff, we can continue the conversation personally from here.\n\n"
            "You can also go straight into the app and unlock Premium Access when ready.",
            InlineKeyboardMarkup([[InlineKeyboardButton("Open Tradepedia App", url=APP_LINK)]]),
        )
        return

    if data == "restart":
        await start(update, context)
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