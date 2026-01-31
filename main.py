#!/usr/bin/env python3
import os
import glob
import yt_dlp
import requests
import time
import threading
import logging
from dotenv import load_dotenv
from urllib.parse import urlparse
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables (fallback for local development)
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("BOT_TOKEN not found in environment variables")
    logger.error("Please set BOT_TOKEN in Railway dashboard or .env file")
    exit(1)

YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
last_update_id = 0
user_processes = {}

def get_ydl_opts(is_playlist=False):
    """Get optimized yt-dlp options for highest quality"""
    return {
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'outtmpl': '%(title).100s.%(ext)s',
        'quiet': True,
        'noplaylist': not is_playlist,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'retries': 3,
        'fragment_retries': 3,
        'no_warnings': True,
        'ignoreerrors': True,
        'extract_flat': False
    }

def search_youtube_api(query, max_results=1):
    """Search YouTube using API"""
    if not YOUTUBE_API_KEY:
        return None
    
    try:
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            'key': YOUTUBE_API_KEY,
            'q': query,
            'part': 'snippet',
            'type': 'video',
            'maxResults': max_results,
            'order': 'relevance'
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if 'items' in data and data['items']:
            video_id = data['items'][0]['id']['videoId']
            return f"https://www.youtube.com/watch?v={video_id}"
        return None
    except requests.RequestException as e:
        logger.error(f"YouTube API search error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in YouTube API search: {e}")
        return None

def cleanup_files():
    """Delete all downloaded files"""
    try:
        files_deleted = 0
        patterns = ["*.mp3", "*.m4a", "*.webm", "*.wav", "*.opus"]
        
        for pattern in patterns:
            for file_path in glob.glob(pattern):
                try:
                    if os.path.basename(file_path) == file_path and not file_path.startswith('..'):
                        os.remove(file_path)
                        files_deleted += 1
                except OSError as e:
                    logger.warning(f"Could not remove {file_path}: {e}")
        
        if files_deleted > 0:
            logger.info(f"Cleaned up {files_deleted} files")
    except Exception as e:
        logger.error(f"Cleanup error: {e}")

def start_cleanup_timer():
    """Start cleanup timer that runs every 30 minutes"""
    def cleanup_loop():
        while True:
            cleanup_files()
            time.sleep(1800)
    
    cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
    cleanup_thread.start()

def is_playlist(url):
    """Check if URL is a YouTube playlist"""
    try:
        return ('youtube.com' in url or 'youtu.be' in url) and ('playlist' in url or 'list=' in url or '/channel/' in url or '/user/' in url)
    except Exception as e:
        logger.error(f"Error checking if URL is playlist: {e}")
        return False



def process_youtube_playlist(url, chat_id):
    """Process YouTube playlist directly"""
    try:
        user_processes[chat_id] = True
        
        # Extract playlist info
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'no_warnings': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if 'entries' not in info:
                send_message(chat_id, "No tracks found in playlist.")
                return
            
            entries = [entry for entry in info['entries'] if entry]
            total_tracks = len(entries)
            
            if total_tracks == 0:
                send_message(chat_id, "Empty playlist.")
                return
            
            # Limit playlist size
            max_tracks = 50
            if total_tracks > max_tracks:
                entries = entries[:max_tracks]
                send_message(chat_id, f"Playlist has {total_tracks} tracks. Downloading first {max_tracks}...")
            
            send_message(chat_id, f"📋 Found {len(entries)} tracks! Starting download... 🎵")
            
            sent_count = 0
            failed_count = 0
            
            for i, entry in enumerate(entries, 1):
                try:
                    if not entry or not entry.get('id'):
                        failed_count += 1
                        continue
                    
                    video_url = f"https://www.youtube.com/watch?v={entry['id']}"
                    title = entry.get('title', f'Track {i}')[:40]
                    
                    send_message(chat_id, f"[{i}/{len(entries)}] {title}...")
                    
                    cleanup_files()
                    
                    # Download individual track
                    with yt_dlp.YoutubeDL(get_ydl_opts()) as ydl:
                        ydl.download([video_url])
                    
                    mp3_files = glob.glob("*.mp3")
                    if mp3_files:
                        file_path = mp3_files[0]
                        if send_document(chat_id, file_path):
                            sent_count += 1
                            send_message(chat_id, f"✅ [{i}/{len(entries)}] Sent!")
                        else:
                            send_message(chat_id, f"❌ [{i}/{len(entries)}] Send failed")
                            failed_count += 1
                        
                        try:
                            os.remove(file_path)
                        except OSError:
                            pass
                    else:
                        send_message(chat_id, f"❌ [{i}/{len(entries)}] Download failed")
                        failed_count += 1
                    
                    time.sleep(1)  # Rate limiting
                    
                except Exception as track_error:
                    logger.error(f"Track {i} error: {track_error}")
                    send_message(chat_id, f"❌ [{i}/{len(entries)}] Error")
                    failed_count += 1
                    continue
            
            send_message(chat_id, f"🎉 Playlist complete!\n✅ Sent: {sent_count}\n❌ Failed: {failed_count}")
        
    except Exception as e:
        logger.error(f"YouTube playlist processing error: {e}")
        send_message(chat_id, "YouTube playlist processing failed. Try again later.")
    finally:
        user_processes[chat_id] = False

def process_playlist(url, chat_id):
    """Process YouTube playlist"""
    if 'youtube.com' in url or 'youtu.be' in url:
        process_youtube_playlist(url, chat_id)
    else:
        send_message(chat_id, "Only YouTube playlists are supported.")

def get_track_title_from_url(url):
    """Extract track title from YouTube URL"""
    try:
        ydl_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': False}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', '')
            if title:
                title = re.sub(r'\[.*?\]|\(.*?\)', '', title).strip()
                return title
    except Exception as e:
        logger.error(f"Title extraction error: {e}")
    return None

def clean_youtube_url(url):
    """Clean YouTube URL and extract video ID"""
    try:
        if 'youtu.be/' in url:
            # Extract video ID from short URL
            video_id = url.split('youtu.be/')[1].split('?')[0].split('&')[0]
            return f"https://www.youtube.com/watch?v={video_id}"
        elif 'youtube.com/watch' in url:
            # Clean parameters except v
            if 'v=' in url:
                video_id = url.split('v=')[1].split('&')[0]
                return f"https://www.youtube.com/watch?v={video_id}"
        return url
    except Exception:
        return url

def download_youtube_video(url):
    """Download single YouTube video"""
    try:
        cleanup_files()
        
        # Clean and validate YouTube URL
        clean_url = clean_youtube_url(url)
        
        # Download with optimized settings
        opts = get_ydl_opts()
        
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([clean_url])
        
        mp3_files = glob.glob("*.mp3")
        return mp3_files[0] if mp3_files else None
        
    except Exception as e:
        logger.error(f"YouTube download error: {e}")
        return None

def download_music(url):
    """Download single track from YouTube"""
    try:
        cleanup_files()
        
        # Handle YouTube URLs directly
        if 'youtube.com' in url or 'youtu.be' in url:
            return download_youtube_video(url)
        else:
            # For non-YouTube URLs, search on YouTube
            track_title = get_track_title_from_url(url)
            if track_title:
                api_url = search_youtube_api(track_title)
                download_url = api_url if api_url else f"ytsearch1:{track_title}"
            else:
                return None
        
        with yt_dlp.YoutubeDL(get_ydl_opts()) as ydl:
            ydl.download([download_url])
        
        mp3_files = glob.glob("*.mp3")
        return mp3_files[0] if mp3_files else None
        
    except Exception as e:
        logger.error(f"Download error: {e}")
        return None

def send_message(chat_id, text):
    """Send message to Telegram chat"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        text = str(text)[:4096]
        
        response = requests.post(
            url, 
            json={"chat_id": chat_id, "text": text}, 
            timeout=10
        )
        response.raise_for_status()
        logger.info(f"Message sent to {chat_id}")
        return True
    except requests.RequestException as e:
        logger.error(f"Send message error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending message: {e}")
        return False

def send_document(chat_id, file_path, retries=3):
    """Send document to Telegram chat with retry mechanism"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    
    if not os.path.basename(file_path) == file_path or file_path.startswith('..'):
        logger.error(f"Invalid file path: {file_path}")
        return False
        
    if not os.path.exists(file_path):
        logger.error(f"File does not exist: {file_path}")
        return False
    
    file_size = os.path.getsize(file_path)
    if file_size > 50 * 1024 * 1024:  # 50MB limit
        logger.error(f"File too large: {file_size} bytes")
        return False
    
    for attempt in range(retries):
        try:
            logger.info(f"Sending: {os.path.basename(file_path)} (attempt {attempt + 1})")
            with open(file_path, 'rb') as f:
                files = {'document': f}
                data = {
                    'chat_id': chat_id,
                    'caption': f"🎵 {os.path.splitext(os.path.basename(file_path))[0]}"
                }
                response = requests.post(url, files=files, data=data, timeout=300, stream=True)
                response.raise_for_status()
            logger.info(f"File sent successfully on attempt {attempt + 1}")
            return True
        except requests.RequestException as e:
            logger.error(f"Send attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            continue
        except Exception as e:
            logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
            return False
    
    logger.error(f"Failed to send file after {retries} attempts")
    return False

def get_updates():
    """Get updates from Telegram"""
    global last_update_id
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"offset": last_update_id + 1, "timeout": 10}
    
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        if data.get("ok"):
            updates = data.get("result", [])
            if updates:
                logger.info(f"Received {len(updates)} updates")
            return updates
        else:
            logger.error(f"API error: {data}")
    except requests.RequestException as e:
        logger.error(f"Get updates error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error getting updates: {e}")
    return []

def find_best_match(query, search_results):
    """Find best matching result from search results"""
    if not search_results or 'entries' not in search_results:
        return None
    
    query_lower = query.lower()
    query_words = set(query_lower.split())
    
    best_match = None
    best_score = 0
    
    for entry in search_results['entries'][:5]:  # Check top 5 results
        if not entry:
            continue
            
        title = entry.get('title', '').lower()
        uploader = entry.get('uploader', '').lower()
        
        # Calculate match score
        title_words = set(title.split())
        uploader_words = set(uploader.split())
        all_words = title_words.union(uploader_words)
        
        # Word overlap score
        overlap = len(query_words.intersection(all_words))
        score = overlap / len(query_words) if query_words else 0
        
        # Bonus for exact substring matches
        if any(word in title for word in query_words if len(word) > 3):
            score += 0.3
        
        # Bonus for official/audio content
        if any(term in title for term in ['official', 'audio', 'music']):
            score += 0.1
        
        # Penalty for live/remix versions unless specifically requested
        if 'live' not in query_lower and 'live' in title:
            score -= 0.2
        if 'remix' not in query_lower and 'remix' in title:
            score -= 0.1
        
        if score > best_score:
            best_score = score
            best_match = entry
    
    return best_match if best_score > 0.3 else search_results['entries'][0]

def process_search_query(query, chat_id):
    """Process search query with improved matching"""
    try:
        user_processes[chat_id] = True
        cleanup_files()
        
        # Try YouTube API first
        youtube_url = search_youtube_api(query)
        if youtube_url:
            logger.info(f"Found via API: {youtube_url}")
            download_url = youtube_url
        else:
            # Use yt-dlp search as fallback
            download_url = f"ytsearch1:{query}"
        
        logger.info("Starting download...")
        
        try:
            with yt_dlp.YoutubeDL(get_ydl_opts()) as ydl:
                ydl.download([download_url])
            
            mp3_files = glob.glob("*.mp3")
            if mp3_files:
                file_path = mp3_files[0]
                send_message(chat_id, "Found it! 🎉 Sending your music now... 🎵")
                
                if send_document(chat_id, file_path):
                    send_message(chat_id, "Enjoy the music! 🎧")
                else:
                    send_message(chat_id, "Couldn't send the file. Please try again.")
                
                try:
                    os.remove(file_path)
                except OSError as e:
                    logger.warning(f"Could not remove {file_path}: {e}")
            else:
                send_message(chat_id, "Couldn't find that song. Try being more specific.")
                
        except Exception as e:
            logger.error(f"Download failed: {e}")
            send_message(chat_id, "Download failed. Please try a different search term.")
            
    except Exception as e:
        logger.error(f"Search error: {e}")
        send_message(chat_id, "Search failed. Please try again with a different query.")
    finally:
        user_processes[chat_id] = False

def main():
    """Main bot loop"""
    global last_update_id
    
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook",
            json={"drop_pending_updates": True},
            timeout=10
        )
    except Exception as e:
        logger.error(f"Error clearing webhook: {e}")
    
    commands = [
        {"command": "start", "description": "🎉 Welcome & get started"},
        {"command": "help", "description": "📚 How to use the bot"},
        {"command": "status", "description": "🤖 Check bot status"},
        {"command": "clean", "description": "🧹 Clean temporary files"},
    ]
    
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/setMyCommands",
            json={"commands": commands},
            timeout=10
        )
    except Exception as e:
        logger.error(f"Error setting commands: {e}")
    
    logger.info("🤖 Music Downloader Bot starting...")
    logger.info("🧹 Auto-cleanup every 30 minutes enabled")
    logger.info("📱 Waiting for messages...")
    
    start_cleanup_timer()
    
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
                    logger.info(f"Message from {user} ({chat_id}): {text}")
                    
                    if text == "/start":
                        send_message(chat_id, 
                            "Hey there! 👋 I'm your YouTube music downloader! 🎵\n\n"
                            "🎯 Commands:\n"
                            "/help - 📚 Get help\n"
                            "/status - 🤖 Bot status\n"
                            "/clean - 🧹 Clean temp files\n\n"
                            "🎆 Send me YouTube links or song names to download!")
                    
                    elif text == "/help":
                        send_message(chat_id,
                            "🎆 How to use me:\n\n"
                            "🔗 Send YouTube links:\n"
                            "• Single videos\n"
                            "• Playlists\n"
                            "• Channels\n\n"
                            "🔍 Or just send song names like:\n"
                            "\"Blinding Lights The Weeknd\"\n\n"
                            "I'll search YouTube and download it for you! 🎵")
                    
                    elif text == "/status":
                        active_downloads = len([p for p in user_processes.values() if p])
                        send_message(chat_id,
                            f"🤖 Bot Status:\n\n"
                            f"✅ Online and ready!\n"
                            f"📥 Active downloads: {active_downloads}\n"
                            f"🧹 Auto-cleanup: Every 30 mins\n"
                            f"🚀 Server: Running smooth!")
                    
                    elif text == "/clean":
                        cleanup_files()
                        send_message(chat_id, "Cleaned up temp files! 🧹")
                    
                    elif text.startswith("http"):
                        logger.info(f"Processing URL: {text[:50]}...")
                        
                        # Only support YouTube URLs
                        if not ('youtube.com' in text or 'youtu.be' in text):
                            send_message(chat_id, "Only YouTube links are supported! 🔴")
                            continue
                        
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
                                except OSError as e:
                                    logger.warning(f"Could not remove {file_path}: {e}")
                            else:
                                send_message(chat_id, "Couldn't download that track. Try a different link?")
                        
                        user_processes[chat_id] = False
                    
                    elif not text.startswith('/') and len(text.strip()) > 3:
                        logger.info(f"Processing search: {text}")
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
            
            time.sleep(1)
            
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            break
        except Exception as e:
            logger.error(f"Main loop error: {e}")
            time.sleep(5)
    
    cleanup_files()

if __name__ == "__main__":
    main()