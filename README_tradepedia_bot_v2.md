# Tradepedia Telegram Bot V2

This version upgrades the bot from a simple menu into a trust-first conversion funnel.

## What changed
- Recent results shown before join CTA
- Testimonials stage
- "How It Works" now compares FREE vs VIP signal structure
- VIP is introduced as a curiosity / context upgrade
- 7-day onboarding drip is scheduled after the user continues from the free flow
- Editable funnel content in `content.json`

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements_v2.txt
cp .env.example.v2 .env
python tradepedia_bot_v2.py
```

## Important
Replace the example content in `content.json` with the client's real:
- results
- testimonials
- trust copy
- signal examples