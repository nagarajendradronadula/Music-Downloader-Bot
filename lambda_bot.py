import json
import os
import boto3
import requests
from urllib.parse import unquote
import re

# Environment variables
BOT_TOKEN = os.environ['BOT_TOKEN']
WEBHOOK_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"

def lambda_handler(event, context):
    try:
        # Parse the incoming webhook
        body = json.loads(event['body'])
        
        if 'message' in body:
            message = body['message']
            chat_id = message['chat']['id']
            text = message.get('text', '')
            
            if text == '/start':
                send_message(chat_id, "Hey there! 👋🎉 I'm your music buddy! 🎵✨\n\nJust send me:\n🎥 YouTube links\n🎶 Spotify links\n🍎 Apple Music links\n🌈 Or just tell me a song name!\n\n🎆 Try: \"Blinding Lights The Weeknd\"\n\n⏹️ Send /stop to cancel downloads!")
            
            elif text.startswith('http'):
                # Handle music links
                handle_music_link(chat_id, text)
            
            elif len(text.strip()) > 3:
                # Handle song search
                handle_song_search(chat_id, text)
            
            else:
                send_message(chat_id, "Send me a link or song name! 🎵😊 (at least 3 letters) 😉✨")
        
        return {
            'statusCode': 200,
            'body': json.dumps('OK')
        }
        
    except Exception as e:
        print(f"Error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps('Error')
        }

def handle_music_link(chat_id, url):
    send_message(chat_id, "On it! 🚀🎵 Getting that track for you! ✨🔥")
    
    # Extract title and search YouTube
    title = get_track_title_from_url(url)
    if title:
        youtube_url = search_youtube(title)
        if youtube_url:
            download_and_send(chat_id, youtube_url)
        else:
            send_message(chat_id, "Hmm, couldn't find that song! 😕🤔 Try a different link? 🎆🎵")
    else:
        send_message(chat_id, "Hmm, couldn't find that song! 😕🤔 Try a different link? 🎆🎵")

def handle_song_search(chat_id, query):
    send_message(chat_id, f"Searching for '{query}'... 🔍🎆✨")
    
    youtube_url = search_youtube(query)
    if youtube_url:
        download_and_send(chat_id, youtube_url)
    else:
        send_message(chat_id, "Couldn't find that song! 🤔😬 Try being more specific? 🎆🎵")

def get_track_title_from_url(url):
    # Same logic as before for extracting titles
    if 'music.apple.com' in url:
        match = re.search(r'/(?:album|song)/([^/]+)', url)
        if match:
            title = unquote(match.group(1))
            title = title.replace('-', ' ').replace('_', ' ')
            title = re.sub(r'\s+\d+$', '', title)
            return title.strip() if len(title.strip()) > 3 else None
    
    # Add other service logic here
    return None

def search_youtube(query):
    # Use YouTube Data API to search
    # Return the best match URL
    pass

def download_and_send(chat_id, youtube_url):
    # Use yt-dlp to download and send via S3/Lambda
    send_message(chat_id, "Found it! 🎉🔥 Sending your jam now... 🎵✨")
    # Implementation here
    pass

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})