# -*- coding: utf-8 -*- 

import os
import platform
import sys
import datetime
try:
    from watchfiles import watch
except ModuleNotFoundError:
    keywait = input(f'必要なモジュールがインストールされていません。コマンド「pip install psutil watchfiles」を実行してからやりなおしてください。\n（らくらくNS+を終了します。Enterキーを押してください。）')

# 変数定義
command_dir = 'command_file'
command_input_file = os.path.abspath('./command_file/cmd_input.txt')
command_output_file = os.path.abspath('./command_file/cmd_output.txt')
action_type_map = {
    1: "Added",
    2: "Modified",
    3: "Deleted",
}

# 関数定義
def check_os():
    # 実行OSがWindows、Mac、Linuxのいずれかであることを確認する
    os_system = platform.system()
    if os_system == 'Windows' or os_system == 'Linux' or os_system == 'Darwin':
        print_with_date('動作可能OSであることを確認しました。')
    else:
        keywait = input(f'らくらくNS+はお使いのOSには対応していません。らくらくNS+はWindows、Mac、Linuxに対応しています。\n（らくらくNS+を終了します。Enterキーを押してください。）')
        sys.exit()

def print_with_date(content):
    # 日時とcontentを表示する
    date_time = datetime.datetime.now()
    print(date_time.strftime('[%Y/%m/%d %H:%M:%S] ' + content))
    return None

def cmd_file_generate():
    if not os.path.exists(command_dir):
        os.makedirs(command_dir)
        f = open(command_input_file, 'w')
        f.close()
        f = open(command_output_file, 'w')
        f.close()
    return None

def command_control():
    while True:
        command = input('コマンドを入力してください。コマンド一覧はhelpと入力してください: ')
        with open(command_input_file, 'w') as f:
            f.write(command)
        for changes in watch(os.path.dirname(command_output_file)):
            for action, file_path in changes:
                normalized_file_path = os.path.normpath(file_path)
                if normalized_file_path == os.path.normpath(command_output_file) and action_type_map.get(action) == "Modified":
                    try:
                        with open(command_output_file, 'r', encoding='UTF-8') as f:
                            data = f.read()
                        print(f'{data}')
                    except Exception as e:
                        print(f'ファイルの読み取りに失敗しました。{e}\n（らくらくNS+を終了します。Enterキーを押してください。）')
                    break
            else:
                continue
            break

def start():
    check_os()
    cmd_file_generate()
    print_with_date('らくらくNS+ コマンド入力用ウィンドウ')
    command_control()
    keywait = input(f'何らかの理由により、らくらくNS+を実行するために必要な処理が終了しました。\n（らくらくNS+を終了します。Enterキーを押してください。）')

start()