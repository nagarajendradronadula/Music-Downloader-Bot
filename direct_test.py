#!/usr/bin/env python3
import os
import requests
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Test 1: Get all updates without offset
print("🔍 Test 1: Getting ALL updates...")
response = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates")
data = response.json()
print(f"Status: {response.status_code}")
print(f"Response: {data}")

if data.get('ok') and data.get('result'):
    print(f"\n📨 Found {len(data['result'])} total messages")
    for i, update in enumerate(data['result'][-5:]):  # Show last 5
        if 'message' in update:
            msg = update['message']
            chat_id = msg['chat']['id']
            text = msg.get('text', 'No text')
            print(f"  {i+1}. Chat ID: {chat_id}, Text: '{text}'")
    
    # Test 2: Send a message to the last chat
    if data['result']:
        last_chat_id = data['result'][-1]['message']['chat']['id']
        print(f"\n📤 Test 2: Sending test message to chat {last_chat_id}")
        send_response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": last_chat_id, "text": "🧪 Direct test message - bot is working!"}
        )
        print(f"Send status: {send_response.status_code}")
        print(f"Send response: {send_response.json()}")
else:
    print("❌ No messages found. Make sure you've sent /start to the bot first.")