import aiofiles
import asyncio
import os
import tempfile
import random
import string
import requests
from yt_dlp import YoutubeDL

# 🔹 Global cache
SHARD_CACHE_MATRIX = {}

# 🔹 Get your YouTube Data API key safely from environment variables
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")


async def youtube_search(query: str):
    """
    Search YouTube using the official YouTube Data API v3.
    Returns a dict with 'items' key to stay compatible with old bot code.
    """
    if not YOUTUBE_API_KEY:
        raise Exception("Missing YOUTUBE_API_KEY in environment variables")

    url = (
        "https://www.googleapis.com/youtube/v3/search"
        f"?part=snippet&type=video&maxResults=10"
        f"&q={query}&key={YOUTUBE_API_KEY}"
    )

    data = requests.get(url, timeout=10).json()
    items = []
    for item in data.get("items", []):
        vid = item["id"]["videoId"]
        title = item["snippet"]["title"]
        thumb = item["snippet"]["thumbnails"]["high"]["url"]
        items.append({
            "videoId": vid,
            "title": title,
            "link": f"https://www.youtube.com/watch?v={vid}",
            "thumbnail": thumb,
        })

    # 🔹 Wrap inside a dict for backward compatibility
    return {"items": items}



async def vector_transport_resolver(url: str) -> str:
    """
    Resolves and downloads audio directly from YouTube using yt-dlp (fast + reliable).
    """
    if os.path.exists(url) and os.path.isfile(url):
        return url

    if url in SHARD_CACHE_MATRIX:
        return SHARD_CACHE_MATRIX[url]

    try:
        # Extract YouTube video ID
        if "youtube.com/watch?v=" in url:
            video_id = url.split("watch?v=")[-1].split("&")[0]
        elif "youtu.be/" in url:
            video_id = url.split("youtu.be/")[-1].split("?")[0]
        else:
            raise Exception("Unsupported URL, not a valid YouTube link")

        # Prepare output path
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        file_name = temp_file.name
        temp_file.close()

        # yt-dlp options
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": file_name,
            "quiet": True,
            "noplaylist": True,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
        }

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: YoutubeDL(ydl_opts).download([url]))

        if not os.path.exists(file_name):
            raise Exception("yt-dlp failed to download audio")

        SHARD_CACHE_MATRIX[url] = file_name
        return file_name

    except Exception as e:
        raise Exception(f"Error downloading audio: {e}")
