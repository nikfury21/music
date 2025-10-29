import aiofiles
import asyncio
import os
import tempfile
import random
import string
import requests
import aiohttp

# 🔹 Global cache
SHARD_CACHE_MATRIX = {}

# 🔹 Get your YouTube Data API key safely from environment variables
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# 🔹 Your deployed proxy (change to your own Render URL)
AUDIO_PROXY_URL = "https://ytproxy-x9hd.onrender.com/audio"  # ✅ your working Render URL


async def youtube_search(query: str):
    """
    Search YouTube using the official YouTube Data API v3.
    Returns a dict with 'items' key to stay compatible with old bot code.
    """
    if not YOUTUBE_API_KEY:
        raise Exception("Missing YOUTUBE_API_KEY in environment variables")

    url = (
        "https://www.googleapis.com/youtube/v3/search"
        f"?part=snippet&type=video&maxResults=10&type=video"
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

    return {"items": items}


async def vector_transport_resolver(url: str) -> str:
    """
    Downloads audio via your deployed yt-dlp proxy API (no cookies, no login needed).
    """
    if os.path.exists(url) and os.path.isfile(url):
        return url

    if url in SHARD_CACHE_MATRIX:
        return SHARD_CACHE_MATRIX[url]

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    file_path = temp_file.name
    temp_file.close()

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{AUDIO_PROXY_URL}?url={url}", timeout=120) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise Exception(f"Proxy returned {resp.status}: {text}")

                async with aiofiles.open(file_path, "wb") as f:
                    async for chunk in resp.content.iter_chunked(131072):
                        await f.write(chunk)

        SHARD_CACHE_MATRIX[url] = file_path
        return file_path

    except Exception as e:
        raise Exception(f"Audio proxy error: {e}")
