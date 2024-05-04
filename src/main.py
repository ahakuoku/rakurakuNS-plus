# -*- coding: utf-8 -*- 

import subprocess
import psutil
try:
    import config
except ModuleNotFoundError:
    keywait = input(f'config.template.pyをコピーし、config.pyにリネームして設定を行ってください。\n（らくらくNS+を終了します。Enterキーを押してください。）')
import time
# import discord
import re
import datetime
import platform
import sys
import os
import shutil
import threading

# 変数定義
if config.server_folder_path.endswith('/') is True:
    server_folder_path = config.server_folder_path[:-1]
else:
    server_folder_path = config.server_folder_path
server_path = server_folder_path + '/' + config.server_name
server_path = server_path.replace('\\', '/')
server_save = 'server' + config.port_number + '-network.sve'
start_code = 0
# intents = discord.Intents.default()
# intents.message_content = True
# client = discord.Client(intents=intents)

# 関数定義
def check_nettool():
    # nettoolの存在確認
    try:
        subprocess.run(['nettool'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        keywait = input(f'nettoolの認識に失敗しました。nettoolを実行ファイルと同じフォルダに置いてからやり直してください。\n（らくらくNS+を終了します。Enterキーを押してください。）')
    except subprocess.CalledProcessError:
        keywait = input(f'nettoolの認識に失敗しました。nettoolを実行ファイルと同じフォルダに置いてからやり直してください。\n（らくらくNS+を終了します。Enterキーを押してください。）')
    print_with_date('nettoolの認識に成功しました。')
    return None

def check_os():
    # 実行OSがWindows、Mac、Linuxのいずれかであることを確認する
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
    # 日時とcontentを表示する
    date_time = datetime.datetime.now()
    print(date_time.strftime('[%Y/%m/%d %H:%M:%S] ' + content))
    return None

def get_pid(process_name):
    # pidを取得する
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] == process_name:
            return proc.info['pid']
    return None

def set_company_pw():
    # パスワードを設定する
    nettool_pw = get_nettool_pw()
    company_pws = [config.player_0_pw, config.player_1_pw, config.player_2_pw, config.player_3_pw, config.player_4_pw, config.player_5_pw, config.player_6_pw, config.player_7_pw, config.player_8_pw, config.player_9_pw, config.player_10_pw, config.player_11_pw, config.player_12_pw, config.player_13_pw, config.player_14_pw]
    i = 0
    for company_pw in company_pws:
        # クラッシュ対策（存在しない会社にパスワードをかけるとクラッシュする）
        company_id = str(i)
        result = subprocess.run(['nettool', '-p', nettool_pw, '-s', '127.0.0.1:' + config.port_number, 'info-company', company_id], capture_output=True, text=True)
        # Nothing received.の後は改行が必要
        if result.stdout != 'Nothing received.\n' and company_pw != '':
            subprocess.run(['nettool', '-p', nettool_pw, '-s', '127.0.0.1:' + config.port_number, 'lock-company', company_id, company_pw], capture_output=True, text=True)
        i += 1
    print_with_date('会社にパスワードを設定しました。')

def app_start():
    # Simutransを起動する
    os_system = platform.system()
    # WindowsとUNIX系OSでコマンドが違うのでその対策
    if os_system == 'Windows':
        return subprocess.Popen(['start', server_path, '-server', config.port_number, '-fps', '30', '-nomidi', '-nosound', '-load', server_save], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif os_system == 'Linux' or os_system == 'Darwin':
        return subprocess.Popen([server_path, '-server', config.port_number, '-fps', '30', '-nomidi', '-nosound', '-load', server_save], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)

def swm_discord_post(title, description, color):
    # Simutrans World Monitorを利用してDiscordに書き込み
    discord_io_file_plain = server_folder_path + '/file_io/out.txt'
    discord_io_file_embed = server_folder_path + '/file_io/out_embed.json'
    if config.use_discord_bot == 1:
        f = open(discord_io_file_plain, 'w', encoding='utf-8')
        f.write('# ' + title + '\n' + description + '\n')
        f.close()
    elif config.use_discord_bot == 2:
        title = title.replace('\n', '\\n')
        description = description.replace('\n', '\\n')
        f = open(discord_io_file_embed, 'w', encoding='utf-8')
        f.write('{"description":"' + description + '","fields":null,"title":"' + title + '","color":' + color + ',"footer":null}')

def nettool_say(content):
    # contentにはASCII文字以外を入れないこと（文字化け対策）
    nettool_pw = get_nettool_pw()
    subprocess.run(['nettool', '-p', nettool_pw, '-s', '127.0.0.1:' + config.port_number, 'say', content], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return None

def wait_simutrans_responce():
    # Simutransの応答を待つ
    nettool_pw = get_nettool_pw()
    print_with_date('Simutransの応答を待っています。しばらくお待ちください。')
    while True:
        result = subprocess.run(['nettool', '-p', nettool_pw, '-s', '127.0.0.1:' + config.port_number, 'clients'], encoding='utf-8', stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        if result.returncode == 0:
            print_with_date('Simutransが応答しました。処理を再開します。')
            break
        time.sleep(1)

def nettool_forcesync():
    # ロード処理
    nettool_pw = get_nettool_pw()
    subprocess.run(['nettool', '-p', nettool_pw, '-s', '127.0.0.1:' + config.port_number, 'force-sync'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    wait_simutrans_responce()
    save_backup()

def save_backup():
    # バックアップ
    print_with_date('セーブデータのバックアップを行います。')
    # autosaveフォルダがないなら作る
    path = server_folder_path + '/autosave'
    if not os.path.isdir(path):
        print_with_date('autosaveフォルダが存在しません。作成します。')
        os.mkdir(path)
    # バックアップ上限を超えたファイルがあるなら削除
    path = server_folder_path + '/autosave/autosave_' + str(config.autosave_backup) + '.sve'
    is_file = os.path.isfile(path)
    if is_file:
        os.remove(path)
    # 変数定義
    run_for = config.autosave_backup - 1
    backup_after_number = config.autosave_backup
    # バックアップ済みのファイルの名称変更
    for i in range(run_for):
        backup_before_number = backup_after_number - 1
        path = server_folder_path + '/autosave/autosave_' + str(backup_before_number) + '.sve'
        before_filename = server_folder_path + '/autosave/autosave_' + str(backup_before_number) + '.sve'
        after_filename = server_folder_path + '/autosave/autosave_' + str(backup_after_number) + '.sve'
        is_file = os.path.isfile(path)
        if is_file:
            os.rename(before_filename, after_filename)
        backup_after_number -= 1
    # ファイルをコピー
    shutil.copy(server_folder_path + '/' +  server_save, server_folder_path + '/autosave/autosave_1.sve')
    print_with_date('バックアップ処理が終了しました。')
    return None

def restart():
    global start_code
    while True:
        # PIDを取得し、Noneなら起動する
        server_pid = get_pid(config.server_name)
        if server_pid is None:
            app_process = app_start()
            # 初回起動時とそれ以外で表示メッセージを変える
            if start_code == 0:
                print_with_date('サーバーを起動します。')
                wait_simutrans_responce()
                set_company_pw()
            elif start_code == 1:
                print_with_date('サーバーダウンを検出しました。再起動します。')
                swm_discord_post('サーバーダウンを検出しました。', '現在復旧中です。しばらくお待ちください。', '16711680')
                wait_simutrans_responce()
                set_company_pw()
                print_with_date('サーバーを再起動しました。')
                swm_discord_post('サーバーが復旧しました。', 'サーバーに入る際は、過度なログインラッシュのないよう順序よくお入りください。', '65280')
        start_code = 1
        time.sleep(1)
    return None

def autosave():
    autosave_interval = config.autosave_interval - 30
    time.sleep(autosave_interval)
    while True:
        nettool_say('Autosave soon.')
        print_with_date('オートセーブ予告メッセージを送信しました。')
        time.sleep(30)
        start_time = time.time()
        print_with_date('オートセーブ中です。')
        nettool_forcesync()
        set_company_pw()
        print_with_date('オートセーブ処理が完了しました。')
        end_time = time.time()
        time_diff = end_time - start_time
        autosave_interval = autosave_interval - time_diff
        time.sleep(autosave_interval)
    return None

def start():
    check_os()
    check_nettool()
    thread_1 = threading.Thread(target=restart)
    thread_2 = threading.Thread(target=autosave)
    thread_1.start()
    thread_2.start()
    thread_1.join()
    thread_2.join()
    # client.run(config.discord_token)
    keywait = input(f'何らかの理由により、らくらくNS+を実行するために必要な処理が終了しました。\n（らくらくNS+を終了します。Enterキーを押してください。）')

start()