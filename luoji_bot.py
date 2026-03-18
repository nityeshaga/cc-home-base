#!/usr/bin/env python3
"""
Luo Ji — AI cofounder for Curated Connections.

HTTP Events API version (production-standard). Uses Flask + Cloudflare Tunnel
instead of Socket Mode. Slack sends stateless HTTP POSTs to your public URL.

Key difference from Socket Mode: Slack requires a 200 response within 3 seconds.
Claude Code calls take minutes, so we respond immediately and process in a
background thread, posting the result when ready.

Also supports proactive messaging via CLI:
    python luoji_bot.py --send USER_ID "message"
    python luoji_bot.py --channel "#general" "message"
    echo '{"result":"..."}' | python luoji_bot.py --send-result USER_ID
"""

import argparse
import json
import logging
import logging.handlers
import os
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, request, jsonify
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from slack_sdk import WebClient

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOG_DIR = Path(__file__).parent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("luoji")

_rotating_handler = logging.handlers.RotatingFileHandler(
    LOG_DIR / "luoji.log",
    maxBytes=5 * 1024 * 1024,
    backupCount=3,
    encoding="utf-8",
)
_rotating_handler.setFormatter(
    logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
)
logger.addHandler(_rotating_handler)

AUDIT_LOG = LOG_DIR / "audit.log"
audit_handler = logging.FileHandler(AUDIT_LOG, encoding="utf-8")
audit_handler.setFormatter(
    logging.Formatter("%(asctime)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
)
audit_logger = logging.getLogger("luoji.audit")
audit_logger.addHandler(audit_handler)
audit_logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv()

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_SIGNING_SECRET = os.environ["SLACK_SIGNING_SECRET"]
AUTHORIZED_USERS = set(
    u.strip() for u in os.environ.get("AUTHORIZED_USERS", "").split(",") if u.strip()
)
PROJECT_DIR = os.environ.get("PROJECT_DIR", "")
if not PROJECT_DIR:
    logger.error("PROJECT_DIR not set. Add it to .env")
    raise SystemExit(1)

CLAUDE_TIMEOUT = int(os.environ.get("CLAUDE_TIMEOUT", "1800"))  # 30 min default
MAX_SLACK_MSG_LEN = 3900
PORT = int(os.environ.get("PORT", "3000"))

# ---------------------------------------------------------------------------
# Slack app (with signing secret for request verification)
# ---------------------------------------------------------------------------

app = App(
    token=SLACK_BOT_TOKEN,
    signing_secret=SLACK_SIGNING_SECRET,
)
slack_client = WebClient(token=SLACK_BOT_TOKEN)

# ---------------------------------------------------------------------------
# Session store: thread_ts → Claude session_id (file-backed)
# ---------------------------------------------------------------------------

SESSION_FILE = LOG_DIR / ".sessions.json"
MAX_SESSIONS = 200


def _load_sessions() -> dict:
    try:
        return json.loads(SESSION_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_session(thread_ts: str, session_id: str) -> None:
    sessions = _load_sessions()
    sessions[thread_ts] = session_id
    if len(sessions) > MAX_SESSIONS:
        for key in sorted(sessions.keys())[:-MAX_SESSIONS]:
            del sessions[key]
    SESSION_FILE.write_text(json.dumps(sessions))


def _get_session(thread_ts: str) -> str | None:
    return _load_sessions().get(thread_ts)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def is_authorized(user_id: str) -> bool:
    return not AUTHORIZED_USERS or user_id in AUTHORIZED_USERS


def log_unauthorized(event: dict) -> None:
    user = event.get("user", "unknown")
    channel = event.get("channel", "unknown")
    text = event.get("text", "")[:100]
    audit_logger.warning(
        f'UNAUTHORIZED | USER:{user} | CHANNEL:{channel} | MSG:"{text}"'
    )


def audit_interaction(
    event: dict, response_text: str, duration: float, session_id: str | None
) -> None:
    user = event.get("user", "unknown")
    channel = event.get("channel", "unknown")
    text = event.get("text", "")[:200]
    audit_logger.info(
        f"USER:{user} | CHANNEL:{channel} | SESSION:{session_id or 'new'} "
        f"| DURATION:{duration:.1f}s | MSG_LEN:{len(text)} | RESP_LEN:{len(response_text)} "
        f'| MSG:"{text}"'
    )


# ---------------------------------------------------------------------------
# Claude CLI
# ---------------------------------------------------------------------------


def call_claude(prompt: str, session_id: str | None = None) -> tuple[str, str | None]:
    """Invoke `claude -p` and return (response_text, session_id)."""
    cmd = [
        "claude",
        "-p", prompt,
        "--output-format", "json",
        "--permission-mode", "bypassPermissions",
    ]
    if session_id:
        cmd.extend(["--resume", session_id])

    logger.info(f"Spawning claude CLI (resume={session_id or 'none'})")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=CLAUDE_TIMEOUT,
        cwd=PROJECT_DIR,
    )

    if result.returncode != 0:
        stderr = result.stderr.strip()
        logger.error(f"Claude CLI failed (rc={result.returncode}): {stderr[:500]}")
        raise RuntimeError(f"Claude CLI error: {stderr[:300]}")

    raw = result.stdout.strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return raw, session_id

    response_text = data.get("result", raw)
    new_session_id = data.get("session_id") or session_id
    return response_text, new_session_id


# ---------------------------------------------------------------------------
# Markdown → Slack mrkdwn
# ---------------------------------------------------------------------------


def md_to_slack(text: str) -> str:
    """Convert GitHub-flavored markdown to Slack mrkdwn."""
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)
    text = re.sub(r"~~(.+?)~~", r"~\1~", text)
    text = re.sub(r"```\w*\n", "```\n", text)
    text = re.sub(r"^#{1,6}\s+(.+)$", r"*\1*", text, flags=re.MULTILINE)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"<\2|\1>", text)
    return text


def chunk_message(text: str) -> list:
    """Split a message into Slack-safe chunks."""
    if len(text) <= MAX_SLACK_MSG_LEN:
        return [text]

    chunks = []
    while text:
        if len(text) <= MAX_SLACK_MSG_LEN:
            chunks.append(text)
            break
        split_at = text.rfind("\n", 0, MAX_SLACK_MSG_LEN)
        if split_at == -1:
            split_at = text.rfind(" ", 0, MAX_SLACK_MSG_LEN)
        if split_at == -1:
            split_at = MAX_SLACK_MSG_LEN
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return chunks


# ---------------------------------------------------------------------------
# File handling
# ---------------------------------------------------------------------------


def download_slack_files(event: dict) -> list[Path]:
    """Download Slack file attachments to temp files for Claude to read."""
    files = event.get("files", [])
    if not files:
        return []

    downloaded = []
    for f in files:
        url = f.get("url_private_download") or f.get("url_private")
        if not url:
            continue

        name = f.get("name", "attachment")
        suffix = Path(name).suffix or ".bin"

        try:
            req = urllib.request.Request(
                url, headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}
            )
            with urllib.request.urlopen(req) as resp:
                tmp = tempfile.NamedTemporaryFile(
                    suffix=suffix, prefix="slack-", delete=False
                )
                tmp.write(resp.read())
                tmp.close()
                downloaded.append(Path(tmp.name))
                logger.info(f"Downloaded Slack file: {name} -> {tmp.name}")
        except Exception as e:
            logger.error(f"Failed to download Slack file {name}: {e}")

    return downloaded


# ---------------------------------------------------------------------------
# Proactive messaging (CLI mode)
# ---------------------------------------------------------------------------


def send_dm(
    user_id: str,
    message: str,
    session_id: str | None = None,
    thread_ts: str | None = None,
) -> str | None:
    """Send a proactive DM. Returns thread_ts."""
    response = slack_client.conversations_open(users=[user_id])
    channel_id = response["channel"]["id"]

    slack_text = md_to_slack(message)
    chunks = chunk_message(slack_text)

    parent_ts = thread_ts
    for chunk in chunks:
        result = slack_client.chat_postMessage(
            channel=channel_id, text=chunk, thread_ts=parent_ts,
        )
        if parent_ts is None:
            parent_ts = result["ts"]

    effective_thread_ts = thread_ts or parent_ts

    if session_id and effective_thread_ts:
        _save_session(effective_thread_ts, session_id)

    audit_logger.info(
        f"PROACTIVE_DM | USER:{user_id} | CHANNEL:{channel_id} "
        f"| THREAD:{effective_thread_ts} | SESSION:{session_id or 'none'} "
        f"| MSG_LEN:{len(message)}"
    )
    return effective_thread_ts


def send_to_channel(channel: str, message: str) -> None:
    """Post a message to a channel."""
    slack_text = md_to_slack(message)
    for chunk in chunk_message(slack_text):
        slack_client.chat_postMessage(channel=channel, text=chunk)
    audit_logger.info(f"PROACTIVE_CHANNEL | CHANNEL:{channel} | MSG_LEN:{len(message)}")


# ---------------------------------------------------------------------------
# Async message processing (handles Slack's 3-second deadline)
#
# Slack requires HTTP 200 within 3 seconds. Claude takes minutes.
# So we respond immediately and process in a background thread.
# ---------------------------------------------------------------------------


def process_message_async(event: dict) -> None:
    """Process a message in a background thread."""
    user_id = event.get("user", "")
    text = event.get("text", "").strip()
    channel = event.get("channel", "")
    thread_ts = event.get("thread_ts") or event.get("ts")

    # Strip bot mention
    text = re.sub(r"<@[A-Z0-9]+>\s*", "", text).strip()

    # Download attachments
    attached_files = download_slack_files(event)

    if not text and not attached_files:
        return

    if attached_files:
        file_instructions = [f"The user attached a file. Read it at: {fp}" for fp in attached_files]
        text = "\n".join(file_instructions) + "\n\n" + (text or "Describe what you see in the attached file(s).")

    # Post "thinking" indicator
    try:
        slack_client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text="Luo Ji is thinking...",
        )
    except Exception:
        pass

    # Call Claude
    session_id = _get_session(thread_ts)

    start = time.time()
    try:
        response_text, new_session_id = call_claude(text, session_id)
    except subprocess.TimeoutExpired:
        minutes = CLAUDE_TIMEOUT // 60
        slack_client.chat_postMessage(
            channel=channel, thread_ts=thread_ts,
            text=f"Sorry, that timed out after {minutes} minutes. Try a simpler question?",
        )
        return
    except RuntimeError as e:
        slack_client.chat_postMessage(
            channel=channel, thread_ts=thread_ts,
            text=f"Something went wrong: {e}",
        )
        return
    except FileNotFoundError:
        slack_client.chat_postMessage(
            channel=channel, thread_ts=thread_ts,
            text="Claude CLI not found. Make sure `claude` is installed and on PATH.",
        )
        return
    duration = time.time() - start

    # Save session
    if new_session_id and thread_ts:
        _save_session(thread_ts, new_session_id)

    # Send response
    slack_text = md_to_slack(response_text)
    for chunk in chunk_message(slack_text):
        slack_client.chat_postMessage(
            channel=channel, text=chunk, thread_ts=thread_ts,
        )

    audit_interaction(event, response_text, duration, new_session_id)
    logger.info(f"Responded to {user_id} in {duration:.1f}s ({len(response_text)} chars)")


# ---------------------------------------------------------------------------
# Slack event handlers
# ---------------------------------------------------------------------------


@app.event("message")
def handle_message(event, say):
    """Handle DMs and channel messages."""
    subtype = event.get("subtype")
    if subtype and subtype != "file_share":
        return

    user_id = event.get("user", "")
    if not is_authorized(user_id):
        log_unauthorized(event)
        say(text="I only respond to authorized users.", thread_ts=event.get("ts"))
        return

    # Process async — return immediately so Slack gets its 200
    threading.Thread(target=process_message_async, args=(event,), daemon=True).start()


@app.event("app_mention")
def handle_mention(event, say):
    """Handle @Luo Ji mentions in channels."""
    user_id = event.get("user", "")
    if not is_authorized(user_id):
        log_unauthorized(event)
        say(text="I only respond to authorized users.", thread_ts=event.get("ts"))
        return

    threading.Thread(target=process_message_async, args=(event,), daemon=True).start()


# Catch-all for events we subscribe to but don't handle
@app.event("member_joined_channel")
def handle_member_joined(event):
    pass


@app.event("reaction_added")
def handle_reaction(event):
    pass


@app.event("file_shared")
def handle_file_shared(event):
    pass


# ---------------------------------------------------------------------------
# Flask app (HTTP Events API)
# ---------------------------------------------------------------------------

flask_app = Flask(__name__)
handler = SlackRequestHandler(app)


@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)


@flask_app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "bot": "luoji"})


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Luo Ji — AI Cofounder Bot")
    parser.add_argument(
        "--send", nargs=2, metavar=("USER_ID", "MESSAGE"),
        help="Send a proactive DM and exit",
    )
    parser.add_argument(
        "--send-result", metavar="USER_ID",
        help="Read Claude JSON from stdin, send as DM with session linking",
    )
    parser.add_argument(
        "--thread", metavar="THREAD_TS",
        help="Reply in an existing thread (use with --send or --send-result)",
    )
    parser.add_argument(
        "--channel", nargs=2, metavar=("CHANNEL", "MESSAGE"),
        help="Post a message to a channel and exit",
    )
    args = parser.parse_args()

    # CLI modes — send and exit
    if args.send:
        thread_ts = send_dm(args.send[0], args.send[1], thread_ts=args.thread)
        if thread_ts:
            print(thread_ts)
        return

    if args.send_result:
        raw = sys.stdin.read().strip()
        try:
            data = json.loads(raw)
            message = data.get("result", "")
            session_id = data.get("session_id")
        except json.JSONDecodeError:
            message = raw
            session_id = None
        if not message:
            message = "Job completed but produced no output."
        send_dm(args.send_result, message, session_id=session_id, thread_ts=args.thread)
        return

    if args.channel:
        send_to_channel(args.channel[0], args.channel[1])
        return

    # Server mode
    if not SLACK_BOT_TOKEN or not SLACK_SIGNING_SECRET:
        logger.error("Missing SLACK_BOT_TOKEN or SLACK_SIGNING_SECRET in .env")
        raise SystemExit(1)

    signal.signal(signal.SIGTERM, lambda s, f: sys.exit(0))
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))

    logger.info(f"Luo Ji starting on port {PORT}")
    logger.info(f"Authorized users: {AUTHORIZED_USERS or 'all'}")
    logger.info(f"Project dir: {PROJECT_DIR}")

    flask_app.run(host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    main()
