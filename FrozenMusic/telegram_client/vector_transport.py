import aiofiles
import asyncio
import os
import tempfile
import requests
import aiohttp

# 🔹 Global cache
SHARD_CACHE_MATRIX = {}

# 🔹 Get your YouTube Data API key safely from environment variables
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# 🔹 Your deployed ytproxy (change this to your own Render URL)
AUDIO_PROXY_URL = os.getenv("AUDIO_PROXY_URL", "https://ytproxy-x9hd.onrender.com/audio")


async def youtube_search(query: str):
    """
    Search YouTube using the official YouTube Data API v3.
    Returns results compatible with your bot.
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

    return {"items": items}


async def vector_transport_resolver(url: str) -> str:
    """
    Fetches and caches the audio file for a YouTube URL using your deployed proxy.
    """
    # 1️⃣ If the path is already a local file
    if os.path.exists(url) and os.path.isfile(url):
        return url

    # 2️⃣ Cached version
    if url in SHARD_CACHE_MATRIX:
        return SHARD_CACHE_MATRIX[url]

    # 3️⃣ Prepare temp file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    file_path = temp_file.name
    temp_file.close()

    try:
        async with aiohttp.ClientSession() as session:
            proxy_url = f"{AUDIO_PROXY_URL}?url={url}"
            async with session.get(proxy_url, timeout=180) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise Exception(f"Proxy returned {resp.status}: {error_text}")

                async with aiofiles.open(file_path, "wb") as f:
                    async for chunk in resp.content.iter_chunked(131072):
                        await f.write(chunk)

        # Save in cache
        SHARD_CACHE_MATRIX[url] = file_path
        return file_path

    except asyncio.TimeoutError:
        raise Exception("Proxy request timed out.")
    except Exception as e:
        raise Exception(f"Audio proxy error: {e}")
