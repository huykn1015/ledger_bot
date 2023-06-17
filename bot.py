import csv
import heapq
import json
import math
from os.path import exists
import pandas as pd
import urllib.request
import discord
from discord.utils import get
from discord.ext import commands, tasks
from dataclasses import dataclass, asdict, field

    
#dict of account -> account info
balances = {}
#dict of pokernow id -> discord id
poker_ids = {}

def save_dicts():
    id_json = json.dumps(poker_ids, indent=4)
    balances_json = json.dumps(balances, indent=4)
    with open("balances.json", "w") as outbalance:
        json.dump(balances_json, outbalance)
    with open("poker_ids.json", "w") as outid:
        json.dump(id_json, outid)



BOT_TOKEN = "MTExOTEyMzIxNzAyNjY1MDI1Mw.GROrKU.F6w64fyO0hVdkkaWB_9vkgpzoqhsMS-W44Ze3Q"
CHANNEL_ID = 1119180260697702443
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents = intents)

@bot.event
async def on_ready():
    channel = bot.get_channel(CHANNEL_ID)
    print("Loading")
    global balances
    global poker_ids
    if exists("balances.json"):
        with open("balances.json") as balances_json_in:
            balance_in = json.load(balances_json_in)
            balances = json.loads(balance_in)
            print(balances.keys())
    if exists("poker_ids.json"):
        with open("poker_ids.json") as ids_json_in:
            ids_in = json.load(ids_json_in)
            poker_ids = json.loads(ids_in)
            print(poker_ids)


@bot.command()
async def save(ctx):
    save_dicts()

#register multiple ids to a discord account
@bot.command()
async def register(ctx, poker_id):
    #id must not already be registered
    acc_id = ctx.message.author.id
    channel = bot.get_channel(CHANNEL_ID)
    if acc_id not in balances.keys():
        balances[str(acc_id)] = 0 
    if poker_id in poker_ids.keys():
        await channel.send("Pokernow ID has already been linked to <@{}>".format(poker_ids[poker_id]))
        return None
    poker_ids[poker_id] = ctx.message.author.id
    print(balances)
    save_dicts()
    await channel.send("Poker ID {} now linked to {}".format(poker_id, ctx.message.author.mention)) 

@register.error
async def register_id_error(ctx, error):
    if(isinstance(error, commands.MissingRequiredArgument)):
        channel = bot.get_channel(CHANNEL_ID)
        await channel.send("Please Enter Pokernow player ID")

#get balance of calling user 
@bot.command(name="balance")
async def get_balance(ctx):
    acc_id = ctx.message.author.id
    channel = bot.get_channel(CHANNEL_ID)
    if str(acc_id) not in balances.keys():
        await channel.send("Cannot Find Account") 
        return None
    acc_balance = balances[str(acc_id)]
    await channel.send("{} balance: {:.2f}".format(ctx.message.author.mention, acc_balance))


#transfer balance from caller to dest user
@bot.command(name="pay")
async def send_amount(ctx, dest:discord.User, amount):
    send_id = ctx.message.author.id
    dest_id = dest.id
    amount = float(amount)
    if amount == 0.0:
        await channel.send("Invalid Payment Amount")
        return None
    channel = bot.get_channel(CHANNEL_ID)
    if send_id not in balances.keys():
        await channel.send("Cannot Find Sender Account") 
        return None
    if dest_id not in balances.keys():
        await channel.send("Cannot Find Destination Account") 
        return None
    balances[send_id] -= amount
    balances[dest_id] += amount
    save_dicts()
    await channel.send("{} sent {} to <@{}>".format(ctx.message.author.mention, amount, dest_id )) 

@send_amount.error
async def send_error(ctx, error):
    if(isinstance(error, commands.MissingRequiredArgument)):
        channel = bot.get_channel(CHANNEL_ID)
        await channel.send("Please specify reviever and a valid Balance")


#takes game and addes values to all balances 
@bot.command(name="log")
async def log(ctx, link, sb):
    game_id = link.split("/games/")[1]
    url = "https://www.pokernow.club/games/{}/ledger_{}.csv".format(game_id, game_id)
    ledger = pd.read_csv(url)
    confirm_text = ""
    print(ledger)
    for row, player in ledger.iterrows():
        print(player['player_id'])
        if player['player_id'] in poker_ids.keys():
            print("match")
            acc_id = poker_ids[player['player_id']]
            balances[str(acc_id)] += float(player['net']) * float(sb)
            print("acc_id")
            confirm_text += "<@{}> : Added {:.2f} to balance\n".format(acc_id, float(player['net']) * float(sb))
            print ("<@{}> : Added {:.2f} to balance\n".format(acc_id, float(player['net']) * float(sb)))
    channel = bot.get_channel(CHANNEL_ID)
    save_dicts()
    await channel.send(confirm_text)
    
@log.error
async def create_error(ctx, error):
    if(isinstance(error, commands.MissingRequiredArgument)):
        channel = bot.get_channel(CHANNEL_ID)
        await channel.send("Please provide a pokernow link and a the small blind amount")

@bot.command(name="payout")
async def payout(ctx):
    netpos = [] #all negative balances
    netneg = [] #all positive balances
    #key = id of acc receiving money, value = list of payments
    #payments = (payer id, amount)
    payouts = {} 
    for acc_id, net in balances.items():
        if net > 0:
            netpos.append((-net, acc_id))
            payouts[acc_id] = []
        elif net < 0:
            netneg.append((net, acc_id))
    heapq.heapify(netpos)
    heapq.heapify(netneg)
    while netneg and netpos:
        pos, pos_id = heapq.heappop(netpos)
        neg, neg_id = heapq.heappop(netneg)
        pos = - pos
        if pos >= - neg:
            payouts[pos_id].append((neg_id, -neg))
            if(pos != -neg):
                heapq.heappush(netpos,(-pos - neg, pos_id))
        else:
            payouts[pos_id].append((neg_id, pos))
            heapq.heappush(netneg, ((neg + pos, neg_id)))
    payment_text = ""
    for dest_id, pay in payouts.items():
        for sender_id, amount in pay:
            payment_text += "<@{}> Send {:.2f}; ".format(sender_id, amount)
        payment_text += "to <@{}>\n".format(dest_id)
    channel = bot.get_channel(CHANNEL_ID)
    for acc_id in balances.keys():
        balances[acc_id] = 0
    await channel.send(payment_text)


#@bot.command(name="history")


bot.run(BOT_TOKEN)