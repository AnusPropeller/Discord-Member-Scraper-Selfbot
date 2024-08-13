import json
import os
import sys
import re
import asyncio
import discord
from discord.ext import commands

bot = commands.Bot(command_prefix="?", self_bot=True)
script_dir = os.path.dirname(os.path.abspath(__file__))

if sys.platform == 'win32':  # weird fix for a bug I ran into
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def findlist(guild_ids: str):
    data = {
        'user-ids': [],
    }
    if not os.path.exists(f"{guild_ids}.json"):
        with open(f"{guild_ids}.json", 'w') as f:
            json.dump(data, f)
            print(f"Created Config File {guild_ids}.json.")
    else:
        if os.path.getsize(f"{guild_ids}.json") > 0:
            print("File exist, but is has values. Reformatting.")
            with open(f"{guild_ids}.json", 'w') as f:
                json.dump(data, f)
        else:
            print("File exist, but is empty. Refilling.")
            with open(f"{guild_ids}.json", 'w') as f:
                json.dump(data, f)


guild_id = input("Input the Guild ID that will be scraped for user ids: ")
if not guild_id.strip().isnumeric():
    print("Invalid Guild ID: Non numeric input.")
    quit()
welcome_channel_id = input("ID of the welcome channel (type a letter if there is none): ")
if not welcome_channel_id.strip().isnumeric():
    print("Welcome channel id isn't valid, will assume there is none.")
    welcome_channel_id = None
only_members = False
fetch_question = input("Save only current server members? [Y/n]: ")
if fetch_question.lower().startswith("y"): only_members = True
stop_early = False
stop_question = input("Stop within 150 members of cache? [Y/n]: ")
if stop_question.lower().startswith("y"): stop_early = True
depth_question = input("How many messages deep should the bot go per channel. No limit or a range between 1000 to 40000"
                       ". Type 'n' for no limit. (welcome channel exempt): ")
message_depth = 1000
depth_question = depth_question.replace(",", "").replace(".", "")
print(depth_question.strip().lower())
if depth_question.strip().lower() == "n": message_depth = None
elif not depth_question.isnumeric():
    print("Invalid input, quitting")
    quit()
elif int(depth_question) < 1000:
    print("Defaulting to 1000 depth")
    message_depth = 1000
elif int(depth_question) > 40000:
    print("Defaulting to 40000 depth.")
    message_depth = 40000
else:
    print(f"Using depth {depth_question}")
    message_depth = int(depth_question)


async def parse_input(user_input: str):
    prompt = user_input.strip()
    if not prompt.isnumeric():
        print("Invalid guild ID passed. Restart the script.")
        return
    guild = None
    try:
        guild = await bot.fetch_guild(int(prompt))
    except discord.Forbidden:
        print("Failed to fetch the guild: No access to the Guild.")
        return
    except discord.HTTPException:
        print("Failed to fetch the guild: HTTP Exception.")
        return
    if guild:
        print(f"Nuking guild {guild.name}")
        await scrape_users(guild=guild)


@bot.event
async def on_ready():
    print(f"Logged in as user {bot.user.name} is in {len(bot.guilds)} guilds.")
    print("This is a logging only console: You cannot use commands here.")
    await parse_input(guild_id)


async def scrape_users(guild: discord.Guild):
    findlist(guild_ids=str(guild.id))
    member = await guild.fetch_member(bot.user.id)
    channels = None
    try:
        channels = await guild.fetch_channels()
    except discord.InvalidData:
        print("Failed to Fetch Guild Channels: Invalid Data.")
    except discord.HTTPException:
        print("Failed to Fetch Guild Channels: HTTPException.")

    good_channels_for_member_scraping = []
    channel_ratings = {}
    if channels:
        for x in channels:
            if not x.permissions_for(member).read_messages: continue
            roles_seeing_channel_count = 0
            for role in guild.roles:
                if x.permissions_for(role).read_messages: roles_seeing_channel_count += 1
            channel_ratings[f'{x.id}'] = roles_seeing_channel_count

    sorted_channels = sorted(channel_ratings.items(), key=lambda item: item[1], reverse=True)

    # Append the top 5 channels to the list
    for channel_id, count in sorted_channels[:5]:
        append_channel = await guild.fetch_channel(channel_id)
        good_channels_for_member_scraping.append(append_channel)

    with open(f"{guild.id}.json", 'r') as file:
        data = json.load(file)
    curr_member_list = data['user-ids']
    if len(good_channels_for_member_scraping) > 0:
        members = await guild.fetch_members(channels=good_channels_for_member_scraping, force_scraping=True,
                                            delay=.1, cache=True)
        for x in members:
            if x.id == bot.user.id:
                members.remove(x)
                continue
            if x.status is not discord.Status.offline:
                curr_member_list.append(x.id)
                members.remove(x)
        for x in members:
            curr_member_list.append(x.id)
            members.remove(x)
    channels_to_scrape = []
    new_channels = await guild.fetch_channels()
    tep = []
    for x in new_channels:
        try:
            tip = await guild.fetch_channel(x.id)
            print(f"Fetching channel {tip.name}")
            tep.append(tip)
        except discord.Forbidden:
            print(f"Failed to fetch channel {x.name}: Forbidden")

    print(f"Fetched guild channels length: {len(tep)}")
    for channel_curr in tep:
        if channel_curr.type is discord.ChannelType.category: continue
        if channel_curr.type is discord.ChannelType.forum:
            if channel_curr.permissions_for(guild.me).read_messages:
                try:
                    async for thread in channel_curr.archived_threads(limit=None):
                        channels_to_scrape.append(thread)
                except discord.Forbidden:
                    print("Failed to check channel threads: Forbidden.")
                except discord.HTTPException:
                    print("Failed to check channel threads: HTTPException")
                for thread in channel_curr.threads:
                    channels_to_scrape.append(thread)
        elif channel_curr.type is discord.ChannelType.text:
            if channel_curr.permissions_for(guild.me).read_messages:
                channels_to_scrape.append(channel_curr)
                try:
                    async for thread in channel_curr.archived_threads(limit=None):
                        channels_to_scrape.append(thread)
                except discord.Forbidden:
                    print("Failed to check channel threads: Forbidden.")
                except discord.HTTPException:
                    print("Failed to check channel threads: HTTPException")
                for thread in channel_curr.threads:
                    channels_to_scrape.append(thread)
        elif channel_curr.type is discord.ChannelType.stage_voice or channel_curr.type is discord.ChannelType.voice:
            if channel_curr.permissions_for(guild.me).read_messages:
                channels_to_scrape.append(channel_curr)
    print(f"channels to scrape: {len(channels_to_scrape)}")
    not_in_guild = []
    try:
        for x in channels_to_scrape:
            if stop_early and (guild.member_count > 250):
                if (guild.member_count - len(curr_member_list)) < 151: break
            mes_depth = message_depth
            welcome_channel = False
            if x.id == welcome_channel_id:
                mes_depth = None
                welcome_channel = True
                print("Scraping welcome Channel!")
            print(f"Scraping channel {x.name} for members.")
            async for message in x.history(limit=mes_depth):
                if stop_early and (guild.member_count > 250):
                    if (guild.member_count - len(curr_member_list)) < 151: break
                if message.author.id in curr_member_list and not (welcome_channel and message.author.bot): continue
                if message.author.id in not_in_guild and not (welcome_channel and message.author.bot): continue
                try:
                    if not message.author.bot:
                        if only_members: await guild.fetch_member(message.author.id)
                        print(f"New member added: {message.author.name} | Count: {len(curr_member_list) + 1}")
                        curr_member_list.append(message.author.id)
                    if welcome_channel and message.author.bot:
                        for mention in message.mentions:
                            if only_members: await guild.fetch_member(mention.id)
                            curr_member_list.append(mention.id)
                except discord.NotFound:
                    not_in_guild.append(message.author.id)
                except discord.Forbidden:
                    print("Failed to fetch user: Forbidden.")
                except discord.HTTPException:
                    print("Failed to fetch user: HTTPException.")
        if not only_members: print(f"Scraped {len(curr_member_list)} users, downloading to /{guild.id}.json.")
        else: print(f"Scraped {len(curr_member_list)} members, downloading to /{guild.id}.json.")
        print(f"Cache of server says that it has {guild.member_count} current members.")
        data['user-ids'] = curr_member_list
        with open(f"{guild.id}.json", 'w') as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Failed: {e}")
        print(f"Saving current list to {guild.id}.json")
        data['user-ids'] = curr_member_list
        with open(f"{guild.id}.json", 'w') as f:
            json.dump(data, f)


user_token = input("Input user token: ")

token_pattern = r'[MNO][a-zA-Z\d_-]{23,25}\.[a-zA-Z\d_-]{6}\.[a-zA-Z\d_-]{27}'

if not re.match(token_pattern, user_token):
    print("Bad User Token sensed. Please check for bad characters.")
    print("Continue with bad token? Script will do nothing if it is bad.")
    question = input("Type [Yes/No]: ")
    answer = question.lower().strip()
    if answer == "no":
        quit()
    elif answer != "yes":
        print("Invalid input, quitting.")
        quit()

bot.run(user_token)
