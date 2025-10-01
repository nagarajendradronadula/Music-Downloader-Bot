#!/usr/bin/env python3
import os
import requests
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
last_update_id = 0

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        response = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
        print(f"✅ Message sent to {chat_id}: {response.status_code}")
        if response.status_code != 200:
            print(f"❌ Send error: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Send message error: {e}")
        return False

def get_updates():
    global last_update_id
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"offset": last_update_id + 1, "timeout": 10}
    
    try:
        print(f"🔄 Polling for updates (offset: {last_update_id + 1})...")
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        
        if data.get("ok"):
            updates = data.get("result", [])
            if updates:
                print(f"📨 Received {len(updates)} updates")
            else:
                print("⏳ No new messages")
            return updates
        else:
            print(f"❌ API error: {data}")
    except Exception as e:
        print(f"❌ Get updates error: {e}")
    return []

def main():
    global last_update_id
    
    print("🤖 Test Bot starting...")
    print(f"🔑 Bot token: {BOT_TOKEN[:10]}...")
    
    # Test bot info
    try:
        response = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe")
        if response.status_code == 200:
            bot_info = response.json()["result"]
            print(f"✅ Bot connected: @{bot_info['username']}")
        else:
            print(f"❌ Bot connection failed: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Bot test failed: {e}")
        return
    
    print("📱 Waiting for messages... (send /start to test)")
    print("Debug: Starting polling loop...")
    
    while True:
        try:
            updates = get_updates()
            
            for update in updates:
                last_update_id = update["update_id"]
                
                if "message" in update:
                    message = update["message"]
                    chat_id = message["chat"]["id"]
                    text = message.get("text", "")
                    user = message.get("from", {}).get("first_name", "User")
                    
                    print(f"📩 Message from {user} ({chat_id}): {text}")
                    
                    if text == "/start":
                        send_message(chat_id, "✅ Bot is working! I can send and receive messages.")
                    elif text == "/test":
                        send_message(chat_id, "🧪 Test successful! Bot communication is working perfectly.")
                    else:
                        send_message(chat_id, f"Echo: {text}")
            
            time.sleep(3)  # Longer sleep for debugging
            
        except KeyboardInterrupt:
            print("\n🛑 Test bot stopped")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()