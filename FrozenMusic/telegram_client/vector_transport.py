import aiohttp
import aiofiles
import asyncio
import os
import tempfile
import random
import string


# 🔹 Global cache
SHARD_CACHE_MATRIX = {}

# 🔹 Replace this with your deployed Piped instance URL (no cookies needed)
PIPED_API_URL = "https://piped-pv46.onrender.com/streams/"


async def vector_transport_resolver(url: str) -> str:
    """
    Resolves and downloads audio quickly using Piped API (no yt-dlp).
    """
    if os.path.exists(url) and os.path.isfile(url):
        return url

    if url in SHARD_CACHE_MATRIX:
        return SHARD_CACHE_MATRIX[url]

    try:
        # Extract video ID from YouTube link
        if "youtube.com/watch?v=" in url:
            video_id = url.split("watch?v=")[-1].split("&")[0]
        elif "youtu.be/" in url:
            video_id = url.split("youtu.be/")[-1].split("?")[0]
        else:
            raise Exception("Unsupported URL, not a valid YouTube link")

        # Query your Piped instance
        api_url = f"{PIPED_API_URL}{video_id}"
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, timeout=60) as response:
                if response.status != 200:
                    raise Exception(f"Piped API error {response.status}: {await response.text()}")
                data = await response.json()

        # Pick best audio format (fallback if missing)
        audio_streams = data.get("audioStreams", [])
        if not audio_streams:
            raise Exception("No audio streams available for this video")

        # Sort by bitrate, choose highest
        best_audio = max(audio_streams, key=lambda x: x.get("bitrate", 0))
        download_url = best_audio["url"]

        # Save to a temp file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        file_name = temp_file.name
        temp_file.close()

        async with aiohttp.ClientSession() as session:
            async with session.get(download_url, timeout=120) as resp:
                if resp.status == 200:
                    async with aiofiles.open(file_name, 'wb') as f:
                        async for chunk in resp.content.iter_chunked(131072):
                            await f.write(chunk)

                    SHARD_CACHE_MATRIX[url] = file_name
                    return file_name
                else:
                    raise Exception(f"Error fetching audio file: HTTP {resp.status}")

    except asyncio.TimeoutError:
        raise Exception("Piped API took too long to respond. Please try again.")
    except Exception as e:
        error_msg = str(e)
        if len(error_msg) > 300:
            error_msg = error_msg[:300] + "... (truncated)"
        raise Exception(f"Error downloading audio: {error_msg}")
