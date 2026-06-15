import logging
import os
from collections import defaultdict
from datetime import date

import requests
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

logging.basicConfig(level=logging.INFO)

app = App(token=os.environ["SLACK_BOT_TOKEN"])

# In-memory daily booking counter.
#   Key: f"{user_id}:{YYYY-MM-DD}"   Value: int
# Survives only while the process is running. Swap for Postgres/Redis if you
# need persistence across Railway restarts.
booking_counts: dict[str, int] = defaultdict(int)


LIST_OPTIONS = [
    {"text": {"type": "plain_text", "text": f"List {n}"}, "value": f"List {n}"}
    for n in range(1, 6)
] + [
    {"text": {"type": "plain_text", "text": "Affiliate"}, "value": "Affiliate"}
]

FUNNEL_OPTIONS = [
    {"text": {"type": "plain_text", "text": label}, "value": label}
    for label in ("1st try", "2nd try", "Recovery")
]


def format_eur(amount: float) -> str:
    """European-style euro formatting. 240000 -> '240.000 €', 1234.5 -> '1.234,50 €'."""
    if amount == int(amount):
        return f"{int(amount):,} €".replace(",", ".")
    return f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"


@app.command("/booking")
def open_booking_modal(ack, body, client):
    ack()
    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "booking_submit",
            "title": {"type": "plain_text", "text": "New Booking"},
            "submit": {"type": "plain_text", "text": "Submit"},
            "close": {"type": "plain_text", "text": "Cancel"},
            # Remember which channel to post back to
            "private_metadata": body["channel_id"],
            "blocks": [
                {
                    "type": "input",
                    "block_id": "list_block",
                    "label": {"type": "plain_text", "text": "List"},
                    "element": {
                        "type": "static_select",
                        "action_id": "list_select",
                        "placeholder": {"type": "plain_text", "text": "Pick a list"},
                        "options": LIST_OPTIONS,
                    },
                },
                {
                    "type": "input",
                    "block_id": "funnel_block",
                    "label": {"type": "plain_text", "text": "Funnel"},
                    "element": {
                        "type": "static_select",
                        "action_id": "funnel_select",
                        "placeholder": {"type": "plain_text", "text": "Pick a funnel"},
                        "options": FUNNEL_OPTIONS,
                    },
                },
                {
                    "type": "input",
                    "block_id": "tpv_block",
                    "label": {"type": "plain_text", "text": "TPV (€)"},
                    "element": {
                        "type": "number_input",
                        "is_decimal_allowed": True,
                        "action_id": "tpv_input",
                        "min_value": "0",
                    },
                },
                {
                    "type": "input",
                    "block_id": "photo_block",
                    "label": {"type": "plain_text", "text": "Cool photo"},
                    "element": {
                        "type": "file_input",
                        "action_id": "photo_input",
                        "filetypes": ["jpg", "jpeg", "png", "gif", "heic", "webp"],
                        "max_files": 1,
                    },
                },
            ],
        },
    )


@app.view("booking_submit")
def handle_booking_submit(ack, body, client, view, logger):
    ack()
    user_id = body["user"]["id"]
    channel_id = view["private_metadata"]
    values = view["state"]["values"]

    list_value = values["list_block"]["list_select"]["selected_option"]["value"]
    funnel_value = values["funnel_block"]["funnel_select"]["selected_option"]["value"]
    tpv_value = float(values["tpv_block"]["tpv_input"]["value"])
    file_info = values["photo_block"]["photo_input"]["files"][0]

    # Increment daily count for this booker
    key = f"{user_id}:{date.today().isoformat()}"
    booking_counts[key] += 1
    count_today = booking_counts[key]

    # file_input gives us a Slack-private URL. Download it so we can re-share
    # it to the channel inline with our text message.
    headers = {"Authorization": f"Bearer {os.environ['SLACK_BOT_TOKEN']}"}
    try:
        resp = requests.get(file_info["url_private"], headers=headers, timeout=30)
        resp.raise_for_status()
        file_content = resp.content
    except Exception as e:
        logger.exception("Failed to download uploaded file")
        client.chat_postMessage(
            channel=user_id,
            text=f":warning: Sorry, I couldn't process your photo: {e}",
        )
        return

    comment = (
        f"🎉 <@{user_id}> just booked!\n\n"
        f"💰 *TPV:* {format_eur(tpv_value)}\n"
        f"📋 *List:* {list_value}\n"
        f"🎯 *Funnel:* {funnel_value}\n"
        f"🔥 *Bookings today:* {count_today}"
    )

    client.files_upload_v2(
        channel=channel_id,
        file=file_content,
        filename=file_info.get("name", "booking.jpg"),
        initial_comment=comment,
    )


if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
