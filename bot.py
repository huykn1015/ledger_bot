from discord.ext import commands, tasks
import discord
from dataclasses import dataclass, asdict, field

@dataclass
class account_info:
    balance: int
    buyin: int

with open('accounts.csv', newline= '') as csvfile:
    csvreader = csv.reader(csvfile, delimiter=',')
    lineCount = 0
    
#csv of all accounts
accounts = {}

BOT_TOKEN = "MTExOTEyMzIxNzAyNjY1MDI1Mw.GROrKU.F6w64fyO0hVdkkaWB_9vkgpzoqhsMS-W44Ze3Q"
CHANNEL_ID = 1119180260697702443
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents = intents)

@bot.event
async def on_ready():
    print("Start")
    channel = bot.get_channel(CHANNEL_ID)


@bot.command()
async def create(ctx, amount):
    account_id = ctx.message.author.id
    channel = bot.get_channel(CHANNEL_ID)
    if account_id in accounts.keys():
        await channel.send("Account Already Created") 
        return None
    if amount == None:
        await channel.send("Invalid Balance")
    amount = int(amount)
    acc_info = account_info( amount, amount)
    accounts[account_id] = acc_info
    channel = bot.get_channel(CHANNEL_ID)
    await channel.send("Created account for {} with balance of {}".format(ctx.message.author.mention, amount))

@create.error
async def create_error(ctx, error):
    if(isinstance(error, commands.MissingRequiredArgument)):
        channel = bot.get_channel(CHANNEL_ID)
        await channel.send("Please Enter a valid Balance") 

@bot.command(name="balance")
async def get_balance(ctx):
    account_id = ctx.message.author.id
    channel = bot.get_channel(CHANNEL_ID)
    if account_id not in accounts.keys():
        await channel.send("Cannot Find Account") 
        return None
    acc_info = accounts[account_id]
    await channel.send("{} balance: {}, buyin: {}".format(ctx.message.author.mention, acc_info.balance, acc_info.buyin))


@bot.command(name="send")
async def send_amount(ctx, dest:discord.User, amount):
    send_id = ctx.message.author.id
    dest_id = dest.id
    amount = int(amount)
    channel = bot.get_channel(CHANNEL_ID)
    if send_id not in accounts.keys():
        await channel.send("Cannot Find Sender Account") 
        return None
    if dest_id not in accounts.keys():
        await channel.send("Cannot Find Destination Account") 
        return None
    send_info = accounts[send_id]
    dest_info = accounts[dest_id]
    if send_info.balance < amount:
        await channel.sent("Not Sufficient Funds")
        return None
    send_info.balance -= amount
    dest_info.balance += amount
    await channel.send("{} sent {} to <@{}>".format(ctx.message.author.mention, amount, dest_id )) 

@bot.command(name="add")
async def add(ctx, amount):
    send_id = ctx.message.author.id
    amount = int(amount)
    channel = bot.get_channel(CHANNEL_ID)
    if send_id not in accounts.keys():
        await channel.send("Cannot Find Sender Account") 
        return None
    send_info = account_info[send_id]
    send_info.balance += amount
    await channel.send("Added {} to {}".format(amount, ctx.message.author.mention))

#@bot.command(name="sub")

#@bot.command(name="buyout")

#@bot.command(name="history")











bot.run(BOT_TOKEN)