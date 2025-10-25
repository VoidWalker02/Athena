import discord
from discord.ext import commands
import yt_dlp as youtube_dl  # Use yt-dlp instead of youtube_dl
import asyncio
import time
import re
from collections import defaultdict, deque
import random


# Define intents
intents = discord.Intents.default()
intents.message_content = True
looping = False
current_title = None
current_duration = None
current_webpage_url = None
current_thumbnail = None
current_requester_id = None
search_results = {}
volume = 1.0
queues = defaultdict(deque)


YDL_SEARCH_OPTS = {
    "format": "bestaudio[ext=m4a]/bestaudio/best",  # prefer stable m4a over HLS
    "noplaylist": True,
    "quiet": True,
    "force_generic_extractor": False,
    "extractor_args": {"youtube": {"player_client": ["android"]}},
}



# Initialize bot
bot = commands.Bot(command_prefix="&", intents=intents)

@bot.event
async def on_ready():
    print("Salutations.")

join_locks = {}  # one lock per guild to avoid concurrent connects

def get_guild_lock(guild_id: int) -> asyncio.Lock:
    lock = join_locks.get(guild_id)
    if lock is None:
        lock = asyncio.Lock()
        join_locks[guild_id] = lock
    return lock

def _fmt_time(sec):
    if sec is None: return "Unknown"
    sec = int(max(0, sec))
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

def _headers_str(h: dict | None) -> str:
    # FFmpeg expects CRLF between headers
    if not h: return ""
    return "\r\n".join(f"{k}: {v}" for k, v in h.items())

def _clamp(x, lo, hi):
    return max(lo,min(hi,x))

def _parse_timestamp(s: str):
    """
    Accepts 'SS', 'MM:SS', or 'HH:MM:SS'. Returns total seconds (int) or None.
    """
    s = s.strip()
    if re.fullmatch(r"\d+", s):  # seconds only
        return int(s)
    parts = s.split(":")
    if not all(p.isdigit() for p in parts):
        return None
    if len(parts) == 2:  # MM:SS
        m, sec = map(int, parts)
        return m * 60 + sec
    if len(parts) == 3:  # HH:MM:SS
        h, m, sec = map(int, parts)
        return h * 3600 + m * 60 + sec
    return None

def is_playlist_link(url: str) -> bool:
    return "list=" in url or "/playlist?" in url

def extract_playlist(url: str, max_items: int = 50):
    """
    Returns a list of (webpage_url, title, duration|None) for a YouTube playlist/mix.
    Uses flat extraction for speed; duration may be None.
    """
    opts = {
        **YDL_SEARCH_OPTS,
        "noplaylist": False,                  # allow playlist extraction here
        "extract_flat": "in_playlist",       # no stream links; fast
        "quiet": True,
    }
    with youtube_dl.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    # Normalize to a list of entries
    entries = info.get("entries") or []
    out = []
    for e in entries[:max_items]:
        vid_id = e.get("id")
        title = e.get("title", "Unknown")
        duration = e.get("duration")  # often None in flat
        page_url = e.get("url") or (f"https://www.youtube.com/watch?v={vid_id}" if vid_id else None)
        if page_url:
            # Sometimes flat URLs are just video IDs; ensure full URL
            if not page_url.startswith("http"):
                page_url = f"https://www.youtube.com/watch?v={page_url}"
            out.append((page_url, title, duration))
    return out
    


async def play_next_in_queue(ctx):
    """Helper function to play next track on server's queue."""

    guild_id = ctx.guild.id
    vc = ctx.voice_client

    if not vc or not vc.is_connected():
        return
    if not queues[guild_id]:
        await ctx.send("Queue is now empty.")
        return
    next_url, next_title, requester_id, duration = queues[guild_id].popleft()
    await ctx.invoke(play, url=next_url)

@bot.command()
async def join(ctx):
    """Join the caller's VC."""
    if not ctx.author.voice or not ctx.author.voice.channel:
        return await ctx.send("You must first join a voice channel.")

    channel = ctx.author.voice.channel
    me = ctx.guild.me
    perms = channel.permissions_for(me)
    if not perms.connect:
        return await ctx.send(f"I don't have **Connect** permission for {channel.mention}.")
    if not perms.speak:
        return await ctx.send(f"I don't have **Speak** permission in {channel.mention}.")

    lock = get_guild_lock(ctx.guild.id)
    async with lock:
        vc = ctx.voice_client
        try:
            # If connected somewhere already
            if vc and vc.is_connected():
                if vc.channel.id == channel.id:
                    return await ctx.send(f"I'm already in {channel.mention}.")
                # Move within guild
                await vc.move_to(channel)
                return await ctx.send(f"Moved to {channel.mention}.")

            # Hard reset any stale connection
            if vc:
                try:
                    await vc.disconnect(force=True)
                except Exception:
                    pass
                await asyncio.sleep(0.5)

            # Fresh connect; disable session resume
            await channel.connect(timeout=10.0)
            await ctx.send(f"Joined {channel.mention}.")

        except asyncio.TimeoutError:
            await ctx.send("Timed out connecting to voice. Try again in a few seconds.")
        except discord.errors.ConnectionClosed as e:
            try:
                if ctx.voice_client:
                    await ctx.voice_client.disconnect(force=True)
            except Exception:
                pass
            await ctx.send(f"Voice gateway closed ({getattr(e, 'code', 'unknown')}). Please run `&join` again.")
        except discord.ClientException as e:
            await ctx.send(f"Couldn't join voice: {e}")
        except RuntimeError as e:
            await ctx.send(f"Voice setup error (PyNaCl/Opus?): {e}")

@bot.command()
async def leave(ctx):
    """Command to make the bot leave the voice channel."""
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
    else:
        await ctx.send("I am not currently in a voice channel.")

@bot.command()
async def pause(ctx):
    """Command to pause playback."""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("Current playback paused.")
    else:
        await ctx.send("No playback currently active.")

@bot.command()
async def resume(ctx):
    """Resume paused playback."""
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("Playback resumed.")
    else:
        await ctx.send("No playback currently active.")

@bot.command()
async def skip(ctx):
    """Skips current song."""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("Skipped current playback.")
    else:
        await ctx.send("No playback currently active.")

@bot.command()
async def loop(ctx):
    """Enable looping of current song."""
    global looping
    looping = not looping
    await ctx.send(f"Playback loop has been {'enabled' if looping else 'disabled'}.")

@bot.command()
async def nowplaying(ctx):
    """Display current track."""
    vc = ctx.voice_client
    if not vc or not (vc.is_playing() or vc.is_paused()):
        return await ctx.send("No current playback.")
    
    if not current_title:
        return await ctx.send("Please wait. No available metadata as of yet.")
    
    status = "Paused." if vc.is_paused() else "Playing."
    duration_str = _fmt_time(current_duration)

    embed = discord.Embed(
        title="Now Playing",
        description=f"[{current_title}]({current_webpage_url})" if current_webpage_url else current_title,
        color=0x5865F2,
    )
    embed.add_field(name="Status", value =status, inline=True)
    embed.add_field(name="Duration", value=duration_str, inline=True)

    if current_requester_id:
        member = ctx.guild.get_member(current_requester_id)
        if member:
            embed.add_field(name="Requested by: ", value=member.mention, inline=True)

    if current_thumbnail:
        embed.set_thumbnail(url=current_thumbnail)

    embed.set_footer(text=f"{ctx.guild.name}")

    await ctx.send(embed=embed)

@bot.command()
async def search(ctx, *, query: str):
    """Search YouTube and list the top 5 results (plain text)."""
    import yt_dlp as youtube_dl
    import asyncio

    async with ctx.typing():
        def _extract():
            opts = {**YDL_SEARCH_OPTS, "default_search": "ytsearch5"}
            with youtube_dl.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(query, download=False)
                entries = info.get("entries", []) if info else []
                return entries[:5]

        try:
            results = await asyncio.get_running_loop().run_in_executor(None, _extract)
        except Exception as e:
            return await ctx.send(f" Search failed: {e}")

    if not results:
        return await ctx.send(" No results found.")

    # cache them per (guild, user)
    out = []
    final_results = []
    for i, e in enumerate(results, start=1):
        title = e.get("title", "Unknown")
        dur = _fmt_time(e.get("duration"))
        uploader = e.get("uploader") or e.get("channel") or ""
        url = e.get("webpage_url") or e.get("url")

        final_results.append({
            "title": title,
            "duration": e.get("duration"),
            "uploader": uploader,
            "webpage_url": url,
        })

        line = f"{i}. {title} ({dur}{' • ' + uploader if uploader else ''})\n{url}"
        out.append(line)

    search_results[(ctx.guild.id, ctx.author.id)] = final_results

    msg = "\n\n".join(out)
    await ctx.send(f"**Search results for:** {query}\nUse `&pick 1-5` to choose:\n```{msg}```")


@bot.command()
async def pick(ctx, index: int):
    """Picks a result from your last search and plays it."""
    key = (ctx.guild.id, ctx.author.id)
    results = search_results.get(key)

    if not results:
        return await ctx.send("You have no recernt searches. Please run '&search <query> first.'")
    
    max_idx = min(5,len(results))
    if not (1<= index <= max_idx):
        return await ctx.send(f"Please input a number between 1 and {max_idx}.")

    choice = results[index-1]
    title = choice.get("title", "Unknown")
    url = choice.get("webpage_url") or choice.get("url")

    if not url:
        return await ctx.send("Could not locate usable URL for that result, apologies.")

    await ctx.send(f"You picked **{index}.**\n{url}")

    #feed it to the play command
    try:
        await ctx.invoke(play, url=url)
    except Exception as e:
        await ctx.send(f"Failed to play **{title}**: {e}")

@bot.command()
async def vol(ctx, percent: int | None = None):
    """Get/Set global volume for the bot. Volume values go from 0 - 200. """

    global volume

    if percent is None:
        cur = int(round(volume * 100))
        return await ctx.send(f"Current volume: **{cur}%**")

    try:
        p = int(percent)
    except ValueError:
        return await ctx.send("Please enter a whole number between 0 and 200.")

    p = _clamp(percent, 0, 200)
    volume = p / 100.0

    #adjust volume live if playing

    vc = ctx.voice_client 
    if vc and vc.source:
        try:
            if isinstance(vc.source, discord.PCMVolumeTransformer):
                vc.source.volume = volume
            else:
                vc.source = discord.PCMVolumeTransformer(vc.source, volume=volume)
        except Exception:
            pass

        await ctx.send(f"Volume has been set to **{p}%**")

@bot.command()
async def seek(ctx, position: str):
    """Jump to a timestamp in the current track. Accepts seconds, m:s and h:m:s """
    vc = ctx.voice_client
    if not vc or not (vc.is_playing() or vc.is_paused()):
        return await ctx.send(" Nothing is playing.")

    # parse time
    seconds = _parse_timestamp(position)
    if seconds is None or seconds < 0:
        return await ctx.send(" Time must be SS, MM:SS, or HH:MM:SS.")

    # we need to know what to re-extract (page URL). If missing, bail nicely.
    if not current_webpage_url:
        return await ctx.send("I don't have the source URL for this track. Try playing it again, then seek.")

    # re-extract a fresh direct audio URL (avoids expired links)
    try:
        with youtube_dl.YoutubeDL(YDL_SEARCH_OPTS) as ydl:
            info = ydl.extract_info(current_webpage_url, download=False)
            stream_url = info["url"]
    except Exception as e:
        return await ctx.send(f"Couldn't refresh the stream: {e}")

    # restart FFmpeg from the desired offset
    try:
        before = f"-ss {seconds} -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
        ffmpeg_opts = "-vn"
        vc.stop()
        vc.play(
            discord.FFmpegPCMAudio(stream_url, before_options=before, options=ffmpeg_opts),
            after=lambda e: print(f"[seek] ffmpeg error: {e}") if e else None
        )
        await ctx.send(f"Seeked to **{position}**.")
    except Exception as e:
        await ctx.send(f"Seek failed: {e}")


@bot.command()
async def queue(ctx):
    """Displays the current queue."""

    q = queues[ctx.guild.id]
    if not q:
        return await ctx.send("The queue is currently empty.")

   # Format each queued song like search results
    out = []
    for i, (url, title, requester_id, duration) in enumerate(q, start=1):
        member = ctx.guild.get_member(requester_id)
        requester = f" • {member.display_name}" if member else ""
        dur_str = _fmt_time(duration) if duration else "Unknown"
        line = f"{i}. {title or 'Unknown'} ({dur_str}{requester})\n{url}"
        out.append(line)

    msg = "\n\n".join(out)
    await ctx.send(f"**Current Queue ({len(q)} tracks):**\n```{msg}```")

       
    
@bot.command()
async def clear(ctx):
    """Clear the current queue."""
    queues[ctx.guild.id].clear()
    await ctx.send("Queue cleared.")

@bot.command()
async def shuffle(ctx):
    q = queues[ctx.guild.id]
    if not q:
        return await ctx.send("Queue is empty.")
    tmp = list(q)
    random.shuffle(tmp)
    queues[ctx.guild.id] = deque(tmp)
    await ctx.send("Queue shuffled.")

@bot.command()
async def skipto(ctx, index: int):
    """Skip to a specific song in the queue (1 = next up)."""
    q = queues[ctx.guild.id]
    if not q:
        return await ctx.send("Queue is empty.")

    n = len(q)
    if index < 1 or index > n:
        return await ctx.send(f"Index must be between 1 and {n}.")

    # Peek target title for feedback (queue stores 4-tuples)
    target_url, target_title, _, _ = list(q)[index - 1]

    # Drop items before the chosen index so it becomes the head
    for _ in range(index - 1):
        q.popleft()

    await ctx.send(f"Skipping to **{target_title or 'Unknown'}** (#{index}).")

    vc = ctx.voice_client
    if vc and (vc.is_playing() or vc.is_paused()):
        # Just stop; your play()'s after() will advance to the new head.
        vc.stop()
    else:
        # Nothing playing; start the new head immediately.
        await play_next_in_queue(ctx)


@bot.command()
async def move(ctx, old: int, new: int):
    """Move a track to a different position in the queue."""
    q = queues[ctx.guild.id]
    if not q:
        return await ctx.send("Queue is empty.")
    if not (1 <= old <= len(q) and 1 <= new <= len(q)):
        return await ctx.send(f"Indexes must be between 1 and {len(q)}.")
    item = q[old-1]
    del q[old-1]
    q.insert(new-1, item)
    await ctx.send(f"Moved **{item[1]}** to position {new}.")

@bot.command()
async def playlist(ctx, url: str, limit: int = 50):
    """Enqueue a Youtube Playlist, standard limit is 50, goes up to 200. """

    if limit < 1 or limit > 200:
        return await ctx.send("Limit must be between 1 and 200.")
    
    if not is_playlist_link(url):
        return await ctx.send("This does not appear to be a playlist link. Please use the regular play command.")

    await ctx.send("Loading playlist, this may take a moment.")

    try:
        entries = extract_playlist(url, max_items=limit)
    except Exception as e:
        return await ctx.send("No playable entries located.")

    q = queues[ctx.guild.id]
    added = 0
    for page_url, title, duration in entries:
        q.append((page_url,title,ctx.author.id,duration))
        added += 1

    #if nothing is playing, start playback

    vc = ctx.voice_client
    if not vc:
        await ctx.invoke(join)
        vc = ctx.voice_client
    if vc and not (vc.is_playing() or vc.is_paused()):
        await play_next_in_queue(ctx)

    # Nice summary (first few items)
    preview = "\n".join(f"{i+1}. {entries[i][1]}" for i in range(min(5, len(entries))))
    more = f"\n… and {len(entries)-5} more." if len(entries) > 5 else ""
    await ctx.send(f"Added **{added}** tracks to the queue.\n```{preview}{more}```") 






@bot.command()
async def play(ctx, url: str):
    """Command to play audio from a YouTube URL."""
    global looping, current_url
    global current_title, current_duration, current_webpage_url, current_thumbnail, current_requester_id

    vc = ctx.voice_client
    if vc and (vc.is_playing() or vc.is_paused()):
        try:
            # extract metadata for a single video
            with youtube_dl.YoutubeDL(YDL_SEARCH_OPTS) as ydl:
                info = ydl.extract_info(url, download=False)
            link = info.get("webpage_url") or url
            title = info.get("title", "Unknown")
            duration = info.get("duration")
            queues[ctx.guild.id].append((link, title, ctx.author.id, duration))
            await ctx.send(f"Added **{title}** to the queue.")
        except Exception as e:
            await ctx.send(f"Failed to queue track: {e}")
        return

    if not ctx.voice_client:
        await ctx.invoke(join)  # join first

    # --- extract once for initial play ---
    with youtube_dl.YoutubeDL(YDL_SEARCH_OPTS) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            stream_url = info["url"]
            headers = info.get("http_headers") or {}
        except Exception as e:
            await ctx.send(f"Error extracting audio: {e}")
            return

    # --- store metadata for nowplaying/seek ---
    current_url = info.get("webpage_url") or url
    current_title = info.get("title", "Unknown")
    current_duration = info.get("duration")
    current_webpage_url = current_url
    current_thumbnail = info.get("thumbnail") or (info.get("thumbnails") or [{}])[-1].get("url")
    current_requester_id = ctx.author.id

    # --- ffmpeg options (headers + reconnect) ---
    headers_blob = _headers_str(headers)
    before = (
        (f'-headers "{headers_blob}" ' if headers_blob else "")
        + "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 "
        + '-user_agent "Mozilla/5.0"'
    )
    opts = "-vn -err_detect ignore_err"

    vc = ctx.voice_client

    async def _loop_restart():
        """Re-extract & restart the current track for loop."""
        # If we lost VC, bail quietly
        if not vc or not vc.is_connected():
            return
        try:
            with youtube_dl.YoutubeDL(YDL_SEARCH_OPTS) as y2:
                i2 = y2.extract_info(current_webpage_url, download=False)
                s2 = i2["url"]
                h2 = i2.get("http_headers") or {}
            hb2 = _headers_str(h2)
            bef2 = (
                (f'-headers "{hb2}" ' if hb2 else "")
                + "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 "
                + '-user_agent "Mozilla/5.0"'
            )
            vc.stop()
            base2 = discord.FFmpegPCMAudio(s2, before_options=bef2, options=opts)
            src2 = discord.PCMVolumeTransformer(base2, volume=volume)
            vc.play(src2, after=make_after())
        except Exception as ee:
            print("Loop re-extract/play failed:", ee)

    def make_after():
        def _after(error: Exception | None):
            if error:
                print(f"FFmpeg after() error: {error}")
            elif looping and current_webpage_url:
                ctx.bot.loop.create_task(_loop_restart())
            else:
                # when finished, advance the queue
                ctx.bot.loop.create_task(play_next_in_queue(ctx))
        return _after

    # start playback
    vc.stop()
    base_source = discord.FFmpegPCMAudio(stream_url,before_options=before, options =opts)
    source = discord.PCMVolumeTransformer(base_source,volume=volume)
    vc.play(source, after=make_after())

    await ctx.send(f"Now playing: {current_title}")

bot.run("INSERT_YOUR_TOKEN_HERE")

