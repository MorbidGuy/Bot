import discord
import logging
import asyncio
import pandas as pd


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.members = True
intents.voice_states = True
client = discord.Client(intents=intents)

stop_flag = False
players_df = pd.DataFrame()
selected_ids = []
command_messages = []
prefix = '!'  # Default prefix

# Defina o caminho para o arquivo Excel aqui
file_path = '/caimnho/para/tabela/de/Balanceamento.xlsx'

async def delete_messages(channel, limit):
    limit = min(limit, 100)
    deleted_count = 0
    async for message in channel.history(limit=limit):
        try:
            await message.delete()
            deleted_count += 1
        except discord.Forbidden:
            logging.warning("Permissões insuficientes para apagar uma mensagem.")
        except discord.HTTPException as e:
            logging.error(f"Erro ao apagar mensagem: {e}")
        await asyncio.sleep(0.5)  # Pausa para evitar rate limiting
    logging.info(f"{deleted_count} mensagens foram apagadas no canal {channel.name}")
    return deleted_count

async def delete_user_messages(channel, member):
    deleted_count = 0
    async for message in channel.history(limit=100):
        if message.author == member:
            try:
                await message.delete()
                deleted_count += 1
            except discord.Forbidden:
                logging.warning("Permissões insuficientes para apagar uma mensagem.")
            except discord.HTTPException as e:
                logging.error(f"Erro ao apagar mensagem: {e}")
    logging.info(f"{deleted_count} mensagens do usuário {member.display_name} foram apagadas no canal {channel.name}")
    return deleted_count

async def delete_all_messages(channel):
    deleted_count = 0
    while True:
        messages = [message async for message in channel.history(limit=100)]
        if not messages:
            break
        for message in messages:
            try:
                await message.delete()
                deleted_count += 1
            except discord.Forbidden:
                logging.warning("Permissões insuficientes para apagar uma mensagem.")
            except discord.HTTPException as e:
                logging.error(f"Erro ao apagar mensagem: {e}")
            await asyncio.sleep(0.5)  # Pausa para evitar rate limiting
        await asyncio.sleep(1)  # Pausa entre as chamadas para evitar rate limiting
    logging.info(f"{deleted_count} mensagens foram apagadas no canal {channel.name}")
    return deleted_count

async def delete_related_messages(channel):
    async for message in channel.history(limit=100):
        if message.id in command_messages:
            try:
                await message.delete()
                command_messages.remove(message.id)
            except discord.Forbidden:
                logging.warning("Permissões insuficientes para apagar uma mensagem.")
            except discord.HTTPException as e:
                logging.error(f"Erro ao apagar mensagem: {e}")
    logging.info("Mensagens relacionadas ao comando !select_ids foram apagadas.")

async def join(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        if ctx.voice_client is None:
            await channel.connect()
            await ctx.send(f'Entrei no canal de voz {channel}')
        else:
            await ctx.voice_client.move_to(channel)
            await ctx.send(f'Mudei para o canal de voz {channel}')
    else:
        await ctx.send('Você não está em um canal de voz.')

async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send('Saí do canal de voz.')
    else:
        await ctx.send('Não estou em nenhum canal de voz.')

def load_players_data():
    global players_df
    players_df = pd.read_excel(file_path)
    print("Colunas disponíveis no DataFrame:", players_df.columns.tolist())
    required_columns = ['ID', 'Divergencias', 'Nicks']
    actual_columns = players_df.columns.tolist()
    missing_columns = [col for col in required_columns if col not in actual_columns]
    if missing_columns:
        raise ValueError(f"O arquivo Excel deve conter as colunas {', '.join(required_columns)}. Colunas faltantes: {', '.join(missing_columns)}.")
    players_df['Divergencias'] = players_df['Divergencias'].apply(lambda x: list(map(int, str(x).split(','))) if pd.notna(x) else [])

async def blackops(message):
    if not message.author.guild_permissions.administrator:
        await message.channel.send("Você não tem permissão para usar este comando.")
        return
    
    await message.channel.send("Por favor, forneça o número de mensagens para apagar (máximo de 100).")
    def check(msg):
        return msg.author == message.author and msg.channel == message.channel and msg.content.isdigit()
    try:
        num_message = await client.wait_for('message', timeout=60.0, check=check)
        num_messages = int(num_message.content)
        if num_messages < 1 or num_messages > 100:
            await message.channel.send("Número inválido. Forneça um número entre 1 e 100.")
            return
        deleted_count = await delete_messages(message.channel, num_messages)
        await message.channel.send(f"{deleted_count} mensagens foram apagadas no canal.")
    except asyncio.TimeoutError:
        await message.channel.send("Tempo esgotado. Tente novamente.")

async def beforeiforget(message):
    if not message.author.guild_permissions.administrator:
        await message.channel.send("Você não tem permissão para usar este comando.")
        return
    
    if message.mentions:
        member = message.mentions[0]
        deleted_count = await delete_user_messages(message.channel, member)
        await message.channel.send(f"{deleted_count} mensagens de {member.display_name} foram apagadas.")
    else:
        await message.channel.send("Por favor, mencione um usuário para apagar as mensagens.")

async def select_player_ids(message):
    global selected_ids, command_messages
    selected_ids = []
    command_messages = []
    
    await message.channel.send("Por favor, forneça 10 IDs dos jogadores (1 a 18), separados por espaço. Você tem 5 minutos.")
    def check(msg):
        return msg.author == message.author and msg.channel == message.channel and all(x.isdigit() for x in msg.content.split())
    
    try:
        ids_message = await client.wait_for('message', timeout=300.0, check=check)
        ids = list(map(int, ids_message.content.split()))
        command_messages.append(ids_message.id)
        if len(ids) != 10 or any(id_ < 1 or id_ > 18 for id_ in ids):
            await message.channel.send("Você deve fornecer exatamente 10 IDs válidos, separados por espaço.")
            return
        selected_ids.extend(ids)
    except asyncio.TimeoutError:
        await message.channel.send("Tempo esgotado. Por favor, tente novamente.")
        return
    
    if len(selected_ids) != 10:
        await message.channel.send("Seleção de IDs incompleta. Certifique-se de fornecer exatamente 10 IDs.")
        return
    
    available_players_df = players_df[players_df['ID'].isin(selected_ids)]
    if len(available_players_df) < 10:
        await message.channel.send("Alguns IDs fornecidos não são válidos ou não estão disponíveis.")
        return
    
    randomized_df = available_players_df.sample(frac=1).reset_index(drop=True)
    team_size = len(randomized_df) // 2
    team1 = randomized_df.head(team_size)
    team2 = randomized_df.tail(team_size)
    
    team1_list = '\n'.join(team1['Nicks'])
    team2_list = '\n'.join(team2['Nicks'])
    
    await message.channel.send(f"**Times selecionados:**\n\n**Time 1:**\n{team1_list}\n\n**Time 2:**\n{team2_list}")

    # Apaga até 5 mensagens relacionadas ao comando !select_ids
    if command_messages:
        messages_to_delete = command_messages[:5]
        deleted_count = 0
        for msg_id in messages_to_delete:
            try:
                message_to_delete = await message.channel.fetch_message(msg_id)
                await message_to_delete.delete()
                deleted_count += 1
                if deleted_count >= 5:
                    break
            except discord.NotFound:
                continue

async def ajuda_command(message):
    help_text = {
        '!select_ids': "Permite selecionar 10 IDs de jogadores para criar dois times aleatórios. Os times serão exibidos sem elos e 5 mensagens serão apagadas após a seleção.",
        '!ajuda': "Exibe esta mensagem de ajuda.",
        '!cancelar': "Cancela o comando !blackout se ele estiver em execução.",
        '!ban': "Bane um usuário do servidor com um motivo especificado. (Admin)",
        '!kick': "Expulsa um usuário do servidor com um motivo especificado. (Admin)",
        '!setprefix': "Altera o prefixo do bot para o valor fornecido. (Admin)",
        '!blackout': "Apaga todas as mensagens do canal atual. Somente administradores podem usar este comando.",
        '!blackops': "Apaga um número específico de mensagens do canal atual (de 1 a 100). Somente administradores podem usar este comando.",
        '!beforeiforget': "Apaga todas as mensagens de um usuário mencionado no canal atual. Somente administradores podem usar este comando."
    }

    embed = discord.Embed(title="Comandos Disponíveis", description="Aqui estão os comandos que você pode usar:", color=0x00ff00)
    
    if message.author.guild_permissions.administrator:
        # Para administradores, envia a lista completa de comandos na DM
        dm_channel = await message.author.create_dm()
        for cmd, desc in help_text.items():
            embed.add_field(name=cmd, value=desc, inline=False)
        await dm_channel.send(embed=embed)
    else:
        # Para usuários comuns, envia a lista de comandos permitidos no canal onde o comando foi enviado
        user_help_text = {k: v for k, v in help_text.items() if k not in ['!ban', '!kick', '!setprefix', '!blackout', '!blackops', '!beforeiforget']}
        embed.clear_fields()  # Limpa campos anteriores
        for cmd, desc in user_help_text.items():
            embed.add_field(name=cmd, value=desc, inline=False)
        await message.channel.send(embed=embed)

@client.event
async def on_ready():
    logging.info(f'Bot conectado como {client.user.name} ({client.user.id})')
    load_players_data()

@client.event
async def on_message(message):
    global prefix, stop_flag
    if message.author == client.user:
        return
    
    if message.content.startswith(prefix):
        command = message.content[len(prefix):].split()[0]
        
        if command == 'select_ids':
            await select_player_ids(message)
        elif command == 'ajuda':
            await ajuda_command(message)
        elif command == 'blackout':
            if message.author.guild_permissions.administrator:
                await message.channel.send("Iniciando o comando !blackout.")
                deleted_count = await delete_all_messages(message.channel)
                await message.channel.send(f"{deleted_count} mensagens foram apagadas no canal.")
            else:
                await message.channel.send("Você não tem permissão para usar este comando.")
        elif command == 'blackops':
            if message.author.guild_permissions.administrator:
                await blackops(message)
            else:
                await message.channel.send("Você não tem permissão para usar este comando.")
        elif command == 'beforeiforget':
            if message.author.guild_permissions.administrator:
                await beforeiforget(message)
            else:
                await message.channel.send("Você não tem permissão para usar este comando.")
        elif command == 'setprefix':
            if message.author.guild_permissions.administrator:
                new_prefix = message.content[len(prefix):].split(maxsplit=1)[1]
                prefix = new_prefix
                await message.channel.send(f"Prefixo alterado para: {prefix}")
            else:
                await message.channel.send("Você não tem permissão para usar este comando.")
        elif command == 'ban':
            if message.author.guild_permissions.administrator:
                user = message.mentions[0]
                reason = ' '.join(message.content.split()[2:])
                await user.ban(reason=reason)
                await message.channel.send(f"{user} foi banido por {message.author} por: {reason}")
            else:
                await message.channel.send("Você não tem permissão para usar este comando.")
        elif command == 'kick':
            if message.author.guild_permissions.administrator:
                user = message.mentions[0]
                reason = ' '.join(message.content.split()[2:])
                await user.kick(reason=reason)
                await message.channel.send(f"{user} foi expulso por {message.author} por: {reason}")
            else:
                await message.channel.send("Você não tem permissão para usar este comando.")
        elif command == 'cancelar':
            stop_flag = True
            await message.channel.send("O comando !blackout foi cancelado.")
    
    # Mensagem padrão para comandos não reconhecidos
    if not message.content.startswith(prefix):
        await message.channel.send("Comando não reconhecido.")

# Substitua 'seu_token_aqui' pelo token real do seu bot
client.run('TOKEN_YOUR_BOT')
