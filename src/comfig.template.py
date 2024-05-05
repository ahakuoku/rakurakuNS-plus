# -*- coding: utf-8 -*- 

##################################################
# 注意事項
# 「config.template,py」をコピーして「config.py」にリネームしてから設定してください。
# 使用する前に、コマンド「pip install psutil discord.py」を実行する必要があります。
# この設定ファイルは将来的に廃止され、別の手段による設定に置換される予定です。
# 各設定項目を削除したり、設定値を削除した状態で起動すると思わぬ動作の原因になることがあります。
# 
# 開発版特有の注意
# 現在、開発の初期段階のため一部設定が使用されていません。
# 使用されていないのは「restart_time」です。
# 
# Discordへの書き込みについて
# 現在暫定的にSimutrans World Monitorとの連携を使用しています。
# このため、Discord関連の設定方法は下記の「設定方法」と異なります。
# 「use_discord_bot」は1の場合はプレーンテキストを書き込み、2の場合はembedで書き込みます。
# 「discord_token」「discord_channel」は現在使用していません。
# 
# 設定方法
# server_folder_path: サーバーフォルダのパスを指定します。「'」で囲み、囲みの前に「r」が存在する必要があります。
# server_name       : サーバーのファイル名を指定します。「'」で囲む必要があります。
# port_number       : ポート番号を指定します。「'」で囲む必要があります。
# autosave_backup   : オートセーブのバックアップ数を指定します。
# autosave_interval : オートセーブの間隔を秒で指定します。間隔は多少ずれるかもしれません。
# player_n_pw       : 各会社のパスワードを設定します。0がプレイヤー会社、1が公共事業です。空欄にするとパスワードを設定しません。
# restart_time      : 毎日自動再起動を行うタイミングを時単位で指定します。5時に再起動するのであれば「5」と指定します。-1を指定すると自動再起動を行いません。
# use_discord_bot   : Discordのbotを使用するかどうか指定します。0の場合は使用せず、1もしくは2の場合に使用します。
# discord_token     : Discordのbotのトークンを指定します。
# discord_channel   : Discordのbotが書き込むチャンネルを指定します。
##################################################

server_folder_path = r'C:/Users/XXX/Simutrans'
server_name        = 'sim-WinGDI64-OTRP.exe'
port_number        = '13353'
autosave_backup    = 80
autosave_interval  = 1200
player_0_pw        = ''
player_1_pw        = ''
player_2_pw        = ''
player_3_pw        = ''
player_4_pw        = ''
player_5_pw        = ''
player_6_pw        = ''
player_7_pw        = ''
player_8_pw        = ''
player_9_pw        = ''
player_10_pw       = ''
player_11_pw       = ''
player_12_pw       = ''
player_13_pw       = ''
player_14_pw       = ''
restart_time       = ''
use_discord_bot    = 1
discord_token      = r'aiueo'
discord_channel    = 1234567890