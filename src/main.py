# -*- coding: utf-8 -*- 

import subprocess
import psutil
import config

# 変数定義
server_path = config.server_folder_path + '/' + config.server_name
server_save = '' + config.port_number

# 関数定義
def get_pid(process_name):
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] == process_name:
            return proc.info['pid']
    return None

# PIDがNoneなら起動する
server_pid = get_pid(config.server_name)
print(f'PID: {server_pid}')
print(f'server_path: {server_path}')
if server_pid is None:
    subprocess.Popen(['start', server_path, '-server', config.port_number, '-fps', '30'], shell=True)