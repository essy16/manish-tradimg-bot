"""
Tradepedia Telegram Bot - Phase 2 Conversational Funnel
Auto-flow + delays + human-style conversation
"""

from __future__ import annotations
from datetime import time,datetime, timedelta
from zoneinfo import ZoneInfo

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
FREE_CHANNEL_ID = os.getenv("FREE_CHANNEL_ID", "").strip()
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
            "caption": "📊Avramis Despotis Personal Account performance :"
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

def get_user_temperature(context: ContextTypes.DEFAULT_TYPE) -> str:
    memory = context.user_data.get("memory", {})
    score = memory.get("conversion_score", 0)

    interests = memory.get("interests", [])
    objections = memory.get("objections", [])

    if score >= 7 or "premium_pricing" in interests or "xm_route" in interests:
        return "hot"

    if "trust" in objections or score <= 3:
        return "cold"

    return "warm"


def schedule_premium_noon_followups(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.job_queue:
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    temperature = get_user_temperature(context)

    followups = [
        ("premium_followup_1", 1),
        ("premium_followup_2", 2),
        ("premium_followup_3", 4),
        ("premium_followup_4", 7),
        ("premium_followup_5", 10),
    ]

    for name, days_after in followups:
        context.job_queue.run_once(
            send_smart_premium_followup,
            when=days_after * 24 * 60 * 60,
            data={
                "chat_id": chat_id,
                "temperature": temperature,
                "day": days_after,
            },
            name=f"{name}_{user_id}",
        )

async def send_smart_premium_followup(context: ContextTypes.DEFAULT_TYPE) -> None:
    job = context.job
    chat_id = job.data["chat_id"]
    temperature = job.data.get("temperature", "warm")
    day = job.data.get("day", 1)

    if temperature == "hot":
        text = random.choice([
            "You’ve already seen enough to understand the difference.\n\nPremium is where you get earlier setups, deeper structure, and trade updates before most people react.",
            "If you’re serious about trading with structure, Premium Access is the next step.\n\nFree shows you the direction. Premium gives the full execution plan.",
            "You’re not looking for random signals — you’re looking for structure.\n\nThat’s exactly what Premium Access is built for."
        ])

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Unlock Premium Access", callback_data="premium_offer")],
            [InlineKeyboardButton("📈 XM Route: 6 Months Free", callback_data="broker_path")]
        ])

    elif temperature == "cold":
        text = random.choice([
            "No pressure to upgrade yet.\n\nThe smart move is to keep watching the free signals and judge the structure from what you see.",
            "Trading requires trust, and trust should be earned.\n\nStay in the free channel first. Watch the setups, timing, and updates.",
            "Don’t rush Premium.\n\nUse the free channel to see how Tradepedia works before making any decision."
        ])

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Join Free Signals", url=FREE_CHANNEL_LINK)],
            [InlineKeyboardButton("Show Results", callback_data="next_results")]
        ])

    else:
        text = random.choice([
            "By now, you should start seeing the difference between random signals and structured trading.\n\nPremium gives you the deeper analysis behind the move.",
            "Free helps you observe.\n\nPremium helps you understand the full structure, timing, risk, and updates.",
            "The next step is simple: keep watching free, or unlock Premium when you want the full trading ecosystem."
        ])

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Unlock Premium Access", callback_data="premium_offer")],
            [InlineKeyboardButton("✅ Join Free Signals", url=FREE_CHANNEL_LINK)]
        ])

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"☀️ <b>Tradepedia Premium Reminder</b>\n\n{text}",
        parse_mode=ParseMode.HTML,
        reply_markup=buttons
    )


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

async def user_has_joined_free_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not FREE_CHANNEL_ID:
        return False

    try:
        member = await context.bot.get_chat_member(
            chat_id=FREE_CHANNEL_ID,
            user_id=update.effective_user.id
        )

        return member.status in ["member", "administrator", "creator"]

    except Exception:
        logger.exception("Could not verify channel membership")
        return False

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
    results = CONTENT.get("recent_results", [])

    # send only first result for now to avoid getting stuck
    if not results:
        await send_plain_text(update, context, "No result images found yet.")
        return

    item = results[0]
    image_path = Path(item["image"])
    caption = item.get("caption", "")

    if not image_path.exists():
        await send_plain_text(update, context, f"Missing result image: {item['image']}")
        return

    try:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.UPLOAD_PHOTO,
        )

        with image_path.open("rb") as photo:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=photo,
                caption=caption,
                read_timeout=60,
                write_timeout=60,
                connect_timeout=60,
            )

    except Exception:
        logger.exception("Failed to send result image")
        await send_plain_text(update, context, "Result image took too long to send, continuing the flow.")


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
                "📊 <b>Avramis Despotis Personal Account performance :</b>\n\n"
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

    schedule_pre_join_elite_funnel(update, context)
    schedule_auto_join_check(update, context)

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
    video_path = Path("videos/intro.mp4")

    if not video_path.exists():
        await send_plain_text(update, context, "Intro video missing. Continuing...")
        return

    try:
        with video_path.open("rb") as video:
            msg = await context.bot.send_video_note(
                chat_id=update.effective_chat.id,
                video_note=video,
                read_timeout=60,
                write_timeout=60,
                connect_timeout=60,
            )

        if msg.video_note:
            print("\n🔥 COPY THIS FILE_ID:\n", msg.video_note.file_id, "\n", flush=True)

    except Exception:
        logger.exception("Intro video failed")
        await send_plain_text(update, context, "Intro video took too long. Continuing...")
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

async def send_pre_join_push(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = job.data["chat_id"]

    if random.random() > 0.5:
        with open("images/proof1.jpeg", "rb") as photo:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=photo,
                caption="This is what free members are seeing in real time."
            )

    # 🔥 STOP IF USER ALREADY JOINED
    try:
        member = await context.bot.get_chat_member(
            chat_id=FREE_CHANNEL_ID,
            user_id=chat_id
        )

        joined = member.status in ["member", "administrator", "creator"]

        if joined:
            return    
    except:
        pass

    await context.bot.send_message(
        chat_id=chat_id,
        text=job.data["text"],
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Join Free Signals", url=FREE_CHANNEL_LINK)]
        ])
    )


def schedule_pre_join_push(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    if not context.job_queue:
        return

    chat_id = update.effective_chat.id

    pushes = [
        (60, "Most people watch signals too late… that’s why they lose."),
        (180, "Free channel shows setups BEFORE the move — not after."),
        (300, "You don’t need to trade yet. Just observe the structure first."),
    ]

    for seconds, text in pushes:
        context.job_queue.run_once(
            send_pre_join_push,
            when=seconds,
            data={"chat_id": chat_id, "text": text},
        )

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
            [InlineKeyboardButton("✅ Join Free Signals", url=FREE_CHANNEL_LINK)]  # ✅ FIXED
        ])

    return InlineKeyboardMarkup([
    [InlineKeyboardButton("✅ Join Free Signals", url=FREE_CHANNEL_LINK)],
    [InlineKeyboardButton("✅ I Joined", callback_data="after_free_join")],
    [InlineKeyboardButton("🚀 Unlock Premium Access", callback_data="premium_offer")]
])




async def send_video_testimonials(update, context):
    videos = CONTENT.get("video_testimonials", [])

    for item in videos:
        video_path = Path(item["video"])
        caption = item.get("caption", "")

        if not video_path.exists():
            await send_plain_text(update, context, f"Missing video testimonial: {item['video']}")
            continue

        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.UPLOAD_VIDEO,
        )

        with video_path.open("rb") as video:
            await context.bot.send_video(
                chat_id=update.effective_chat.id,
                video=video,
                caption=caption,
            )

        await asyncio.sleep(3)

async def show_testimonials_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await send_plain_text(update, context, "Absolutely — here are real Tradepedia testimonials.")
    await send_video_testimonials(update, context)

    await asyncio.sleep(2)

    await send_plain_text(
    update,
    context,
    "Now let me show you what separates Free from Premium.",
    InlineKeyboardMarkup([
        [InlineKeyboardButton("Continue", callback_data="next_explain")],
        [InlineKeyboardButton("✅ Join Free Signals", url=FREE_CHANNEL_LINK)],
        [InlineKeyboardButton("✅ I Joined", callback_data="after_free_join")],
    ])
)
    schedule_auto_join_check(update, context)
    
async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    user_text = update.message.text.strip()
    if not user_text:
        return

    text_lower = user_text.lower()
    memory = update_user_memory(context, user_text)

    if any(w in text_lower for w in ["i joined", "i have joined", "joined", "done", "i am in"]):
        await schedule_onboarding(update, context)
        schedule_conversion_journey(update, context)

        image_path = Path("images/i-joined.png")
        if image_path.exists():
            with image_path.open("rb") as photo:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=photo,
                    caption="✅ Good — that’s the right way to start.\n\nNow watch how the next few trades are structured.",
                )
        else:
            await send_plain_text(update, context, "✅ Good — that’s the right way to start.")

        await asyncio.sleep(2)
        await send_plain_text(update, context, "Pay attention to structure, timing, and risk.")

        await asyncio.sleep(2)
        await send_plain_text(
            update,
            context,
            "Ready to see what Premium includes?",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("Show me Premium Access", callback_data="premium_offer")]
            ])
        )
        return

    if any(w in text_lower for w in ["testimonial", "testimonials", "review", "reviews", "feedback"]):
        await show_testimonials_flow(update, context)
        return

    if any(w in text_lower for w in ["result", "results", "proof", "performance", "profits", "profit"]):
        await send_plain_text(update, context, "Here are recent Tradepedia results.")
        await send_results(update, context)

        await asyncio.sleep(2)

        await send_plain_text(
            update,
            context,
            "Want to see real testimonials too?",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("Show Testimonials", callback_data="next_testimonials")],
                [InlineKeyboardButton("✅ Join Free Signals", url=FREE_CHANNEL_LINK)],
            ])
        )
        return

    if any(w in text_lower for w in ["not convinced", "convince me", "convince me harder", "why should i trust", "show more proof", "more proof"]):
        await send_plain_text(
            update,
            context,
            "Fair. Don’t decide from words alone — look at the trading evidence first."
        )

        proof_1 = Path("images/proof-extra-1.png")
        proof_2 = Path("images/proof-extra-2.png")

        if proof_1.exists():
            with proof_1.open("rb") as photo:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=photo,
                    caption=(
                        "This is the kind of live trading activity Premium members are positioned around.\n\n"
                        "The point is not hype — it is seeing structure before the move happens."
                    ),
                )

        await asyncio.sleep(3)

        if proof_2.exists():
            with proof_2.open("rb") as photo:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=photo,
                    caption=(
                        "This is why timing matters.\n\n"
                        "Free gives you a starting point. Premium gives the deeper structure, updates, and execution context."
                    ),
                )

        await asyncio.sleep(2)

        await send_plain_text(
            update,
            context,
            "Start free first. If the structure makes sense, Premium becomes the next step.",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Join Free Signals", url=FREE_CHANNEL_LINK)],
                [InlineKeyboardButton("✅ I Joined", callback_data="after_free_join")],
                [InlineKeyboardButton("🚀 Unlock Premium Access", callback_data="premium_offer")],
            ])
        )
        return

    if "avramis" in text_lower:
        await send_plain_text(
            update,
            context,
            (
                "Avramis Despotis is the founder of Tradepedia.\n\n"
                "He is a well-known trader with a verified multi-year track record and multi-million dollar performance across different market conditions.\n\n"
                "Tradepedia is built around his structured approach to trading — timing, execution, and consistency."
            ),
            InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Join Free Signals", url=FREE_CHANNEL_LINK)],
                [InlineKeyboardButton("🚀 Unlock Premium Access", callback_data="premium_offer")],
            ])
        )
        return

    if any(w in text_lower for w in ["hi", "hello", "hey"]):
        await send_plain_text(
            update,
            context,
            random.choice([
                "Hey — welcome to Tradepedia.",
                "Hi — glad you’re here.",
                "Welcome — you’re in the right place.",
            ])
        )

        await asyncio.sleep(1.5)

        await send_plain_text(
            update,
            context,
            "What would you like to see first?",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 Results", callback_data="next_results")],
                [InlineKeyboardButton("💬 Testimonials", callback_data="next_testimonials")],
                [InlineKeyboardButton("🚀 Premium Access", callback_data="premium_offer")],
            ])
        )
        return

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING,
    )

    try:
        if openai_client:
            response = await asyncio.to_thread(
                openai_client.responses.create,
                model=OPENAI_MODEL,
                instructions=(
                    TRADEPEDIA_AI_SYSTEM
                    + "\n\nUse a fresh, non-repetitive tone. Do not reuse the same opening line."
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
        else:
            reply = random.choice([
                "Tell me what you want to know — results, testimonials, or Premium.",
                "I can show you proof, user feedback, or how Premium works.",
                "What are you trying to understand first?",
            ])

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

    except Exception:
        logger.exception("AI reply failed")
        await send_plain_text(
            update,
            context,
            "I’m here — ask me anything about Tradepedia, results, testimonials, or Premium Access.",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Join Free Signals", url=FREE_CHANNEL_LINK)],
                [InlineKeyboardButton("🚀 Unlock Premium Access", callback_data="premium_offer")],
            ])
        )

async def check_join_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    joined = await user_has_joined_free_channel(update, context)

    await update.message.reply_text(
        f"FREE_CHANNEL_ID: {FREE_CHANNEL_ID}\n"
        f"Your user ID: {update.effective_user.id}\n"
        f"Joined detected: {joined}"
    )

def schedule_auto_join_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.job_queue:
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    context.job_queue.run_repeating(
        auto_check_join_status,
        interval=30,
        first=10,
        data={
            "chat_id": chat_id,
            "user_id": user_id,
            "checks": 0,
        },
        name=f"auto_join_check_{user_id}",
    )


async def auto_check_join_status(context: ContextTypes.DEFAULT_TYPE) -> None:
    job = context.job
    chat_id = job.data["chat_id"]
    user_id = job.data["user_id"]
    checks = job.data.get("checks", 0)

    if checks >= 20:  # stops after about 10 minutes
        job.schedule_removal()
        return

    job.data["checks"] = checks + 1

    try:
        member = await context.bot.get_chat_member(
            chat_id=FREE_CHANNEL_ID,
            user_id=user_id
        )

        if member.status in ["member", "administrator", "creator"]:
            job.schedule_removal()

            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    "✅ I can see you’ve joined the free channel.\n\n"
                    "That’s the perfect place to start — watch the next few signals closely."
                ),
                parse_mode=ParseMode.HTML
            )

            await asyncio.sleep(2)

            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    "Free helps you observe the signals.\n\n"
                    "Premium is where you get the full structure, earlier setups, trade updates, app tools, and Inner Circle access."
                ),
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🚀 Unlock Premium Access", callback_data="premium_offer")],
                    [InlineKeyboardButton("📈 XM Route: 6 Months Free", callback_data="broker_path")]
                ])
            )

    except Exception:
        logger.exception("Auto join check failed")

def next_uae_noon_after(days_after: int) -> datetime:
    dubai = ZoneInfo("Asia/Dubai")
    now = datetime.now(dubai)
    target = (now + timedelta(days=days_after)).replace(
        hour=12, minute=0, second=0, microsecond=0
    )

    if target <= now:
        target += timedelta(days=1)

    return target


def schedule_free_user_premium_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.job_queue:
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    temperature = get_user_temperature(context)

    schedule_days = [1, 2, 4, 7, 10]

    for day in schedule_days:
        context.job_queue.run_once(
            send_free_user_premium_reminder,
            when=next_uae_noon_after(day),
            data={
                "chat_id": chat_id,
                "user_id": user_id,
                "day": day,
                "temperature": temperature,
            },
            name=f"free_user_premium_reminder_{user_id}_{day}",
        )


async def send_free_user_premium_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    job = context.job
    chat_id = job.data["chat_id"]
    day = job.data.get("day", 1)
    temperature = job.data.get("temperature", "warm")

    if temperature == "hot":
        text = (
            "You’ve already seen how Tradepedia works from the free side.\n\n"
            "Premium is where you get earlier setups, deeper structure, trade updates, app tools, and Inner Circle access."
        )
    elif temperature == "cold":
        text = (
            "No pressure to upgrade yet.\n\n"
            "Keep watching the free signals first. Trust should come from structure, proof, and consistency."
        )
    else:
        text = (
            "By now, you should start seeing the difference between random signals and structured trading.\n\n"
            "Free helps you observe. Premium gives you the full execution plan."
        )

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"☀️ <b>Tradepedia Reminder — Day {day}</b>\n\n{text}",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Unlock Premium Access", callback_data="premium_offer")],
            [InlineKeyboardButton("📈 XM Route: 6 Months Free", callback_data="broker_path")]
        ])
    )


def schedule_free_channel_posts(context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.job_queue or not FREE_CHANNEL_ID:
        return

    context.job_queue.run_daily(
        post_daily_free_channel_update,
        time=time(hour=12, minute=0, tzinfo=ZoneInfo("Asia/Dubai")),
        name="daily_free_channel_update",
    )


async def post_daily_free_channel_update(context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_message(
        chat_id=FREE_CHANNEL_ID,
        text=(
            "📊 <b>Tradepedia Daily Reminder</b>\n\n"
            "Free signals help you observe the market.\n\n"
            "Premium Access gives deeper structure, earlier setups, trade updates, app tools, and Inner Circle access."
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Unlock Premium Access", url=APP_LINK)]
        ])
    )


def schedule_pre_join_elite_funnel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.job_queue:
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # 1 minute testing delays
    pushes = [
        (60, 1),
        (120, 2),
        (180, 3),
        (240, 4),
    ]

    for seconds, step in pushes:
        context.job_queue.run_once(
            send_pre_join_elite_push,
            when=seconds,
            data={
                "chat_id": chat_id,
                "user_id": user_id,
                "step": step,
            },
            name=f"pre_join_elite_{user_id}_{step}",
        )


async def send_pre_join_elite_push(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.data["chat_id"]

    try:
        member = await context.bot.get_chat_member(FREE_CHANNEL_ID, chat_id)
        joined = member.status in ["member", "administrator", "creator"]
    except:
        joined = False

    if joined:
        # 🔥 USER JOINED → SELL PREMIUM
        PREMIUM_VARIATIONS = [
            "You’ve seen how the free signals behave in real time.\n\nPremium positions you before those moves form.",

            "Free shows you the move.\n\nPremium shows you the setup before it happens.",

            "At this point, it’s not about more signals.\n\nIt’s about better timing and structure.",

            "Most traders react late.\n\nPremium is designed to position you early.",
        ]

        text = random.choice(PREMIUM_VARIATIONS)

        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🚀 Unlock Premium", callback_data="premium_offer")]
            ])
        )

    else:
        # 🔥 USER NOT JOINED → PUSH TO JOIN
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "You're still outside.\n\n"
                "The real signals are happening inside the free channel.\n\n"
                "Join first — then come back here."
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Join Free Channel", url=FREE_CHANNEL_LINK)],
                [InlineKeyboardButton("I Joined", callback_data="after_free_join")]
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

    last_action = state.get("last_action")
    last_action_time = state.get("last_action_time", 0)
    now = asyncio.get_event_loop().time()

    if last_action == data and now - last_action_time < 5:
        return

    processing_key = f"processing_{data}"
    if state.get(processing_key):
        return

    state["last_action"] = data
    state["last_action_time"] = now
    state[processing_key] = True

    try:
        if data == "restart":
            await start(update, context)
            return

        if data == "exp_beginner":
            state["experience"] = "beginner"
            state["step"] = "loss_question"

            await send_sequence(update, context, [
                {"text": "Got it — that’s actually a good place to start.", "delay": 1},
                {"text": "Most beginners don’t lose because of the market.", "delay": 2},
                {"text": "They lose because they follow signals blindly without understanding structure.", "delay": 2},
                {"text": "Let me ask you something...", "delay": 2},
                {
                    "text": "<b>Have you ever lost money following signals before?</b>",
                    "delay": 2,
                    "reply_markup": InlineKeyboardMarkup([
                        [InlineKeyboardButton("Yes", callback_data="lost_yes")],
                        [InlineKeyboardButton("No", callback_data="lost_no")],
                    ]),
                },
            ])
            return

        if data == "exp_mid":
            state["experience"] = "mid"
            state["step"] = "loss_question"

            await send_sequence(update, context, [
                {"text": "Good — then you’ll understand this quickly.", "delay": 1},
                {"text": "The issue with most signal groups is poor timing.", "delay": 2},
                {"text": "Late entries. No reasoning. No structure.", "delay": 2},
                {
                    "text": "<b>Have you lost money following signals before?</b>",
                    "delay": 2,
                    "reply_markup": InlineKeyboardMarkup([
                        [InlineKeyboardButton("Yes", callback_data="lost_yes")],
                        [InlineKeyboardButton("No", callback_data="lost_no")],
                    ]),
                },
            ])
            return

        if data == "exp_signals":
            state["experience"] = "signals"
            state["step"] = "loss_question"

            await send_sequence(update, context, [
                {"text": "Let me guess — inconsistent results?", "delay": 1},
                {"text": "That usually happens when entries are late and the reasoning is missing.", "delay": 2},
                {"text": "Signals alone are not enough.", "delay": 2},
                {
                    "text": "<b>Have you lost money with other signal groups before?</b>",
                    "delay": 2,
                    "reply_markup": InlineKeyboardMarkup([
                        [InlineKeyboardButton("Yes", callback_data="lost_yes")],
                        [InlineKeyboardButton("No", callback_data="lost_no")],
                    ]),
                },
            ])
            return

        if data == "lost_yes":
            state["pain"] = "yes"
            state["step"] = "performance_proof"

            await send_sequence(update, context, [
                {"text": "Yeah... that’s exactly why most traders come to us.", "delay": 2},
                {"text": "Not because they’re new.", "delay": 2},
                {"text": "But because they’ve already been burned by bad timing and low-quality signals.", "delay": 2},
                {"text": "So before anything else...", "delay": 2},
            ])

            await send_performance_proof(update, context)
            return

        if data == "lost_no":
            state["pain"] = "no"
            state["step"] = "performance_proof"

            await send_sequence(update, context, [
                {"text": "That’s good.", "delay": 1},
                {"text": "It means you haven’t built too many bad habits yet.", "delay": 2},
                {"text": "So the smartest thing now is to verify consistency before trusting anyone.", "delay": 2},
            ])

            await send_performance_proof(update, context)
            return

        if data == "next_results":
            state["step"] = "results"

            await send_sequence(update, context, [
                {"text": "Now let me show you recent live account proof.", "delay": 2},
            ])

            await send_results(update, context)

            await send_sequence(update, context, [
                {"text": "So now you’ve seen both:", "delay": 2},
                {"text": "• multi-year consistency\n• recent live execution", "delay": 2},
                {
                    "text": "That’s the difference between marketing and real trading.",
                    "delay": 2,
                    "reply_markup": InlineKeyboardMarkup([
                        [InlineKeyboardButton("Show me real testimonials", callback_data="next_testimonials")]
                    ]),
                },
            ])
            return
        
        
        if data == "next_testimonials":
            state["step"] = "testimonials"

            await send_sequence(update, context, [
                {"text": "Now look at what real users say.", "delay": 2},
                {"text": "Not theory. Not hype.", "delay": 2},
                {"text": "Real people seeing confidence through structure.", "delay": 2},
            ])

            await show_testimonials_flow(update, context)
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
                {"text": "That’s the difference between guessing and structured trading.", "delay": 3},
                {"text": "Now you have two smart options:", "delay": 3},
                {"text": "Start with the free channel if you want to observe first.", "delay": 3},
                {
                    "text": "Or unlock Premium Access if you already want the full structure, app tools, and Inner Circle.",
                    "delay": 3,
                    "reply_markup": InlineKeyboardMarkup([
                        [InlineKeyboardButton("✅ Join Free Signals", url=FREE_CHANNEL_LINK)],
                        [InlineKeyboardButton("🚀 Unlock Premium Access", callback_data="premium_offer")],
                        [InlineKeyboardButton("📈 XM Route: 6 Months Free", callback_data="broker_path")],
                    ]),
                },
            ])
            return

        if data == "join_free":
            state["step"] = "join_free"

            await send_sequence(update, context, [
                {"text": "You do <b>not</b> need to jump into Premium immediately.", "delay": 2},
                {"text": "The best move is simple:", "delay": 2},
                {"text": "Join the free channel first.", "delay": 2},
                {"text": "Watch how the setups are structured.", "delay": 2},
                {
                    "text": "Then tap the button below once you’ve joined.",
                    "delay": 2,
                    "reply_markup": InlineKeyboardMarkup([
                        [InlineKeyboardButton("✅ Join Free Signals Channel", url=FREE_CHANNEL_LINK)],
                        [InlineKeyboardButton("✅ I Joined", callback_data="after_free_join")],
                    ]),
                },
            ])
            schedule_auto_join_check(update, context)
            return

        
        elif data == "after_free_join":
            joined = await user_has_joined_free_channel(update, context)

            if not joined:
                await send_plain_text(
                    update,
                    context,
                    "I couldn’t confirm you joined yet.\n\nPlease join the free channel first, then tap ✅ I Joined again.",
                    InlineKeyboardMarkup([
                        [InlineKeyboardButton("✅ Join Free Signals Channel", url=FREE_CHANNEL_LINK)],
                        [InlineKeyboardButton("✅ I Joined", callback_data="after_free_join")]
                    ])
                )
                return

            state["step"] = "joined_free"

            await schedule_onboarding(update, context)
            schedule_conversion_journey(update, context)
            schedule_free_user_premium_reminders(update, context)

            image_path = Path("images/i-joined.png")

            if image_path.exists():
                with image_path.open("rb") as photo:
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=photo,
                        caption=(
                            "✅ Since you’ve joined the free channel, that’s the perfect place to start.\n\n"
                            "Watch the next few signals closely."
                        ),
                    )
            else:
                await send_plain_text(
                    update,
                    context,
                    (
                        "✅ Since you’ve joined the free channel, that’s the perfect place to start.\n\n"
                        "Watch the next few signals closely."
                    )
                )

            await asyncio.sleep(2)

            await send_plain_text(
                update,
                context,
                (
                    "Free helps you observe the signals.\n\n"
                    "Premium is where you get the full structure, earlier setups, trade updates, app tools, and Inner Circle access."
                )
            )

            await asyncio.sleep(2)

            await send_plain_text(
                update,
                context,
                "When you’re ready to go beyond free signals, Premium Access is the next step.",
                InlineKeyboardMarkup([
                    [InlineKeyboardButton("🚀 Unlock Premium Access", callback_data="premium_offer")],
                    [InlineKeyboardButton("📈 XM Route: 6 Months Free", callback_data="broker_path")]
                ])
            )
            return
        
        
        if data == "premium_offer":
            state["step"] = "premium_offer"

            await send_sequence(update, context, [
                {"text": "🚀 <b>Unlock Tradepedia Premium Access</b>", "delay": 2},
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
            ])
            return

        if data == "broker_path":
            state["step"] = "broker_path"

            await send_sequence(update, context, [
                {"text": "📈 <b>Alternative Premium Access Route</b>", "delay": 2},
                {
                    "text": "Open an XM account using our link, deposit $250, then chat with us to activate your <b>6 months free Premium Access</b>.",
                    "delay": 3,
                    "reply_markup": broker_markup(),
                },
            ])
            return

        if data == "human_close":
            state["step"] = "human_close"

            await send_sequence(update, context, [
                {"text": "Perfect.", "delay": 1},
                {"text": "If you want a direct handoff, we can continue the conversation personally from here.", "delay": 2},
                {
                    "text": "You can also go straight into the app and unlock Premium Access when ready.",
                    "delay": 2,
                    "reply_markup": InlineKeyboardMarkup([
                        [InlineKeyboardButton("Open Tradepedia App", url=APP_LINK)]
                    ]),
                },
            ])
            return

        await send_plain_text(update, context, "Unknown action. Type /start to begin again.")

    finally:
        state[processing_key] = False

def schedule_conversion_journey(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.job_queue:
        return

    chat_id = update.effective_chat.id

    journey = [
    (60, "User joined free channel. First Premium reminder."),
    (120, "User has observed free channel. Explain Premium value."),
    (180, "User still has not upgraded. Soft urgency without pressure."),
]

    for seconds, text in journey:
        context.job_queue.run_once(
            send_conversion_push,
            when=seconds,
            data={"chat_id": chat_id, "text": text},
        )




async def send_conversion_push(context: ContextTypes.DEFAULT_TYPE) -> None:
    job = context.job
    chat_id = job.data["chat_id"]
    text_hint = job.data.get("text", "")

    try:
        if openai_client:
            response = await asyncio.to_thread(
                openai_client.responses.create,
                model=OPENAI_MODEL,
                instructions=(
                    TRADEPEDIA_AI_SYSTEM
                    + "\n\nCreate ONE short Telegram follow-up message."
                    + "\nPurpose: move a free-channel user toward Premium Access."
                    + "\nRules:"
                    + "\n- 2 to 4 short sentences only."
                    + "\n- No guaranteed profits."
                    + "\n- No financial advice."
                    + "\n- Mention structure, timing, trade updates, or Premium benefits."
                    + "\n- End with a soft CTA."
                    + "\n- Do not repeat previous wording."
                ),
                input=f"""
                User situation:
                {text_hint}

                Generate a follow-up that:
                - feels new and different
                - builds on previous exposure
                - does NOT repeat previous phrases
                - feels like a human trader speaking
                """
                            )
            message = response.output_text.strip()
        else:
            message = text_hint

        await context.bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🚀 Unlock Premium Access", callback_data="premium_offer")],
                [InlineKeyboardButton("📈 XM Route: 6 Months Free", callback_data="broker_path")]
            ])
        )

    except Exception:
        logger.exception("AI conversion follow-up failed")
        await context.bot.send_message(
            chat_id=chat_id,
            text=text_hint or "Premium gives you deeper structure, earlier setups, and trade updates when you’re ready.",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🚀 Unlock Premium Access", callback_data="premium_offer")]
            ])
        )


async def send_premium_example(update, context):
    chat_id = update.effective_chat.id

    BASE_DIR = Path(__file__).resolve().parent
    image_path = BASE_DIR / "images" / "premium-gold.png"

    if image_path.exists():
        with image_path.open("rb") as photo:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=photo,
                caption="GOLD (H4) — Bearish Reversal"
            )
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Premium chart missing: {image_path}"
        )

    await asyncio.sleep(8)

    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "<b>GOLD (H4) — Bearish Reversal</b>\n\n"
            "<b>Bias:</b> Bearish\n"
            "<b>HTF Alignment:</b> Moderate\n"
            "<b>Score:</b> 6\n"
            "<b>Trade Class:</b> Reversal — Bearish\n"
            "<b>Risk:</b> 0.75% — Standard risk — continuation within prevailing structure.\n\n"
            "<b>Context:</b>\n"
            "Price has failed to extend significantly beyond the prior high and formed a double top, "
            "indicating weakening bullish momentum within the uptrend. The rejection and move back "
            "toward previous support suggest early signs of a corrective phase rather than full trend continuation.\n\n"
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

    await asyncio.sleep(8)

    await context.bot.send_message(
        chat_id=chat_id,
        text="When a signal reaches target, an update is sent:",
        parse_mode="HTML"
    )

    await asyncio.sleep(10)

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

    await asyncio.sleep(10)

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
    app.add_handler(CommandHandler("checkjoin", check_join_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_message))
    app.add_error_handler(error_handler)
    schedule_free_channel_posts(app)

    return app


if __name__ == "__main__":
    logger.info("Bot starting...")
    build_app().run_polling(allowed_updates=Update.ALL_TYPES)