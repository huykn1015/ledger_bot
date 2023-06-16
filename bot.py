from discord.ext import commands, tasks
import discord
from dataclasses import dataclass


BOT_TOKEN = "MTExOTEyMzIxNzAyNjY1MDI1Mw.GROrKU.F6w64fyO0hVdkkaWB_9vkgpzoqhsMS-W44Ze3Q"
CHANNEL_ID = 1119180260697702443

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

@bot.event
async def on_ready():
    print("Start")
    channel = bot.get_channel(CHANNEL_ID)
    await channel.send("start")
bot.run(BOT_TOKEN)


