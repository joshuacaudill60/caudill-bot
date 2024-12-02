"""
An extremely basic music Discord bot written using discord.py.
"""

import asyncio
import os
import re
import urllib.parse
import urllib.request

import discord
import yt_dlp
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

INTENTS = discord.Intents.default()
INTENTS.members = True
INTENTS.message_content = True

# Change only the no_category default string
help_command = commands.DefaultHelpCommand(
    no_category = 'Commands'
)

# Create the bot and pass it the modified help_command
bot = commands.Bot(
    command_prefix = ".",
    intents = INTENTS,
    help_command = help_command
)

QUEUES = {}
VOICE_CLIENTS = {}
YT_BASE_URL = "https://www.youtube.com/"
YT_RESULTS_URL = YT_BASE_URL + "results?"
YT_WATCH_URL = YT_BASE_URL + "watch?v="
YT_DL_OPT = {"format": "bestaudio/best"}
YTDL = yt_dlp.YoutubeDL(YT_DL_OPT)

FFMPEG_OPTS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": '-vn -filter:a "volume=0.25"',
}


async def play_next(ctx):
    """
    Plays the next song
    """
    if QUEUES[ctx.guild.id] != []:
        link = QUEUES[ctx.guild.id].pop(0)  # Pop the next song in queue
        await play(ctx, link=link)


@bot.command()
async def skip(ctx):
    """
    Skips the song
    """
    VOICE_CLIENTS[ctx.guild.id].stop()  # Stop playing music
    play_next(ctx)  # Play the next song in queue


@bot.command()
async def play(ctx, *, link):
    """
    Plays a song
    """
    try:
        voice_client = await ctx.author.voice.channel.connect()
        VOICE_CLIENTS[voice_client.guild.id] = voice_client
    except asyncio.TimeoutError as timeout_error:
        print(timeout_error)
    except discord.ClientException as client_exception:
        print(client_exception)
    except discord.opus.OpusNotLoaded as opus_not_loaded:
        print(opus_not_loaded)

    try:
        if YT_BASE_URL not in link:
            query_string = urllib.parse.urlencode({"search_query": link})
            content = urllib.request.urlopen(YT_RESULTS_URL + query_string)
            search_results = re.findall(r"/watch\?v=(.{11})", content.read().decode())
            link = YT_WATCH_URL + search_results[0]

        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, lambda: YTDL.extract_info(link, download=False)
        )
        song = data["url"]
        player = discord.FFmpegOpusAudio(song, **FFMPEG_OPTS)
        VOICE_CLIENTS[ctx.guild.id].play(
            player,
            after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop),
        )
    except discord.ClientException as client_exception:
        print(client_exception)
    except TypeError as type_error:
        print(type_error)
    except discord.opus.OpusNotLoaded as opus_not_loaded:
        print(opus_not_loaded)
    except ValueError as value_error:
        print(value_error)


@bot.command()
async def clear_queue(ctx):
    """
    Clears the queue
    """
    if ctx.guild.id in QUEUES:
        QUEUES[ctx.guild.id].clear()  # Clear the queue if it is not empty
        await ctx.send("Queue cleared!")
    else:
        await ctx.send("There is no queue to clear!")


@bot.command(name="pause")
async def pause(ctx):
    """
    Pauses the song
    """
    VOICE_CLIENTS[ctx.guild.id].pause()  # Pause the song


@bot.command(name="resume")
async def resume(ctx):
    """
    Resumes the song
    """
    VOICE_CLIENTS[ctx.guild.id].resume()  # Resume the song


@bot.command(name="stop")
async def stop(ctx):
    """
    Stops the music
    """
    VOICE_CLIENTS[ctx.guild.id].stop()  # Stop playing music
    await VOICE_CLIENTS[ctx.guild.id].disconnect()  # Disconnect from VC
    del VOICE_CLIENTS[ctx.guild.id]  # Delete the voice client


@bot.command(name="queue")
async def queue(ctx, *, url):
    """
    Queues a song
    """
    if ctx.guild.id not in QUEUES:
        QUEUES[ctx.guild.id] = []
    QUEUES[ctx.guild.id].append(url)
    await ctx.send("Added to queue!")


@bot.event
async def on_ready():
    """
    Prints message when bot is ready
    """
    print("[+] caudillbot is ready")


@bot.event
async def on_member_join(member):
    """
    Sends a message when a member joins
    """
    guild = member.guild
    if guild.system_channel is not None:
        to_send = f"Welcome {member.mention} to {guild.name}!"
        await guild.system_channel.send(to_send)


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)  # Runs the Discord bot
