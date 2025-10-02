#!/usr/bin/env python3
import os
import glob
import yt_dlp
import requests
import time
import threading
from dotenv import load_dotenv
from urllib.parse import urlparse
import re

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
last_update_id = 0
user_processes = {}  # Track ongoing processes per user

def search_youtube_api(query, max_results=1):
    """Search YouTube using API"""
    try:
        url = f"https://www.googleapis.com/youtube/v3/search"
        params = {
            'key': YOUTUBE_API_KEY,
            'q': query,
            'part': 'snippet',
            'type': 'video',
            'maxResults': max_results,
            'order': 'relevance'
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if 'items' in data and data['items']:
            video_id = data['items'][0]['id']['videoId']
            return f"https://www.youtube.com/watch?v={video_id}"
        return None
    except Exception as e:
        print(f"YouTube API search error: {e}")
        return None

def cleanup_files():
    """Delete all downloaded files"""
    try:
        files_deleted = 0
        for pattern in ["*.mp3", "*.m4a", "*.webm", "*.wav", "*.opus"]:
            for f in glob.glob(pattern):
                try:
                    os.remove(f)
                    files_deleted += 1
                except:
                    pass
        if files_deleted > 0:
            print(f"🧹 Cleaned up {files_deleted} files")
    except Exception as e:
        print(f"Cleanup error: {e}")

def start_cleanup_timer():
    """Start cleanup timer that runs every 30 minutes"""
    def cleanup_loop():
        while True:
            cleanup_files()
            time.sleep(1800)  # 30 minutes
    
    cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
    cleanup_thread.start()



def is_playlist(url):
    """Check if URL is a playlist"""
    if 'youtube.com' in url:
        return 'playlist' in url or 'list=' in url
    elif 'spotify.com' in url:
        return '/playlist/' in url or '/album/' in url
    elif 'music.apple.com' in url:
        # Single track has ?i= parameter, playlist/album doesn't
        return '/playlist/' in url or ('/album/' in url and '?i=' not in url)
    else:
        return False

def get_track_title_from_url(url):
    """Extract track title directly from URL structure"""
    import re
    from urllib.parse import unquote
    
    try:
        # Apple Music: extract from /album/title or /song/title
        if 'music.apple.com' in url:
            # Pattern: /album/title-name/id or /song/title-name/id
            match = re.search(r'/(?:album|song)/([^/]+)', url)
            if match:
                title = unquote(match.group(1))
                # Replace hyphens with spaces and clean up
                title = title.replace('-', ' ').replace('_', ' ')
                # Remove ID numbers at the end
                title = re.sub(r'\s+\d+$', '', title)
                return title.strip() if len(title.strip()) > 3 else None
        
        # Spotify: extract from /track/id then get metadata
        elif 'spotify.com' in url:
            # Try yt-dlp for Spotify
            try:
                ydl_opts = {'quiet': True, 'no_warnings': True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    title = info.get('title', '')
                    artist = info.get('artist', '') or info.get('uploader', '')
                    if title:
                        return f"{artist} {title}" if artist else title
            except:
                pass
            
            # Fallback: get from page title
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            title_match = re.search(r'<title>([^<]+)</title>', response.text)
            if title_match:
                title = title_match.group(1).replace(' - song and lyrics by', '').replace(' | Spotify', '').strip()
                return title if len(title) > 3 else None
        
        # Other services: try page title
        else:
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            title_match = re.search(r'<title>([^<]+)</title>', response.text)
            if title_match:
                title = title_match.group(1).strip()
                return title if len(title) > 3 else None
                
    except Exception as e:
        print(f"Title extraction error: {e}")
        pass
    
    return None

def download_music(url):
    """Download single track - supports YouTube, Spotify, Apple Music"""
    try:
        for f in glob.glob("*.mp3") + glob.glob("*.m4a") + glob.glob("*.webm"):
            try:
                # Validate file path to prevent path traversal
                if os.path.basename(f) == f and not f.startswith('..'):
                    os.remove(f)
            except (OSError, PermissionError) as e:
                print(f"Could not remove {f}: {e}")
        
        download_url = url
        
        # If not YouTube, get track title and search YouTube
        if 'youtube.com' not in url and 'youtu.be' not in url:
            track_title = get_track_title_from_url(url)
            if track_title:
                download_url = f"ytsearch1:{track_title}"
            else:
                return None
        
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio',
            'outtmpl': '%(title)s.%(ext)s',
            'quiet': True,
            'noplaylist': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '128',
            }],
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            'extractor_args': {
                'youtube': {
                    'skip': ['dash', 'hls'],
                    'player_skip': ['configs', 'webpage']
                }
            },
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([download_url])
        
        # Look for MP3 files first, then fallback
        mp3_files = glob.glob("*.mp3")
        if mp3_files:
            return mp3_files[0]
        
        audio_files = glob.glob("*.m4a") + glob.glob("*.webm") + glob.glob("*.mp4")
        return audio_files[0] if audio_files else None
    except Exception as e:
        print(f"Download error: {e}")
        return None

def get_spotify_access_token():
    """Get Spotify access token using client credentials"""
    try:
        import base64
        
        # These are public credentials for client credentials flow
        client_id = "your_client_id_here"  # You need to get this from Spotify
        client_secret = "your_client_secret_here"  # You need to get this from Spotify
        
        # For now, use a simple approach without API keys
        return None
    except:
        return None

def extract_spotify_id(url):
    """Extract Spotify ID from URL"""
    import re
    
    # Extract playlist/album/track ID from URL
    patterns = [
        r'spotify\.com/playlist/([a-zA-Z0-9]+)',
        r'spotify\.com/album/([a-zA-Z0-9]+)',
        r'spotify\.com/track/([a-zA-Z0-9]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_spotify_tracks_simple(url):
    """Get Spotify tracks using simple method"""
    try:
        spotify_id = extract_spotify_id(url)
        if not spotify_id:
            return []
        
        print(f"Extracted Spotify ID: {spotify_id}")
        
        # Since we don't have API keys, let's try yt-dlp's Spotify support
        try:
            ydl_opts = {
                'quiet': False,
                'extract_flat': True,
                'skip_download': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                tracks = []
                
                if 'entries' in info:
                    # Playlist/Album
                    for entry in info['entries']:
                        if entry and entry.get('title'):
                            title = entry['title']
                            # Try to get artist from title or other fields
                            artist = entry.get('uploader', '')
                            if artist:
                                tracks.append(f"{artist} - {title}")
                            else:
                                tracks.append(title)
                else:
                    # Single track
                    title = info.get('title', '')
                    artist = info.get('uploader', '')
                    if title:
                        if artist:
                            tracks.append(f"{artist} - {title}")
                        else:
                            tracks.append(title)
                
                print(f"yt-dlp found {len(tracks)} tracks")
                return tracks[:15]  # Limit to 15 tracks
                
        except Exception as e:
            print(f"yt-dlp Spotify extraction failed: {e}")
            return []
            
    except Exception as e:
        print(f"Spotify extraction error: {e}")
        return []

def get_spotify_apple_tracks(url):
    """Get tracks from Spotify or Apple Music"""
    if 'spotify.com' in url:
        return get_spotify_tracks_simple(url)
    elif 'music.apple.com' in url:
        # For Apple Music, we'll use a simple fallback
        try:
            # Try to extract basic info
            import re
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            title_match = re.search(r'<title>([^<]+)</title>', response.text)
            if title_match:
                title = title_match.group(1).replace(' - Apple Music', '').strip()
                return [title] if title else []
        except:
            pass
        return []
    else:
        return []

def download_and_send_playlist(url, chat_id):
    """Human-like approach: get track names, search YouTube, download & send"""
    try:
        # Handle Spotify/Apple Music playlists
        if 'spotify.com' in url or 'music.apple.com' in url:
            track_names = get_spotify_apple_tracks(url)
            if not track_names:
                return False
            
            send_message(chat_id, f"🎵 Found {len(track_names)} tracks. Searching YouTube and sending...")
            
            sent_count = 0
            
            # Step 2: For each track, search YouTube and download
            for i, track_name in enumerate(track_names, 1):
                try:
                    send_message(chat_id, f"🔍 [{i}/{len(track_names)}] Searching: {track_name[:40]}...")
                    
                    # Clear previous files
                    for f in glob.glob("*.mp3") + glob.glob("*.m4a") + glob.glob("*.webm"):
                        os.remove(f)
                    
                    # Search YouTube with better matching
                    youtube_search = f"ytsearch3:{track_name}"  # Get top 3 results
                    
                    ydl_opts_search = {
                        'quiet': True,
                        'extract_flat': True,
                    }
                    
                    # Find best match from search results
                    best_url = None
                    with yt_dlp.YoutubeDL(ydl_opts_search) as ydl_search:
                        search_results = ydl_search.extract_info(youtube_search, download=False)
                        
                        if search_results and 'entries' in search_results:
                            for result in search_results['entries']:
                                if result:
                                    title = result.get('title', '').lower()
                                    # Check if title contains key parts of our track
                                    track_parts = track_name.lower().split(' - ')
                                    if len(track_parts) >= 2:
                                        artist = track_parts[0].strip()
                                        song = track_parts[1].strip()
                                        
                                        # Better matching logic
                                        if (artist[:10] in title or song[:15] in title) and \
                                           ('official' in title or 'audio' in title or 'music' in title):
                                            best_url = result.get('url')
                                            break
                            
                            # Fallback to first result if no perfect match
                            if not best_url and search_results['entries']:
                                best_url = search_results['entries'][0].get('url')
                    
                    if best_url:
                        ydl_opts = {
                            'format': 'bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio',
                            'outtmpl': '%(title)s.%(ext)s',
                            'quiet': True,
                            'noplaylist': True,
                        }
                        
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            ydl.download([best_url])
                    else:
                        continue
                    
                    # Send immediately
                    audio_files = glob.glob("*.mp3") + glob.glob("*.m4a") + glob.glob("*.webm")
                    if audio_files:
                        file_path = audio_files[0]
                        send_message(chat_id, f"📤 [{i}/{len(track_names)}] Sending...")
                        
                        if send_document(chat_id, file_path):
                            sent_count += 1
                            send_message(chat_id, f"✅ [{i}/{len(track_names)}] Sent!")
                        else:
                            send_message(chat_id, f"❌ [{i}/{len(track_names)}] Send failed")
                        
                        os.remove(file_path)
                    
                    import time
                    time.sleep(1)
                    
                except Exception as track_error:
                    send_message(chat_id, f"❌ [{i}/{len(track_names)}] Error: {str(track_error)[:50]}")
                    continue
            
            send_message(chat_id, f"🎉 Done! {sent_count}/{len(track_names)} tracks sent.")
            return True
        
        # Handle YouTube playlists
        else:
            ydl_opts_info = {'quiet': True, 'extract_flat': True}
            
            with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if 'entries' not in info:
                    return False
                
                entries = [entry for entry in info['entries'] if entry]
                total_tracks = len(entries)
                
                send_message(chat_id, f"Sweet! Found {total_tracks} songs. Getting them for you... 🎶")
                
                sent_count = 0
                
                for i, entry in enumerate(entries, 1):
                    # Check if user wants to stop
                    if chat_id in user_processes and not user_processes[chat_id]:
                        send_message(chat_id, "Download stopped! ⏹️")
                        return False
                    
                    try:
                        track_url = entry.get('url') or entry.get('webpage_url')
                        track_title = entry.get('title', 'Unknown Track')
                        
                        if not track_url:
                            continue
                        
                        send_message(chat_id, f"Getting song {i}/{total_tracks}... 🎵")
                        
                        # Clear previous files
                        for f in glob.glob("*.mp3") + glob.glob("*.m4a") + glob.glob("*.webm"):
                            os.remove(f)
                        
                        ydl_opts = {
                            'format': 'bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio',
                            'outtmpl': '%(title)s.%(ext)s',
                            'quiet': True,
                            'noplaylist': True,
                        }
                        
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl_single:
                            ydl_single.download([track_url])
                        
                        audio_files = glob.glob("*.mp3") + glob.glob("*.m4a") + glob.glob("*.webm")
                        if audio_files:
                            file_path = audio_files[0]
                            send_message(chat_id, f"Sending {i}/{total_tracks}... 📤")
                            
                            if send_document(chat_id, file_path):
                                sent_count += 1
                                send_message(chat_id, f"✅ {i}/{total_tracks} done!")
                            else:
                                send_message(chat_id, f"❌ Couldn't send {i}/{total_tracks}")
                            
                            os.remove(file_path)
                        
                        import time
                        time.sleep(1)
                        
                    except Exception as track_error:
                        send_message(chat_id, f"❌ [{i}/{total_tracks}] Error: {str(track_error)[:50]}")
                        continue
                
                send_message(chat_id, f"All done! Got you {sent_count}/{total_tracks} songs! 🎉")
                return True
            
    except Exception as e:
        send_message(chat_id, f"❌ Playlist error: {str(e)[:50]}")
        return False

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        response = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
        print(f"Message sent to {chat_id}: {response.status_code}")
        if response.status_code != 200:
            print(f"Send error: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Send message error: {e}")
        return False

def send_document(chat_id, file_path):
    """Send individual music file"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    
    try:
        print(f"📤 Sending: {os.path.basename(file_path)}")
        with open(file_path, 'rb') as f:
            files = {'document': f}
            data = {'chat_id': chat_id}
            response = requests.post(url, files=files, data=data, timeout=60)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Send failed: {e}")
        return False

def get_updates():
    global last_update_id
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"offset": last_update_id + 1, "timeout": 10}
    
    try:
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        
        if data.get("ok"):
            updates = data.get("result", [])
            if updates:
                print(f"Received {len(updates)} updates")
            return updates
        else:
            print(f"API error: {data}")
    except Exception as e:
        print(f"Get updates error: {e}")
    return []

def main():
    global last_update_id
    
    # Clear webhook
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook", 
                 json={"drop_pending_updates": True})
    
    # Set bot commands
    commands = [
        {"command": "start", "description": "🎉 Welcome & get started"},
        {"command": "search", "description": "🔍 Search for songs by name"},
        {"command": "single", "description": "🎵 Download single tracks"},
        {"command": "playlist", "description": "🎶 Download YouTube playlists"},
        {"command": "help", "description": "📚 How to use the bot"},
        {"command": "status", "description": "🤖 Check bot status"},
        {"command": "stop", "description": "⏹️ Cancel current download"},
        {"command": "clean", "description": "🧹 Clean temporary files"},
        {"command": "exit", "description": "🚪 Exit current mode"}
    ]
    
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/setMyCommands", 
                 json={"commands": commands})
    
    print("🤖 Music Downloader Bot starting...")
    print(f"✅ Bot token: {BOT_TOKEN[:10]}...")
    print("🧹 Auto-cleanup every 30 minutes enabled")
    print("⚡ Bot commands set successfully")
    print("📱 Waiting for messages...")
    

    
    # Start cleanup timer
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
                    print(f"📩 Message from {user} ({chat_id}): {text}")
                    
                    if text == "/start":
                        print(f"🎯 Processing /start command from {chat_id}")
                        send_message(chat_id, "Hey there! 👋🎉 I'm your music buddy! 🎵✨\n\n🤖 Commands:\n/search - 🔍 Search for songs\n/single - 🎵 Download single track\n/playlist - 🎶 Download playlist\n/help - 📚 Get help\n/status - 🤖 Bot status\n/stop - ⏹️ Cancel download\n/clean - 🧹 Clean temp files\n/exit - 🚪 Exit current mode\n\n🎆 Or just send links/song names directly!")
                    elif text == "/search":
                        send_message(chat_id, "🔍 Search Mode Active!\n\nJust type the song name:\nExample: \"Blinding Lights The Weeknd\" 🎵✨\n\nUse /exit to leave this mode")
                        user_processes[chat_id] = "search_mode"
                    elif text == "/single":
                        send_message(chat_id, "🎵 Single Track Mode!\n\nSend me:\n🎥 YouTube link\n🎶 Spotify link\n🍎 Apple Music link\n\nI'll download it for you! 🚀✨")
                        user_processes[chat_id] = "single_mode"
                    elif text == "/playlist":
                        send_message(chat_id, "🎶 Playlist Mode!\n\nSend me a YouTube playlist link and I'll download all songs one by one! 🔥✨\n\n⚠️ Note: Only YouTube playlists supported")
                        user_processes[chat_id] = "playlist_mode"
                    elif text == "/help":
                        send_message(chat_id, "🎆 How to use me:\n\n🔍 /search - Search songs by name\n🎵 /single - Download single tracks\n🎶 /playlist - Download YouTube playlists\n⏹️ /stop - Cancel downloads\n🤖 /status - Check bot status\n🚪 /exit - Exit current mode\n\n🎉 You can also send links/names directly!")
                    elif text == "/status":
                        active_downloads = len([p for p in user_processes.values() if p and p != "search_mode" and p != "single_mode" and p != "playlist_mode"])
                        send_message(chat_id, f"🤖 Bot Status:\n\n✅ Online and ready!\n📥 Active downloads: {active_downloads}\n🧹 Auto-cleanup: Every 30 mins\n🚀 Server: Running smooth!")
                    elif text == "/clean":
                        cleanup_files()
                        send_message(chat_id, "Cleaned up temp files! 🧹✨")
                    elif text == "/exit":
                        if chat_id in user_processes and user_processes[chat_id] in ["search_mode", "single_mode", "playlist_mode"]:
                            mode = user_processes[chat_id].replace("_mode", "")
                            user_processes[chat_id] = False
                            send_message(chat_id, f"Exited {mode} mode! 😌 Back to normal mode 🎆")
                        else:
                            send_message(chat_id, "You're not in any special mode! 😊")
                    elif text == "/stop":
                        if chat_id in user_processes:
                            if user_processes[chat_id] in ["search_mode", "single_mode", "playlist_mode"]:
                                user_processes[chat_id] = False
                                send_message(chat_id, "Mode cancelled! ⏹️😌 Back to normal mode")
                            elif user_processes[chat_id]:
                                user_processes[chat_id] = False
                                send_message(chat_id, "Download stopped! ⏹️😌✨")
                            else:
                                send_message(chat_id, "Nothing to stop! 😊🤷♂️")
                        else:
                            send_message(chat_id, "Nothing to stop! 😊🤷♂️")
                    elif text.startswith("http"):
                        print(f"🔗 Processing URL: {text[:50]}...")
                        # Check if user is in a specific mode
                        current_mode = user_processes.get(chat_id, None)
                        
                        if current_mode == "single_mode":
                            if is_playlist(text):
                                send_message(chat_id, "That's a playlist! 🎶 Use /playlist mode or send a single track link 🎵")
                                continue
                                continue
                        elif current_mode == "playlist_mode":
                            if not is_playlist(text):
                                send_message(chat_id, "That's a single track! 🎵 Use /single mode or send a playlist link 🎶")
                                continue
                                continue
                        
                        user_processes[chat_id] = True  # Start process
                        
                        if is_playlist(text):
                            if 'spotify.com' in text or 'music.apple.com' in text:
                                send_message(chat_id, "Getting Spotify/Apple playlist tracks... 🎵")
                                success = download_and_send_playlist(text, chat_id)
                                if not success:
                                    send_message(chat_id, "Couldn't get playlist tracks! Try individual songs instead! 🎵")
                            else:
                                send_message(chat_id, "Awesome playlist! 🎉🎶 Let me grab all those bangers for you! 🔥✨")
                                success = download_and_send_playlist(text, chat_id)
                                if not success:
                                    send_message(chat_id, "Hmm, playlist didn't work! 😅🤔 Try sending individual songs instead! 🎵🎆")
                        else:
                            send_message(chat_id, "On it! 🚀🎵 Getting that track for you! ✨🔥")
                            
                            file_path = download_music(text)
                            
                            if file_path and os.path.exists(file_path):
                                file_size = os.path.getsize(file_path)
                                send_message(chat_id, "Here's your music! 🎧🎉✨")
                                
                                if send_document(chat_id, file_path):
                                    send_message(chat_id, "Enjoy the vibes! 😊🎆🎵")
                                else:
                                    send_message(chat_id, "Oops! 😅😬 Couldn't send that. Try again? 🤔✨")
                                
                                os.remove(file_path)
                            else:
                                send_message(chat_id, "Hmm, couldn't find that song! 😕🤔 Try a different link? 🎆🎵")
                        
                        user_processes[chat_id] = False  # End process
                    elif not text.startswith('/'):
                        # Only treat as song search if not a command
                        current_mode = user_processes.get(chat_id, None)
                        
                        if current_mode in ["single_mode", "playlist_mode"]:
                            if current_mode == "single_mode":
                                send_message(chat_id, "You're in single track mode! 🎵 Send a link or use /search for song names")
                            else:
                                send_message(chat_id, "You're in playlist mode! 🎶 Send a playlist link or use /search for song names")
                            continue
                        
                        if len(text.strip()) > 3:
                            print(f"🔍 Processing search: {text}")
                            if current_mode == "search_mode":
                                send_message(chat_id, f"Perfect! Searching for '{text}'... 🔍🎆✨")
                            user_processes[chat_id] = True  # Start process
                            send_message(chat_id, f"Searching for '{text}'... 🔍🎆✨")
                            
                            # Clear previous files
                            for f in glob.glob("*.mp3") + glob.glob("*.m4a") + glob.glob("*.webm") + glob.glob("*.mp4"):
                                try:
                                    os.remove(f)
                                except:
                                    pass
                            
                            # Search YouTube using API first, fallback to yt-dlp
                            youtube_url = search_youtube_api(text)
                            if youtube_url:
                                print(f"🔍 Found via API: {youtube_url}")
                                download_url = youtube_url
                            else:
                                youtube_search = f"ytsearch1:{text}"
                                print(f"🔍 Fallback search: {youtube_search}")
                                download_url = youtube_search
                            
                            try:
                                ydl_opts = {
                                    'format': 'bestaudio[ext=m4a]/bestaudio',
                                    'outtmpl': '%(title)s.%(ext)s',
                                    'quiet': True,
                                    'noplaylist': True,
                                    'postprocessors': [{
                                        'key': 'FFmpegExtractAudio',
                                        'preferredcodec': 'mp3',
                                        'preferredquality': '128',
                                    }],
                                    'concurrent_fragment_downloads': 4,
                                }
                                
                                print("📥 Starting download...")
                                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                                    ydl.download([download_url])
                                
                                # Send the downloaded file
                                # Look for MP3 files first
                                mp3_files = glob.glob("*.mp3")
                                if mp3_files:
                                    audio_files = mp3_files
                                else:
                                    audio_files = glob.glob("*.m4a") + glob.glob("*.webm") + glob.glob("*.mp4")
                                
                                print(f"📁 Found {len(audio_files)} files")
                                
                                if audio_files:
                                    file_path = audio_files[0]
                                    print(f"📤 Sending file: {file_path}")
                                    send_message(chat_id, "Found it! 🎉🔥 Sending your jam now... 🎵✨")
                                    
                                    if send_document(chat_id, file_path):
                                        send_message(chat_id, "There you go! 🎧🎆 Enjoy the music! 🎵")
                                    else:
                                        send_message(chat_id, "Hmm, couldn't send that. Try again? 🤷‍♂️")
                                    
                                    try:
                                        if os.path.basename(file_path) == file_path and not file_path.startswith('..'):
                                            os.remove(file_path)
                                    except (OSError, PermissionError):
                                        pass
                                else:
                                    send_message(chat_id, "Couldn't find that song! 🤔😬 Try being more specific? 🎆🎵")
                                    
                            except Exception as e:
                                print(f"❌ Search error: {e}")
                                send_message(chat_id, f"Oops, search failed: {str(e)[:50]}... Try a different search? 🎆✨")
                            
                            user_processes[chat_id] = False  # End process
                        else:
                            send_message(chat_id, "Send me a link or song name! 🎵😊 (at least 3 letters) 😉✨")
                    else:
                        send_message(chat_id, "Unknown command! 🤔 Use /help to see available commands 😊")
            
            time.sleep(1)
            
        except KeyboardInterrupt:
            print("\n🛑 Bot stopped")
            break
        except Exception as e:
            print(f"❌ Main loop error: {e}")
            time.sleep(5)
    
    # Cleanup
    for f in glob.glob("*.mp3"):
        try:
            os.remove(f)
        except:
            pass

if __name__ == "__main__":
    main()