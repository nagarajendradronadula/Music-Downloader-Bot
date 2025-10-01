# 🎵 Music Downloader Telegram Bot

A user-friendly Telegram bot that downloads music from major platforms with enhanced support for YouTube, Spotify, and Apple Music.

## ✨ Features
- **Multi-Platform Support**: YouTube, Spotify, Apple Music, SoundCloud
- **Smart Detection**: Automatically detects single tracks vs playlists
- **High Quality**: Downloads in MP3 format (192kbps)
- **User-Friendly**: Real-time status updates and clear error messages
- **Batch Download**: Playlists are zipped for easy download

## 🚀 How to Run This Project

### Prerequisites
- Python 3.8 or higher
- Telegram Bot Token (from @BotFather)
- FFmpeg installed

### Step 1: Clone and Setup
```bash
git clone <repository-url>
cd "Music Downloader"
```

### Step 2: Create Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Install FFmpeg
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

### Step 5: Configure Environment
1. Copy `.env` file and add your bot token:
```bash
cp .env .env.local
```
2. Edit `.env.local` and replace `your_bot_token_here` with your actual bot token

### Step 6: Run the Bot
```bash
# For direct bot (recommended for local development)
python direct_bot.py

# For lambda deployment
python lambda_bot.py
```

### Getting a Bot Token
1. Message @BotFather on Telegram
2. Send `/newbot`
3. Follow instructions to create your bot
4. Copy the token to your `.env.local` file

## 📱 Usage

1. Start the bot with `/start`
2. Send any music link from supported platforms
3. **Single Track** → Sent as audio file
4. **Playlist/Album** → Sent as ZIP file

## 🎯 Supported Platforms

| Platform | Single Tracks | Playlists | Status |
|----------|---------------|-----------|---------|
| 🔴 YouTube | ✅ | ✅ | Full Support |
| 🟢 Spotify | ✅ | ✅ | Full Support |
| 🍎 Apple Music | ✅ | ✅ | Full Support |
| 🟠 SoundCloud | ✅ | ✅ | Full Support |

## 🛠️ Technical Details

- **Audio Format**: MP3 (192kbps)
- **File Naming**: Artist - Title.mp3
- **Playlist Limit**: No artificial limits
- **Error Handling**: Comprehensive error messages
- **Platform Detection**: Automatic URL analysis

## 📋 Commands

- `/start` - Welcome message and instructions
- `/help` - Detailed usage guide
- Send any music URL - Download music

## 🔧 Troubleshooting

**Common Issues:**
- Ensure FFmpeg is installed for audio conversion
- Check internet connection for downloads
- Verify the music link is publicly accessible
- Some region-locked content may not be available

**Error Messages:**
- The bot provides clear error messages for failed downloads
- Platform-specific error handling for better user experience