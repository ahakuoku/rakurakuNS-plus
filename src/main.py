# -*- coding: utf-8 -*- 

import subprocess
import sys
import importlib.util
import os

try:
    import yaml
except ModuleNotFoundError:
    input(
        '必要なモジュールがインストールされていません。\n'
        'コマンド「pip install psutil schedule discord PyYAML」を実行してからやりなおしてください。\n'
        '（らくらくNS+を終了します。Enterキーを押してください。）'
    )
    sys.exit()

try:

    # exe起動時
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)

    # 通常Python実行時
    else:
        base_dir = os.path.dirname(os.path.realpath(__file__))

    config_path = os.path.join(base_dir, 'config.yaml')

    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as config_file:
            config_data = yaml.safe_load(config_file) or {}
    else:
        config_data = {}

except Exception:

    keywait = input(
        '設定ファイルの読み込みに失敗しました。設定画面から設定してください。\n'
        '（らくらくNS+を終了します。Enterキーを押してください。）'
    )

    sys.exit()

try:
    import psutil
except ModuleNotFoundError:
    input(
        '必要なモジュールがインストールされていません。\n'
        'コマンド「pip install psutil schedule discord PyYAML」を実行してからやりなおしてください。\n'
        '（らくらくNS+を終了します。Enterキーを押してください。）'
    )
    sys.exit()

try:
    import schedule
except ModuleNotFoundError:
    input(
        '必要なモジュールがインストールされていません。\n'
        'コマンド「pip install psutil schedule discord PyYAML」を実行してからやりなおしてください。\n'
        '（らくらくNS+を終了します。Enterキーを押してください。）'
    )
    sys.exit()

import time

try:
    import discord
except ModuleNotFoundError:
    input(
        '必要なモジュールがインストールされていません。\n'
        'コマンド「pip install psutil schedule discord PyYAML」を実行してからやりなおしてください。\n'
        '（らくらくNS+を終了します。Enterキーを押してください。）'
    )
    sys.exit()

import re
import datetime
import platform
import shutil
import threading
import sched
import asyncio
import ctypes

try:
    import tkinter as tk
except ModuleNotFoundError:
    input(
        '必要なモジュールがインストールされていません。\n'
        'コマンド「pip install psutil schedule discord PyYAML」を実行してからやりなおしてください。\n'
        '（らくらくNS+を終了します。Enterキーを押してください。）'
    )
    sys.exit()

from tkinter import ttk, filedialog, messagebox
import array
import tempfile

# 変数定義
intents = discord.Intents.default()
bot = discord.Client(intents=intents)

CONFIG_DISPLAY_NAMES = {
    'path': 'サーバー実行ファイル',
    'port': 'ポート',
    'restart_time': '自動再起動時刻',
    'press_space_after_start': '起動30秒後にスペースキーを押す',
    'mode': 'オートセーブモード',
    'backup_count': 'バックアップ数',
    'interval': 'オートセーブ間隔',
    'long_term_keep_days': '長期バックアップ保存日数',
    'long_term_time': '長期バックアップ実行時刻',
    'enabled': 'Discord botの使用設定',
    'autosave_notice': 'Discordでオートセーブを告知する',
    'token': 'Discord botトークン',
    'channel': 'DiscordチャンネルID',
    'passwords': 'プレイヤーパスワード',
    'ban_ips': 'BAN IP',
}

def load_config():
    global config, config_data
    with open(config_path, 'r', encoding='utf-8') as config_file:
        config_data = yaml.safe_load(config_file) or {}
    config = type('Config', (), {})()
    server = config_data.get('server', {})
    server_path = server.get('path')
    if server_path is None:
        # 旧形式のYAMLも読み込めるようにする。
        folder_path = server.get('folder_path', '')
        server_name = server.get('name', '')
        separator = '\\' if '\\' in str(folder_path) and '/' not in str(folder_path) else '/'
        server_path = f'{folder_path}{separator}{server_name}'
    server_path = str(server_path)
    separator_positions = [position for position in (server_path.rfind('/'), server_path.rfind('\\')) if position >= 0]
    separator_position = max(separator_positions, default=-1)
    config.server_folder_path = server_path[:separator_position] if separator_position >= 0 else ''
    config.server_name = server_path[separator_position + 1:] if separator_position >= 0 else server_path
    config.port_number = server.get('port')
    config.restart_time = server.get('restart_time')
    config.press_space_after_start = server.get('press_space_after_start', 0)
    autosave = config_data.get('autosave', {})
    config.autosave_mode = autosave.get('mode')
    config.autosave_backup = autosave.get('backup_count')
    config.autosave_interval = autosave.get('interval')
    backup = config_data.get('backup', {})
    config.long_backup_keep = backup.get('long_term_keep_days')
    config.long_backup_time = backup.get('long_term_time')
    players = config_data.get('players', {}).get('passwords', {})
    ban_ips = config_data.get('network', {}).get('ban_ips', {})
    for i in range(63):
        setattr(config, f'player_{i}_pw', players.get(i, players.get(str(i), '')))
        setattr(config, f'banip_{i}', ban_ips.get(i, ban_ips.get(str(i), '')))
    discord_settings = config_data.get('discord', {})
    config.use_discord_bot = discord_settings.get('enabled', 0)
    config.discord_token = discord_settings.get('token', '')
    config.discord_channel = discord_settings.get('channel', '')
    config.discord_autosave_notice = discord_settings.get('autosave_notice', 0)

def default_config_data():
    return {
        'server': {'path': '', 'port': '13353', 'restart_time': -1, 'press_space_after_start': 0},
        'autosave': {'mode': 0, 'backup_count': 80, 'interval': 1200},
        'backup': {'long_term_keep_days': 0, 'long_term_time': 5},
        'players': {'passwords': {i: '' for i in range(63)}},
        'network': {'ban_ips': {i: '' for i in range(63)}},
        'discord': {'enabled': 0, 'token': '', 'channel': '', 'autosave_notice': 0},
        # アプリケーション内部状態。設定画面には表示しない。
        'runtime': {
            'maintenance_mode': 0,
            'update_schedule': None,
            'next_autosave_at': None,
        },
    }

def persist_runtime_state():
    """設定画面では編集できない、再起動後も必要な内部状態を保存する。"""
    runtime = {
        'maintenance_mode': int(getattr(app, 'maintenance_mode', 0)) if 'app' in globals() else 0,
        'update_schedule': None,
        'next_autosave_at': globals().get('next_autosave_at'),
    }
    item = globals().get('scheduled_updates')
    if item is not None:
        runtime['update_schedule'] = {
            'when': item['when'].isoformat(),
            'body': item.get('body'),
            'pak': item.get('pak'),
            'backup': item.get('backup', 0),
            'discord_notice': item.get('discord_notice', 0),
            'restart_server': item.get('restart_server', 1),
        }
    data = dict(config_data)
    data['runtime'] = runtime
    config_data['runtime'] = runtime
    with open(config_path, 'w', encoding='utf-8') as config_file:
        yaml.safe_dump(data, config_file, allow_unicode=True, sort_keys=False)

def restore_runtime_state():
    global scheduled_updates, next_autosave_at
    runtime = config_data.get('runtime', {})
    app.maintenance_mode = int(runtime.get('maintenance_mode', 0) or 0)
    app.update_maintenance_button()
    next_autosave_at = runtime.get('next_autosave_at')
    saved = runtime.get('update_schedule')
    if saved:
        try:
            when = datetime.datetime.fromisoformat(str(saved['when']))
            # 予定時刻を過ぎていても予約を復元し、更新ループで直ちに実行する。
            scheduled_updates = {
                'when': when, 'body': saved.get('body'), 'pak': saved.get('pak'),
                'backup': saved.get('backup', 0),
                'discord_notice': saved.get('discord_notice', 0),
                'restart_server': saved.get('restart_server', 1),
            }
        except (KeyError, TypeError, ValueError):
            scheduled_updates = None

class config_window:
    def __init__(self, master, first_run=False):
        self.master = master
        self.first_run = first_run
        self.window = tk.Toplevel(master)
        self.window.title('設定')
        self.window.geometry('980x620')
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        self.fields = {}
        self.secret_entries = {'token': [], 'passwords': []}
        self.secret_visibility = {'token': tk.IntVar(value=0), 'passwords': tk.IntVar(value=0)}
        data = config_data if config_data else default_config_data()
        notebook = ttk.Notebook(self.window)
        notebook.pack(fill='both', expand=True, padx=8, pady=8)
        server_values = data.get('server', {})
        if 'path' not in server_values:
            folder = server_values.get('folder_path', '')
            name = server_values.get('name', '')
            separator = '\\' if '\\' in str(folder) and '/' not in str(folder) else '/'
            server_values = dict(server_values)
            server_values['path'] = f'{folder}{separator}{name}' if folder or name else ''
        self.add_tab(notebook, 'サーバー', ['path', 'port', 'restart_time', 'press_space_after_start'], server_values)
        self.add_tab(notebook, 'オートセーブ', ['mode', 'backup_count', 'interval'], data.get('autosave', {}))
        self.add_tab(notebook, 'バックアップ', ['long_term_keep_days', 'long_term_time'], data.get('backup', {}))
        self.add_tab(notebook, 'Discord', ['enabled', 'autosave_notice', 'token', 'channel'], data.get('discord', {}))
        self.add_password_tab(notebook, data.get('players', {}).get('passwords', {}))
        self.add_multiline_tab(notebook, 'BAN IP', 'ban_ips', data.get('network', {}).get('ban_ips', {}))
        button_frame = ttk.Frame(self.window)
        button_frame.pack(fill='x', padx=8, pady=(0, 8))
        ttk.Button(button_frame, text='らくらくNS+ v0.2.0以前の設定ファイルをインポート', command=self.import_legacy_config).pack(side='left')
        ttk.Button(button_frame, text='らくらくNS（bat版）の設定をインポート', command=self.import_setting_bat).pack(side='left', padx=(8, 0))
        ttk.Button(button_frame, text='保存', style='Accent.TButton', command=self.save).pack(side='right', padx=(8, 0))
        ttk.Button(button_frame, text='キャンセル', command=self.close).pack(side='right')
        self.window.transient(master)
        self.window.grab_set()

    def add_tab(self, notebook, title, fields, values):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text=title)
        is_server_tab = title == 'サーバー'
        is_discord_tab = title == 'Discord'
        if is_server_tab or is_discord_tab:
            frame.grid_columnconfigure(1, weight=1)
        for row, key in enumerate(fields):
            ttk.Label(frame, text=CONFIG_DISPLAY_NAMES[key]).grid(row=row, column=0, sticky='w', padx=10, pady=8)
            if key == 'mode':
                try:
                    mode = int(values.get(key, 0) or 0)
                except (TypeError, ValueError):
                    mode = 0
                variable = tk.IntVar(value=mode if mode in (0, 1) else 0)
                mode_frame = ttk.Frame(frame)
                mode_frame.grid(row=row, column=1, sticky='w', padx=10, pady=8)
                ttk.Radiobutton(
                    mode_frame, text='一定間隔', variable=variable, value=0
                ).pack(side='left', padx=(0, 16))
                ttk.Radiobutton(
                    mode_frame, text='最後のロードからの経過時間', variable=variable, value=1
                ).pack(side='left')
                self.fields[key] = variable
            elif key in ('enabled', 'autosave_notice', 'press_space_after_start'):
                variable = tk.IntVar(value=1 if int(values.get(key, 0) or 0) in (1, 2) else 0)
                text = '使用する' if key == 'enabled' else '有効にする'
                entry = ttk.Checkbutton(frame, text=text, style='Switch.TCheckbutton', variable=variable)
                entry.grid(row=row, column=1, sticky='w', padx=10, pady=8)
                self.fields[key] = variable
            else:
                entry = ttk.Entry(frame, width=48, show='*' if key == 'token' else '')
                entry.insert(0, str(values.get(key, '')))
                entry.grid(
                    row=row, column=1,
                    columnspan=2 if (is_server_tab and key != 'path') or (is_discord_tab and key != 'token') else 1,
                    sticky='ew', padx=10, pady=8
                )
                self.fields[key] = entry
                if key == 'path':
                    ttk.Button(
                        frame, text='参照…', command=self.select_server_executable
                    ).grid(row=row, column=2, padx=5, pady=8)
                if key == 'token':
                    self.secret_entries['token'].append(entry)
                    ttk.Checkbutton(
                        frame, text='表示', variable=self.secret_visibility['token'],
                        style='Switch.TCheckbutton',
                        command=lambda: self.toggle_secret('token')
                    ).grid(row=row, column=2 if is_discord_tab else 3, padx=5, pady=8)
            help_column = 3 if is_server_tab or is_discord_tab else 2
            ttk.Button(frame, text='説明', command=lambda k=key: self.show_help(k)).grid(row=row, column=help_column, padx=5, pady=8)

    def select_server_executable(self):
        """ファイル選択ダイアログでサーバー実行ファイルを指定する。"""
        current_path = self.fields['path'].get().strip()
        initial_dir = os.path.dirname(current_path) if current_path else ''
        if platform.system() == 'Windows':
            filetypes = [
                ('実行ファイル', '*.exe'),
                ('すべてのファイル', '*.*'),
            ]
        else:
            # Linux/macOSの実行ファイルは拡張子を持たないことが多いため、
            # 拡張子では絞り込まず、すべてのファイルを選択対象にする。
            filetypes = [('実行ファイル', '*')]
        path = filedialog.askopenfilename(
            title='サーバー実行ファイルを選択',
            initialdir=initial_dir if os.path.isdir(initial_dir) else None,
            filetypes=filetypes,
            parent=self.window,
        )
        if path:
            self.fields['path'].delete(0, 'end')
            self.fields['path'].insert(0, path)

    def add_multiline_tab(self, notebook, title, key, values):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text=title)
        ttk.Label(frame, text='番号=値（1行に1件）').pack(anchor='w', padx=10, pady=8)
        ttk.Button(frame, text='説明', command=lambda k=key: self.show_help(k)).pack(anchor='e', padx=10)
        text = tk.Text(frame, width=65, height=25)
        text.pack(fill='both', expand=True, padx=10, pady=5)
        for i in range(63):
            value = values.get(i, values.get(str(i), ''))
            if value not in (None, ''):
                text.insert('end', f'{i}={value}\n')
        self.fields[key] = text

    def add_password_tab(self, notebook, values):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text='プレイヤー')
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        ttk.Label(
            frame,
            text='会社ごとのパスワード（15番以降はOTRP v59_0_2以降専用）'
        ).grid(row=0, column=0, sticky='w', padx=10, pady=8)
        ttk.Checkbutton(
            frame, text='パスワードを表示', variable=self.secret_visibility['passwords'],
            style='Switch.TCheckbutton',
            command=lambda: self.toggle_secret('passwords')
        ).grid(row=0, column=1, sticky='w', padx=10, pady=8)
        canvas_frame = ttk.Frame(frame)
        canvas_frame.grid(row=1, column=0, sticky='nsew', padx=5)
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)
        canvas = tk.Canvas(canvas_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky='nsew')
        scrollbar.grid(row=0, column=1, sticky='ns')
        contents = ttk.Frame(canvas)
        canvas_window = canvas.create_window((0, 0), window=contents, anchor='nw')
        contents.bind('<Configure>', lambda event: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda event: canvas.itemconfigure(canvas_window, width=event.width))
        canvas.bind('<MouseWheel>', lambda event: canvas.yview_scroll(-int(event.delta / 120), 'units'))
        contents.bind('<MouseWheel>', lambda event: canvas.yview_scroll(-int(event.delta / 120), 'units'))
        canvas.bind('<Button-4>', lambda event: canvas.yview_scroll(-1, 'units'))
        canvas.bind('<Button-5>', lambda event: canvas.yview_scroll(1, 'units'))
        contents.bind('<Button-4>', lambda event: canvas.yview_scroll(-1, 'units'))
        contents.bind('<Button-5>', lambda event: canvas.yview_scroll(1, 'units'))
        password_fields = {}
        for i in range(63):
            column = (i // 21) * 2
            row = (i % 21) + 1
            ttk.Label(contents, text=f'会社 {i}').grid(row=row, column=column, sticky='w', padx=(10, 4), pady=3)
            entry = ttk.Entry(contents, width=22, show='*')
            value = values.get(i, values.get(str(i), ''))
            entry.insert(0, str(value or ''))
            entry.grid(row=row, column=column + 1, sticky='w', padx=(0, 18), pady=3)
            entry.bind('<MouseWheel>', lambda event: canvas.yview_scroll(-int(event.delta / 120), 'units'))
            entry.bind('<Button-4>', lambda event: canvas.yview_scroll(-1, 'units'))
            entry.bind('<Button-5>', lambda event: canvas.yview_scroll(1, 'units'))
            password_fields[i] = entry
            self.secret_entries['passwords'].append(entry)
        ttk.Button(frame, text='説明', command=lambda: self.show_help('passwords')).grid(row=2, column=0, padx=10, pady=8, sticky='w')
        self.fields['passwords'] = password_fields

    def toggle_secret(self, key):
        show = '' if self.secret_visibility[key].get() else '*'
        for entry in self.secret_entries[key]:
            entry.configure(show=show)

    def show_help(self, key):
        descriptions = {
            'path': '起動するSimutransサーバーの実行ファイルを、フォルダを含むフルパスで指定します。',
            'port': 'サーバーが使用するポート番号を指定します。',
            'restart_time': '毎日自動再起動する時刻を0～24で指定します。-1で無効です。',
            'press_space_after_start': '有効にすると、Simutransの起動開始から30秒後にスペースキーを1回送信します。Standard以外の本体では通常必要ありません。',
            'mode': 'オートセーブのモードを選択します。「一定間隔」は指定した間隔ごとに、「最後のロードからの経過時間」は最後にロードしてから指定した時間が経過した時点でオートセーブします。',
            'backup_count': 'オートセーブのバックアップ保存数を指定します。',
            'interval': 'オートセーブの間隔を秒で指定します。60以上を指定してください。',
            'long_term_keep_days': '長期バックアップの保存日数です。0で無効、-1で無期限です。',
            'long_term_time': '長期バックアップを実行する時刻を0～24で指定します。',
            'enabled': 'Discord botを使用するか切り替えます。オンにすると有効です。',
            'autosave_notice': '有効にすると、オートセーブ開始30秒前の予告をDiscordに投稿します。Discord botの使用設定が有効な場合に利用できます。なお、Discordの通知が非常に多くなるため利用は推奨しません。',
            'token': 'Discord botのトークンを指定します。',
            'channel': 'Discord botが書き込むチャンネルIDを指定します。',
            'passwords': '会社番号ごとのパスワードを入力します。空欄の会社にはパスワードを設定しません。',
            'ban_ips': '番号=IPアドレスの形式で入力します。1行に1件、番号は0～62です。',
        }
        messagebox.showinfo('設定項目の説明', descriptions.get(key, 'この項目の説明はありません。'), parent=self.window)

    def import_legacy_config(self):
        path = filedialog.askopenfilename(
            title='インポートするconfig.pyを選択',
            filetypes=[('Python設定ファイル', 'config.py'), ('Pythonファイル', '*.py')],
            parent=self.window,
        )
        if not path:
            return
        try:
            spec = importlib.util.spec_from_file_location('legacy_config', path)
            legacy = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(legacy)
            legacy_folder_path = str(getattr(legacy, 'server_folder_path', ''))
            legacy_server_name = str(getattr(legacy, 'server_name', ''))
            if '\\' in legacy_folder_path and '/' in legacy_folder_path:
                # 区切り文字が混在している場合は、スラッシュへ統一する。
                legacy_folder_path = legacy_folder_path.replace('\\', '/')
                legacy_separator = '/'
            elif '\\' in legacy_folder_path:
                legacy_separator = '\\'
            else:
                legacy_separator = '/'
            values = {
                'path': f'{legacy_folder_path.rstrip(chr(92) + "/")}{legacy_separator}{legacy_server_name}',
                'port': getattr(legacy, 'port_number', '13353'),
                'restart_time': getattr(legacy, 'restart_time', -1),
                'press_space_after_start': getattr(legacy, 'press_space_after_start', 0),
                'mode': getattr(legacy, 'autosave_mode', 0),
                'backup_count': getattr(legacy, 'autosave_backup', 80),
                'interval': getattr(legacy, 'autosave_interval', 1200),
                'long_term_keep_days': getattr(legacy, 'long_backup_keep', 0),
                'long_term_time': getattr(legacy, 'long_backup_time', 5),
                'enabled': getattr(legacy, 'use_discord_bot', 0),
                'autosave_notice': getattr(legacy, 'discord_autosave_notice', 0),
                'token': getattr(legacy, 'discord_token', ''),
                'channel': getattr(legacy, 'discord_channel', ''),
            }
            for key, value in values.items():
                if key == 'mode':
                    # mode is represented by radio buttons backed by IntVar.
                    self.fields[key].set(1 if int(value or 0) == 1 else 0)
                elif key in ('enabled', 'autosave_notice', 'press_space_after_start'):
                    self.fields[key].set(1 if int(value or 0) in (1, 2) else 0)
                else:
                    self.fields[key].delete(0, 'end')
                    self.fields[key].insert(0, str(value))
            for i in range(63):
                value = getattr(legacy, f'player_{i}_pw', '')
                self.fields['passwords'][i].delete(0, 'end')
                self.fields['passwords'][i].insert(0, str(value or ''))
            text = self.fields['ban_ips']
            text.delete('1.0', 'end')
            for i in range(63):
                value = getattr(legacy, f'banip_{i}', '')
                if value not in ('', None):
                    text.insert('end', f'{i}={value}\n')
            messagebox.showinfo('インポート完了', 'config.pyの設定を画面に反映しました。保存するとconfig.yamlが作成されます。', parent=self.window)
        except Exception as error:
            messagebox.showerror('インポート失敗', f'config.pyを読み込めませんでした。\n{error}', parent=self.window)

    def import_setting_bat(self):
        path = filedialog.askopenfilename(
            title='インポートするsetting.batを選択',
            filetypes=[('設定ファイル', 'setting.bat'), ('バッチファイル', '*.bat')],
            parent=self.window,
        )
        if not path:
            return
        try:
            settings = {}
            with open(path, 'r', encoding='cp932', errors='replace') as setting_file:
                for line in setting_file:
                    line = line.strip()
                    if not line.lower().startswith('set ') or '=' not in line:
                        continue
                    key, value = line[4:].split('=', 1)
                    settings[key.strip()] = value.strip().strip('"')

            launch_file = settings.get('launch_file') or settings.get('check_exe', '')
            setting_directory = os.path.dirname(os.path.abspath(path))
            server_path = os.path.join(setting_directory, launch_file) if launch_file else ''
            self.fields['path'].delete(0, 'end')
            self.fields['path'].insert(0, server_path)

            server_address = settings.get('server_address', '')
            if ':' in server_address:
                self.fields['port'].delete(0, 'end')
                self.fields['port'].insert(0, server_address.rsplit(':', 1)[1])

            if settings.get('autosave_interval') is not None:
                self.fields['interval'].delete(0, 'end')
                self.fields['interval'].insert(0, settings['autosave_interval'])

            # bat版の変数名はバージョン差があるため、既知の表記を順に受け付ける。
            autosave_notice = next(
                (settings[key] for key in (
                    'discord_autosave_notice', 'discord_autosave',
                    'autosave_discord_notice', 'discord_save_notice'
                ) if key in settings),
                None,
            )
            if autosave_notice is not None:
                self.fields['autosave_notice'].set(
                    1 if str(autosave_notice).strip().lower() in ('1', '2', 'true', 'on', 'yes') else 0
                )

            for i in range(63):
                self.fields['passwords'][i].delete(0, 'end')
            for i in range(1, 4):
                number = settings.get(f'company_password_{i}_number', '-1')
                password = settings.get(f'company_password_{i}', '')
                if number.lstrip('-').isdigit() and 0 <= int(number) < 63:
                    self.fields['passwords'][int(number)].insert(0, password)

            ban_text = self.fields['ban_ips']
            ban_text.delete('1.0', 'end')
            for i in range(1, 64):
                address = settings.get(f'ban_address_{i}', '')
                if address:
                    ban_text.insert('end', f'{i - 1}={address}\n')
            messagebox.showinfo('インポート完了', 'setting.batの設定を画面に反映しました。保存するとconfig.yamlが作成されます。', parent=self.window)
        except Exception as error:
            messagebox.showerror('インポート失敗', f'setting.batを読み込めませんでした。\n{error}', parent=self.window)

    def save(self):
        data = default_config_data()
        # 設定画面にない内部状態を保持する。
        data['runtime'] = config_data.get('runtime', data['runtime'])
        for key in ('server', 'autosave', 'backup', 'discord'):
            for name in data[key]:
                data[key][name] = self.fields[name].get()
        for i, entry in self.fields['passwords'].items():
            data['players']['passwords'][i] = entry.get()
        for line in self.fields['ban_ips'].get('1.0', 'end').splitlines():
            if '=' in line:
                index, value = line.split('=', 1)
                if index.strip().isdigit() and 0 <= int(index) < 63:
                    data['network']['ban_ips'][int(index)] = value
        error = self.validate_config_data(data)
        if error:
            messagebox.showerror('入力エラー', error, parent=self.window)
            return
        with open(config_path, 'w', encoding='utf-8') as config_file:
            yaml.safe_dump(data, config_file, allow_unicode=True, sort_keys=False)
        # 保存直後にYAMLを読み込み直し、アプリ内の設定も更新する。
        load_config()
        if not self.first_run:
            check_config()
            app.server_name_label.config(text='管理対象のサーバー：' + config.server_name)
        self.close()

    def validate_config_data(self, data):
        server_path = str(data['server']['path']).strip()
        if not server_path:
            return f'「{CONFIG_DISPLAY_NAMES["path"]}」のパスを入力してください。'
        if not os.path.isfile(server_path):
            return f'指定された「{CONFIG_DISPLAY_NAMES["path"]}」が存在しません。'

        integer_rules = (
            ('server.port', data['server']['port'], 0, 65535),
            ('server.restart_time', data['server']['restart_time'], -1, 24),
            ('server.press_space_after_start', data['server']['press_space_after_start'], 0, 1),
            ('autosave.mode', data['autosave']['mode'], 0, 1),
            ('autosave.backup_count', data['autosave']['backup_count'], 1, None),
            ('autosave.interval', data['autosave']['interval'], 60, None),
            ('backup.long_term_keep_days', data['backup']['long_term_keep_days'], -1, None),
            ('backup.long_term_time', data['backup']['long_term_time'], 0, 24),
            ('discord.enabled', data['discord']['enabled'], 0, 2),
            ('discord.autosave_notice', data['discord']['autosave_notice'], 0, 1),
        )
        for name, value, minimum, maximum in integer_rules:
            display_name = CONFIG_DISPLAY_NAMES[name.split('.')[-1]]
            try:
                number = int(value)
            except (TypeError, ValueError):
                return f'設定「{display_name}」には整数を入力してください。'
            if number < minimum or (maximum is not None and number > maximum):
                return f'設定「{display_name}」の値が範囲外です。'
        if int(data['discord']['enabled']) in (1, 2):
            if not str(data['discord']['token']).strip():
                return f'{CONFIG_DISPLAY_NAMES["enabled"]}を有効にする場合は、{CONFIG_DISPLAY_NAMES["token"]}を入力してください。'
            try:
                int(data['discord']['channel'])
            except (TypeError, ValueError):
                return f'設定「{CONFIG_DISPLAY_NAMES["channel"]}」には整数を入力してください。'
        return None

    def close(self):
        self.window.grab_release()
        self.window.destroy()

# 関数定義（GUI系）
class window_main(tk.Frame):
    def __init__(self, master):
        global os_type
        super().__init__(master)
        self.grid(row=0, column=0, sticky="nsew")
        self.master.title("らくらくNS+")
        self.master.resizable(False, False)
        if os_type == "Linux":
            self.master.geometry("550x370")
        else:
            self.master.geometry("550x330")
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
            self, text="サーバーを一時停止", command=self.maintenance_check_start
        )
        self.maintenance_mode_button.grid(row=2, column=2, padx=5, pady=10, sticky="w")

        self.server_stop_button = ttk.Button(self, text="会期終了", command=self.server_close_check_start)
        self.server_stop_button.grid(row=3, column=3, padx=5, pady=(0, 10), sticky="ew")

        self.update_schedule_button = ttk.Button(
            self, text="本体・Pakの更新をスケジュール", command=self.update_schedule_start
        )
        self.update_schedule_button.grid(row=3, column=0, columnspan=2, padx=5, pady=(0, 10), sticky="ew")

        self.settings_button = ttk.Button(self, text="設定", command=self.open_settings)
        self.settings_button.grid(row=4, column=2, padx=5, pady=(0, 10), sticky="ew")

        self.exit_button = ttk.Button(self, text="らくらくNS+を終了", style='Accent.TButton', command=self.exit_check_start)
        self.exit_button.grid(row=4, column=3, padx=5, pady=(0, 10), sticky="ew")

    def open_settings(self):
        if hasattr(self, "newWindow") and self.newWindow.winfo_exists():
            self.newWindow.lift()
            return
        self.newWindow = config_window(self.master).window

    def update_schedule_start(self):
        if hasattr(self, "newWindow") and self.newWindow.winfo_exists():
            self.newWindow.lift()
            return
        self.newWindow = tk.Toplevel(self.master)
        self.newWindow.grab_set()
        update_schedule_window(self.newWindow)

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

    def update_maintenance_button(self):
            if self.maintenance_mode == 0:
                text = "サーバーを一時停止"
            elif self.maintenance_mode == 1:
                text = "サーバーを再開"
            elif self.maintenance_mode == 2:
                text = "サーバーを再開"

            self.maintenance_mode_button.config(text=text)
            self.maintenance_mode_button.update_idletasks()

    def toggle_maintenance_mode(self):
        global start_code

        # 手動再開モード
        if self.maintenance_mode == 2:
            start_code = 7
            self.maintenance_mode = 0

        # 通常 → メンテ
        elif self.maintenance_mode == 0:
            start_code = 3
            self.maintenance_mode = 1

        # メンテ → 通常
        elif self.maintenance_mode == 1:
            self.maintenance_mode = 0
        
        self.update_maintenance_button()
        persist_runtime_state()

    def set_manual_restart_mode(self):
        self.maintenance_mode = 2
        self.update_maintenance_button()
        persist_runtime_state()

    def log_text_insert(self, content):
        # 他スレッドからも呼び出せる安全な方法
        self.master.after(0, self._log_text_insert, content)

    def _log_text_insert(self, content):
        # 実際にTkinterのUIを更新する処理（必ずメインスレッドで実行）
        self.log_text.configure(state="normal")
        self.log_text.insert('end', content + '\n')
        self.log_text.configure(state="disabled")
        self.log_text.see("end")

class update_schedule_window(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.master.title("本体・Pakの更新をスケジュール")
        # 下部の通知設定・操作ボタンが画面外へ出ないよう、内容に合わせて高さを確保する
        self.master.geometry("620x500")
        self.master.minsize(620, 500)
        self.master.resizable(False, False)
        self.master.protocol('WM_DELETE_WINDOW', self.close_window)
        self.create_widgets()

    def create_widgets(self):
        self.body_var = tk.IntVar(value=0)
        self.pak_var = tk.IntVar(value=0)
        self.backup_var = tk.IntVar(value=1)
        self.discord_notice_var = tk.IntVar(value=0)
        self.restart_server_var = tk.IntVar(value=1)
        self.body_path = tk.StringVar()
        self.pak_path = tk.StringVar()
        self.time_var = tk.StringVar(value=datetime.datetime.now().strftime('%Y/%m/%d %H:%M'))

        ttk.Checkbutton(self.master, text="本体を更新する", style='Switch.TCheckbutton', variable=self.body_var).grid(row=0, column=0, padx=10, pady=8, sticky='w')
        ttk.Entry(self.master, textvariable=self.body_path, width=55).grid(row=1, column=0, padx=10, sticky='w')
        ttk.Button(self.master, text="本体ファイルを選択", command=self.choose_body).grid(row=1, column=1, padx=5)

        ttk.Checkbutton(self.master, text="Paksetを更新する", style='Switch.TCheckbutton', variable=self.pak_var).grid(row=2, column=0, padx=10, pady=8, sticky='w')
        ttk.Entry(self.master, textvariable=self.pak_path, width=55).grid(row=3, column=0, padx=10, sticky='w')
        ttk.Button(self.master, text="Paksetフォルダを選択", command=self.choose_pak).grid(row=3, column=1, padx=5)

        ttk.Label(self.master, text="更新日時（YYYY/MM/DD HH:MM、日付省略時は当日）").grid(row=4, column=0, padx=10, pady=(15, 2), sticky='w')
        ttk.Entry(self.master, textvariable=self.time_var, width=25).grid(row=5, column=0, padx=10, sticky='w')
        ttk.Checkbutton(self.master, text="更新直前のセーブデータを長期バックアップする", style='Switch.TCheckbutton', variable=self.backup_var).grid(row=6, column=0, padx=10, pady=12, sticky='w')
        ttk.Checkbutton(self.master, text="Discordに予告を投稿", style='Switch.TCheckbutton', variable=self.discord_notice_var).grid(row=7, column=0, padx=10, pady=4, sticky='w')
        ttk.Label(self.master, text="更新後の動作").grid(row=8, column=0, padx=10, pady=(8, 2), sticky='w')
        ttk.Radiobutton(self.master, text="更新完了後、サーバーを再起動する", variable=self.restart_server_var, value=1).grid(row=9, column=0, padx=25, sticky='w')
        ttk.Radiobutton(self.master, text="更新完了後、サーバーの再起動をせずにらくらくNS+を終了する", variable=self.restart_server_var, value=0).grid(row=10, column=0, padx=25, sticky='w')
        button_frame = ttk.Frame(self.master)
        button_frame.grid(row=11, column=0, columnspan=3, padx=10, pady=5, sticky='w')
        ttk.Button(button_frame, text="スケジュール登録", style='Accent.TButton', command=self.register).pack(side='left', padx=(0, 5))
        ttk.Button(button_frame, text="今すぐ更新する", command=self.update_now).pack(side='left', padx=5)
        ttk.Button(button_frame, text="スケジュールをキャンセル", command=self.cancel_schedule).pack(side='left', padx=5)
        ttk.Button(button_frame, text="キャンセル", command=self.close_window).pack(side='left', padx=(20, 5))

    def choose_body(self):
        path = filedialog.askopenfilename(title="更新する本体ファイルを選択")
        if path:
            self.body_path.set(path)

    def choose_pak(self):
        path = filedialog.askdirectory(title="更新するPaksetフォルダを選択")
        if path:
            if not os.path.isfile(os.path.join(path, 'ground.Outside.pak')):
                messagebox.showerror("Pakset確認", "これはPaksetではありません。ground.Outside.pakがあるかどうか、名前は正しいかどうかをご確認ください。（ファイル名は大文字と小文字を区別します。）", parent=self.master)
                return
            self.pak_path.set(path)

    def register(self):
        update_data = self.validate_update_inputs()
        if update_data is None:
            return
        try:
            raw = self.time_var.get().strip()
            if re.fullmatch(r'\d{1,2}:\d{2}', raw):
                raw = datetime.datetime.now().strftime('%Y/%m/%d ') + raw
            when = datetime.datetime.strptime(raw, '%Y/%m/%d %H:%M')
        except ValueError:
            messagebox.showerror("入力確認", "更新日時は YYYY/MM/DD HH:MM または HH:MM で入力してください。", parent=self.master)
            return
        if when <= datetime.datetime.now():
            messagebox.showerror("入力確認", "未来の日時を指定してください。", parent=self.master)
            return
        body, pak = update_data
        schedule_update(when, body, pak, self.backup_var.get(), self.discord_notice_var.get(), self.restart_server_var.get())
        messagebox.showinfo("登録完了", when.strftime('%Y/%m/%d %H:%M') + " に更新します。", parent=self.master)
        self.close_window()

    def validate_update_inputs(self):
        if not self.body_var.get() and not self.pak_var.get():
            messagebox.showwarning("入力確認", "本体またはPaksetのどちらかを更新する設定にしてください。", parent=self.master)
            return None
        if self.body_var.get() and not os.path.isfile(self.body_path.get()):
            messagebox.showerror("入力確認", "更新する本体ファイルを選択してください。", parent=self.master)
            return None
        if self.pak_var.get() and (not os.path.isdir(self.pak_path.get()) or not os.path.isfile(os.path.join(self.pak_path.get(), 'ground.Outside.pak'))):
            messagebox.showerror("入力確認", "更新するPaksetフォルダを選択してください。", parent=self.master)
            return None
        return (self.body_path.get() if self.body_var.get() else None,
                self.pak_path.get() if self.pak_var.get() else None)

    def update_now(self):
        update_data = self.validate_update_inputs()
        if update_data is None:
            return
        if not messagebox.askyesno("確認", "今すぐ本体・Pakの更新を開始しますか？", parent=self.master):
            return
        body, pak = update_data
        threading.Thread(target=execute_scheduled_update, args=({
            'body': body, 'pak': pak, 'backup': self.backup_var.get(),
            'restart_server': self.restart_server_var.get()
        },), daemon=True).start()
        self.close_window()

    def cancel_schedule(self):
        if not cancel_scheduled_update():
            messagebox.showinfo("確認", "キャンセルする更新スケジュールはありません。", parent=self.master)
            return
        messagebox.showinfo("キャンセル完了", "更新スケジュールをキャンセルしました。", parent=self.master)
        self.close_window()

    def close_window(self):
        self.master.destroy()


class maintenance_check(tk.Frame):
    # メンテナンスモード確認ダイアログウィンドウ
    def __init__(self, master, main_window):
        super().__init__(master)
        self.master = master  # 既存のToplevelを受け取る
        self.main_window = main_window  # メインウィンドウの参照
        self.master.title("らくらくNS+")
        self.master.resizable(False, False)
        mode = self.main_window.maintenance_mode
        os_system = platform.system()
        if mode == 0 and os_system == 'Windows':
            self.master.geometry("350x160")
        elif mode == 0 and os_system in ('Linux', 'Darwin'):
            self.master.geometry("350x175")
        else:
            self.master.geometry("350x120")
        self.master.protocol('WM_DELETE_WINDOW', self.close_window)

        self.create_widgets()

    def create_widgets(self):
        mode = self.main_window.maintenance_mode

        # 状態ごとにメッセージを変更
        if mode == 0:
            text = "サーバーを一時中断します。\nよろしいですか？"

        elif mode == 1:
            text = "サーバーを再開します。\nよろしいですか？"

        elif mode == 2:
            text = "サーバーを再開します。\nよろしいですか？"

        self.label = ttk.Label(self.master, text=text)
        self.label.pack(padx=10, pady=10, fill="both", expand=True)

        button_frame = ttk.Frame(self.master)
        button_frame.pack(pady=10, fill="x")

        self.exit_button = ttk.Button(
            button_frame,
            text="はい",
            style='Accent.TButton',
            command=self.maintenance_mode_check
        )
        self.exit_button.pack(side="left", padx=5, expand=True)

        self.cancel_button = ttk.Button(
            button_frame,
            text="いいえ",
            command=self.close_window
        )
        self.cancel_button.pack(side="right", padx=5, expand=True)

        # 長期バックアップ用スイッチ（メンテ開始時以外は出さない）
        self.long_backup_var = tk.IntVar(value=0)
        if mode == 0:
            self.switch = ttk.Checkbutton(
                self.master,
                text="メンテナンス開始時点のデータを\n長期バックアップする",
                style="Switch.TCheckbutton",
                variable=self.long_backup_var
            )
            self.switch.pack(padx=10, pady=(0, 10), anchor="w")

    def close_window(self):
        # ダイアログを閉じる
        self.master.destroy()

    def maintenance_mode_check(self):
        # メンテナンスモードかどうかをチェックし、メンテナンスモードの実行/解除
        global start_code
        mode = self.main_window.maintenance_mode

        # スイッチ状態取得（ON=1 / OFF=0）
        long_backup_code = self.long_backup_var.get()

        # 通常 → メンテナンス
        if mode == 0:
            maintenance_thread = threading.Thread(
                target=self.server_stop_thread,
                args=(3, long_backup_code)
            )
            maintenance_thread.start()

        # メンテ終了 → サーバー起動
        elif mode == 1:
            start_code = 2  # サーバー起動コード

        # 手動再開待ち → サーバー起動
        elif mode == 2:
            start_code = 7
        self.main_window.toggle_maintenance_mode()  # メインウィンドウのボタンを更新
        self.master.destroy()  # ダイアログを閉じる

    def server_stop_thread(self, set_code, long_backup_code):
        # サーバー終了処理をバックグラウンドで実行
        server_stop(set_code, long_backup_code)

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
        self.label = ttk.Label(self.master, text="サーバー会期を終了し、らくらくNS+を終了します。\nよろしいですか？")
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
        server_stop(set_code, 0)
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

def gui_main(create_app=True):
    global app

    root = tk.Tk()

    os_system = platform.system()

    # Windows
    if os_system == 'Windows':

        # タスクバー・Explorer用
        try:
            root.iconbitmap(resource_path("icon.ico"))
        except Exception:
            pass

    # 共通アイコン設定（Win/Mac/Linux）
    try:
        icon_image = tk.PhotoImage(file=resource_path("icon.png"))
        root.iconphoto(True, icon_image)

        # ガベージコレクション対策
        root.icon_image = icon_image

    except Exception:
        pass

    # テーマ読み込み
    root.tk.call("source", resource_path("azure.tcl"))
    root.tk.call("set_theme", "light")

    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)

    if create_app:
        app = window_main(master=root)

    return root

def print_gui_log(content):
    # GUIのログに追記
    date_time = datetime.datetime.now()
    content = date_time.strftime('[%Y/%m/%d %H:%M:%S] ' + content)
    app.log_text_insert(content)
    return None

def restart_server_threaded(set_code):
    thread = threading.Thread(target=server_stop, args=(set_code, 0))
    thread.start()

# 関数定義（Discord関連）
async def send_notification(
    title,
    description,
    color=0x00ff00
):

    if config.use_discord_bot not in (1, 2):
        return

    try:

        await bot.wait_until_ready()

        channel = bot.get_channel(
            int(config.discord_channel)
        )

        # チャンネル取得失敗
        if channel is None:

            print_gui_log(
                '指定されたDiscordのチャンネルはありません。'
            )

            return

        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )

        await channel.send(embed=embed)

    except ValueError:
        print_gui_log('設定「discord_channel」には整数を入力してください。')

    except discord.errors.Forbidden:
        print_gui_log('指定されたDiscordのチャンネルへの送信権限がありません。')

    except Exception as e:
        print_gui_log(f'Discordへの通知送信中にエラーが発生しました: {e}')

def discord_post(title, description, color=0x00ff00):
    if config.use_discord_bot in (1, 2):
        coro = send_notification(title, description, color)
        future = asyncio.run_coroutine_threadsafe(coro, bot.loop)
        try:
            future.result(timeout=10)
        except Exception as e:
            print_with_date(f"通知送信エラー: {e}")

def post_autosave_notice():
    """設定が有効な場合だけ、オートセーブ予告をDiscordへ送信する。"""
    if getattr(config, 'discord_autosave_notice', 0) in (1, 2):
        discord_post(
            'まもなくオートセーブです。',
            'オートセーブ完了まで、サーバーに入らないでください。',
            0xffbf00,
        )

def post_autosave_completed():
    """設定が有効な場合だけ、オートセーブ完了をDiscordへ送信する。"""
    if getattr(config, 'discord_autosave_notice', 0) in (1, 2):
        discord_post(
            'オートセーブが完了しました。',
            'サーバーに入る際は、過度なログインラッシュのないようにお願いします。',
            0x00ff00,
        )

# Bot用のスレッドターゲット
def run_discord_bot():

    if config.use_discord_bot not in (1, 2):
        return

    try:
        bot.run(config.discord_token)

    except discord.errors.LoginFailure:

        print_gui_log(
            'Discordのbotのトークンが不正です。'
            'Discordのbotを起動できませんでした。'
        )

    except Exception as e:

        print_gui_log(
            f'Discordのbotを起動中にエラーが発生しました: {e}'
        )

@bot.event
async def on_ready():
    if config.use_discord_bot in (1, 2):
            print_gui_log(f'Discordのbotを起動しました。: {bot.user}')

            channel = bot.get_channel(
                int(config.discord_channel)
            )

            if channel is None:
                print_gui_log('指定されたDiscordのチャンネルはありません。')

# 関数定義（一般）

def start_threads():
    threading.Thread(target=monitoring, daemon=True).start()
    threading.Thread(target=autosave, daemon=True).start()
    threading.Thread(target=auto_restart, daemon=True).start()
    if config.use_discord_bot in (1, 2):
        threading.Thread(target=run_discord_bot, daemon=True).start()
    threading.Thread(target=auto_long_backup, daemon=True).start()
    threading.Thread(target=scheduled_update_loop, daemon=True).start()

# 更新スケジュールは常に1件だけ保持する。新しい登録で既存の予約を置き換える。
scheduled_updates = None
scheduled_updates_lock = threading.Lock()

def schedule_update(when, body_source, pak_source, long_backup_code, discord_notice_code, restart_server_code=1):
    global scheduled_updates
    update_item = {
        'when': when, 'body': body_source, 'pak': pak_source,
        'backup': long_backup_code, 'discord_notice': discord_notice_code,
        'restart_server': restart_server_code
    }
    with scheduled_updates_lock:
        scheduled_updates = update_item
    persist_runtime_state()
    if discord_notice_code:
        if body_source and pak_source:
            update_kind = '本体・Pak更新'
        elif body_source:
            update_kind = '本体更新'
        else:
            update_kind = 'Pak更新'
        time_text = when.strftime('%H:%M') if when.date() == datetime.datetime.now().date() else when.strftime('%Y/%m/%d %H:%M')
        discord_post('メンテナンス開始時刻のお知らせ', f'{update_kind}のため、{time_text}より5分ほどメンテナンスを行います。', 0xffbf00)
    print_gui_log('本体・Pakの更新をスケジュールしました。')

def cancel_scheduled_update():
    """登録済みの更新スケジュールを取り消す。取り消せた場合はTrueを返す。"""
    global scheduled_updates
    with scheduled_updates_lock:
        if scheduled_updates is None:
            return False
        scheduled_updates = None
    persist_runtime_state()
    print_gui_log('本体・Pakの更新スケジュールをキャンセルしました。')
    return True

def scheduled_update_loop():
    while True:
        due = []
        now = datetime.datetime.now()
        global scheduled_updates
        with scheduled_updates_lock:
            if scheduled_updates is not None and scheduled_updates['when'] <= now:
                due.append(scheduled_updates)
                scheduled_updates = None
                persist_runtime_state()
        for item in due:
            threading.Thread(target=execute_scheduled_update, args=(item,), daemon=True).start()
        time.sleep(1)

def execute_scheduled_update(item):
    global start_code
    try:
        print_gui_log('スケジュールされた更新を開始します。')
        # 既存の停止処理で同期・バックアップ・サーバー停止を行う
        server_stop(3, item['backup'])
        time.sleep(2)
        replace_update_files(item['body'], item['pak'])
        if item.get('restart_server', 1):
            # 監視ループに通常起動を依頼する
            start_code = 2
            print_gui_log('更新が完了しました。サーバーを再開します。')
        else:
            # 監視ループがサーバーを起動しないようにしてからGUIを終了する。
            start_code = 8
            print_gui_log('更新が完了しました。サーバーを再起動せず、らくらくNS+を終了します。')
            app.master.after(0, app.master.destroy)
    except Exception as e:
        print_gui_log(f'スケジュール更新に失敗しました: {e}')
        start_code = 2

def replace_update_files(body_source, pak_source):
    if body_source:
        shutil.copy2(body_source, server_path)
        print_gui_log('本体を更新しました。')
    if pak_source:
        target = os.path.join(server_folder_path, 'pakset')
        os.makedirs(target, exist_ok=True)
        for name in os.listdir(pak_source):
            src = os.path.join(pak_source, name)
            dst = os.path.join(target, name)
            if os.path.isdir(src):
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
        print_gui_log('Paksetを更新しました。')

def resource_path(filename):
    # pyinstaller対策
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_dir, filename)

def check_nettool():
    # nettoolの存在確認

    try:

        nettool_path = run_nettool()

        subprocess.run(
            [nettool_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    except Exception:
        keywait = input(
            'nettoolの認識に失敗しました。\n'
            '（らくらくNS+を終了します。Enterキーを押してください。）'
        )
        sys.exit()

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
    return os_system

# 初期化・設定チェック
def check_config():
    global server_folder_path
    global server_path
    global server_save
    global launch_save
    global start_code
    global exit_code
    global nettool_pw
    global scheduler
    global scheduler_running
    global server_ip
    global intents
    global autosave_mode
    global long_backup_folder_path
    global long_backup_time
    global long_backup_keep
    global restart_time

    # ====================================================
    # 必須設定
    # ====================================================

    required_settings = (
        'server_folder_path',
        'server_name',
    )

    for setting in required_settings:
        if not hasattr(config, setting):
            input(
                f'設定「{setting}」が定義されていません。設定をしてください。\n'
                '（らくらくNS+を終了します。Enterキーを押してください。）'
            )
            sys.exit()

    # ====================================================
    # デフォルト値
    # ====================================================

    default_settings = {
        'port_number': (
            '13353',
            '設定「port_number」が定義されていません。'
            'ポート13353でサーバーを開始します。'
        ),

        'autosave_mode': (
            0,
            '設定「autosave_mode」が定義されていません。'
            '一定間隔でオートセーブを行います。'
        ),

        'autosave_backup': (
            80,
            '設定「autosave_backup」が定義されていません。'
            'バックアップは80個取ります。'
        ),

        'autosave_interval': (
            20,
            '設定「autosave_interval」が定義されていません。'
            'オートセーブは20分間隔、もしくは最後のロードから20分後に行います。'
        ),

        'long_backup_keep': (
            0,
            '設定「long_backup_keep」が定義されていません。'
            '自動長期バックアップは行いません。'
        ),

        'long_backup_time': (
            5,
            '設定「long_backup_time」が定義されていません。'
            '自動長期バックアップが有効な場合、午前5時に行います。'
        ),

        'restart_time': (
            -1,
            '設定「restart_time」が定義されていません。'
            '自動再起動は行いません。'
        ),

        'press_space_after_start': (
            0,
            '設定「press_space_after_start」が定義されていません。'
            '起動30秒後のスペースキー送信は行いません。'
        ),
    }

    for setting, (default_value, message) in default_settings.items():
        if not hasattr(config, setting):
            setattr(config, setting, default_value)
            print_with_date(message)

    # ====================================================
    # プレイヤーパスワード
    # ====================================================

    for i in range(63):
        attr_name = f'player_{i}_pw'

        if not hasattr(config, attr_name):
            setattr(config, attr_name, '')
            if i < 15:
                print_with_date(
                    f'設定「{attr_name}」が定義されていません。'
                    f'プレイヤー{i}にパスワードはかけません。'
                )

    # ====================================================
    # IPBANユーザー
    # ====================================================

    for i in range(63):
        attr_name = f'banip_{i}'

        if not hasattr(config, attr_name):
            setattr(config, attr_name, '')

    # ====================================================
    # server_folder_path
    # ====================================================

    try:
        server_folder_path = os.path.normpath(
            str(config.server_folder_path)
        )

        if not os.path.isdir(server_folder_path):
            raise FileNotFoundError

    except (NameError, TypeError, ValueError):
        input(
            '設定「server_folder_path」に不正な値が設定されています。'
            '存在するフォルダを入力してください。\n'
            '（らくらくNS+を終了します。Enterキーを押してください。）'
        )
        sys.exit()

    except FileNotFoundError:
        input(
            '設定「server_folder_path」で設定されたフォルダは存在しません。'
            '存在するフォルダを入力してください。\n'
            '（らくらくNS+を終了します。Enterキーを押してください。）'
        )
        sys.exit()

    # ====================================================
    # server_name
    # ====================================================

    try:
        server_name = str(config.server_name).strip()

        if server_name == '':
            raise ValueError

        # server_path生成
        server_path = os.path.normpath(
            os.path.join(server_folder_path, server_name)
        )

        # Linux/macOS向けに / に統一
        server_path = server_path.replace('\\', '/')

        # 存在確認
        if not os.path.exists(server_path):
            raise FileNotFoundError

    except (NameError, TypeError, ValueError):
        input(
            '設定「server_name」に不正な値が設定されています。'
            '正しいサーバー名を入力してください。\n'
            '（らくらくNS+を終了します。Enterキーを押してください。）'
        )
        sys.exit()

    except FileNotFoundError:
        input(
            '設定「server_name」で設定されたサーバーファイルが存在しません。'
            '設定を確認してください。\n'
            '（らくらくNS+を終了します。Enterキーを押してください。）'
        )
        sys.exit()

    # ====================================================
    # autosave_mode
    # ====================================================

    try:
        autosave_mode = int(config.autosave_mode)

        if autosave_mode not in (0, 1):
            raise ValueError

    except (NameError, ValueError, TypeError):
        input(
            '設定「autosave_mode」に不正な値が設定されています。'
            '0か1いずれかの値を入力してください。\n'
            '（らくらくNS+を終了します。Enterキーを押してください。）'
        )
        sys.exit()
    config.autosave_mode = autosave_mode

    # ====================================================
    # restart_time
    # ====================================================

    try:
        restart_time = int(config.restart_time)

        if restart_time != -1 and not (0 <= restart_time <= 24):
            raise ValueError

    except (NameError, ValueError, TypeError):
        input(
            '設定「restart_time」に不正な値が設定されています。'
            '-1、0～24のいずれかの整数を入力してください。\n'
            '（らくらくNS+を終了します。Enterキーを押してください。）'
        )
        sys.exit()
    config.restart_time = restart_time

    # ====================================================
    # press_space_after_start
    # ====================================================

    try:
        press_space_after_start = int(config.press_space_after_start)

        if press_space_after_start not in (0, 1):
            raise ValueError

    except (NameError, ValueError, TypeError):
        input(
            '設定「press_space_after_start」に不正な値が設定されています。'
            '0か1いずれかの値を入力してください。\n'
            '（らくらくNS+を終了します。Enterキーを押してください。）'
        )
        sys.exit()
    config.press_space_after_start = press_space_after_start

    # ====================================================
    # long_backup_keep
    # ====================================================

    try:
        long_backup_keep = int(config.long_backup_keep)

        if long_backup_keep < -1:
            raise ValueError

    except (NameError, ValueError, TypeError):
        input(
            '設定「long_backup_keep」に不正な値が設定されています。'
            '-1以上の整数を入力してください。\n'
            '（らくらくNS+を終了します。Enterキーを押してください。）'
        )
        sys.exit()
    config.long_backup_keep = long_backup_keep

    # ====================================================
    # long_backup_time
    # ====================================================

    try:
        long_backup_time = int(config.long_backup_time)

        if not (0 <= long_backup_time <= 24):
            raise ValueError

    except (NameError, ValueError, TypeError):
        input(
            '設定「long_backup_time」に不正な値が設定されています。'
            '0～24のいずれかの整数を入力してください。\n'
            '（らくらくNS+を終了します。Enterキーを押してください。）'
        )
        sys.exit()
    config.long_backup_time = long_backup_time

    # ====================================================
    # port_number
    # ====================================================

    try:
        port_number = int(config.port_number)

        if not (0 <= port_number <= 65535):
            raise ValueError

        # 文字列として再保存
        config.port_number = str(port_number)

    except (NameError, ValueError, TypeError):
        input(
            '設定「port_number」に不正な値が設定されています。'
            '0～65535のいずれかの整数を入力してください。\n'
            '（らくらくNS+を終了します。Enterキーを押してください。）'
        )
        sys.exit()

    # ====================================================
    # autosave_backup
    # ====================================================

    try:
        autosave_backup = int(config.autosave_backup)

        if autosave_backup <= 0:
            raise ValueError

    except (NameError, ValueError, TypeError):
        input(
            '設定「autosave_backup」に不正な値が設定されています。'
            '1以上の整数を入力してください。\n'
            '（らくらくNS+を終了します。Enterキーを押してください。）'
        )
        sys.exit()
    config.autosave_backup = autosave_backup

    # ====================================================
    # autosave_interval
    # ====================================================

    try:
        autosave_interval = int(config.autosave_interval)

        if autosave_interval < 60:
            raise ValueError

    except (NameError, ValueError, TypeError):
        input(
            '設定「autosave_interval」に不正な値が設定されています。'
            '60以上の整数を入力してください。\n'
            '（らくらくNS+を終了します。Enterキーを押してください。）'
        )
        sys.exit()
    config.autosave_interval = autosave_interval

    # ====================================================
    # player_x_pw
    # ====================================================

    for i in range(63):

        try:
            pw = getattr(config, f'player_{i}_pw')

            # int / floatは禁止
            # （'1' のような文字列は許可）
            if isinstance(pw, (int, float)):
                raise ValueError

            # 文字列化
            setattr(config, f'player_{i}_pw', str(pw))

        except (NameError, ValueError, TypeError):
            input(
                f'設定「player_{i}_pw」に不正な値が設定されています。'
                '文字列を入力してください。\n'
                '（らくらくNS+を終了します。Enterキーを押してください。）'
            )
            sys.exit()

    # ====================================================
    # banip_x
    # ====================================================

    for i in range(63):

        try:
            ip = getattr(config, f'banip_{i}')

            # int / floatは禁止
            # （'1' のような文字列は許可）
            if isinstance(ip, (int, float)):
                raise ValueError

            # 文字列化
            setattr(config, f'banip_{i}', str(ip))

        except (NameError, ValueError, TypeError):
            input(
                f'設定「banip_{i}」に不正な値が設定されています。'
                '文字列を入力してください。\n'
                '（らくらくNS+を終了します。Enterキーを押してください。）'
            )
            sys.exit()

    # ====================================================
    # use_discord_bot
    # ====================================================

    if not hasattr(config, 'use_discord_bot'):
        config.use_discord_bot = 0
        print_with_date(
            '設定「use_discord_bot」が定義されていません。'
            'Discordのbotは使用しません。'
        )

    try:
        use_discord_bot = int(config.use_discord_bot)

        if use_discord_bot not in (0, 1, 2):
            raise ValueError

    except (NameError, ValueError, TypeError):
        input(
            '設定「use_discord_bot」に不正な値が設定されています。'
            '0、1、2のいずれかを入力してください。\n'
            '（らくらくNS+を終了します。Enterキーを押してください。）'
        )
        sys.exit()
    config.use_discord_bot = use_discord_bot

    # ====================================================
    # 各種パス・変数生成
    # ====================================================

    server_save = f'server{config.port_number}-network.sve'
    launch_save = os.path.join(
        '..',
        f'server{config.port_number}-network.sve'
    )

    long_backup_folder_path = os.path.join(
        server_folder_path,
        'autosave',
        'long-backup'
    )

    # Linux/macOS向けに / に統一
    server_path = server_path.replace('\\', '/')
    launch_save = launch_save.replace('\\', '/')
    long_backup_folder_path = long_backup_folder_path.replace('\\', '/')

    # ====================================================
    # 初期変数
    # ====================================================

    start_code = 0
    exit_code = 0
    nettool_pw = 0

    scheduler = sched.scheduler(time.time, time.sleep)
    scheduler_running = False

    server_ip = '127.0.0.1:'

    print_with_date('設定に正常な値が入力されていることを確認しました。')

    return None

def get_savefile_timestamp(type):
    # typeが0なら文字列分単位、1なら文字列秒単位、2なら配列で取得する
    pt = server_folder_path + '/' + server_save
    if os.path.isfile(pt) == True:
        unix_time = os.path.getctime(pt)
        dt = datetime.datetime.fromtimestamp(int(unix_time))
        if type == 0:
            final_time = dt.strftime("%H:%M")
        elif type == 1:
            final_time = dt.strftime("%H:%M:%S")
        elif type == 2:
            for_hour = dt.hour
            for_minute = dt.minute
            for_second = dt.second
            final_time = array.array('i', [for_hour, for_minute, for_second])
    else:
        if type == 0:
            final_time = "99:99"
        elif type == 1:
            final_time = "99:99:99"
        elif type == 2:
            final_time = array.array('i', [99, 99, 99])
    return final_time

def convert_to_time(hour):
    if hour == -1:
        pass
    elif 0 <= hour <= 24:
        if hour == 24:
            return time(0, 0, 0)
        return time(hour, 0, 0)
    return time(0, 0, 0)

def run_nettool():
    # Windows
    if platform.system() == 'Windows':

        # PyInstaller実行時
        if getattr(sys, 'frozen', False):

            internal_path = resource_path('nettool.exe')

            # 一時フォルダへコピー
            temp_dir = tempfile.gettempdir()
            external_path = os.path.join(temp_dir, 'nettool.exe')

            # 上書きコピー
            shutil.copy2(internal_path, external_path)

            return external_path

        # 通常Python実行時
        else:
            return resource_path('nettool.exe')

    # Linux/macOS
    else:
        return 'nettool'

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
    nettool_password_tmp2 = re.sub('^server_admin_pw( *= *)', '', nettool_password_tmp)
    nettool_password = nettool_password_tmp2.rstrip('\n')
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

def get_pid(target_name):

    # 指定したプロセスのPIDを取得し、ゾンビプロセスがあれば回収する。

    target_pid = None

    # システム上の全プロセスをスキャン（必要な情報だけ取得して高速化）
    for proc in psutil.process_iter(['pid', 'name', 'status']):
        try:
            # 1. 名前が一致するかチェック
            if proc.info['name'] == target_name:
                
                # 2. ゾンビ状態（終了済みだがリストに残っている）の場合
                if proc.info['status'] == psutil.STATUS_ZOMBIE:
                    try:
                        # ゾンビを回収（親プロセスとして終了ステータスを読み取る）
                        # timeout=0 なので、一瞬で処理が終わります
                        proc.wait(timeout=0)
                        # print(f"DEBUG: Zombie process {proc.info['pid']} reaped.")
                    except (psutil.TimeoutExpired, psutil.NoSuchProcess):
                        # すでに消えていたり、回収に失敗しても無視して次へ
                        pass
                    continue # ゾンビはPIDとして返さない

                # 3. 正常に動作しているプロセスを見つけた場合
                target_pid = proc.info['pid']
                
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            # 権限がないプロセスや、途中で消えたプロセスは無視
            continue

    return target_pid

def set_company_pw():
    # パスワードを設定する
    global nettool_pw
    for i in range(63):
        company_id = str(i)
        company_pw = getattr(config, f'player_{i}_pw', '')
        nettool_lockcompany(company_id, company_pw)
    print_gui_log('会社にパスワードを設定しました。')

def app_start():
    # Simutransを起動する
    os_system = platform.system()
    # WindowsとUNIX系OSでコマンドが違うのでその対策
    if os_system == 'Windows':
        process = subprocess.Popen(['start', server_path, '-server', config.port_number, '-fps', '30', '-nomidi', '-nosound', '-load', launch_save], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif os_system == 'Linux' or os_system == 'Darwin':
        process = subprocess.Popen([server_path, '-server', config.port_number, '-fps', '30', '-nomidi', '-nosound', '-load', launch_save], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    else:
        return None

    if int(getattr(config, 'press_space_after_start', 0)) == 1:
        space_timer = threading.Timer(30, press_space_key)
        space_timer.daemon = True
        space_timer.start()
    return process

def press_space_key():
    """Simutrans起動から30秒後に、現在アクティブなウィンドウへスペースキーを送る。"""
    try:
        os_system = platform.system()
        if os_system == 'Windows':
            user32 = ctypes.windll.user32
            user32.keybd_event(0x20, 0, 0, 0)
            user32.keybd_event(0x20, 0, 2, 0)
        elif os_system == 'Linux':
            subprocess.run(['xdotool', 'key', 'space'], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif os_system == 'Darwin':
            subprocess.run(['osascript', '-e', 'tell application "System Events" to key code 49'], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print_gui_log('スペースキーを送信しました。')
    except Exception as error:
        print_gui_log(f'スペースキーの送信に失敗しました: {error}')

def nettool_say(content):
    # contentにはASCII文字以外を入れないこと（文字化け対策）
    global nettool_pw
    subprocess.run([run_nettool(), '-p', nettool_pw, '-s', server_ip + config.port_number, 'say', content], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return None

def wait_simutrans_responce():
    # Simutransの応答を待つ
    global nettool_pw
    print_gui_log('Simutransの応答を待っています。しばらくお待ちください。')
    while True:
        result = subprocess.run([run_nettool(), '-p', nettool_pw, '-s', server_ip + config.port_number, 'clients'], encoding='utf-8', stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        if result.returncode == 0:
            print_gui_log('Simutransが応答しました。処理を再開します。')
            break
        time.sleep(1)

def nettool_lockcompany(company_id, company_pw):
    # クラッシュ対策（存在しない会社にパスワードをかけるとクラッシュする）
    result = subprocess.run([run_nettool(), '-p', nettool_pw, '-s', server_ip + config.port_number, 'info-company', company_id], capture_output=True, text=True, encoding='utf-8')
    # Nothing received.の後は改行が必要
    if result.stdout != 'Nothing received.\n' and company_pw != '':
        subprocess.run([run_nettool(), '-p', nettool_pw, '-s', server_ip + config.port_number, 'lock-company', company_id, company_pw], capture_output=True, text=True)

def nettool_forcesync():
    # ロード処理
    global nettool_pw
    subprocess.run([run_nettool(), '-p', nettool_pw, '-s', server_ip + config.port_number, 'force-sync'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    wait_simutrans_responce()
    save_backup()

def nettool_banip(banip):
    # IPBANユーザーを設定する
    global nettool_pw
    if banip != '':
        subprocess.run([run_nettool(), '-p', nettool_pw, '-s', server_ip + config.port_number, 'ban-ip', banip])

def set_ban_user():
    # IPBANユーザーを設定する
    for i in range(63):
        banip = getattr(config, f'banip_{i}', '')
        nettool_banip(banip)
    print_gui_log('BANユーザーを設定しました。')

def delete_old_long_backup_files():
    # 指定日数を超えたファイルを削除する

    print_gui_log('古い長期バックアップのデータを削除します。')

    # -1なら無期限保管
    if long_backup_keep == -1:
        print_gui_log('長期バックアップは無期限保管設定のため削除をスキップします。')
        return

    # 現在時刻
    now = time.time()

    # 日数 → 秒に変換
    limit_seconds = long_backup_keep * 24 * 60 * 60

    # フォルダ内を走査
    for filename in os.listdir(long_backup_folder_path):
        file_path = os.path.join(long_backup_folder_path, filename)

        # ファイルのみ対象
        if os.path.isfile(file_path):

            # 最終更新時刻を取得
            modified_time = os.path.getmtime(file_path)

            # 経過時間
            elapsed = now - modified_time

            # 指定日数を超えていたら削除
            if elapsed > limit_seconds:
                try:
                    # print_gui_log(f'削除: {file_path}')
                    os.remove(file_path)

                except Exception as e:
                    # print_gui_log(f'削除失敗: {e}')
                    pass

    print_gui_log('古い長期バックアップのデータを削除しました。')

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

def long_backup(force_backup):
    # 0なら長期バックアップ無効
    if long_backup_keep == 0 and force_backup == 0:
        print_gui_log('長期バックアップは無効化されています。')
        return
    print_gui_log('長期バックアップを作成します。')

    try:
        # フォルダ作成
        os.makedirs(long_backup_folder_path, exist_ok=True)

        dt = datetime.datetime.now()
        nowdate = dt.strftime('%Y%m%d%H%M')

        src = os.path.join(server_folder_path, server_save)
        dst = os.path.join(
            long_backup_folder_path,
            f'backup-{nowdate}.sve'
        )

        # デバッグ用
        # print_gui_log(f'コピー元: {src}')
        # print_gui_log(f'コピー先: {dst}')

        shutil.copy(src, dst)

        # 本当に存在するか確認
        if os.path.exists(dst):
            print_gui_log('長期バックアップを作成しました。')
        else:
            print_gui_log('バックアップファイルが存在しません。')

        delete_old_long_backup_files()

    except Exception as e:
        print_gui_log(f'長期バックアップの作成に失敗しました。: {e}')

def auto_long_backup():
    # 指定の時間に長期バックアップする
    # long_backup_keepが0の場合はバックアップしない
    if long_backup_keep != 0:
        schedule.every().days.at(f'{long_backup_time:02}:00:00').do(long_backup, 0)
        while True:
            schedule.run_pending()
            time.sleep(1)
    return None

def server_stop(set_code, long_backup_code):
    # サーバーを止める機能
    global nettool_pw
    global start_code
    if set_code == 2:
        if start_code == 3:
            return None
        nettool_say('Server restart soon.')
        print_gui_log('再起動予告メッセージを送信しました。')
        discord_post('まもなく再起動を行います。', 'これからのログインはおやめください。', 0xffbf00)
    elif set_code == 3:
        nettool_say('Maintenance soon.')
        print_gui_log('メンテナンス予告メッセージを送信しました。')
        discord_post('まもなくメンテナンスです。', 'これからのログインはおやめください。', 0xffbf00)
    elif set_code == 5:
        nettool_say('Server close soon.')
        print_gui_log('サーバー終了予告メッセージを送信しました。')
        discord_post('まもなくサーバーを終了します。', 'これからのログインはおやめください。', 0xffbf00)
    time.sleep(30)
    nettool_forcesync()
    if long_backup_code == 1:
        long_backup(1)
    if set_code == 2:
        nettool_say('Server is restarting.')
        print_gui_log('再起動中告知メッセージを送信しました。')
    elif set_code == 3:
        nettool_say('Maintenance start.')
        print_gui_log('メンテナンス告知メッセージを送信しました。')
        discord_post('ただいまメンテナンス中です。', 'メンテナンス中でもサーバーに入れる場合がありますが、許可なく入らないでください。', 0xffbf00)
    elif set_code == 5:
        nettool_say('Server closed. Thank you for playing!')
        print_gui_log('サーバー終了告知メッセージを送信しました。')
        discord_post('サーバーは終了しました。', '皆様のご参加ありがとうございました。', 0x00ff00)
    start_code = set_code
    subprocess.run([run_nettool(), '-p', nettool_pw, '-s', server_ip + config.port_number, 'shutdown'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
        schedule.every().days.at(restart_time + ":59:30").do(server_stop(2, 0))
        while True:
            schedule.run_pending()
            time.sleep(1)
    return None

def monitoring():
    global start_code
    global nettool_pw
    server_pid = get_pid(config.server_name)
    if not server_pid is None:
        # 初回起動時、サーバー起動済みであった場合の処理
        print_gui_log('サーバーは起動済みです。')
        set_ban_user()
        start_code = 1
    while True:
        # start_codeが3（メンテナンス中）または6（復旧待ち）であれば処理を行わない
        if start_code not in (3, 6, 8):
            # PIDを取得し、Noneなら起動する
            server_pid = get_pid(config.server_name)
            if server_pid is None:
                # 初回起動時とそれ以外で表示メッセージを変える
                if start_code == 0:
                    # 初回起動時
                    app_start()
                    print_gui_log('サーバーを起動します。')
                    nettool_pw = get_nettool_pw(1)
                    wait_simutrans_responce()
                    set_company_pw()
                    set_ban_user()
                    start_code = 1
                elif start_code == 1:
                    # サーバーダウン時
                    save_timestamp = get_savefile_timestamp(0)
                    if save_timestamp == "99:99":
                        # サーバーダウン（手動復旧必要時）
                        print_gui_log('サーバーダウンを検出しました。復旧用のデータを配置し手動で復旧してください。')
                        discord_post('サーバーがダウンしました。', '復旧用のデータがないため、今回は自動復旧できません。\nご迷惑をおかけしますが、復旧までしばらくお待ちください。', 0xff0000)
                        start_code = 6
                        app.after(0,app.set_manual_restart_mode)
                        while start_code == 6:
                            time.sleep(1)
                        continue
                    else:
                        # サーバーダウン（自動復旧時）
                        app_start()
                        print_gui_log('サーバーダウンを検出しました。再起動します。')
                        discord_post('サーバーがダウンしました。', '自動で復帰します。しばらくお待ちください。\nこれに伴い、' + save_timestamp + 'までデータが巻き戻ります。', 0xff0000)
                    nettool_pw = get_nettool_pw(1)
                    wait_simutrans_responce()
                    set_company_pw()
                    set_ban_user()
                    print_gui_log('サーバーを再起動しました。')
                    discord_post('サーバーが復旧しました。', 'サーバーに入る際は、過度なログインラッシュのないよう順序よくお入りください。', 0x00ff00)
                elif start_code == 2:
                    # 再起動した場合
                    app_start()
                    print_gui_log('サーバーを起動します。')
                    nettool_pw = get_nettool_pw(1)
                    wait_simutrans_responce()
                    set_company_pw()
                    set_ban_user()
                    print_gui_log('サーバーを起動しました。')
                    discord_post('サーバーを再起動しました。', 'サーバーに入る際は、過度なログインラッシュのないよう順序よくお入りください。', 0x00ff00)
                    start_code = 1
                elif start_code == 4:
                    # メンテナンス終了時
                    app_start()
                    print_gui_log('サーバーを再開します。')
                    nettool_pw = get_nettool_pw(1)
                    wait_simutrans_responce()
                    set_company_pw()
                    set_ban_user()
                    print_gui_log('サーバーを再開しました。')
                    discord_post('メンテナンスを終了しました。', '皆様のご協力ありがとうございました。', 0x00ff00)
                    start_code = 1
                elif start_code == 7:
                    # サーバー手動再開時
                    app_start()
                    print_gui_log('サーバーを再開します。')
                    nettool_pw = get_nettool_pw(1)
                    wait_simutrans_responce()
                    set_company_pw()
                    set_ban_user()
                    print_gui_log('サーバーを再開しました。')
                    discord_post('サーバーを再開しました。', '大変お待たせしました。', 0x00ff00)
                    start_code = 1
                elif start_code == 5:
                    app_start()
                    break
        time.sleep(1)
    return None

def autosave():

    global next_autosave_at

    pt = server_folder_path + '/' + server_save

    # ====================================================
    # 従来タイマー方式
    # ====================================================
    if autosave_mode == 0:

        autosave_interval = config.autosave_interval - 30
        saved_next = float(next_autosave_at) if next_autosave_at else 0
        initial_wait = max(0, saved_next - time.time()) if saved_next > time.time() else max(0, autosave_interval)
        next_autosave_at = time.time() + initial_wait
        persist_runtime_state()

        # backup用タイマー
        last_backup_time = time.time()

        if initial_wait > 0:
            time.sleep(initial_wait)

        while True:

            # ----------------------------------------
            # autosave予告
            # ----------------------------------------
            post_autosave_notice()
            nettool_say('Autosave soon.')
            print_gui_log('オートセーブ予告メッセージを送信しました。')

            time.sleep(30)

            # ----------------------------------------
            # autosave
            # ----------------------------------------
            print_gui_log('オートセーブ中です。')

            start_time = time.time()

            nettool_forcesync()
            set_company_pw()

            end_time = time.time()

            print_gui_log('オートセーブ処理が完了しました。')
            post_autosave_completed()

            last_backup_time = time.time()

            # ----------------------------------------
            # 次回autosave待機
            # ----------------------------------------
            process_time = end_time - start_time

            next_autosave = (
                config.autosave_interval
                - 30
                - process_time
            )
            next_autosave_at = time.time() + max(0, next_autosave)
            persist_runtime_state()

            # autosave待機中に
            # backupだけ実行する可能性あり
            while next_autosave > 0:

                now_time = time.time()

                # backup単独判定
                if (
                    now_time - last_backup_time
                    >= config.autosave_interval
                ):

                    print_gui_log('定期バックアップを実行します。')

                    save_backup()

                    print_gui_log('定期バックアップ処理が完了しました。')

                    last_backup_time = time.time()

                sleep_time = min(1, next_autosave)

                time.sleep(sleep_time)

                next_autosave -= sleep_time

            next_autosave_at = time.time()
            persist_runtime_state()

        return None

    # ====================================================
    # savefile timestamp方式
    # ====================================================
    now_time = time.time()

    if next_autosave_at:
        now_time = max(now_time, float(next_autosave_at))

    # 最後のsave activity時刻
    last_save_activity_time = now_time

    # 最後のbackup時刻
    last_backup_time = now_time

    # autosave予告済みフラグ
    autosave_warned = False

    while True:

        now_time = time.time()

        # ------------------------------------------------
        # セーブファイル存在確認
        # ------------------------------------------------
        if os.path.isfile(pt):

            current_save_time = os.path.getctime(pt)

            # save更新検知
            if current_save_time > last_save_activity_time:

                last_save_activity_time = current_save_time

                # save更新があったので予告リセット
                autosave_warned = False

        else:

            # ファイルがない場合は従来タイマー方式
            current_save_time = now_time

        # ------------------------------------------------
        # autosave予告判定
        # ------------------------------------------------
        autosave_warn_time = (
            last_save_activity_time
            + config.autosave_interval
            - 30
        )

        if (
            autosave_warned == False
            and now_time >= autosave_warn_time
        ):

            post_autosave_notice()
            nettool_say('Autosave soon.')
            print_gui_log('オートセーブ予告メッセージを送信しました。')

            autosave_warned = True

        # ------------------------------------------------
        # autosave判定
        # ------------------------------------------------
        autosave_execute_time = (
            last_save_activity_time
            + config.autosave_interval
        )
        next_autosave_at = autosave_execute_time

        if now_time >= autosave_execute_time:

            # 予告後に手動saveされた可能性を再確認
            if os.path.isfile(pt):

                latest_save_time = os.path.getctime(pt)

                if latest_save_time > last_save_activity_time:

                    last_save_activity_time = latest_save_time
                    autosave_warned = False

                    time.sleep(1)
                    continue

            # ----------------------------------------
            # autosave
            # ----------------------------------------
            print_gui_log('オートセーブ中です。')

            nettool_forcesync()
            set_company_pw()

            print_gui_log('オートセーブ処理が完了しました。')
            post_autosave_completed()

            # autosave後のsave時刻取得
            if os.path.isfile(pt):

                last_save_activity_time = os.path.getctime(pt)

            else:
                last_save_activity_time = time.time()

            next_autosave_at = last_save_activity_time + config.autosave_interval
            persist_runtime_state()

            # backupタイマー更新
            last_backup_time = time.time()

            # 次回予告用
            autosave_warned = False

            time.sleep(1)
            continue

        # ------------------------------------------------
        # backup単独判定
        # ------------------------------------------------
        backup_execute_time = (
            last_backup_time
            + config.autosave_interval
        )

        if now_time >= backup_execute_time:

            print_gui_log('定期バックアップを実行します。')

            save_backup()

            print_gui_log('定期バックアップ処理が完了しました。')

            # backupタイマー更新
            last_backup_time = time.time()

        # CPU負荷軽減
        time.sleep(1)

    return None

if __name__ == "__main__":
    os_type = check_os()
    root = gui_main(create_app=False)
    # GUI初期化関数の戻り値が失われた場合でも、以降の初期設定画面を表示できるようにする。
    if root is None:
        root = tk.Tk()
    if not os.path.exists(config_path):
        dialog = config_window(root, first_run=True)
        root.wait_window(dialog.window)
        if not os.path.exists(config_path):
            root.destroy()
            sys.exit()
    load_config()
    check_config()
    check_nettool()
    nettool_pw = get_nettool_pw(0)
    app = window_main(master=root)
    restore_runtime_state()

    root.after(100, start_threads)

    root.mainloop()
