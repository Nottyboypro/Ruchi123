import asyncio, httpx, os, re, yt_dlp
import aiofiles
import aiohttp

from typing import Union
from pyrogram.types import Message
from pyrogram.enums import MessageEntityType
from youtubesearchpython.__future__ import VideosSearch


def time_to_seconds(time):
    stringt = str(time)
    return sum(int(x) * 60**i for i, x in enumerate(reversed(stringt.split(":"))))


async def shell_cmd(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, errorz = await proc.communicate()
    if errorz:
        if "unavailable videos are hidden" in (errorz.decode("utf-8")).lower():
            return out.decode("utf-8")
        else:
            return errorz.decode("utf-8")
    return out.decode("utf-8")

async def get_stream_url(query, video=False):
    """
    ⚡ Ultra-Fast YouTube Downloader + Instant Streaming
    - Starts streaming after 10% download
    - Continues downloading in background
    - Caches for future instant playback
    - High bitrate audio/video
    """

    api_base = "https://nottyapi-254bfd1a99f5.herokuapp.com"
    api_key = "-2bm4EVA2XrRtOkOLA1xENfVCjoHlLvoGYNuuqTTBlY"
    endpoint = "/ytmp4" if video else "/ytmp3"
    api_url = f"{api_base}{endpoint}"

    os.makedirs("downloads", exist_ok=True)
    filename_safe = query.replace("/", "_").replace(":", "_")
    ext = ".mp4" if video else ".mp3"
    local_path = os.path.join("downloads", filename_safe + ext)
    temp_path = local_path + ".part"  # temporary partial file

    # 🔹 If cached, return immediately
    if os.path.exists(local_path) and os.path.getsize(local_path) > 1024:
        print(f"🧠 Cached file found: {local_path}")
        asyncio.create_task(
            httpx.AsyncClient(timeout=10).get(api_url, params={"url": query, "api_key": api_key})
        )
        return local_path

    try:
        # 🔹 Step 1: Get file URL
        async with httpx.AsyncClient(timeout=40) as client:
            response = await client.get(api_url, params={"url": query, "api_key": api_key})
            if response.status_code != 200:
                print(f"❌ API Error: {response.status_code}")
                return None
            data = response.json()
            if not (data.get("status") == "success" and data.get("url")):
                print(f"⚠️ Invalid API response: {data}")
                return None

            file_url = data["url"]
            print(f"🎧 Streaming from: {file_url}")

        # 🔹 Step 2: Stream-as-you-download
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url, timeout=aiohttp.ClientTimeout(total=None)) as resp:
                if resp.status != 200:
                    print(f"❌ Download failed: HTTP {resp.status}")
                    return None

                total = resp.content_length or 0
                chunk_size = 256 * 1024  # 256 KB for faster speed
                downloaded = 0
                started_stream = False

                async with aiofiles.open(temp_path, "wb") as f:
                    async for chunk in resp.content.iter_chunked(chunk_size):
                        await f.write(chunk)
                        downloaded += len(chunk)

                        # Start stream once 10% is ready
                        if not started_stream and total > 0 and downloaded >= total * 0.1:
                            started_stream = True
                            print("🎶 10% ready — starting stream instantly!")
                            # Return early to start VC stream, background continues
                            asyncio.create_task(_finish_download(resp, f, local_path, temp_path))
                            return temp_path

                # Completed fully (if total < 10MB or finished before trigger)
                await f.flush()
                os.replace(temp_path, local_path)
                print(f"✅ Download complete: {local_path}")
                return local_path

    except Exception as e:
        print(f"💥 Error: {e}")
        return None


async def _finish_download(resp, file_obj, final_path, temp_path):
    """
    Continue downloading remaining chunks in background
    after streaming has already started.
    """
    try:
        async for chunk in resp.content.iter_chunked(256 * 1024):
            await file_obj.write(chunk)
        await file_obj.flush()
        await file_obj.close()
        os.replace(temp_path, final_path)
        print(f"✅ Background download finished: {final_path}")
    except Exception as e:
        print(f"⚠️ Background download failed: {e}")


class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.status = "https://www.youtube.com/oembed?url="
        self.listbase = "https://youtube.com/playlist?list="
        self.reg = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    async def exists(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if re.search(self.regex, link):
            return True
        else:
            return False

    async def url(self, message_1: Message) -> Union[str, None]:
        messages = [message_1]
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)
        text = ""
        offset = None
        length = None
        for message in messages:
            if offset:
                break
            if message.entities:
                for entity in message.entities:
                    if entity.type == MessageEntityType.URL:
                        text = message.text or message.caption
                        offset, length = entity.offset, entity.length
                        break
            elif message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == MessageEntityType.TEXT_LINK:
                        return entity.url
        if offset in (None,):
            return None
        return text[offset : offset + length]

    async def details(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
            duration_min = result["duration"]
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
            vidid = result["id"]
            if str(duration_min) == "None":
                duration_sec = 0
            else:
                duration_sec = int(time_to_seconds(duration_min))
        return title, duration_min, duration_sec, thumbnail, vidid

    async def title(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
        return title

    async def duration(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            duration = result["duration"]
        return duration

    async def thumbnail(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
        return thumbnail

    async def video(self, link: str, videoid: Union[bool, str] = None):
        """
        Updated to use our integrated API for video streaming
        """
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
            
        return await get_stream_url(link, True)
        
    async def audio(self, link: str, videoid: Union[bool, str] = None):
        """
        New method to get audio stream URL using our integrated API
        """
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
            
        return await get_stream_url(link, False)

    async def playlist(self, link, limit, user_id, videoid: Union[bool, str] = None):
        if videoid:
            link = self.listbase + link
        if "&" in link:
            link = link.split("&")[0]
        playlist = await shell_cmd(
            f"yt-dlp -i --get-id --flat-playlist --playlist-end {limit} --skip-download {link}"
        )
        try:
            result = playlist.split("\n")
            for key in result:
                if key == "":
                    result.remove(key)
        except:
            result = []
        return result

    async def track(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
            duration_min = result["duration"]
            vidid = result["id"]
            yturl = result["link"]
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
        track_details = {
            "title": title,
            "link": yturl,
            "vidid": vidid,
            "duration_min": duration_min,
            "thumb": thumbnail,
        }
        return track_details, vidid

    async def formats(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        ytdl_opts = {"quiet": True}
        ydl = yt_dlp.YoutubeDL(ytdl_opts)
        with ydl:
            formats_available = []
            r = ydl.extract_info(link, download=False)
            for format in r["formats"]:
                try:
                    str(format["format"])
                except:
                    continue
                if not "dash" in str(format["format"]).lower():
                    try:
                        format["format"]
                        format["filesize"]
                        format["format_id"]
                        format["ext"]
                        format["format_note"]
                    except:
                        continue
                    formats_available.append(
                        {
                            "format": format["format"],
                            "filesize": format["filesize"],
                            "format_id": format["format_id"],
                            "ext": format["ext"],
                            "format_note": format["format_note"],
                            "yturl": link,
                        }
                    )
        return formats_available, link

    async def slider(
        self,
        link: str,
        query_type: int,
        videoid: Union[bool, str] = None,
    ):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        a = VideosSearch(link, limit=10)
        result = (await a.next()).get("result")
        title = result[query_type]["title"]
        duration_min = result[query_type]["duration"]
        vidid = result[query_type]["id"]
        thumbnail = result[query_type]["thumbnails"][0]["url"].split("?")[0]
        return title, duration_min, thumbnail, vidid

    async def download(
        self,
        link: str,
        mystic,
        video: Union[bool, str] = None,
        videoid: Union[bool, str] = None,
        songaudio: Union[bool, str] = None,
        songvideo: Union[bool, str] = None,
        format_id: Union[bool, str] = None,
        title: Union[bool, str] = None,
    ) -> str:
        """
        Updated download method to use our integrated API instead of yt-dlp
        """
        if videoid:
            link = self.base + link
            
        # For simple audio/video downloads, use our API
        if video and not songvideo:
            downloaded_file = await get_stream_url(link, True)
            return downloaded_file, None
        elif not video and not songaudio:
            downloaded_file = await get_stream_url(link, False)
            return downloaded_file, None
        
        # For specific format downloads, fall back to original yt-dlp method
        loop = asyncio.get_running_loop()

        def audio_dl():
            ydl_optssx = {
                "format": "bestaudio/best",
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
            }
            x = yt_dlp.YoutubeDL(ydl_optssx)
            info = x.extract_info(link, False)
            xyz = os.path.join("downloads", f"{info['id']}.{info['ext']}")
            if os.path.exists(xyz):
                return xyz
            x.download([link])
            return xyz

        def video_dl():
            ydl_optssx = {
                "format": "(bestvideo[height<=?720][width<=?1280][ext=mp4])+(bestaudio[ext=m4a])",
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
            }
            x = yt_dlp.YoutubeDL(ydl_optssx)
            info = x.extract_info(link, False)
            xyz = os.path.join("downloads", f"{info['id']}.{info['ext']}")
            if os.path.exists(xyz):
                return xyz
            x.download([link])
            return xyz

        def song_video_dl():
            formats = f"{format_id}+140"
            fpath = f"downloads/{title}"
            ydl_optssx = {
                "format": formats,
                "outtmpl": fpath,
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
                "prefer_ffmpeg": True,
                "merge_output_format": "mp4",
            }
            x = yt_dlp.YoutubeDL(ydl_optssx)
            x.download([link])

        def song_audio_dl():
            fpath = f"downloads/{title}.%(ext)s"
            ydl_optssx = {
                "format": format_id,
                "outtmpl": fpath,
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
                "prefer_ffmpeg": True,
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
            }
            x = yt_dlp.YoutubeDL(ydl_optssx)
            x.download([link])

        if songvideo:
            await loop.run_in_executor(None, song_video_dl)
            fpath = f"downloads/{title}.mp4"
            return fpath
        elif songaudio:
            await loop.run_in_executor(None, song_audio_dl)
            fpath = f"downloads/{title}.mp3"
            return fpath
        elif video:
            downloaded_file = await loop.run_in_executor(None, video_dl)
            direct = None
        else:
            downloaded_file = await loop.run_in_executor(None, audio_dl)
            direct = None
        return downloaded_file, direct
