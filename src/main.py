import subprocess
import psutil

# 各種設定
server_folder_path = ''
server_name = 'sim-WinGDI64-OTRP.exe'
port_number = '13353'
autosave_backup = 80

# 変数定義
server_path = server_folder_path + '/' + server_name
server_save = '' + port_number

# 関数定義
def get_pid(process_name):
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] == process_name:
            return proc.info['pid']
    return None

# PIDがNoneなら起動する
server_pid = get_pid(server_name)
print(f'PID: {server_pid}')
print(f'server_path: {server_path}')
if server_pid is None:
    subprocess.Popen(['start', server_path, '-server', port_number, '-fps', '30'], shell=True)