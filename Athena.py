import discord
from discord.ext import commands
import yt_dlp as youtube_dl  # Use yt-dlp instead of youtube_dl
import asyncio

# Define intents
intents = discord.Intents.default()
intents.message_content = True
looping = False

# Initialize bot, change & to whatever you want to use to invoke the bot, like ! ? $ # etc.
bot = commands.Bot(command_prefix="&", intents=intents)

@bot.event
async def on_ready():
    print("Salutations.")

@bot.command()
async def join(ctx):
    """Command to make the bot join the voice channel."""
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
    else:
        await ctx.send("You must first join a voice channel.")

@bot.command()
async def leave(ctx):
    """Command to make the bot leave the voice channel."""
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
    else:
        await ctx.send("I am not currently in a voice channel.")
""" Pause the currently playing music. """
@bot.command()
async def pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("Current playback paused.")
    else:
        await ctx.send("No playback currently active.")

"""Resumes song currently playing. """
@bot.command()
async def resume(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("Playback resumed.")
    else:
        await ctx.send("No playback currently active.")
""" """
@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("Skipped current playback.")
    else:
        await ctx.send("No playback currently active.")

@bot.command()
async def loop(ctx):
    global looping
    looping = not looping
    await ctx.send(f"Playback loop has been {'enabled' if looping else 'disabled'}.")

@bot.command()
async def helpme(ctx):
    await ctx.send("\n play \n resume \n skip \nloop \n pause \n join \n leave")




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


