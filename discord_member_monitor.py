import os
import time
import requests
import websocket
import json
import threading


DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
GATEWAY_URL = "wss://gateway.discord.gg/?v=9&encoding=json"

identified = False
guild_members = {}

headers = {
    "Authorization": DISCORD_TOKEN,
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/json"
}

def send_to_webhook(content):
    try:
        requests.post(WEBHOOK_URL, json={"content": content})
    except Exception as e:
        print(f"Webhook error: {e}")

def get_current_members():
    global guild_members
    r = requests.get("https://discord.com/api/v9/users/@me/guilds", headers=headers)
    for guild in r.json():
        guild_id = guild['id']
        try:
            members_r = requests.get(f"https://discord.com/api/v9/guilds/{guild_id}/members?limit=1000", headers=headers)
            if members_r.status_code == 200:
                guild_members[guild_id] = set(member['user']['id'] for member in members_r.json())
        except Exception:
            continue

def on_message(ws, message):
    global identified, guild_members
    data = json.loads(message)

    if data.get("t") == "READY" and not identified:
        print("Identified with Discord Gateway.")
        get_current_members()
        identified = True

    if data.get("t") == "GUILD_MEMBER_ADD":
        guild_id = data['d']['guild_id']
        user = data['d']['user']
        user_id = user['id']
        username = f"{user['username']}#{user.get('discriminator', '')}"

        if user_id not in guild_members.get(guild_id, set()):
            guild_members.setdefault(guild_id, set()).add(user_id)
            send_to_webhook(f"New member joined in Guild {guild_id}: {username} ({user_id})")

def on_error(ws, error):
    print(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("Closed connection, reconnecting in 5 seconds...")
    time.sleep(5)
    start_gateway()

def on_open(ws):
    def run():
        payload = {
            "op": 2,
            "d": {
                "token": DISCORD_TOKEN,
                "capabilities": 4093,
                "properties": {
                    "os": "linux",
                    "browser": "chrome",
                    "device": "chrome"
                },
                "presence": {
                    "status": "online",
                    "activities": [],
                    "since": 0,
                    "afk": False
                },
                "compress": False
            }
        }
        ws.send(json.dumps(payload))
    threading.Thread(target=run).start()

def start_gateway():
    ws = websocket.WebSocketApp(
        GATEWAY_URL,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
        on_open=on_open
    )
    ws.run_forever()

if __name__ == "__main__":
    if not DISCORD_TOKEN or not WEBHOOK_URL:
        print("Missing environment variables. Please set DISCORD_TOKEN and WEBHOOK_URL.")
    else:
        start_gateway()
      
