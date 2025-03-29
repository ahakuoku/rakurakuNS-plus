# -*- coding: utf-8 -*- 

import subprocess
try:
    import config
except ModuleNotFoundError:
    keywait = input(f'config.template.pyをコピーし、config.pyにリネームして設定を行ってください。\n（らくらくNS+を終了します。Enterキーを押してください。）')
try:
    import psutil
except ModuleNotFoundError:
    keywait = input(f'必要なモジュールがインストールされていません。コマンド「pip install psutil schedule」を実行してからやりなおしてください。\n（らくらくNS+を終了します。Enterキーを押してください。）')
try:
    import schedule
except ModuleNotFoundError:
    keywait = input(f'必要なモジュールがインストールされていません。コマンド「pip install psutil schedule」を実行してからやりなおしてください。\n（らくらくNS+を終了します。Enterキーを押してください。）')
import time
# import discord
import re
import datetime
import platform
import sys
import os
import shutil
import threading
import sched
import tkinter as tk
from tkinter import ttk

# 変数定義
root = None
if config.server_folder_path.endswith('/') is True:
    server_folder_path = config.server_folder_path[:-1]
else:
    server_folder_path = config.server_folder_path
server_path = server_folder_path + '/' + config.server_name
server_path = server_path.replace('\\', '/')
server_save = 'server' + config.port_number + '-network.sve'
launch_save = '../server' + config.port_number + '-network.sve'
start_code = 0
exit_code = 0
nettool_pw = 0
scheduler = sched.scheduler(time.time, time.sleep)
scheduler_running = False
server_ip = '127.0.0.1:'
# intents = discord.Intents.default()
# intents.message_content = True
# client = discord.Client(intents=intents)

# 関数定義（GUI系）
class window_main(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.grid(row=0, column=0, sticky="nsew")
        self.master.title("らくらくNS+")
        self.master.resizable(False, False)
        self.master.geometry("550x240")
        self.maintenance_mode = 0  # メンテナンスモードの状態（0:通常, 1:メンテナンス中）
        self.create_widgets()

    def create_widgets(self):
        # Gridの設定
        self.master.grid_rowconfigure(0, weight=1)
        self.master.grid_columnconfigure(0, weight=1)

        # GUIの配置
        self.server_name_label = ttk.Label(self, text="管理対象のサーバー：" + config.server_name, anchor="w")
        self.server_name_label.grid(row=0, column=0, columnspan=4, sticky="w")

        self.log_text = tk.Text(self, width=40, height=10, wrap="word")
        self.log_text.configure(state="disabled")
        self.log_text.grid(row=1, column=0, columnspan=4, sticky="nsew")
        
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.log_text.yview)
        self.scrollbar.grid(row=1, column=4, sticky="ns")
        self.log_text.config(yscrollcommand=self.scrollbar.set)

        self.restart_button = ttk.Button(self, text="サーバー再起動", command=self.server_restart_check_start)
        self.restart_button.grid(row=2, column=0, padx=5, pady=10, sticky="w")

        # メンテナンスモードボタン
        self.maintenance_mode_button = ttk.Button(
            self, text="メンテナンスモード", command=self.maintenance_check_start
        )
        self.maintenance_mode_button.grid(row=2, column=1, padx=5, pady=10, sticky="w")

        self.server_stop_button = ttk.Button(self, text="サーバー終了", command=self.server_close_check_start)
        self.server_stop_button.grid(row=2, column=2, padx=5, pady=10, sticky="w")

        self.exit_button = ttk.Button(self, text="らくらくNS+を終了", style='Accent.TButton', command=self.exit_check_start)
        self.exit_button.grid(row=2, column=3, padx=5, pady=10, sticky="w")

    def server_restart_check_start(self):
        # 確認ダイアログを開く
        if hasattr(self, "newWindow") and self.newWindow.winfo_exists():
            self.newWindow.lift()
            return

        self.newWindow = tk.Toplevel(self.master)
        self.newWindow.grab_set()
        server_restart_check(self.newWindow)

    def exit_check_start(self):
        # 確認ダイアログを開く
        if hasattr(self, "newWindow") and self.newWindow.winfo_exists():
            self.newWindow.lift()
            return

        self.newWindow = tk.Toplevel(self.master)
        self.newWindow.grab_set()
        exit_check(self.newWindow)

    def server_close_check_start(self):
        # 確認ダイアログを開く
        if hasattr(self, "newWindow") and self.newWindow.winfo_exists():
            self.newWindow.lift()
            return

        self.newWindow = tk.Toplevel(self.master)
        self.newWindow.grab_set()
        server_close_check(self.newWindow)

    def maintenance_check_start(self):
        # メンテナンスモード確認ダイアログを開く
        if hasattr(self, "newWindow") and self.newWindow.winfo_exists():
            self.newWindow.lift()
            return

        self.newWindow = tk.Toplevel(self.master)
        self.newWindow.grab_set()
        maintenance_check(self.newWindow, self)  # 自分自身を渡す

    def toggle_maintenance_mode(self):
        # メンテナンスモードの切り替え
        global start_code
        if self.maintenance_mode == 0:
            start_code = 3
            self.maintenance_mode = 1
            self.maintenance_mode_button["text"] = "メンテナンス終了"
        else:
            self.maintenance_mode = 0
            self.maintenance_mode_button["text"] = "メンテナンスモード"

    def log_text_insert(self, content):
        # 他スレッドからも呼び出せる安全な方法
        self.master.after(0, self._log_text_insert, content)

    def _log_text_insert(self, content):
        # 実際にTkinterのUIを更新する処理（必ずメインスレッドで実行）
        self.log_text.configure(state="normal")
        self.log_text.insert('end', content + '\n')
        self.log_text.configure(state="disabled")
        self.log_text.see("end")

class maintenance_check(tk.Frame):
    # メンテナンスモード確認ダイアログウィンドウ
    def __init__(self, master, main_window):
        super().__init__(master)
        self.master = master  # 既存のToplevelを受け取る
        self.main_window = main_window  # メインウィンドウの参照
        self.master.title("らくらくNS+")
        self.master.resizable(False, False)
        self.master.geometry("350x120")
        self.master.protocol('WM_DELETE_WINDOW', self.close_window)

        self.create_widgets()

    def create_widgets(self):
        # ダイアログのウィジェットを配置
        if self.main_window.maintenance_mode == 0:
            self.label = ttk.Label(self.master, text="サーバーを中断しメンテナンスモードに入ります。\nよろしいですか？")
        else:
            self.label = ttk.Label(self.master, text="メンテナンスモードを終了しサーバーを再開します。\nよろしいですか？")

        self.label.pack(padx=10, pady=10, fill="both", expand=True)

        button_frame = ttk.Frame(self.master)
        button_frame.pack(pady=10, fill="x")

        self.exit_button = ttk.Button(button_frame, text="はい", style='Accent.TButton', command=self.maintenance_mode_check)
        self.exit_button.pack(side="left", padx=5, expand=True)

        self.cancel_button = ttk.Button(button_frame, text="いいえ", command=self.close_window)
        self.cancel_button.pack(side="right", padx=5, expand=True)

    def close_window(self):
        # ダイアログを閉じる
        self.master.destroy()

    def maintenance_mode_check(self):
        # メンテナンスモードかどうかをチェックし、メンテナンスモードの実行/解除
        global start_code
        if start_code == 3:
            start_code = 4
        else:
            maintenance_thread = threading.Thread(target=self.server_stop_thread, args=(3,))
            maintenance_thread.start()
        self.main_window.toggle_maintenance_mode()  # メインウィンドウのボタンを更新
        self.master.destroy()  # ダイアログを閉じる

    def server_stop_thread(self, set_code):
        # サーバー終了処理をバックグラウンドで実行
        server_stop(set_code)

class exit_check(tk.Frame):
    # 確認ダイアログウィンドウ
    def __init__(self, master):
        super().__init__(master)
        self.master = master  # 既存のToplevelを受け取る
        self.master.title("らくらくNS+")
        self.master.resizable(False, False)
        self.master.geometry("250x120")
        self.master.protocol('WM_DELETE_WINDOW', self.close_window)

        self.create_widgets()

    def create_widgets(self):
        # ダイアログのウィジェットを配置
        self.label = ttk.Label(self.master, text="らくらくNS+を終了します。\nよろしいですか？")
        self.label.pack(padx=10, pady=10, fill="both", expand=True)

        button_frame = ttk.Frame(self.master)
        button_frame.pack(pady=10, fill="x")

        self.exit_button = ttk.Button(button_frame, text="はい", style='Accent.TButton', command=self.exit_app)
        self.exit_button.pack(side="left", padx=5, expand=True)

        self.cancel_button = ttk.Button(button_frame, text="いいえ", command=self.close_window)
        self.cancel_button.pack(side="right", padx=5, expand=True)

    def close_window(self):
        # ダイアログを閉じる
        self.master.destroy()

    def exit_app(self):
        # アプリケーションを終了する
        self.master.destroy()  # ダイアログを閉じる
        self.master.master.destroy()  # メインウィンドウも閉じる

class server_close_check(tk.Frame):
    # 確認ダイアログウィンドウ
    def __init__(self, master):
        super().__init__(master)
        self.master = master  # 既存のToplevelを受け取る
        self.master.title("らくらくNS+")
        self.master.resizable(False, False)
        self.master.geometry("320x120")
        self.master.protocol('WM_DELETE_WINDOW', self.close_window)

        self.create_widgets()

    def create_widgets(self):
        # ダイアログのウィジェットを配置
        self.label = ttk.Label(self.master, text="サーバーを終了し、らくらくNS+を終了します。\nよろしいですか？")
        self.label.pack(padx=10, pady=10, fill="both", expand=True)

        button_frame = ttk.Frame(self.master)
        button_frame.pack(pady=10, fill="x")

        self.exit_button = ttk.Button(button_frame, text="はい", style='Accent.TButton', command=self.exit_server)
        self.exit_button.pack(side="left", padx=5, expand=True)

        self.cancel_button = ttk.Button(button_frame, text="いいえ", command=self.close_window)
        self.cancel_button.pack(side="right", padx=5, expand=True)

    def close_window(self):
        # ダイアログを閉じる
        self.master.destroy()

    def exit_server(self):
        # サーバーを終了する
        exit_thread = threading.Thread(target=self.server_stop_thread, args=(5,))
        exit_thread.start()
        self.master.destroy()

    def server_stop_thread(self, set_code):
        # サーバー終了処理をバックグラウンドで実行
        server_stop(set_code)
        self.master.after(0, self.close_main_window)

    def close_main_window(self):
        # メインウィンドウを閉じる
        self.master.master.quit()
        self.master.master.destroy()

class server_restart_check(tk.Frame):
    # 確認ダイアログウィンドウ
    def __init__(self, master):
        super().__init__(master)
        self.master = master  # 既存のToplevelを受け取る
        self.master.title("らくらくNS+")
        self.master.resizable(False, False)
        self.master.geometry("250x120")
        self.master.protocol('WM_DELETE_WINDOW', self.close_window)

        self.create_widgets()

    def create_widgets(self):
        # ダイアログのウィジェットを配置
        self.label = ttk.Label(self.master, text="サーバーを再起動します。\nよろしいですか？")
        self.label.pack(padx=10, pady=10, fill="both", expand=True)

        button_frame = ttk.Frame(self.master)
        button_frame.pack(pady=10, fill="x")

        self.exit_button = ttk.Button(button_frame, text="はい", style='Accent.TButton', command=self.restart_server)
        self.exit_button.pack(side="left", padx=5, expand=True)

        self.cancel_button = ttk.Button(button_frame, text="いいえ", command=self.close_window)
        self.cancel_button.pack(side="right", padx=5, expand=True)

    def close_window(self):
        # ダイアログを閉じる
        self.master.destroy()

    def restart_server(self):
        # 再起動する
        restart_server_threaded(2)
        self.master.destroy()  # ダイアログを閉じる

def gui_main():
    global app
    root = tk.Tk()
    root.tk.call("source", "azure.tcl")
    root.tk.call("set_theme", "light")

    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)

    app = window_main(master=root)
    app.mainloop()
    return None

def print_gui_log(content):
    # GUIのログに追記
    date_time = datetime.datetime.now()
    content = date_time.strftime('[%Y/%m/%d %H:%M:%S] ' + content)
    app.log_text_insert(content)
    return None

def restart_server_threaded(set_code):
    thread = threading.Thread(target=server_stop, args=(set_code,))
    thread.start()

# 関数定義（GUI系以外）
def check_nettool():
    # nettoolの存在確認
    try:
        subprocess.run(['nettool'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        keywait = input(f'nettoolの認識に失敗しました。nettoolをらくらくNS+の実行ファイルと同じフォルダに置いてからやり直してください。\n（らくらくNS+を終了します。Enterキーを押してください。）')
    except subprocess.CalledProcessError:
        keywait = input(f'nettoolの認識に失敗しました。nettoolをらくらくNS+の実行ファイルと同じフォルダに置いてからやり直してください。\n（らくらくNS+を終了します。Enterキーを押してください。）')
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

def check_config():
    # 設定チェック
    try:
        hour = int(config.restart_time)
        if hour == -1 or 0 <= hour <= 24:
            pass
        else:
            keywait = input(f'設定「restart_time」に不正な値が入力されています。-1、0～24のいずれかの整数を入力してください。\n（らくらくNS+を終了します。Enterキーを押してください。）')
            sys.exit()
    except ValueError:
        keywait = input(f'設定「restart_time」に不正な値が入力されています。-1、0～24のいずれかの整数を入力してください。\n（らくらくNS+を終了します。Enterキーを押してください。）')
    print_with_date('設定に正常な値が入力されていることを確認しました。')
    return None

def convert_to_time(hour):
    if hour == -1:
        pass
    elif 0 <= hour <= 24:
        if hour == 24:
            return time(0, 0, 0)
        return time(hour, 0, 0)
    return time(0, 0, 0)

def schedule_event(hour, minute, second, action):
    # 関数を予約する
    now = datetime.datetime.now()
    run_time = now.replace(hour=hour, minute=minute, second=second, microsecond=0)
    if run_time <= now:
        run_time += datetime.timedelta(days=1)
    delay = (run_time - now).total_seconds()
    scheduler.enter(delay, 1, action)
    if not scheduler.empty():
        scheduler.run()

def get_nettool_pw(output):
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
    if output == 0:
        print_with_date('nettoolのパスワード取得に成功しました。')
    else:
        print_gui_log('nettoolのパスワード取得に成功しました。')
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
    global nettool_pw
    company_pws = [config.player_0_pw, config.player_1_pw, config.player_2_pw, config.player_3_pw, config.player_4_pw, config.player_5_pw, config.player_6_pw, config.player_7_pw, config.player_8_pw, config.player_9_pw, config.player_10_pw, config.player_11_pw, config.player_12_pw, config.player_13_pw, config.player_14_pw]
    i = 0
    for company_pw in company_pws:
        # クラッシュ対策（存在しない会社にパスワードをかけるとクラッシュする）
        company_id = str(i)
        result = subprocess.run(['nettool', '-p', nettool_pw, '-s', server_ip + config.port_number, 'info-company', company_id], capture_output=True, text=True, encoding='utf-8')
        # Nothing received.の後は改行が必要
        if result.stdout != 'Nothing received.\n' and company_pw != '':
            subprocess.run(['nettool', '-p', nettool_pw, '-s', server_ip + config.port_number, 'lock-company', company_id, company_pw], capture_output=True, text=True)
        i += 1
    print_gui_log('会社にパスワードを設定しました。')

def app_start():
    # Simutransを起動する
    os_system = platform.system()
    # WindowsとUNIX系OSでコマンドが違うのでその対策
    if os_system == 'Windows':
        return subprocess.Popen(['start', server_path, '-server', config.port_number, '-fps', '30', '-nomidi', '-nosound', '-load', launch_save], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif os_system == 'Linux' or os_system == 'Darwin':
        return subprocess.Popen([server_path, '-server', config.port_number, '-fps', '30', '-nomidi', '-nosound', '-load', launch_save], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)

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
    global nettool_pw
    subprocess.run(['nettool', '-p', nettool_pw, '-s', server_ip + config.port_number, 'say', content], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return None

def wait_simutrans_responce():
    # Simutransの応答を待つ
    global nettool_pw
    print_gui_log('Simutransの応答を待っています。しばらくお待ちください。')
    while True:
        result = subprocess.run(['nettool', '-p', nettool_pw, '-s', server_ip + config.port_number, 'clients'], encoding='utf-8', stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        if result.returncode == 0:
            print_gui_log('Simutransが応答しました。処理を再開します。')
            break
        time.sleep(1)

def nettool_forcesync():
    # ロード処理
    global nettool_pw
    subprocess.run(['nettool', '-p', nettool_pw, '-s', server_ip + config.port_number, 'force-sync'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    wait_simutrans_responce()
    save_backup()

def save_backup():
    # バックアップ
    print_gui_log('セーブデータのバックアップを行います。')
    # autosaveフォルダがないなら作る
    path = server_folder_path + '/autosave'
    if not os.path.isdir(path):
        print_gui_log('autosaveフォルダが存在しません。作成します。')
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
    print_gui_log('バックアップ処理が終了しました。')
    return None

def server_stop(set_code):
    # サーバーを止める機能
    global nettool_pw
    global start_code
    if set_code == 2:
        if start_code == 3:
            return None
        nettool_say('Server restart soon.')
        print_gui_log('再起動予告メッセージを送信しました。')
        swm_discord_post('まもなく再起動を行います。', 'これからのログインはおやめください。', '16760576')
    elif set_code == 3:
        nettool_say('Maintenance soon.')
        print_gui_log('メンテナンス予告メッセージを送信しました。')
        swm_discord_post('まもなくメンテナンスです。', 'これからのログインはおやめください。', '16760576')
    elif set_code == 5:
        nettool_say('Server close soon.')
        print_gui_log('サーバー終了予告メッセージを送信しました。')
        swm_discord_post('まもなくサーバーを終了します。', 'これからのログインはおやめください。', '16760576')
    time.sleep(30)
    nettool_forcesync()
    if set_code == 2:
        nettool_say('Server is restarting.')
        print_gui_log('再起動中告知メッセージを送信しました。')
    elif set_code == 3:
        nettool_say('Maintenance start.')
        print_gui_log('メンテナンス告知メッセージを送信しました。')
        swm_discord_post('ただいまメンテナンス中です。', 'メンテナンス中でもサーバーに入れる場合がありますが、許可なく入らないでください。', '16760576')
    elif set_code == 5:
        nettool_say('Server is close. Thank you for playing!')
        print_gui_log('サーバー終了告知メッセージを送信しました。')
        swm_discord_post('サーバーは終了しました。', '皆様のご参加ありがとうございました。', '65280')
    start_code = set_code
    subprocess.run(['nettool', '-p', nettool_pw, '-s', server_ip + config.port_number, 'shutdown'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # if config.restart_time == 0:
    #     restart_time = 23
    # else:
    #     restart_time = config.restart_time - 1
    # schedule_event(restart_time, 59, 30, lambda: server_stop(2))
    return None

def auto_restart():
    # サーバー定時再起動
    global nettool_pw
    global start_code
    if config.restart_time != -1:
        if config.restart_time == 0:
            restart_time = 23
        else:
            restart_time = config.restart_time - 1
        schedule.every().days.at(restart_time + ":59:30").do(server_stop(2))
        while True:
            schedule.run_pending()
            time.sleep(1)
        # schedule_event(restart_time, 59, 30, lambda: server_stop(2))
    return None

def monitoring():
    global start_code
    global nettool_pw
    server_pid = get_pid(config.server_name)
    if not server_pid is None:
        # 初回起動時、サーバー起動済みであった場合の処理
        print_gui_log('サーバーは起動済みです。')
        start_code = 1
    while True:
        # start_codeが3（メンテナンス中）であれば処理を行わない
        if not start_code == 3:
            # PIDを取得し、Noneなら起動する
            server_pid = get_pid(config.server_name)
            if server_pid is None:
                app_process = app_start()
                # 初回起動時とそれ以外で表示メッセージを変える
                if start_code == 0:
                    print_gui_log('サーバーを起動します。')
                    nettool_pw = get_nettool_pw(1)
                    wait_simutrans_responce()
                    set_company_pw()
                    start_code = 1
                elif start_code == 1:
                    print_gui_log('サーバーダウンを検出しました。再起動します。')
                    swm_discord_post('サーバーダウンを検出しました。', '現在復旧中です。しばらくお待ちください。', '16711680')
                    nettool_pw = get_nettool_pw(1)
                    wait_simutrans_responce()
                    set_company_pw()
                    print_gui_log('サーバーを再起動しました。')
                    swm_discord_post('サーバーが復旧しました。', 'サーバーに入る際は、過度なログインラッシュのないよう順序よくお入りください。', '65280')
                elif start_code == 2:
                    print_gui_log('サーバーを起動します。')
                    nettool_pw = get_nettool_pw(1)
                    wait_simutrans_responce()
                    set_company_pw()
                    print_gui_log('サーバーを起動しました。')
                    swm_discord_post('サーバーを再起動しました。', 'サーバーに入る際は、過度なログインラッシュのないよう順序よくお入りください。', '65280')
                elif start_code == 4:
                    print_gui_log('サーバーを再開します。')
                    nettool_pw = get_nettool_pw(1)
                    wait_simutrans_responce()
                    set_company_pw()
                    print_gui_log('サーバーを再開しました。')
                    swm_discord_post('メンテナンスを終了しました。', '皆様のご協力ありがとうございました。', '65280')
                    start_code = 1
                elif start_code == 5:
                    break
        time.sleep(1)
    return None

def autosave():
    # オートセーブ処理
    autosave_interval = config.autosave_interval - 30
    time.sleep(autosave_interval)
    while True:
        nettool_say('Autosave soon.')
        print_gui_log('オートセーブ予告メッセージを送信しました。')
        time.sleep(30)
        start_time = time.time()
        print_gui_log('オートセーブ中です。')
        nettool_forcesync()
        set_company_pw()
        print_gui_log('オートセーブ処理が完了しました。')
        end_time = time.time()
        time_diff = end_time - start_time
        autosave_interval = config.autosave_interval - 30
        next_autosave_in = autosave_interval - time_diff
        if next_autosave_in > 0:
            time.sleep(next_autosave_in)
        else:
            time.sleep(1)
    return None

if __name__ == "__main__":
    check_os()
    check_config()
    check_nettool()
    nettool_pw = get_nettool_pw(0)

    thread_1 = threading.Thread(target=gui_main)
    thread_1.start()

    time.sleep(1)

    thread_2 = threading.Thread(target=monitoring, daemon=True)
    thread_2.start()

    thread_3 = threading.Thread(target=autosave, daemon=True)
    thread_3.start()

    thread_4 = threading.Thread(target=auto_restart, daemon=True)
    thread_4.start()

    thread_1.join()

    # client.run(config.discord_token)