"""
Jarvis OS — YouTube Tools.

Provides 4 tools for YouTube Data API v3 interaction.
Transcript extraction uses the youtube-transcript-api library (fallback to captions API).
"""

import re

from jarvis.database.core import AsyncSessionLocal
from jarvis.integrations.google_client import GoogleClient, get_google_account
from jarvis.tools.base import Tool, ToolCategory, ToolMetadata, ToolParameter, ToolResult

YOUTUBE_BASE = "https://www.googleapis.com/youtube/v3"


async def _get_client_and_account(account_email=None):
    db = AsyncSessionLocal()
    account = await get_google_account(db, account_email=account_email)
    if not account:
        await db.close()
        return None, None, None
    client = GoogleClient(db, account)
    return db, account, client


def _extract_video_id(video_id_or_url: str) -> str:
    """Extract video ID from a URL or return as-is if already an ID."""
    if "youtube.com" in video_id_or_url or "youtu.be" in video_id_or_url:
        # Try standard URL
        match = re.search(r'(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})', video_id_or_url)
        if match:
            return match.group(1)
    return video_id_or_url


def _format_duration(iso_duration: str) -> str:
    """Convert ISO 8601 duration (PT1H2M3S) to human-readable."""
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', iso_duration)
    if not match:
        return iso_duration
    hours, minutes, seconds = match.groups(default="0")
    parts = []
    if int(hours) > 0:
        parts.append(f"{hours}h")
    if int(minutes) > 0:
        parts.append(f"{minutes}m")
    if int(seconds) > 0:
        parts.append(f"{seconds}s")
    return " ".join(parts) or "0s"


class YouTubeSearchTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="youtube_search",
            description="Search YouTube for videos by query. Returns video titles, URLs, channels, and descriptions.",
            category=ToolCategory.RESEARCH,
            dangerous=False,
            parameters=[
                ToolParameter(name="query", type="string", description="Search query"),
                ToolParameter(name="max_results", type="integer", description="Max results (1-25)", required=False, default=5),
                ToolParameter(name="order", type="string", description="Sort order: 'relevance', 'date', 'viewCount', 'rating'", required=False, default="relevance"),
                ToolParameter(name="account_email", type="string", description="Specific Google account to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "")
        max_results = min(int(kwargs.get("max_results", 5)), 25)
        order = kwargs.get("order", "relevance")
        account_email = kwargs.get("account_email")

        db, _, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        try:
            async with client:
                resp = await client.get(
                    f"{YOUTUBE_BASE}/search",
                    params={
                        "part": "snippet",
                        "q": query,
                        "type": "video",
                        "maxResults": max_results,
                        "order": order,
                    },
                )
                if resp.status_code != 200:
                    return ToolResult(success=False, error=f"YouTube API error: {resp.status_code} — {resp.text}")

                items = resp.json().get("items", [])
                if not items:
                    return ToolResult(success=True, output=f"No videos found for '{query}'.")

                output = f"🎬 **YouTube results for '{query}':**\n\n"
                results = []
                for i, item in enumerate(items, 1):
                    snippet = item.get("snippet", {})
                    video_id = item.get("id", {}).get("videoId", "")
                    title = snippet.get("title", "(no title)")
                    channel = snippet.get("channelTitle", "")
                    description = snippet.get("description", "")[:150]
                    published = snippet.get("publishedAt", "")[:10]

                    output += (
                        f"{i}. **{title}**\n"
                        f"   🎥 {channel} · {published}\n"
                        f"   🔗 https://www.youtube.com/watch?v={video_id}\n"
                        f"   {description}...\n\n"
                    )
                    results.append({"video_id": video_id, "title": title, "channel": channel})

                return ToolResult(success=True, output=output, metadata={"results": results})
        finally:
            await db.close()


class YouTubeGetVideoInfoTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="youtube_get_video_info",
            description="Get detailed information about a YouTube video (title, description, duration, views, likes, channel).",
            category=ToolCategory.RESEARCH,
            dangerous=False,
            parameters=[
                ToolParameter(name="video_id", type="string", description="YouTube video ID or URL"),
                ToolParameter(name="account_email", type="string", description="Specific Google account to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        video_id = _extract_video_id(kwargs.get("video_id", ""))
        if not video_id:
            return ToolResult(success=False, error="video_id is required")

        account_email = kwargs.get("account_email")
        db, _, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        try:
            async with client:
                resp = await client.get(
                    f"{YOUTUBE_BASE}/videos",
                    params={"part": "snippet,contentDetails,statistics", "id": video_id},
                )
                if resp.status_code != 200:
                    return ToolResult(success=False, error=f"YouTube API error: {resp.status_code}")

                items = resp.json().get("items", [])
                if not items:
                    return ToolResult(success=False, error=f"Video '{video_id}' not found.")

                video = items[0]
                snippet = video.get("snippet", {})
                stats = video.get("statistics", {})
                details = video.get("contentDetails", {})

                duration = _format_duration(details.get("duration", ""))
                views = int(stats.get("viewCount", 0))
                likes = int(stats.get("likeCount", 0))

                output = (
                    f"🎬 **{snippet.get('title', '')}**\n\n"
                    f"🎥 Channel: {snippet.get('channelTitle', '')}\n"
                    f"⏱️ Duration: {duration}\n"
                    f"👀 Views: {views:,}\n"
                    f"👍 Likes: {likes:,}\n"
                    f"📅 Published: {snippet.get('publishedAt', '')[:10]}\n"
                    f"🔗 https://www.youtube.com/watch?v={video_id}\n\n"
                    f"**Description:**\n{snippet.get('description', '')[:2000]}"
                )

                return ToolResult(success=True, output=output, metadata=video)
        finally:
            await db.close()


class YouTubeGetTranscriptTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="youtube_get_transcript",
            description=(
                "Get the transcript/captions of a YouTube video. "
                "Uses the youtube-transcript-api library for auto-generated and manual captions."
            ),
            category=ToolCategory.RESEARCH,
            dangerous=False,
            parameters=[
                ToolParameter(name="video_id", type="string", description="YouTube video ID or URL"),
                ToolParameter(name="language", type="string", description="Language code (e.g., 'en', 'es')", required=False, default="en"),
                ToolParameter(name="account_email", type="string", description="Specific Google account to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        video_id = _extract_video_id(kwargs.get("video_id", ""))
        if not video_id:
            return ToolResult(success=False, error="video_id is required")

        language = kwargs.get("language", "en")

        try:
            from youtube_transcript_api import YouTubeTranscriptApi

            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=[language])

            # Format transcript
            full_text = ""
            for entry in transcript_list:
                timestamp = int(entry.get("start", 0))
                minutes = timestamp // 60
                seconds = timestamp % 60
                text = entry.get("text", "")
                full_text += f"[{minutes:02d}:{seconds:02d}] {text}\n"

            if len(full_text) > 15000:
                full_text = full_text[:15000] + "\n\n... (transcript truncated)"

            return ToolResult(
                success=True,
                output=f"📝 **Transcript for video {video_id}:**\n\n{full_text}",
                metadata={"video_id": video_id, "segments": len(transcript_list)},
            )

        except ImportError:
            return ToolResult(
                success=False,
                error="youtube-transcript-api is not installed. Run: pip install youtube-transcript-api",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Could not fetch transcript: {str(e)}. The video may not have captions available.",
            )


class YouTubeListPlaylistsTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="youtube_list_playlists",
            description="List the authenticated user's YouTube playlists.",
            category=ToolCategory.RESEARCH,
            dangerous=False,
            parameters=[
                ToolParameter(name="max_results", type="integer", description="Max results (1-25)", required=False, default=10),
                ToolParameter(name="account_email", type="string", description="Specific Google account to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        max_results = min(int(kwargs.get("max_results", 10)), 25)
        account_email = kwargs.get("account_email")

        db, _, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        try:
            async with client:
                resp = await client.get(
                    f"{YOUTUBE_BASE}/playlists",
                    params={"part": "snippet,contentDetails", "mine": "true", "maxResults": max_results},
                )
                if resp.status_code != 200:
                    return ToolResult(success=False, error=f"YouTube API error: {resp.status_code}")

                items = resp.json().get("items", [])
                if not items:
                    return ToolResult(success=True, output="No playlists found.")

                output = f"🎵 **Your Playlists ({len(items)}):**\n\n"
                for i, item in enumerate(items, 1):
                    snippet = item.get("snippet", {})
                    count = item.get("contentDetails", {}).get("itemCount", 0)
                    output += (
                        f"{i}. **{snippet.get('title', '')}** ({count} videos)\n"
                        f"   {snippet.get('description', '')[:100]}\n"
                        f"   ID: `{item['id']}`\n\n"
                    )

                return ToolResult(success=True, output=output, metadata={"playlists": items})
        finally:
            await db.close()
