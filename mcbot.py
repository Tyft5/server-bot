from os import scandir, getenv, path
import subprocess
import discord
from discord.ext import commands
from dotenv import load_dotenv

# import statusping

load_dotenv()
TOKEN = getenv('DISCORD_TOKEN')
START_DESC = getenv('START_DESC')
STOP_DESC = getenv('STOP_DESC')
LIST_DESC = getenv('LIST_DESC')
MC_PORT = getenv('MC_PORT')

print("Bot started, env loaded.")


def get_world_names(ctx: discord.AutocompleteContext) -> list[str]:
    mc_worlds = [f.name for f in scandir('/opt/minecraft/') if f.is_dir()]
    xmage = path.exists(path.dirname("/opt/xmage/"))
    return ['XMage'] + mc_worlds if xmage else mc_worlds

def get_public_ip() -> str:
    command = ['curl', 'ipinfo.io/ip']
    proc = subprocess.run(command, capture_output=True, text=True)
    return str(proc.stdout)


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(intents=intents)

guild_ids=[321330862933278720, 905274461962530817]


@bot.slash_command(name='start', guild_ids=guild_ids, description=START_DESC)
async def start(
    ctx: discord.ApplicationContext,
    world: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_world_names))
):
    print('Received start command')

    if world == "XMage":
        port = ""
        path = "/opt/xmage/"
        start_cmd = "sh startServer.sh 2>&1"
    else:
        port = f":{MC_PORT}"
        path = f'/opt/minecraft/{world}'
        start_cmd = ("sh run.sh 2>&1 "
                + "| sed -n -e 's/^.*There are \([0-9]*\)\/[0-9] players.*$/\1/' "
                + """-e 't M' -e 'b' -e ": M w players" -e 'd' """
                + """| grep -v -e "INFO" -e "Can't keep up" """)

    command = f'screen -dmS {world} {start_cmd}'

    print(f'Running command: {command}')

    try:
        subprocess.run(command, shell=True, cwd=path)
    except Exception as e:
        print("Start command failed. Exception:")
        print(e)
        msg = f"\U0001F534 Failed to start server {world}."
    else:
        ip = get_public_ip()
        msg = (f"\U0001F7E2 Server {world.capitalize()} is starting "
               + f"at address: {ip}{port}"
               + "\nPlease do not attempt to join until the server status is green."
               + "\nPlease /stop the server when you're through playing.")

    await ctx.respond(msg)


@bot.slash_command(name='stop', guild_ids=guild_ids, description=STOP_DESC)
async def stop(
    ctx: discord.ApplicationContext,
    world: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_world_names))
):

    print('Received stop command')

    # the screen session will end when the server is stopped
    if world == 'XMage':
        path = f'/opt/xmage/'
        stop_cmd = f'pkill -f "/usr/bin/java.*{path}/lib/mage-server-"\15'
    else:
        path = f'/opt/minecraft/{world}'
        stop_cmd = "stop\15"

    command = f"screen -S {world} -p 0 -X stuff '{stop_cmd}'"

    print(f'Running command: {command}')

    subprocess.run(command, shell=True, cwd=path)

    print(f'Stopped {world}')
    msg = f"\U0001F534 Server {world.capitalize()} stopped!"

    await ctx.respond(msg)


@bot.slash_command(name='list', guild_ids=guild_ids, description=LIST_DESC)
async def list(ctx: discord.ApplicationContext):

    print('Received list command')

    world_names = get_world_names(ctx)

    command = ["screen", "-ls"]
    print(f"Running command: {' '.join(command)}")

    proc = subprocess.run(command, capture_output=True, text=True)
    scrn_out = proc.stdout

    running_worlds = []

    for line in scrn_out:
        if 'Detached' in line:
            running_worlds.append(line.split()[0].split('.')[-1])

    msg = ''
    ip = get_public_ip()
    if not world_names:
        msg = 'There are no existing servers!'
    for world in world_names:
        if msg: msg += '\n'
        serverup = False

        if world in running_worlds:
            try:
                # status = statusping.StatusPing(host=ip, port=MC_PORT).get_status()
                # num_players = server_status['players']['online']
                serverup = True
            except Exception:
                serverup = False

        if serverup:

            if world == 'XMage':
                port = ""
            else:
                port = f":{MC_PORT}"

            # msg += (f'\U0001F7E2 {world} is up with {num_players}'
            #         + f' player(s) at {ip}:{MC_PORT}!')
            msg += (f'\U0001F7E2 {world} is up at {ip}{port}!')
            print(f'{world} is up')
        else:
            msg += f'\U0001F534 {world} is down'
            print(f'{world} is down')

    await ctx.respond(msg)

bot.run(TOKEN)
