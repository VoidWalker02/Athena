import discord
from discord.ext import commands
import yt_dlp as youtube_dl  # Use yt-dlp instead of youtube_dl
import asyncio
import time

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

YDL_SEARCH_OPTS = {
    "format": "bestaudio[ext=m4a]/bestaudio/best",  # prefer stable m4a over HLS
    "noplaylist": True,
    "quiet": True,
    "force_generic_extractor": False,
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
            await channel.connect(timeout=10.0, reconnect=False)
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
        return await ctx.send("🔎 No results found.")

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
        return await ctx.send("Please input a number between 1 and {max_idx}.")

    choice = results[index-1]
    title = choice.get("title, Unknown")
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
async def play(ctx, url: str):
    """Command to play audio from a YouTube URL."""
    global looping, current_url

    if not ctx.voice_client:
        await ctx.invoke(join)  # Have the bot join first if not in VC

    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            url2 = info['url']
        except Exception as e:
            await ctx.send(f"Error extracting audio: {e}")
            return

    current_url = url  # Store the current song for looping
    title = info.get("title","unknown")
    duration = info.get("duration")
    webpage = info.get("webpage_url") or url
    thumb = info.get("thumbnail") or (info.get("thumbnails") or [{}])[-1].get("url")

    global current_title, current_duration, current_webpage_url, current_thumbnail, current_requester_id
    current_title = title
    current_duration = duration
    current_webpage_url = webpage
    current_thumbnail = thumb
    current_requester_id = ctx.author.id

    def after_playing(error):
        if error:
            print(f"Error: {error}")

        if looping and current_url:
            ctx.voice_client.play(discord.FFmpegPCMAudio(url2, options='-vn'), after=after_playing)
        else:
            print("Finished playing.")

    ctx.voice_client.stop()
    ctx.voice_client.play(discord.FFmpegPCMAudio(url2, options='-vn'), after=after_playing)

    await ctx.send(f"Now playing: {info.get('title', 'Unknown')}")

bot.run("INSERT_YOUR_TOKEN_HERE")

