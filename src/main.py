# -*- coding: utf-8 -*- 

import subprocess
import psutil
import config
import time
import discord
import re

# 変数定義
server_path = config.server_folder_path + '/' + config.server_name
server_save = '' + config.port_number
client = discord.Client()

# 関数定義
def get_nettool_pw():
    # simuconf.tabを開き、「server_admin_pw」から始まる行を検索
    simuconf_path = config.server_folder_path + '/config/simuconf.tab'
    f = open(simuconf_path, 'r', encoding='utf-8')
    line = f.readline()
    while line:
        line = f.readline()
        if line.startswith('server_admin_pw'):
            print(line)
            nettool_password_tmp = line
    f.close()
    # 行頭の「server_admin_pw = 」を削除し返す
    nettool_password = re.sub('^server_admin_pw( *= *)', '', nettool_password_tmp)
    print(nettool_password)
    return nettool_password

def get_pid(process_name):
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] == process_name:
            return proc.info['pid']
    return None

def restart(crash):
    server_pid = get_pid(config.server_name)
    print(f'PID: {server_pid}')
    print(f'server_path: {server_path}')
    if server_pid is None:
        subprocess.Popen(['start', server_path, '-server', config.port_number, '-fps', '30'], shell=True)
    return None


# PIDがNoneなら起動する
