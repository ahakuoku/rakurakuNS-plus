# -*- coding: utf-8 -*- 

##################################################
# 注意事項
# 使用する前に、コマンド「pip install psutil discord.py」を実行する必要があります。
# この設定ファイルは将来的に廃止され、別の手段による設定に置換される予定です。
# 各設定項目を削除したり、設定値を削除した状態で起動すると思わぬ動作の原因になることがあります。
# 
# 設定方法
# server_folder_path: サーバーフォルダのパスを指定します。「'」で囲む必要があります。
# server_name       : サーバーのファイル名を指定します。「'」で囲む必要があります。
# port_number       : ポート番号を指定します。「'」で囲む必要があります。
# autosave_backup   : オートセーブのバックアップ数を指定します。
# autosave_interval : オートセーブの間隔を秒で指定します。間隔は多少ずれるかもしれません。
# restart_time      : 毎日自動再起動を行うタイミングを時単位で指定します。5時に再起動するのであれば「5」と指定します。-1を指定すると自動再起動を行いません。
# use_discord_bot   : Discordのbotを使用するかどうか指定します。1もしくは2の場合に使用します。
# discord_token     : Discordのbotのトークンを指定します。
# discord_channel   : Discordのbotが書き込むチャンネルを指定します。
##################################################

server_folder_path = 'C:/Users/XXX/Simutrans/'
server_name        = 'sim-WinGDI64-OTRP.exe'
port_number        = '13353'
autosave_backup    = 80
autosave_interval  = 1200
restart_time       = 5
use_discord_bot    = 1
discord_token      = r'aiueo'
discord_channel    = 1234567890