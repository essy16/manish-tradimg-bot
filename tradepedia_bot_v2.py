"""
Tradepedia Telegram Bot - Phase 2 Conversational Funnel
Auto-flow + delays + human-style conversation
"""

from __future__ import annotations
from datetime import time,datetime, timedelta
from zoneinfo import ZoneInfo
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
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

    intervals = [
        (6 * 60 * 60, 1),    # 6 hours
        (12 * 60 * 60, 2),   # 12 hours
        (24 * 60 * 60, 3),   # 24 hours
    ]

    for seconds, step in intervals:
        context.job_queue.run_once(
            send_smart_premium_followup,
            when=seconds,
            data={
                "chat_id": chat_id,
                "temperature": temperature,
                "day": step,
            },
            name=f"premium_followup_{user_id}_{step}",
        )
async def send_smart_premium_followup(context: ContextTypes.DEFAULT_TYPE) -> None:
    job = context.job
    chat_id = job.data["chat_id"]
    temperature = job.data.get("temperature", "warm")
    day = job.data.get("day", 1)

    if temperature == "hot":
        text = random.choice([
            "VIP members were already positioned before this move.\n\nFree shows what is happening. VIP shows the plan before it happens.",
            "This setup was explained step-by-step inside VIP.\n\nFree is useful, but VIP gives the full structure.",
            "Free shows the move.\n\nVIP shows the entry logic, trade management, and updates behind the move.",
            "This is where structure makes the difference.\n\nVIP is not more noise — it is the complete trading experience.",
        ])

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Unlock Premium Access", callback_data="premium_offer")],
            [InlineKeyboardButton("📈 XM Route: 6 Months Free", callback_data="broker_path")]
        ])

    elif temperature == "cold":
        text = random.choice([
            "No pressure to upgrade yet.\n\nStart with the free channel and watch how the setups are handled.",
            "The free channel is there so you can judge from evidence, not hype.",
            "Free gives you a useful starting point.\n\nWatch the timing, updates, and structure first.",
            "You do not need to decide today.\n\nObserve the free signals first, then decide if VIP makes sense.",
        ])

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Join Free Signals", url=FREE_CHANNEL_LINK)],
            [InlineKeyboardButton("Show Results", callback_data="next_results")]
        ])

    else:
        text = random.choice([
            "Free is useful because it lets you observe.\n\nVIP is where the full breakdown, earlier entries, and trade management happen.",
            "You’re starting to see the difference.\n\nFree shows direction. VIP shows the complete plan.",
            "VIP members don’t just receive signals.\n\nThey get structure, context, updates, and the full trading experience.",
            "The free channel builds trust.\n\nVIP is where the deeper analysis and complete execution plan are shared.",
        ])

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Unlock Premium Access", callback_data="premium_offer")],
            [InlineKeyboardButton("✅ Join Free Signals", url=FREE_CHANNEL_LINK)]
        ])

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"☀️ <b>Tradepedia Premium Reminder — Day {day}</b>\n\n{text}",
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
        [InlineKeyboardButton("🌐 Tradepedia WebApp", url=APP_LINK)]    ]

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
    try:
        user_id = update.effective_user.id

        member = await context.bot.get_chat_member(
            chat_id=FREE_CHANNEL_ID,
            user_id=user_id
        )

        print("DEBUG MEMBER STATUS:", member.status)

        return member.status in ["member", "administrator", "creator"]

    except Exception as e:
        print("JOIN CHECK ERROR:", e)
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
    await send_plain_text(
        update,
        context,
        (
            "📊 <b>Live Trade Results</b>\n\n"
            "Tap below to view the real Tradepedia results."
        ),
        InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "📊 View Live Results",
                web_app=WebAppInfo(url="https://social.tp-redirect.com/s/Bl1qKplE")
            )],
            [InlineKeyboardButton("💬 Show Real Testimonials", callback_data="next_testimonials")],
            [InlineKeyboardButton("✅ Join Free Signals", url=FREE_CHANNEL_LINK)],
        ])
    )

    schedule_auto_join_check(update, context)


async def test_channel_post(context: ContextTypes.DEFAULT_TYPE):
    print("TEST: Posting to free channel now...")
    await post_daily_free_channel_update(context)

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

    # schedule_pre_join_elite_funnel(update, context)
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
            user_id=job.data.get("user_id")
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
    user_id = update.effective_user.id
    if not context.job_queue:
        return

    chat_id = update.effective_chat.id

    pushes = [
    (120, 1),
    (300, 2),
    (600, 3),
    (900, 4),
]

    for seconds, text in pushes:
        context.job_queue.run_once(
            send_pre_join_push,
            when=seconds,
            data={"chat_id": chat_id, "user_id": user_id, "text": text},
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
        caption = item.get("caption", "Real Tradepedia client testimonial.")

        if not video_path.exists():
            await send_plain_text(update, context, f"Missing video testimonial: {item['video']}")
            continue

        with video_path.open("rb") as video:
            await context.bot.send_video(
                chat_id=update.effective_chat.id,
                video=video,
                caption=caption,
                supports_streaming=True,
                read_timeout=90,
                write_timeout=90,
                connect_timeout=90,
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

    if any(trigger in text_lower for trigger in [
        "show me money",
        "show me the money",
        "show money",
        "money",
        "results",
        "show results",
        "proof",
        "profit",
        "profits",
    ]):
        await send_results(update, context)
        return

    for key, timezone_name in SUPPORTED_TIMEZONES.items():
        if key in text_lower:
            context.user_data["timezone"] = timezone_name

            await send_plain_text(
                update,
                context,
                f"Done — I’ll use your timezone: <b>{timezone_name}</b>."
            )
            return

    # MONEY / RESULTS
    if any(w in text_lower for w in ["show me the money", "show me money", "show money", "money", "profit proof", "show profits"]):
        await send_results(update, context)
        return
    
    
    # DOUBT / TESTIMONIALS
    if any(w in text_lower for w in [
        "i don't believe",
        "i dont believe",
        "don't believe",
        "dont believe",
        "i do not believe",
        "prove it",
        "testimonial",
        "testimonials",
        "review",
        "reviews",
        "feedback"
    ]):
        await send_plain_text(update, context, "Fair — testimonials are the best place to start.")
        await show_testimonials_flow(update, context)

        await asyncio.sleep(2)

        await send_plain_text(
            update,
            context,
            "If you want to verify it properly, join the free channel first and watch the structure live.",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Join Free Signals", url=FREE_CHANNEL_LINK)],
                [InlineKeyboardButton("✅ I Joined", callback_data="after_free_join")],
                [InlineKeyboardButton("🚀 Unlock Premium Access", callback_data="premium_offer")],
            ])
        )
        return

    # JOINED
    if any(w in text_lower for w in ["i joined", "i have joined", "joined", "done", "i am in"]):
        await schedule_onboarding(update, context)
        schedule_conversion_journey(update, context)
        schedule_free_user_premium_reminders(update, context)

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

    # RESULTS
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

    # MORE PROOF
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

    # AVRAMIS
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

    # GREETING
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

    # DEFAULT AI
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

    if checks >= 20:
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
                    "Now watch the next few signals closely. Free helps you observe, "
                    "but the full structure is inside Premium."
                ),
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🚀 Unlock Premium Access", callback_data="premium_offer")],
                    [InlineKeyboardButton("📈 XM Route: 6 Months Free", callback_data="broker_path")]
                ])
            )

            # schedule premium follow-ups after join
            for seconds, step in [
                (6 * 60 * 60, 1),
                (12 * 60 * 60, 2),
                (24 * 60 * 60, 3),
            ]:
                context.job_queue.run_once(
                    send_smart_premium_followup,
                    when=seconds,
                    data={
                        "chat_id": chat_id,
                        "temperature": "warm",
                        "day": step,
                    },
                    name=f"auto_premium_followup_{user_id}_{step}",
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
    job = context.job
    chat_id = job.data["chat_id"]
    user_id = job.data["user_id"]
    step = job.data.get("step", 1)

    try:
        member = await context.bot.get_chat_member(
            chat_id=FREE_CHANNEL_ID,
            user_id=user_id
        )
        joined = member.status in ["member", "administrator", "creator"]
    except Exception:
        joined = False

    joined_messages = {
        1: [
            "Good — you’re already inside the free channel.\n\nNow don’t just watch the signal. Watch how the setup is structured, updated, and managed.",
            "You’ve started correctly by joining free.\n\nThe next thing to notice is how timing and risk are handled before a trade develops.",
        ],
        2: [
            "Free gives you visibility.\n\nPremium gives you the deeper reasoning behind entries, exits, updates, and trade management.",
            "Once you understand the free signals, Premium becomes easier to judge.\n\nIt’s not more noise — it’s deeper structure.",
        ],
        3: [
            "Most people only ask, “buy or sell?”\n\nPremium is for traders who want to understand why the trade exists and how it should be managed.",
            "The real advantage is not receiving more messages.\n\nIt is seeing the plan earlier, with context and structure.",
        ],
        4: [
            "If the free channel is starting to make sense, Premium is the next layer.\n\nThat’s where the full execution plan, app tools, and Inner Circle access come in.",
            "Stay free if you’re still observing.\n\nBut if you want the complete Tradepedia structure, Premium is where it opens fully.",
        ],
    }

    not_joined_messages = {
        1: [
            "You haven’t joined the free channel yet.\n\nThat’s the best first step because you can watch real signals before deciding anything.",
            "No need to pay first.\n\nStart with the free channel and see how Tradepedia posts setups and updates in real time.",
        ],
        2: [
            "Most people judge trading groups from screenshots.\n\nA better way is to join free and watch how the signals are actually managed.",
            "The free channel lets you observe timing, entries, stops, and updates without pressure.",
        ],
        3: [
            "If you’re still unsure, that’s fine.\n\nJoin free first and use the next few signals as your proof.",
            "The safest way to verify Tradepedia is simple: watch the free channel before thinking about Premium.",
        ],
        4: [
            "Last reminder for now — the free channel is there so you can judge from evidence, not hype.",
            "Start free, observe the structure, then decide if Premium makes sense later.",
        ],
    }

    if joined:
        text = random.choice(joined_messages.get(step, joined_messages[4]))
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Unlock Premium Access", callback_data="premium_offer")],
            [InlineKeyboardButton("📈 XM Route: 6 Months Free", callback_data="broker_path")]
        ])
    else:
        text = random.choice(not_joined_messages.get(step, not_joined_messages[4]))
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Join Free Signals Channel", url=FREE_CHANNEL_LINK)],
            [InlineKeyboardButton("✅ I Joined", callback_data="after_free_join")]
        ])

    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=buttons
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

        elif data == "next_results":
            state["step"] = "results"

            await send_sequence(update, context, [
                {"text": "Now let me show you recent live account proof.", "delay": 2},
            ])

            await send_results(update, context)

            await send_sequence(update, context, [
                {"text": "So now you’ve seen the results.", "delay": 2},
                {
                    "text": "Next, look at what real users say.",
                    "delay": 2,
                    "reply_markup": InlineKeyboardMarkup([
                        [InlineKeyboardButton("Show real testimonials", callback_data="next_testimonials")]
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
            state["step"] = "joined_free"

            await schedule_onboarding(update, context)
            schedule_conversion_journey(update, context)
            schedule_free_user_premium_reminders(update, context)

            await send_plain_text(
                        update,
                        context,
                        (
                            "✅ Good — start with the free channel first.\n\n"
                            "Now watch the next few signals closely. Free helps you observe, but the complete structure, earlier entries, trade updates, and full breakdown are inside the Tradepedia WebApp."
                        ),
                        InlineKeyboardMarkup([
                            [InlineKeyboardButton("🌐 Tradepedia WebApp", url=APP_LINK)],
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
    timezone_name = get_user_timezone(context)

    reminders = [
        (1, 11, "Morning WebApp reminder."),
        (1, 19, "Evening WebApp reminder."),
        (2, 11, "Second day morning WebApp reminder."),
        (2, 19, "Second day evening WebApp reminder."),
        (4, 11, "Fourth day morning WebApp reminder."),
        (4, 19, "Fourth day evening WebApp reminder."),
        (7, 11, "Seventh day WebApp reminder."),
        (10, 19, "Final WebApp reminder."),
    ]

    for day, hour, text in reminders:
        run_at = next_user_time(hour, timezone_name) + timedelta(days=day - 1)

        context.job_queue.run_once(
            send_conversion_push,
            when=run_at,
            data={
                "chat_id": chat_id,
                "text": text,
                "timezone": timezone_name,
                "hour": hour,
            },
        )


SUPPORTED_TIMEZONES = {
    "dubai": "Asia/Dubai",
    "uae": "Asia/Dubai",
    "japan": "Asia/Tokyo",
    "tokyo": "Asia/Tokyo",
    "kenya": "Africa/Nairobi",
    "nairobi": "Africa/Nairobi",
    "uk": "Europe/London",
    "london": "Europe/London",
}


def get_user_timezone(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.user_data.get("timezone", "Asia/Dubai")


def next_user_time(hour: int, timezone_name: str) -> datetime:
    tz = ZoneInfo(timezone_name)
    now = datetime.now(tz)

    target = now.replace(hour=hour, minute=0, second=0, microsecond=0)

    if target <= now:
        target += timedelta(days=1)

    return target

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


async def post_daily_free_channel_update(context: ContextTypes.DEFAULT_TYPE) -> None:
    post_types = [
        (
            "🎯 <b>VIP Update</b>\n\n"
            "VIP members caught this move earlier.\n\n"
            "Free shows the move.\n"
            "VIP shows the full structure before it happens."
        ),
        (
            "📈 <b>Trade Update</b>\n\n"
            "Target 2 / Target 3 already hit inside VIP.\n\n"
            "This is where trade management and timing make the difference."
        ),
        (
            "📊 <b>Performance Insight</b>\n\n"
            "Consistent structure leads to consistent results.\n\n"
            "VIP includes full breakdowns, entries, exits, and updates."
        ),
        (
            "🧠 <b>Market Structure</b>\n\n"
            "Free signals show direction.\n\n"
            "VIP explains why the move happens and how it should be managed."
        ),
        (
            "💬 <b>Member Feedback</b>\n\n"
            "“Caught this early thanks to VIP structure.”\n\n"
            "That’s the difference between reacting and planning."
        ),
    ]

    text = random.choice(post_types)

    await context.bot.send_message(
        chat_id=FREE_CHANNEL_ID,
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🌐 Tradepedia WebApp", url=APP_LINK)]
        ])
    )




def next_dubai_time(hour: int, minute: int = 0) -> datetime:
    dubai = ZoneInfo("Asia/Dubai")
    now = datetime.now(dubai)

    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    if target <= now:
        target += timedelta(days=1)

    return target


async def post_free_channel_and_reschedule(context: ContextTypes.DEFAULT_TYPE) -> None:
    await post_daily_free_channel_update(context)

    # Schedule tomorrow same time again
    job_name = context.job.name

    if job_name == "free_channel_11":
        next_run = next_dubai_time(11, 0)
    else:
        next_run = next_dubai_time(19, 0)

    context.job_queue.run_once(
        post_free_channel_and_reschedule,
        when=next_run,
        name=job_name,
    )


def schedule_free_channel_posts(app: Application) -> None:
    if not app.job_queue or not FREE_CHANNEL_ID:
        return

    app.job_queue.run_once(
        post_free_channel_and_reschedule,
        when=next_dubai_time(11, 0),
        name="free_channel_11",
    )

    app.job_queue.run_once(
        post_free_channel_and_reschedule,
        when=next_dubai_time(19, ),
        name="free_channel_19",
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