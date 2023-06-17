from discord.ext import commands, tasks
import discord
from discord.utils import get
import csv
import heapq
import math
import pandas as pd
import urllib.request
from dataclasses import dataclass, asdict, field

@dataclass
class account_info:
    balance: float
    buyin: float
    
#dict of all accounts
accounts = {}
#dict of pokernow id to discord id
poker_ids = {}

BOT_TOKEN = "MTExOTEyMzIxNzAyNjY1MDI1Mw.GROrKU.F6w64fyO0hVdkkaWB_9vkgpzoqhsMS-W44Ze3Q"
CHANNEL_ID = 1119180260697702443
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents = intents)

@bot.event
async def on_ready():
    channel = bot.get_channel(CHANNEL_ID)

#register poker now account to discord id with starting balance
@bot.command()
async def register(ctx, poker_id, amount):
    account_id = ctx.message.author.id
    channel = bot.get_channel(CHANNEL_ID)

    #account must not exist, poker id must not map to an account, balance must be valid
    if account_id in accounts.keys():
        await channel.send("Account Already Created") 
        return None
    if poker_id in poker_ids.keys():
        await channel.send("Pokernow account has already been linked")
        return None
    if float(amount) == 0.0:
        print("Invalid amount")
        await channel.send("Invalid Amount")

    
    amount = float(amount)
    acc_info = account_info( amount, amount)

    accounts[account_id] = acc_info
    poker_ids[poker_id] = account_id
    await channel.send("Created account for {} with balance of {}".format(ctx.message.author.mention, amount))

@register.error
async def create_error(ctx, error):
    if(isinstance(error, commands.MissingRequiredArgument)):
        channel = bot.get_channel(CHANNEL_ID)
        await channel.send("Please Enter Pokernow player ID and a valid Balance")


#register multiple ids to a discord account
@bot.command()
async def register_id(ctx, poker_id):
    #id must not already be registered
    if poker_id in poker_ids.keys():
        await channel.send("Pokernow account has already been linked")
        return None
    poker_ids[poker_id] = ctx.message.author.id
    channel = bot.get_channel(CHANNEL_ID)
    await channel.send("Poker ID {} linked to {}".format(poker_id, ctx.message.author.mention)) 

#get balance of calling user or all balances
@bot.command(name="balance")
async def get_balance(ctx, *args):
    a = ",".join(args)
    if len(args) > 0 and a[0] == "all":
        for account, acc_info in accounts:
            await channel.send("<@{}> balance: {}, Net: {}".format(account, acc_info.balance, acc_info.buying - acc_info.buyin))
            return None
    account_id = ctx.message.author.id
    channel = bot.get_channel(CHANNEL_ID)
    if account_id not in accounts.keys():
        await channel.send("Cannot Find Account") 
        return None
    acc_info = accounts[account_id]
    await channel.send("{} balance: {}, Net: {}".format(ctx.message.author.mention, acc_info.balance, acc_info.balance - acc_info.buyin))


#transfer balance from caller to dest user
@bot.command(name="pay")
async def send_amount(ctx, dest:discord.User, amount):
    send_id = ctx.message.author.id
    dest_id = dest.id
    amount = float(amount)
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

@send_amount.error
async def create_error(ctx, error):
    if(isinstance(error, commands.MissingRequiredArgument)):
        channel = bot.get_channel(CHANNEL_ID)
        await channel.send("Please specify reviever and a valid Balance")

#add to balance and buyin
@bot.command(name="add")
async def add(ctx, amount):
    acc_id = ctx.message.author.id
    amount = float(amount)
    channel = bot.get_channel(CHANNEL_ID)
    if acc_id not in accounts.keys():
        await channel.send("Cannot Find Sender Account") 
        return None
    acc_info = accounts[acc_id]
    acc_info.balance += amount
    acc_info.buyin += amount
    await channel.send("Added {} to {}\n New balance: {}, New Buy in: {}".format(amount, ctx.message.author.mention, acc_info.balance, acc_info.buyin))


#remove from balance and buyin
@bot.command(name="sub")
async def sub(ctx, amount):
    acc_id = ctx.message.author.id
    amount = float(amount)
    channel = bot.get_channel(CHANNEL_ID)
    acc_info = accounts[acc_id]
    if acc_id not in accounts.keys():
        await channel.send("Cannot Find Sender Account") 
        return None
    if amount > acc_info.balance:
        await channel.sent("Not Sufficient Funds")
        return None
    acc_info.balance -= amount
    acc_info.buyin -= amount
    await channel.send("Removed {:.2f} from {}".format(amount, ctx.message.author.mention))

#takes game and addes values to all balances 
@bot.command(name="log")
async def log(ctx, link, sb):
    game_id = link.split("/games/")[1]
    url = "https://www.pokernow.club/games/{}/ledger_{}.csv".format(game_id, game_id)
    ledger = pd.read_csv(url)
    confirm_text = ""
    for row, player in ledger.iterrows():
        if player['player_id'] in poker_ids.keys():
            account_id = poker_ids[player['player_id']]
            acc_info = accounts[account_id]
            user = await ctx.bot.fetch_user(account_id)
            buy_in =  float(player['buy_in']) * float(sb)
            stack_in = float(player['stack']) * float(sb)
            if not math.isnan(float(player['buy_out'])):
                stack_in +=  float(player['buy_out']) * float(sb) 
            acc_info.buyin += buy_in
            acc_info.balance += stack_in 
            confirm_text += "<@{}> : Added {:.2f} to buy in, added {:.2f} to balance\n".format(user.id, buy_in, stack_in)
    channel = bot.get_channel(CHANNEL_ID)
    await channel.send(confirm_text)
    
    #get csv


@bot.command(name="payout")
async def payout(ctx):
    netpos = [] #all negative balances
    netneg = [] #all positive balances
    #key = id of acc receiving money, value = list of payments
    #payments = (payer id, amount)
    payouts = {} 
    for acc_id, acc_info in accounts:
        net = acc_info.balance - acc_info.buyin
        if net > 0:
            netpos.append((-net, acc_id))
        elif net < 0:
            netneg.append((net, acc_id))
    for net, id in netpos:
        payout[id] = []
    heapq.heapify(netpos)
    heapq.heapify(netneg)
    while netneg and netpos:
        pos, pos_id = - heapq.heappop(netpos)
        neg, neg_id = heapq.heappop(netneg)
        if pos >= - neg:
            payouts[pos_id].append((neg_id, -neg))
            if(pos != -neg):
                heapq.heappush(netpos,(-pos - neg, pos_id))
        else:
            payout[pos_id].append((neg_id, pos))
            heapq.heappush(netneg((neg + pos, neg_id)))
    payment_text = ""
    for dest_id, pay in payout:
        for sender_id, amount in pay:
            payment_text += "<@{}> Send {}; ".format(sender_id, amount)
        payment_text += "to <@{}>\n".format(dest_id)
    channel = bot.get_channel(CHANNEL_ID)
    await channel.send(payment_text)


#@bot.command(name="history")





bot.run(BOT_TOKEN)