#!/usr/bin/env python3
"""
Lambda Bot - For AWS Lambda deployment
"""
import json
import os
from main import (
    send_message, send_document, download_music, process_playlist, 
    process_search_query, is_playlist, cleanup_files, user_processes
)
import threading

def lambda_handler(event, context):
    """AWS Lambda handler for Telegram webhook"""
    try:
        # Parse the incoming webhook data
        body = json.loads(event.get('body', '{}'))
        
        if 'message' in body:
            message = body['message']
            chat_id = message['chat']['id']
            text = message.get('text', '')
            user = message.get('from', {}).get('first_name', 'User')
            
            # Handle commands
            if text == '/start':
                send_message(chat_id, 
                    "Hey there! 👋 I'm your YouTube music downloader! 🎵\n\n"
                    "🎯 Commands:\n"
                    "/help - 📚 Get help\n"
                    "/status - 🤖 Bot status\n"
                    "/clean - 🧹 Clean temp files\n\n"
                    "🎆 Send me YouTube links or song names to download!")
            
            elif text == '/help':
                send_message(chat_id,
                    "🎆 How to use me:\n\n"
                    "🔗 Send YouTube links:\n"
                    "• Single videos\n"
                    "• Playlists\n"
                    "• Channels\n\n"
                    "🔍 Or just send song names like:\n"
                    "\"Blinding Lights The Weeknd\"\n\n"
                    "I'll search YouTube and download it for you! 🎵")
            
            elif text == '/status':
                active_downloads = len([p for p in user_processes.values() if p])
                send_message(chat_id,
                    f"🤖 Bot Status:\n\n"
                    f"✅ Online and ready!\n"
                    f"📥 Active downloads: {active_downloads}\n"
                    f"🚀 Server: Lambda function")
            
            elif text == '/clean':
                cleanup_files()
                send_message(chat_id, "Cleaned up temp files! 🧹")
            
            elif text.startswith("http"):
                # Only support YouTube URLs
                if not ('youtube.com' in text or 'youtu.be' in text):
                    send_message(chat_id, "Only YouTube links are supported! 🔴")
                    return {
                        'statusCode': 200,
                        'body': json.dumps({'status': 'ok'})
                    }
                
                user_processes[chat_id] = True
                
                if is_playlist(text):
                    send_message(chat_id, "Playlist detected! Processing... 🎶")
                    # Process playlist in background
                    playlist_thread = threading.Thread(
                        target=process_playlist,
                        args=(text, chat_id),
                        daemon=True
                    )
                    playlist_thread.start()
                else:
                    send_message(chat_id, "Downloading your track... 🚀")
                    
                    file_path = download_music(text)
                    
                    if file_path and os.path.exists(file_path):
                        send_message(chat_id, "Here's your music! 🎧")
                        
                        if send_document(chat_id, file_path):
                            send_message(chat_id, "Enjoy! 😊🎵")
                        else:
                            send_message(chat_id, "Couldn't send the file. Try again?")
                        
                        try:
                            os.remove(file_path)
                        except OSError:
                            pass
                    else:
                        send_message(chat_id, "Couldn't download that track. Try a different link?")
                
                user_processes[chat_id] = False
            
            elif not text.startswith('/') and len(text.strip()) > 3:
                send_message(chat_id, f"Searching for '{text}'... 🔍")
                
                search_thread = threading.Thread(
                    target=process_search_query,
                    args=(text, chat_id),
                    daemon=True
                )
                search_thread.start()
            
            elif len(text.strip()) <= 3 and not text.startswith('/'):
                send_message(chat_id, "Send me a link or song name (at least 3 letters)! 🎵")
            
            else:
                send_message(chat_id, "Unknown command! Use /help to see available commands 😊")
        
        return {
            'statusCode': 200,
            'body': json.dumps({'status': 'ok'})
        }
        
    except Exception as e:
        print(f"Lambda error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }