#!/usr/bin/env python3
import os
import glob
import yt_dlp
import requests
import time
import threading

BOT_TOKEN = "8281137886:AAFBcWfTYmTM39g9OucuAKSiggOxqwS3MCQ"
last_update_id = 0
user_processes = {}  # Track ongoing processes per user

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
    cleanup_files()  # Clean on start
    threading.Timer(1800.0, start_cleanup_timer).start()  # 1800 seconds = 30 minutes

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
            os.remove(f)
        
        download_url = url
        
        # If not YouTube, get track title and search YouTube
        if 'youtube.com' not in url and 'youtu.be' not in url:
            track_title = get_track_title_from_url(url)
            if track_title:
                download_url = f"ytsearch1:{track_title}"
            else:
                return None
        
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio',
            'outtmpl': '%(title)s.%(ext)s',
            'quiet': True,
            'noplaylist': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([download_url])
        
        audio_files = glob.glob("*.mp3") + glob.glob("*.m4a") + glob.glob("*.webm")
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
        # Only handle YouTube playlists
        if 'spotify.com' in url or 'music.apple.com' in url:
            return False  # Already handled above
            
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
        
        else:
            # YouTube playlist - use original method
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
    requests.post(url, json={"chat_id": chat_id, "text": text})

def send_document(chat_id, file_path):
    """Send individual music file"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    
    try:
        with open(file_path, 'rb') as f:
            files = {'document': f}
            data = {'chat_id': chat_id}
            response = requests.post(url, files=files, data=data, timeout=120)
        return response.status_code == 200
    except:
        return False

def get_updates():
    global last_update_id
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"offset": last_update_id + 1, "timeout": 10}
    
    try:
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        
        if data.get("ok"):
            return data.get("result", [])
    except:
        pass
    return []

def main():
    global last_update_id
    
    # Clear webhook
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook", 
                 json={"drop_pending_updates": True})
    
    print("🤖 Direct bot starting...")
    print("✅ Send music links to your bot!")
    print("🧹 Auto-cleanup every 30 minutes enabled")
    
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
                    
                    if text == "/start":
                        send_message(chat_id, "Hey there! 👋🎉 I'm your music buddy! 🎵✨\n\nJust send me:\n🎥 YouTube links\n🎶 Spotify links\n🍎 Apple Music links\n🌈 Or just tell me a song name!\n\n🎆 Try: \"Blinding Lights The Weeknd\"\n\n🤖 Commands:\n/start - Show this message\n/help - Get help\n/stop - Cancel download\n/status - Bot status\n/clean - Clean temp files")
                    elif text == "/help":
                        send_message(chat_id, "🎆 How to use me:\n\n🎵 Send YouTube/Spotify/Apple Music links\n🔍 Search by typing song names\n⏹️ Use /stop to cancel downloads\n🧹 Files auto-delete every 30 mins\n\n🎉 Examples:\n- https://youtu.be/abc123\n- \"Bohemian Rhapsody Queen\"\n- Spotify track links")
                    elif text == "/status":
                        active_downloads = len([p for p in user_processes.values() if p])
                        send_message(chat_id, f"🤖 Bot Status:\n\n✅ Online and ready!\n📥 Active downloads: {active_downloads}\n🧹 Auto-cleanup: Every 30 mins\n🚀 Server: Running smooth!")
                    elif text == "/clean":
                        cleanup_files()
                        send_message(chat_id, "Cleaned up temp files! 🧹✨")
                    elif text == "/stop":
                        if chat_id in user_processes and user_processes[chat_id]:
                            user_processes[chat_id] = False
                            send_message(chat_id, "Download stopped! ⏹️😌✨")
                        else:
                            send_message(chat_id, "No download running! 😊🤷♂️")
                    elif text.startswith("http"):
                        user_processes[chat_id] = True  # Start process
                        
                        if is_playlist(text):
                            if 'spotify.com' in text or 'music.apple.com' in text:
                                send_message(chat_id, "Oops! 😅😬 Can't download Spotify/Apple playlists!\n\nBut hey! 🎆 Send me individual track links and I'll grab them for you! 🎵✨")
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
                    else:
                        # Treat as song name search
                        if len(text.strip()) > 3:
                            user_processes[chat_id] = True  # Start process
                            send_message(chat_id, f"Searching for '{text}'... 🔍🎆✨")
                            
                            # Clear previous files
                            for f in glob.glob("*.mp3") + glob.glob("*.m4a") + glob.glob("*.webm"):
                                os.remove(f)
                            
                            # Search YouTube for the song
                            youtube_search = f"ytsearch1:{text}"
                            
                            try:
                                ydl_opts = {
                                    'format': 'bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio',
                                    'outtmpl': '%(title)s.%(ext)s',
                                    'quiet': True,
                                    'noplaylist': True,
                                }
                                
                                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                                    ydl.download([youtube_search])
                                
                                # Send the downloaded file
                                audio_files = glob.glob("*.mp3") + glob.glob("*.m4a") + glob.glob("*.webm")
                                if audio_files:
                                    file_path = audio_files[0]
                                    send_message(chat_id, "Found it! 🎉🔥 Sending your jam now... 🎵✨")
                                    
                                    if send_document(chat_id, file_path):
                                        send_message(chat_id, "There you go! 🎧🎆 Enjoy the music! 🎵")
                                    else:
                                        send_message(chat_id, "Hmm, couldn't send that. Try again? 🤷‍♂️")
                                    
                                    os.remove(file_path)
                                else:
                                    send_message(chat_id, "Couldn't find that song! 🤔😬 Try being more specific? 🎆🎵")
                                    
                            except Exception as e:
                                send_message(chat_id, "Oops, something went wrong! 😅😬 Try a different search? 🎆✨")
                            
                            user_processes[chat_id] = False  # End process
                        else:
                            send_message(chat_id, "Send me a link or song name! 🎵😊 (at least 3 letters) 😉✨")
            
            time.sleep(1)
            
        except KeyboardInterrupt:
            print("\n🛑 Bot stopped")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)
    
    # Cleanup
    for f in glob.glob("*.mp3"):
        try:
            os.remove(f)
        except:
            pass

if __name__ == "__main__":
    main()