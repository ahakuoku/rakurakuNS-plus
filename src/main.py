# -*- coding: utf-8 -*- 

import subprocess
import psutil
import config
import time
# import discord
import re
import datetime
import platform
import sys

# 変数定義
if config.server_folder_path.endswith('/') is True:
    server_folder_path = config.server_folder_path[:-1]
else:
    server_folder_path = config.server_folder_path
server_path = server_folder_path + '/' + config.server_name
server_save = '' + config.port_number
# intents = discord.Intents.default()
# intents.message_content = True
# client = discord.Client(intents=intents)

# 関数定義
def check_nettool():
    try:
        subprocess.run(['nettool'])
    except FileNotFoundError:
        keywait = input(f'nettoolの認識に失敗しました。nettoolを実行ファイルと同じフォルダに置いてからやり直してください。\n（らくらくNS+を終了します。Enterキーを押してください。）')
    except subprocess.CalledProcessError:
        keywait = input(f'nettoolの認識に失敗しました。nettoolを実行ファイルと同じフォルダに置いてからやり直してください。\n（らくらくNS+を終了します。Enterキーを押してください。）')
    print_with_date('nettoolの認識に成功しました。')
    return None

def check_os():
    os_system = platform.system()
    if os_system == 'Windows' or os_system == 'Linux' or os_system == 'Darwin':
        print_with_date('動作可能OSであることを確認しました。')
    else:
        keywait = input(f'らくらくNS+はお使いのOSには対応していません。らくらくNS+はWindows、Mac、Linuxに対応しています。\n（らくらくNS+を終了します。Enterキーを押してください。）')
        sys.exit()

def get_nettool_pw():
    # simuconf.tabを開き、「server_admin_pw」から始まる行を検索
    simuconf_path = server_folder_path + '/config/simuconf.tab'
    f = open(simuconf_path, 'r', encoding='utf-8')
    line = f.readline()
    while line:
        line = f.readline()
        if line.startswith('server_admin_pw'):
            nettool_password_tmp = line
    f.close()
    # 行頭の「server_admin_pw = 」を削除し返す
    nettool_password = re.sub('^server_admin_pw( *= *)', '', nettool_password_tmp)
    print_with_date('nettoolのパスワード取得に成功しました。')
    return nettool_password

def print_with_date(content):
    date_time = datetime.datetime.now()
    print(date_time.strftime('[%Y/%m/%d %H:%M:%S] ' + content))
    return None

def get_pid(process_name):
    # pidを取得する
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] == process_name:
            return proc.info['pid']
    return None

def restart():
    # pidを取得する
    server_pid = get_pid(config.server_name)
    first_start = 0
    # PIDがNoneなら起動する
    if server_pid is None:
        app_process = app_start()
        if first_start == 0:
            print_with_date('サーバーを起動します。')
        elif first_start == 1:
            print_with_date('サーバーダウンを検出しました。再起動します。')
            swm_discord_post('サーバーダウンを検出しました。', '現在復旧中です。しばらくお待ちください。', '16711680')
            # @client.event
            # async def on_ready():
                # Discordに鯖落ち通知を送信
                # channel = client.get_channel(config.discord_channel)
                # await channel.send(embed=discord.Embed(title='サーバーダウンを検出しました。', description='現在復旧中です。しばらくお待ちください。', color=0xff0000))
        first_start = 1
    return None

def app_start():
    os_system = platform.system()
    if os_system == 'Windows':
        return subprocess.Popen([server_path, '-server', config.port_number, '-fps', '30', '-nomidi', '-nosound'], creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    elif os_system == 'Linux' or os_system == 'Darwin':
        return subprocess.Popen([server_path, '-server', config.port_number, '-fps', '30', '-nomidi', '-nosound'], start_new_session=True)

def swm_discord_post(title, description, color):
    # Simutrans World Monitorを利用してDiscordに書き込み
    discord_io_file_plain = server_folder_path + '/file_io/out.txt'
    discord_io_file_embed = server_folder_path + '/file_io/out_embed.json'
    if config.use_discord_bot == 1:
        f = open(discord_io_file_plain, 'w')
        f.write('# ' + title + '\n' + description + '\n')
        f.close()
    elif config.use_discord_bot == 2:
        title = title.replace('\n', '\\n')
        description = description.replace('\n', '\\n')
        f = open(discord_io_file_embed, 'w')
        f.write('{"description":"' + description + '","fields":null,"title":"' + title + '","color":' + color + ',"footer":null}')

def nettool_say(content):
    # contentにはASCII文字以外を入れないこと（文字化け対策）
    nettool_pw = get_nettool_pw()
    subprocess.run(['nettool', '-p', nettool_pw, '-s', '127.0.0.1:' + config.port_number, 'say', content])
    return None

def wait_simutrans_responce():
    nettool_pw = get_nettool_pw()
    print_with_date('Simutransの応答を待っています。しばらくお待ちください。')
    while True:
        result = subprocess.run(['nettool', '-p', nettool_pw, '-s', '127.0.0.1:' + config.port_number, 'clients'], encoding='utf-8', stdout=subprocess.PIPE, text=True)
        if result.returncode == 0:
            print_with_date('Simutransが応答しました。処理を再開します。')
            break

def start():
    check_os()
    check_nettool()
    restart()
    # client.run(config.discord_token)

start()