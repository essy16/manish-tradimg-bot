"""
Tradepedia Telegram Bot - Phase 2 Conversational Funnel
Auto-flow + delays + human-style conversation
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import os
from pathlib import Path
from typing import Any
from openai import OpenAI
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode, ChatAction
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
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
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip()

openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

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


    await send_intro_video(update, context)

    messages = [
       
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

async def send_intro_video(update, context):
    video_path = Path(CONTENT.get("intro_video", "videos/intro.mp4"))

    if not video_path.exists():
        await send_plain_text(update, context, "Intro video missing.")
        return

    with video_path.open("rb") as video:
        await context.bot.send_video_note(
            chat_id=update.effective_chat.id,
            video_note=video,
        )

    await asyncio.sleep(1)

    await send_plain_text(
        update,
        context,
        "I’m Avramis Despotis, Founder of Tradepedia.\n\n"
        "People ask me… if you already make money trading, why do this?\n\n"
        "Simple. Because making money alone is boring."
    )

TRADEPEDIA_AI_SYSTEM = """
You are the Tradepedia Telegram funnel assistant.

Style:
- Sound human, calm, confident, and conversational.
- Never repeat the same wording twice.
- Do NOT start every objection reply with “Skepticism is smart”.
- Vary openings naturally.
- Use different phrases such as:
  “Fair question.”
  “I get why you’d ask that.”
  “That’s a normal concern in trading.”
  “You’re right to question things.”
  “No pressure — judge it from the free channel first.”
- Do not sound like a template.
- Keep replies short: 2 to 5 sentences.
- If the user is skeptical, do not argue. Acknowledge, then guide.
- Never promise guaranteed profits.
- Never give financial advice.
- Rotate your phrasing naturally.
- Ask small follow-up questions when useful.

Your job:
- Answer questions about Tradepedia, free signals, Premium Access, app registration, results, testimonials, XM route, and trust concerns.
- If user says scam/fake, respond with empathy and confidence.
- Explain that skepticism is normal in trading.
- Invite them to check the free channel first instead of pushing payment.
- Move the user toward one next step only.

Brand facts:
- Tradepedia is a trading education and signals ecosystem.
- Telegram builds trust before users move to the app.
- Final destination is the Tradepedia app.
- Premium Access includes premium signals, market structure analysis, early access to setups, app tools, and Inner Circle community.
- Pricing: 1 Month AED 199.99, 6 Months AED 999.99, 12 Months AED 1,799.99.
- XM route: Open XM account using our link, deposit $250, then chat with the team to activate 6 months free Premium Access.
- Track record: 2023 $608,000+, 2024 $1.46M+, 2025 $1.18M+, 2026 YTD $929,000+.

If unrelated:
Politely say you can only help with Tradepedia, signals, Premium Access, app registration, or XM access.
"""


def detect_emotion(user_text: str) -> str:
    text = user_text.lower()

    if any(w in text for w in ["scam", "fake", "fraud", "scammer", "scammers", "trust"]):
        return "skeptical"

    if any(w in text for w in ["price", "cost", "expensive", "how much", "premium", "subscribe", "payment"]):
        return "pricing"

    if any(w in text for w in ["xm", "broker", "deposit", "250", "account"]):
        return "xm"

    if any(w in text for w in ["results", "proof", "performance", "withdrawal", "profit"]):
        return "proof"

    if any(w in text for w in ["app", "download", "register", "ios", "android"]):
        return "app"

    if any(w in text for w in ["yes", "ready", "interested", "send", "link", "join"]):
        return "ready"

    return "general"


def update_user_memory(context: ContextTypes.DEFAULT_TYPE, user_text: str) -> dict[str, Any]:
    memory = context.user_data.setdefault("memory", {
        "message_count": 0,
        "objections": [],
        "interests": [],
        "conversion_score": 0,
    })

    emotion = detect_emotion(user_text)
    memory["message_count"] += 1
    memory["last_emotion"] = emotion

    if emotion == "skeptical":
        memory["objections"].append("trust")
        memory["conversion_score"] += 1

    elif emotion == "pricing":
        memory["interests"].append("premium_pricing")
        memory["conversion_score"] += 2

    elif emotion == "xm":
        memory["interests"].append("xm_route")
        memory["conversion_score"] += 3

    elif emotion == "proof":
        memory["interests"].append("proof")
        memory["conversion_score"] += 2

    elif emotion == "app":
        memory["interests"].append("app")
        memory["conversion_score"] += 3

    elif emotion == "ready":
        memory["conversion_score"] += 4

    else:
        memory["conversion_score"] += 1

    memory["conversion_score"] = min(memory["conversion_score"], 10)
    return memory


def get_followup_for_message(user_text: str, memory: dict[str, Any]) -> str:
    emotion = detect_emotion(user_text)
    score = memory.get("conversion_score", 0)

    skeptical = [
    "Fair question. Don’t take anyone’s word for it — watch the free signals first.",
    "I get why you’d ask that. Trading has too much noise, so start free and judge the structure yourself.",
    "You’re right to question things. That’s exactly why we let people observe the free channel first.",
    "No pressure at all. The free channel is there so you can see how Tradepedia works before deciding.",
    "That’s a normal concern. Start with the free signals, then decide based on what you actually see.",
    "Good traders verify first. Join free, watch the setups, and make your own decision."
]

    pricing = [
        "Premium is for traders who want deeper structure, earlier setups, and full app access.",
        "You can start free first, then unlock Premium inside the Tradepedia app when it makes sense.",
        "Most users watch the free signals first, then upgrade when they understand the value."
    ]

    xm = [
        "The XM route is simple: open the account using our link, deposit $250, then message the team to activate 6 months free Premium Access.",
        "For XM access, the team verifies your account after deposit, then activates your 6 months Premium.",
        "XM is the alternative route if you prefer unlocking Premium through broker setup instead of direct app subscription."
    ]

    proof = [
        "The strongest thing to check first is the structure behind the results — not just screenshots.",
        "Start with the free channel and compare how the setups are explained versus random signal groups.",
        "The proof makes more sense when you see how the trades are actually managed."
    ]

    app = [
        "The app is the final destination for Premium Access. Telegram is mainly where trust is built first.",
        "You can use Telegram to observe first, then register in the app when ready.",
        "Premium is unlocked through the Tradepedia app, not as a random Telegram payment."
    ]

    ready = [
        "Best next step: join the free signals first and see the structure live.",
        "You’re close. Start free first, then Premium becomes much easier to understand.",
        "Let’s keep it simple — free channel first, then app access when ready."
    ]

    high_intent = [
        "Since you’re already asking the right questions, the best next move is to start with the free signals and then decide if Premium fits.",
        "You seem serious enough to evaluate it properly. Start free, watch the structure, then move to Premium if it makes sense.",
        "At this stage, don’t overthink it — observe the free channel first and let the structure speak."
    ]

    if score >= 7:
        return random.choice(high_intent)

    if emotion == "skeptical":
        return random.choice(skeptical)

    if emotion == "pricing":
        return random.choice(pricing)

    if emotion == "xm":
        return random.choice(xm)

    if emotion == "proof":
        return random.choice(proof)

    if emotion == "app":
        return random.choice(app)

    if emotion == "ready":
        return random.choice(ready)

    return random.choice([
        "Start with the free channel first — that gives you the clearest picture.",
        "The best way to understand Tradepedia is to watch the structure in real time.",
        "Free first. Once the structure makes sense, Premium becomes the next step."
    ])


def get_buttons_for_message(user_text: str, memory: dict[str, Any]) -> InlineKeyboardMarkup:
    emotion = detect_emotion(user_text)
    score = memory.get("conversion_score", 0)

    if emotion == "xm":
        return broker_markup()

    if emotion in ["pricing", "app"] or score >= 7:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Unlock Premium Access", callback_data="premium_offer")],
            [InlineKeyboardButton("✅ Join Free Signals", callback_data="join_free")]
        ])

    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Join Free Signals", callback_data="join_free")],
        [InlineKeyboardButton("🚀 Unlock Premium Access", callback_data="premium_offer")]
    ])


async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_text = (update.message.text or "").strip()

    if not user_text:
        return

    memory = update_user_memory(context, user_text)
    text_lower = user_text.lower()

    # ✅ HARD OVERRIDE FOR FOUNDER QUESTION
    if "avramis" in text_lower or "who is avramis" in text_lower:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.TYPING,
        )

        await asyncio.sleep(random.uniform(1.5, 3.0))

        await send_plain_text(
            update,
            context,
            (
                "Avramis Despotis is the founder of Tradepedia.\n\n"
                "He is a well-known trader with a verified multi-year track record "
                "and multi-million dollar performance across different market conditions.\n\n"
                "More importantly, he focuses on structured trading — not random signals.\n\n"
                "That’s why everything inside Tradepedia is built around timing, execution, "
                "and consistency rather than hype."
            )
        )

        await asyncio.sleep(random.uniform(1.5, 3.0))

        await send_plain_text(
            update,
            context,
            "Best way to understand that is to watch the free signals first.",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Join Free Signals", callback_data="join_free")],
                [InlineKeyboardButton("🚀 Unlock Premium Access", callback_data="premium_offer")]
            ])
        )
        return

    # ---------------- NORMAL FLOW ---------------- #

    if not openai_client:
        reply = "Good question. The safest way to judge Tradepedia is to start free and watch how the structure works."

        await send_plain_text(update, context, reply)

        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.TYPING,
        )

        await asyncio.sleep(random.uniform(1.5, 3.5))

        followup = get_followup_for_message(user_text, memory)

        await send_plain_text(
            update,
            context,
            followup,
            get_buttons_for_message(user_text, memory)
        )
        return

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING,
    )

    try:
        response = await asyncio.to_thread(
            openai_client.responses.create,
            model=OPENAI_MODEL,
            instructions=(
                TRADEPEDIA_AI_SYSTEM
                + f"\n\nUser memory:\n"
                + f"- Message count: {memory.get('message_count')}\n"
                + f"- Last emotion: {memory.get('last_emotion')}\n"
                + f"- Interests: {memory.get('interests')}\n"
                + f"- Objections: {memory.get('objections')}\n"
                + f"- Conversion score: {memory.get('conversion_score')}/10\n"
            ),
            input=user_text,
        )

        reply = response.output_text.strip()

        await send_plain_text(update, context, reply)

        # ✅ HUMAN DELAY
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.TYPING,
        )

        await asyncio.sleep(random.uniform(1.5, 3.5))

        followup = get_followup_for_message(user_text, memory)

        await send_plain_text(
            update,
            context,
            followup,
            get_buttons_for_message(user_text, memory)
        )

    except Exception:
        logger.exception("OpenAI reply failed")

        fallback = random.choice([
            "Good question. The safest way to judge Tradepedia is to start with the free signals and see the structure yourself.",
            "I understand the question. Start free first, watch how the signals are handled, then decide calmly.",
            "The free channel exists for exactly this reason — so you can observe before making any decision."
        ])

        await send_plain_text(
            update,
            context,
            fallback,
            InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Join Free Signals", callback_data="join_free")],
                [InlineKeyboardButton("🚀 Premium Access", callback_data="premium_offer")]
            ])
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

        await send_sequence(update, context, [
            {"text": "Most groups give signals.", "delay": 2},
            {"text": "Tradepedia gives structure.", "delay": 2},
            {"text": "Let me show you how Premium actually works.", "delay": 2},
        ])

        await send_premium_example(update, context)

        await send_sequence(update, context, [
            {
                "text": "That’s the difference between guessing and structured trading.",
                "delay": 2,
                "reply_markup": InlineKeyboardMarkup([
                    [InlineKeyboardButton("Join Free First", url=FREE_CHANNEL_LINK)]
                ])
            }
        ])
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
                "text": "Open an XM account using our link, deposit $250, then chat with us to activate your <b>6 months free Premium Access</b>.",
                "delay": 3,
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



async def send_premium_example(update, context):
    chat_id = update.effective_chat.id

    # 1️⃣ CHART FIRST
    premium = CONTENT.get("premium_examples", [{"image": "images/premium-gold.png", "caption": "GOLD (H4) — Bearish Reversal"}])[0]
    image_path = Path(premium["image"])
    caption = premium.get("caption", "GOLD (H4) — Bearish Reversal")

    if image_path.exists():
        with image_path.open("rb") as photo:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=photo,
                caption=caption
            )

    await asyncio.sleep(8)

    # 2️⃣ FULL ANALYSIS
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "<b>Bias:</b> Bearish\n"
            "<b>HTF Alignment:</b> Moderate\n"
            "<b>Score:</b> 6\n"
            "<b>Trade Class:</b> Reversal — Bearish\n"
            "<b>Risk:</b> 0.75%\n\n"

            "<b>Context:</b>\n"
            "Double top formed, momentum weakening, rejection at highs.\n"
            "Indicates corrective phase.\n\n"

            "<b>Entry:</b> 4767.66\n"
            "<b>Stop:</b> 4889.35\n"
            "<b>Target 1:</b> 4695.86\n"
            "<b>Target 2:</b> 4574.17\n"
            "<b>Target 3:</b> 4375.82\n\n"

            "“Keep fighting the trend… someone has to be on the wrong side.”\n"
            "— Avramis Despotis"
        ),
        parse_mode="HTML"
    )

    await asyncio.sleep(2)

    await context.bot.send_message(
    chat_id=chat_id,
    text="When a signal reaches target, an update is sent:",
    parse_mode="HTML"
)

    await asyncio.sleep(8)

    # 3️⃣ UPDATE 1
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "<b>Gold — Trade Update</b>\n\n"
            "T1 hit ✅\n"
            "Closed 50%\n"
            "Stop moved to entry\n\n"
            "<b>Position now risk-free</b>"
        ),
        parse_mode="HTML"
    )

    await asyncio.sleep(2)

    # 4️⃣ FINAL UPDATE
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "<b>Gold — Trade Update</b>\n\n"
            "Closed remaining 50% ✅\n\n"
            "Looking for next opportunity."
        ),
        parse_mode="HTML"
    )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled exception", exc_info=context.error)


def build_app() -> Application:
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_message))
    app.add_error_handler(error_handler)

    return app


if __name__ == "__main__":
    logger.info("Bot starting...")
    build_app().run_polling(allowed_updates=Update.ALL_TYPES)