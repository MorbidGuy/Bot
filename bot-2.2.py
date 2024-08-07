import discord
import logging
import shutil
import psutil
import subprocess
import os
import asyncio

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True  
intents.members = True   
client = discord.Client(intents=intents)

stop_flag = False  

def check_system_resources():
    logging.info("Verificando uso dos recursos do sistema")
    memory = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=1)

    logging.info(f"Uso de memória: {memory.percent}%")
    logging.info(f"Uso de CPU: {cpu}%")

async def delete_messages(channel, limit):
    """Deleta um número específico de mensagens no canal especificado."""
    deleted_count = 0
    async for message in channel.history(limit=limit):
        await message.delete()
        deleted_count += 1
    logging.info(f"{deleted_count} mensagens foram apagadas no canal {channel.name}")
    return deleted_count

async def delete_user_messages(channel, member):
    """Deleta todas as mensagens de um membro específico no canal especificado."""
    deleted_count = 0
    async for message in channel.history(limit=100):  
        if message.author == member:
            await message.delete()
            deleted_count += 1
    logging.info(f"{deleted_count} mensagens do usuário {member.display_name} foram apagadas no canal {channel.name}")
    return deleted_count

async def delete_all_messages(channel):
    """Deleta todas as mensagens no canal especificado."""
    deleted_count = 0
    async for message in channel.history(limit=100):  
        await message.delete()
        deleted_count += 1
    logging.info(f"{deleted_count} mensagens foram apagadas no canal {channel.name}")
    return deleted_count

@client.event
async def on_ready():
    logging.info(f'Bot Conectado como {client.user}')

@client.event
async def on_message(message):
    global stop_flag

    if stop_flag:
        
        return

    if message.author == client.user:
        return

    if message.content.startswith('Stop'):
        stop_flag = True
        logging.info("Comando 'Stop' recebido. O bot será parado.")
        await message.channel.send("O bot foi parado com sucesso.")
        await client.close()
        return

    if message.content.startswith('BlackOps'):
        try:
            _, limit = message.content.split()
            limit = int(limit)
            deleted_count = await delete_messages(message.channel, limit)
            await message.channel.send(f'{deleted_count} mensagens foram apagadas.')
        except ValueError:
            await message.channel.send("Por favor, forneça um número válido de mensagens a serem apagadas.")

    elif message.content.startswith('BeforeIForget'):
        if message.author.guild_permissions.manage_messages:
            mentioned_member = message.mentions[0] if message.mentions else None
            if mentioned_member:
                deleted_count = await delete_user_messages(message.channel, mentioned_member)
                await message.channel.send(f'{deleted_count} mensagens do usuário foram apagadas.')
            else:
                await message.channel.send("Por favor, mencione um usuário válido.")
        else:
            await message.channel.send("Você não tem permissão para usar esse comando.")

    elif message.content.startswith('Blackout'):
        if message.author.guild_permissions.manage_messages:
            deleted_count = await delete_all_messages(message.channel)
            await message.channel.send(f"Deletado com sucesso. {deleted_count} mensagens foram apagadas.")
        else:
            await message.channel.send("Você não tem permissão para usar esse comando.")

@client.event
async def on_member_join(member):
    """Notifica quando um membro entra no servidor."""
    channel = discord.utils.get(member.guild.text_channels, name='geral')  
    if channel:
        await channel.send(f"Bem-vindo(a), {member.mention}! 🎉")

@client.event
async def on_member_remove(member):
    """Notifica quando um membro sai do servidor."""
    channel = discord.utils.get(member.guild.text_channels, name='geral')  
    if channel:
        await channel.send(f"Até logo, {member.mention}. 😢")

def run_subprocess():
    logging.info("Executando o subprocesso...")
    result = subprocess.run(['dir'], shell=True, capture_output=True, text=True)
    logging.info(f"Saída do subprocesso:\n{result.stdout}")

def main():
    check_system_resources()
    run_subprocess() 

    token = 'YOUR_TOKEN_BOT'  
    client.run(token)

if __name__ == "__main__":
    main()
