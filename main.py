import logging
import asyncio
import re
import os
import yaml
from telethon import TelegramClient, events
import discord

logging.basicConfig(level=logging.INFO)

config_file = 'config.yaml'
if not os.path.exists(config_file):
    def ask_input(prompt):
        return input(prompt)

    config_data = {
        'api_id': ask_input('Enter your Telegram API ID: '),
        'api_hash': ask_input('Enter your Telegram API Hash: '),
        'session_name': ask_input('Enter your Telegram session name: '),
        'discord_bot_token': ask_input('Enter your Discord bot token: '),
        'discord_channel_id': int(ask_input('Enter your Discord channel ID: ')),
        'input_channel_ids': [int(x) for x in ask_input('Enter your input channel IDs (comma-separated): ').split(',')]
    }

    with open(config_file, 'w') as file:
        yaml.dump(config_data, file)
else:
    with open(config_file, 'r') as file:
        config_data = yaml.safe_load(file)

api_id = config_data['api_id']
api_hash = config_data['api_hash']
session_name = config_data['session_name']
discord_bot_token = config_data['discord_bot_token']
discord_channel_id = config_data['discord_channel_id']
input_channel_ids = config_data['input_channel_ids']

intents = discord.Intents.default()
intents.message_content = True
discord_client = discord.Client(intents=intents)

@discord_client.event
async def on_ready():
    logging.info(f'Logged in as {discord_client.user.name}')

@discord_client.event
async def on_message(message):
    if message.author.id == allowed_user_id and isinstance(message.channel, discord.DMChannel):
        url = message.content
        logging.info(f'Received DM from allowed user: {message.content}')
        await process_message_url(url)
    elif message.author.id != allowed_user_id and isinstance(message.channel, discord.DMChannel):
        logging.info('Message received from an unauthorized user. Ignored.')

telegram_client = TelegramClient(session_name, api_id, api_hash)

@telegram_client.on(events.NewMessage(chats=input_channel_ids))
async def handler(event):
    message = event.message.text
    if message:
        logging.info(f'Forwarding message from Telegram: {message}')
        channel = discord_client.get_channel(discord_channel_id)
        if channel:
            await channel.send(message)
        else:
            logging.error(f'Channel with ID {discord_channel_id} not found.')

async def process_message_url(url):
    match = re.match(r'https://t.me/c/(\d+)/(\d+)', url)
    if not match:
        logging.error('Invalid URL format.')
        return

    channel_id, message_id = match.groups()
    channel_id = int(channel_id)
    message_id = int(message_id)

    if channel_id not in input_channel_ids:
        logging.error(f'Channel ID {channel_id} is not in the input_channel_ids list.')
        return

    try:
        chat = await telegram_client.get_entity(channel_id)
        message = await telegram_client.get_messages(chat, ids=message_id)
        message_text = message.text
        logging.info(f'Forwarding message from Telegram: {message_text}')
        
        channel = discord_client.get_channel(discord_channel_id)
        if channel:
            await channel.send(message_text)
        else:
            logging.error(f'Channel with ID {discord_channel_id} not found.')
    except Exception as e:
        logging.error(f'Failed to fetch or forward message: {e}')

async def main():
    await telegram_client.start()

    await discord_client.start(discord_bot_token)


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
