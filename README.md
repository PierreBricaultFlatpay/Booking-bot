# Booking Bot

A Slack bot that lets your team log bookings via `/booking` and posts a celebratory message with a photo to the channel.

## What it does

1. User types `/booking` in any channel
2. A modal opens asking for **List** (1–5 or Affiliate), **Funnel** (1st try / 2nd try / Recovery), **TPV**, and a **photo**
3. The bot posts a message in that channel showing the booker, TPV, list, funnel, daily booking count, and the photo inline

## Setup

### 1. Create the Slack app

1. Go to <https://api.slack.com/apps> → **Create New App** → **From an app manifest**
2. Pick your workspace
3. Paste the contents of `manifest.yaml` and create the app

### 2. Grab the two tokens you'll need

- **`SLACK_BOT_TOKEN`** — On the app's **OAuth & Permissions** page, click **Install to Workspace**, then copy the *Bot User OAuth Token* (starts with `xoxb-`)
- **`SLACK_APP_TOKEN`** — On **Basic Information** → **App-Level Tokens**, click **Generate Token and Scopes**, add the `connections:write` scope, and copy the token (starts with `xapp-`)

### 3. Deploy to Railway

1. Push this repo to GitHub
2. In Railway: **New Project** → **Deploy from GitHub repo** → pick the repo
3. Add the two env vars under **Variables**:
   - `SLACK_BOT_TOKEN`
   - `SLACK_APP_TOKEN`
4. Railway will detect the Procfile and run `python app.py`

> If Railway insists on a `web` process type, just rename `worker:` to `web:` in the Procfile — Socket Mode doesn't actually need a port.

### 4. Try it

In any channel where the bot is invited (`/invite @Booking Bot`), type `/booking`.

## Local dev

```bash
pip install -r requirements.txt
export SLACK_BOT_TOKEN=xoxb-...
export SLACK_APP_TOKEN=xapp-...
python app.py
```

## Notes & extension ideas

- **Daily counter is in-memory** and resets when the bot restarts. For real persistence, replace `booking_counts` with Postgres (Railway has a one-click add-on) or Redis.
- The bot posts in the channel where `/booking` was invoked. If you want a single fixed channel (e.g. `#sales-wins`), replace `view["private_metadata"]` with a hardcoded channel ID in `handle_booking_submit`.
- Want a weekly or monthly leaderboard? The counter dict already keys on `user_id:date` — easy to aggregate.
- TPV is formatted European-style (`240.000 €`, `1.234,50 €`).
