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
    language_dir = os.path.join(base_dir, 'language')

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

language_code = 'en-US'
translations = {}
translation_aliases = {}

def load_language(code='en-US'):
    global language_code, translations, translation_aliases
    requested = str(code or 'ja-JP')
    path = os.path.join(language_dir, f'{requested}.yaml')
    fallback = os.path.join(language_dir, 'ja-JP.yaml')
    try:
        with open(path if os.path.exists(path) else fallback, 'r', encoding='utf-8') as language_file:
            document = yaml.safe_load(language_file) or {}
        language_code = document.get('locale', requested)
        translations = document.get('strings', {})
        translation_aliases = document.get('aliases', {})
    except (OSError, yaml.YAMLError):
        language_code, translations, translation_aliases = 'en-US', {}, {}

def t(key, **values):
    value = translations.get(translation_aliases.get(key, key), key)
    return value.format(**values) if values else value

def available_languages():
    """Return language choices discovered from language/*.yaml."""
    choices = []
    try:
        filenames = sorted(name for name in os.listdir(language_dir) if name.endswith('.yaml'))
    except OSError:
        filenames = []
    for filename in filenames:
        path = os.path.join(language_dir, filename)
        try:
            with open(path, 'r', encoding='utf-8') as language_file:
                document = yaml.safe_load(language_file) or {}
            locale = str(document.get('locale') or os.path.splitext(filename)[0])
            language_name = document.get('language_name')
            if language_name:
                choices.append((locale, str(language_name)))
        except (OSError, yaml.YAMLError):
            continue
    return choices

load_language(config_data.get('language', 'en-US'))

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
import queue
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

# UI部品の文字列を一か所で言語パックへ接続する。既存画面の文言も
# widget生成時に通過するため、新しい画面を追加する際の漏れを防ぐ。
def _localized_widget_factory(widget_class):
    def factory(*args, **kwargs):
        if isinstance(kwargs.get('text'), str):
            kwargs['text'] = t(kwargs['text'])
        return widget_class(*args, **kwargs)
    return factory

for _widget_name in ('Label', 'Button', 'Checkbutton', 'Radiobutton'):
    setattr(ttk, _widget_name, _localized_widget_factory(getattr(ttk, _widget_name)))

_messagebox_functions = ('showinfo', 'showwarning', 'showerror', 'askyesno')
for _messagebox_name in _messagebox_functions:
    _messagebox_function = getattr(messagebox, _messagebox_name)
    def _localized_messagebox(*args, _function=_messagebox_function, **kwargs):
        if args:
            args = (t(args[0]),) + tuple(t(value) if isinstance(value, str) else value for value in args[1:])
        for _key in ('title', 'message'):
            if isinstance(kwargs.get(_key), str):
                kwargs[_key] = t(kwargs[_key])
        return _function(*args, **kwargs)
    setattr(messagebox, _messagebox_name, _localized_messagebox)

for _filedialog_name in ('askopenfilename', 'askdirectory', 'asksaveasfilename'):
    _filedialog_function = getattr(filedialog, _filedialog_name)
    def _localized_filedialog(*args, _function=_filedialog_function, **kwargs):
        if isinstance(kwargs.get('title'), str):
            kwargs['title'] = t(kwargs['title'])
        return _function(*args, **kwargs)
    setattr(filedialog, _filedialog_name, _localized_filedialog)

# 変数定義
intents = discord.Intents.default()
bot = discord.Client(intents=intents)
pending_discord_notifications = []
pending_discord_notifications_lock = threading.Lock()
gui_log_queue = queue.Queue()

# 常駐処理がGUIスレッドやOSへ細かくアクセスし続けないように、更新をまとめる。
GUI_LOG_FLUSH_INTERVAL_MS = 100
GUI_LOG_BATCH_SIZE = 200
GUI_LOG_MAX_LINES = 2000
PROCESS_SCAN_CACHE_SECONDS = 2.0
RESPONSE_MONITOR_INTERVAL_SECONDS = 5.0

_nettool_path_cache = None
_nettool_path_lock = threading.Lock()
_pid_cache = {}
_pid_cache_lock = threading.Lock()

CONFIG_DISPLAY_NAMES = {
    'path': 'config_server_executable', 'port': 'config_port',
    'response_monitor_enabled': 'config_response_monitor',
    'response_timeout': 'config_response_timeout',
    'restart_time': 'config_restart_time',
    'restart_enabled': 'config_restart_enabled',
    'press_space_after_start': 'config_press_space_after_start',
    'mode': 'config_autosave_mode', 'backup_count': 'config_backup_count',
    'interval': 'config_autosave_interval',
    'long_term_keep_days': 'config_long_term_keep_days',
    'long_term_time': 'config_long_term_time',
    'enabled': 'config_discord_enabled', 'autosave_notice': 'config_autosave_notice',
    'token': 'config_discord_token', 'channel': 'config_discord_channel',
    'passwords': 'config_player_passwords', 'ban_ips': 'ban_ip',
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
    config.response_monitor_enabled = server.get('response_monitor_enabled', 0)
    config.response_timeout = server.get('response_timeout', 0)
    config.restart_time = server.get('restart_time')
    runtime = config_data.get('runtime', {})
    saved_auto_restart = runtime.get('auto_restart_enabled')
    try:
        restart_disabled = int(config.restart_time) == -1
    except (TypeError, ValueError):
        restart_disabled = False
    config.restart_enabled = int(
        0 if restart_disabled else
        (config.restart_time != -1 if saved_auto_restart is None else saved_auto_restart)
    )
    config.press_space_after_start = server.get('press_space_after_start', 0)
    autosave = config_data.get('autosave', {})
    config.autosave_mode = autosave.get('mode')
    config.autosave_backup = autosave.get('backup_count')
    try:
        config.autosave_interval = int(autosave.get('interval', 1200))
    except (TypeError, ValueError):
        config.autosave_interval = 1200
    backup = config_data.get('backup', {})
    config.long_backup_keep = backup.get('long_term_keep_days')
    config.long_backup_time = backup.get('long_term_time')
    players = config_data.get('players', {}).get('passwords', {})
    ban_ips = config_data.get('network', {}).get('ban_ips', {})
    for i in range(63):
        setattr(config, f'player_{i}_pw', players.get(i, players.get(str(i), '')))
        setattr(config, f'banip_{i}', ban_ips.get(i, ban_ips.get(str(i), '')))
    discord_settings = config_data.get('discord', {})
    try:
        config.use_discord_bot = int(discord_settings.get('enabled', 0) or 0)
    except (TypeError, ValueError):
        config.use_discord_bot = 0
    config.discord_token = discord_settings.get('token', '')
    config.discord_channel = discord_settings.get('channel', '')
    try:
        config.discord_autosave_notice = int(discord_settings.get('autosave_notice', 0) or 0)
    except (TypeError, ValueError):
        config.discord_autosave_notice = 0

def default_config_data():
    return {
        'language': 'en-US',
        'server': {
            'path': '', 'port': '13353', 'restart_time': -1,
            'response_monitor_enabled': 0, 'response_timeout': 0,
            'press_space_after_start': 0,
        },
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
            'auto_restart_enabled': None,
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
        self.window.title(t('settings'))
        self.window.geometry('980x620')
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        self.fields = {}
        self.long_term_keep_mode = None
        self.long_term_keep_days_entry = None
        self.secret_entries = {'token': [], 'passwords': []}
        self.secret_visibility = {'token': tk.IntVar(value=0), 'passwords': tk.IntVar(value=0)}
        data = config_data if config_data else default_config_data()
        notebook = ttk.Notebook(self.window)
        notebook.pack(fill='both', expand=True, padx=8, pady=8)
        language_frame = ttk.Frame(notebook)
        notebook.add(language_frame, text=t('language_tab'))
        ttk.Label(language_frame, text=t('language_tab')).grid(row=0, column=0, sticky='w', padx=10, pady=12)
        # 言語名は選択中の言語で翻訳せず、各YAMLの固定表記を使う。
        languages = available_languages()
        self.language_var = tk.StringVar(value=config_data.get('language', 'en-US'))
        language_box = ttk.Combobox(
            language_frame, textvariable=self.language_var,
            values=[f'{code} - {name}' for code, name in languages],
            state='readonly', width=28,
        )
        language_box.set(next((f'{code} - {name}' for code, name in languages if code == self.language_var.get()), ''))
        language_box.grid(row=0, column=1, sticky='w', padx=10, pady=12)
        language_box.bind('<<ComboboxSelected>>', self.apply_language)
        ttk.Label(language_frame, text=t('translation_accuracy_notice')).grid(row=1, column=0, columnspan=2, sticky='w', padx=10, pady=8)
        server_values = data.get('server', {})
        if 'path' not in server_values:
            folder = server_values.get('folder_path', '')
            name = server_values.get('name', '')
            separator = '\\' if '\\' in str(folder) and '/' not in str(folder) else '/'
            server_values = dict(server_values)
            server_values['path'] = f'{folder}{separator}{name}' if folder or name else ''
        server_values.setdefault('response_timeout', 0)
        server_values.setdefault('response_monitor_enabled', 0)
        server_values['restart_enabled'] = int(getattr(config, 'restart_enabled', server_values.get('restart_time') != -1))
        self.add_tab(
            notebook,
            t('server'),
            [
                'path', 'port', 'restart_time', 'restart_enabled', 'response_monitor_enabled',
                'response_timeout', 'press_space_after_start',
            ],
            server_values,
        )
        save_data_values = {}
        save_data_values.update(data.get('autosave', {}))
        save_data_values.update(data.get('backup', {}))
        self.add_tab(
            notebook,
            t('save_data'),
            ['mode', 'backup_count', 'interval', 'long_term_keep_days', 'long_term_time'],
            save_data_values,
        )
        self.add_tab(notebook, t('discord'), ['enabled', 'autosave_notice', 'token', 'channel'], data.get('discord', {}))
        self.add_password_tab(notebook, data.get('players', {}).get('passwords', {}))
        self.add_multiline_tab(notebook, t('ban_ip'), 'ban_ips', data.get('network', {}).get('ban_ips', {}))
        button_frame = ttk.Frame(self.window)
        button_frame.pack(fill='x', padx=8, pady=(0, 8))
        ttk.Button(button_frame, text=t('import_legacy_config'), command=self.import_legacy_config).pack(side='left')
        ttk.Button(button_frame, text=t('import_bat_settings'), command=self.import_setting_bat).pack(side='left', padx=(8, 0))
        ttk.Button(button_frame, text=t('save'), style='Accent.TButton', command=self.save).pack(side='right', padx=(8, 0))
        ttk.Button(button_frame, text=t('cancel'), command=self.close).pack(side='right')
        self.window.transient(master)
        self.window.grab_set()

    def apply_language(self, event=None):
        """Apply a language selection immediately by rebuilding the settings UI."""
        selected = self.language_var.get().split(' - ', 1)[0]
        config_data['language'] = selected
        with open(config_path, 'w', encoding='utf-8') as config_file:
            yaml.safe_dump(config_data, config_file, allow_unicode=True, sort_keys=False)
        load_language(selected)
        if 'app' in globals() and app is not None:
            app.apply_language()
        self.window.grab_release()
        self.window.destroy()
        config_window(self.master, first_run=self.first_run)

    def add_tab(self, notebook, title, fields, values):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text=title)
        is_server_tab = title == t('server')
        is_discord_tab = title == t('discord')
        if is_server_tab or is_discord_tab:
            frame.grid_columnconfigure(1, weight=1)
        if is_server_tab:
            frame.grid_columnconfigure(0, minsize=180)
        for row, key in enumerate(fields):
            if is_server_tab and key in ('response_monitor_enabled', 'response_timeout', 'restart_enabled', 'restart_time'):
                if key in ('response_timeout', 'restart_time'):
                    continue
                paired_key = 'response_timeout' if key == 'response_monitor_enabled' else 'restart_time'
                ttk.Label(frame, text=t(CONFIG_DISPLAY_NAMES[key])).grid(
                    row=row, column=0, sticky='w', padx=10, pady=8
                )
                pair_frame = ttk.Frame(frame)
                pair_frame.grid(row=row, column=1, columnspan=4, sticky='ew', padx=10, pady=8)
                pair_frame.grid_columnconfigure(1, minsize=150)
                pair_frame.grid_columnconfigure(2, weight=1)
                variable = tk.IntVar(value=1 if int(values.get(key, 0) or 0) in (1, 2) else 0)
                ttk.Checkbutton(
                    pair_frame, text=t('use'), style='Switch.TCheckbutton', variable=variable
                ).grid(row=0, column=0, sticky='w', padx=(0, 16))
                self.fields[key] = variable
                ttk.Label(pair_frame, text=t(CONFIG_DISPLAY_NAMES[paired_key])).grid(
                    row=0, column=1, sticky='w', padx=(0, 8)
                )
                paired_entry = ttk.Entry(pair_frame, width=12)
                paired_entry.insert(0, str(values.get(paired_key, '')))
                paired_entry.grid(
                    row=0, column=2, sticky='ew'
                )
                self.fields[paired_key] = paired_entry
                ttk.Button(
                    frame, text=t('help'), command=lambda k=key: self.show_help(k)
                ).grid(row=row, column=5, padx=3, pady=6)
                continue
            ttk.Label(frame, text=t(CONFIG_DISPLAY_NAMES[key])).grid(row=row, column=0, sticky='w', padx=10, pady=8)
            if key == 'mode':
                try:
                    mode = int(values.get(key, 0) or 0)
                except (TypeError, ValueError):
                    mode = 0
                variable = tk.IntVar(value=mode if mode in (0, 1) else 0)
                mode_frame = ttk.Frame(frame)
                mode_frame.grid(row=row, column=1, sticky='w', padx=10, pady=8)
                ttk.Radiobutton(
                    mode_frame, text=t('fixed_interval'), variable=variable, value=0
                ).pack(side='left', padx=(0, 16))
                ttk.Radiobutton(
                    mode_frame, text=t('elapsed_since_last_load'), variable=variable, value=1
                ).pack(side='left')
                self.fields[key] = variable
            elif key == 'long_term_keep_days':
                try:
                    keep_days = int(values.get(key, 0) or 0)
                except (TypeError, ValueError):
                    keep_days = 0
                mode = tk.StringVar(
                    value='disabled' if keep_days == 0 else
                    'unlimited' if keep_days == -1 else 'days'
                )
                mode_frame = ttk.Frame(frame)
                mode_frame.grid(row=row, column=1, sticky='w', padx=10, pady=8)
                ttk.Radiobutton(
                    mode_frame, text=t('disabled'), variable=mode, value='disabled'
                ).pack(side='left', padx=(0, 12))
                ttk.Radiobutton(
                    mode_frame, text=t('unlimited'), variable=mode, value='unlimited'
                ).pack(side='left', padx=(0, 12))
                ttk.Radiobutton(
                    mode_frame, text=t('specify_days'), variable=mode, value='days'
                ).pack(side='left', padx=(0, 6))
                days_entry = ttk.Entry(mode_frame, width=10)
                if keep_days > 0:
                    days_entry.insert(0, str(keep_days))
                days_entry.pack(side='left')
                ttk.Label(mode_frame, text=t('day')).pack(side='left', padx=(4, 0))
                self.long_term_keep_mode = mode
                self.long_term_keep_days_entry = days_entry
                self.fields[key] = mode
            elif key in ('enabled', 'autosave_notice', 'press_space_after_start', 'response_monitor_enabled', 'restart_enabled'):
                variable = tk.IntVar(value=1 if int(values.get(key, 0) or 0) in (1, 2) else 0)
                text = t('use') if key in ('enabled', 'response_monitor_enabled', 'restart_enabled') else t('enable')
                entry = ttk.Checkbutton(frame, text=text, style='Switch.TCheckbutton', variable=variable)
                entry.grid(row=row, column=1, sticky='w', padx=10, pady=8)
                self.fields[key] = variable
            else:
                entry = ttk.Entry(frame, width=48, show='*' if key == 'token' else '')
                entry.insert(0, str(values.get(key, '')))
                entry.grid(
                    row=row, column=1,
                    columnspan=3 if is_server_tab and key == 'path' else
                    4 if is_server_tab else
                    2 if is_discord_tab and key != 'token' else 1,
                    sticky='ew', padx=10, pady=8
                )
                self.fields[key] = entry
                if key == 'path':
                    ttk.Button(
                        frame, text=t('browse'), command=self.select_server_executable
                    ).grid(row=row, column=4, padx=5, pady=8)
                if key == 'token':
                    self.secret_entries['token'].append(entry)
                    ttk.Checkbutton(
                        frame, text=t('show'), variable=self.secret_visibility['token'],
                        style='Switch.TCheckbutton',
                        command=lambda: self.toggle_secret('token')
                    ).grid(row=row, column=2 if is_discord_tab else 3, padx=5, pady=8)
            help_column = 5 if is_server_tab else 3 if is_discord_tab else 2
            ttk.Button(frame, text=t('help'), command=lambda k=key: self.show_help(k)).grid(row=row, column=help_column, padx=5, pady=8)

    def select_server_executable(self):
        """ファイル選択ダイアログでサーバー実行ファイルを指定する。"""
        current_path = self.fields['path'].get().strip()
        initial_dir = os.path.dirname(current_path) if current_path else ''
        if platform.system() == 'Windows':
            filetypes = [
                (t('executable'), '*.exe'),
                (t('all_files'), '*.*'),
            ]
        else:
            # Linux/macOSの実行ファイルは拡張子を持たないことが多いため、
            # 拡張子では絞り込まず、すべてのファイルを選択対象にする。
            filetypes = [(t('executable'), '*')]
        path = filedialog.askopenfilename(
            title=t('select_server_executable'),
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
        ttk.Label(frame, text=t('numbered_value_per_line')).pack(anchor='w', padx=10, pady=8)
        ttk.Button(frame, text=t('help'), command=lambda k=key: self.show_help(k)).pack(anchor='e', padx=10)
        text = tk.Text(frame, width=65, height=25)
        text.pack(fill='both', expand=True, padx=10, pady=5)
        for i in range(63):
            value = values.get(i, values.get(str(i), ''))
            if value not in (None, ''):
                text.insert('end', f'{i}={value}\n')
        self.fields[key] = text

    def add_password_tab(self, notebook, values):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text=t('players'))
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        ttk.Label(
            frame,
            text=t('company_passwords_notice')
        ).grid(row=0, column=0, sticky='w', padx=10, pady=8)
        ttk.Checkbutton(
            frame, text=t('show_password'), variable=self.secret_visibility['passwords'],
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
            ttk.Label(contents, text=t('company_number', i=i)).grid(row=row, column=column, sticky='w', padx=(10, 4), pady=3)
            entry = ttk.Entry(contents, width=22, show='*')
            value = values.get(i, values.get(str(i), ''))
            entry.insert(0, str(value or ''))
            entry.grid(row=row, column=column + 1, sticky='w', padx=(0, 18), pady=3)
            entry.bind('<MouseWheel>', lambda event: canvas.yview_scroll(-int(event.delta / 120), 'units'))
            entry.bind('<Button-4>', lambda event: canvas.yview_scroll(-1, 'units'))
            entry.bind('<Button-5>', lambda event: canvas.yview_scroll(1, 'units'))
            password_fields[i] = entry
            self.secret_entries['passwords'].append(entry)
        ttk.Button(frame, text=t('help'), command=lambda: self.show_help('passwords')).grid(row=2, column=0, padx=10, pady=8, sticky='w')
        self.fields['passwords'] = password_fields

    def toggle_secret(self, key):
        show = '' if self.secret_visibility[key].get() else '*'
        for entry in self.secret_entries[key]:
            entry.configure(show=show)

    def show_help(self, key):
        descriptions = {
            'path': 'help_server_executable', 'port': 'help_port',
            'restart_time': 'help_restart_time', 'restart_enabled': 'help_restart_enabled',
            'response_monitor_enabled': 'help_response_monitor',
            'response_timeout': 'help_response_timeout', 'press_space_after_start': 'help_press_space',
            'mode': 'help_autosave_mode', 'backup_count': 'help_backup_count',
            'interval': 'help_autosave_interval', 'long_term_keep_days': 'help_long_term_keep_days',
            'long_term_time': 'help_long_term_time', 'enabled': 'help_discord_enabled',
            'autosave_notice': 'help_autosave_notice', 'token': 'help_discord_token',
            'channel': 'help_discord_channel', 'passwords': 'help_player_passwords',
            'ban_ips': 'help_ban_ips',
        }
        messagebox.showinfo(t('setting_help_title'), t(descriptions.get(key, 'no_description')), parent=self.window)

    def import_legacy_config(self):
        path = filedialog.askopenfilename(
            title=t('select_legacy_config'),
            filetypes=[(t('python_config_file'), 'config.py'), (t('python_file'), '*.py')],
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
                elif key == 'long_term_keep_days':
                    try:
                        keep_days = int(value or 0)
                    except (TypeError, ValueError):
                        keep_days = 0
                    self.long_term_keep_mode.set(
                        'disabled' if keep_days == 0 else
                        'unlimited' if keep_days == -1 else 'days'
                    )
                    self.long_term_keep_days_entry.delete(0, 'end')
                    if keep_days > 0:
                        self.long_term_keep_days_entry.insert(0, str(keep_days))
                elif key in ('enabled', 'autosave_notice', 'press_space_after_start'):
                    self.fields[key].set(1 if int(value or 0) in (1, 2) else 0)
                else:
                    self.fields[key].delete(0, 'end')
                    self.fields[key].insert(0, str(value))
            try:
                restart_disabled = int(self.fields['restart_time'].get()) == -1
            except (TypeError, ValueError):
                restart_disabled = False
            if restart_disabled:
                self.fields['restart_enabled'].set(0)
                self.fields['restart_time'].delete(0, 'end')
                self.fields['restart_time'].insert(0, '0')
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
            messagebox.showinfo(t('import_complete'), t('legacy_import_complete'), parent=self.window)
        except Exception as error:
            messagebox.showerror(t('import_failed'), t('legacy_import_failed', error=error), parent=self.window)

    def import_setting_bat(self):
        path = filedialog.askopenfilename(
            title=t('select_bat_settings'),
            filetypes=[(t('config_file'), 'setting.bat'), (t('batch_file'), '*.bat')],
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
            messagebox.showinfo(t('import_complete'), t('bat_import_complete'), parent=self.window)
        except Exception as error:
            messagebox.showerror(t('import_failed'), t('bat_import_failed', error=error), parent=self.window)

    def save(self):
        data = default_config_data()
        data['language'] = self.language_var.get().split(' - ', 1)[0]
        # 設定画面にない内部状態を保持する。
        data['runtime'] = config_data.get('runtime', data['runtime'])
        try:
            restart_disabled = int(self.fields['restart_time'].get()) == -1
        except (TypeError, ValueError):
            restart_disabled = False
        if restart_disabled:
            self.fields['restart_enabled'].set(0)
        data['runtime']['auto_restart_enabled'] = self.fields['restart_enabled'].get()
        for key in ('server', 'autosave', 'backup', 'discord'):
            for name in data[key]:
                if name == 'long_term_keep_days':
                    mode = self.long_term_keep_mode.get()
                    if mode == 'disabled':
                        data[key][name] = 0
                    elif mode == 'unlimited':
                        data[key][name] = -1
                    else:
                        data[key][name] = self.long_term_keep_days_entry.get()
                else:
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
            messagebox.showerror(t('input_error'), error, parent=self.window)
            return
        with open(config_path, 'w', encoding='utf-8') as config_file:
            yaml.safe_dump(data, config_file, allow_unicode=True, sort_keys=False)
        # 保存直後にYAMLを読み込み直し、アプリ内の設定も更新する。
        load_config()
        if not self.first_run:
            check_config(initialize_runtime=False)
            app.server_name_label.config(text=t('managed_server') + config.server_name)
        self.close()

    def validate_config_data(self, data):
        server_path = str(data['server']['path']).strip()
        if not server_path:
            return t('server_path_required', field=t(CONFIG_DISPLAY_NAMES['path']))
        if not os.path.isfile(server_path):
            return t('server_path_missing', field=t(CONFIG_DISPLAY_NAMES['path']))

        integer_rules = (
            ('server.port', data['server']['port'], 0, 65535),
            ('server.restart_time', data['server']['restart_time'], -1, 24),
            ('server.response_monitor_enabled', data['server']['response_monitor_enabled'], 0, 1),
            ('server.response_timeout', data['server']['response_timeout'], 0, None),
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
            display_name = t(CONFIG_DISPLAY_NAMES[name.split('.')[-1]])
            try:
                number = int(value)
            except (TypeError, ValueError):
                return t('integer_required', field=display_name)
            if number < minimum or (maximum is not None and number > maximum):
                return t('value_out_of_range', field=display_name)
        if int(data['discord']['enabled']) in (1, 2):
            if not str(data['discord']['token']).strip():
                return t('discord_token_required', enabled=t(CONFIG_DISPLAY_NAMES['enabled']), token=t(CONFIG_DISPLAY_NAMES['token']))
            try:
                int(data['discord']['channel'])
            except (TypeError, ValueError):
                return t('integer_required', field=t(CONFIG_DISPLAY_NAMES['channel']))
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
        self.master.title(t('app_name'))
        self.master.resizable(False, False)
        if os_type == "Linux":
            self.master.geometry("680x370")
        else:
            self.master.geometry("680x330")
        self.maintenance_mode = 0  # メンテナンスモードの状態（0:通常, 1:メンテナンス中）
        self.create_widgets()
        self.after(GUI_LOG_FLUSH_INTERVAL_MS, self.flush_gui_log_queue)

    def flush_gui_log_queue(self):
        """WorkerスレッドのログをまとめてTkへ反映する。"""
        messages = []
        for _ in range(GUI_LOG_BATCH_SIZE):
            try:
                messages.append(gui_log_queue.get_nowait())
            except queue.Empty:
                break

        if messages:
            self._log_text_insert_batch(messages)

        # 大量のログが来ても1回のコールバックでGUIを占有し続けない。
        delay = 0 if not gui_log_queue.empty() else GUI_LOG_FLUSH_INTERVAL_MS
        self.after(delay, self.flush_gui_log_queue)

    def create_widgets(self):
        # Gridの設定
        self.master.grid_rowconfigure(0, weight=1)
        self.master.grid_columnconfigure(0, weight=1)
        for column in range(4):
            self.grid_columnconfigure(column, weight=1, uniform="main_buttons")
        self.grid_rowconfigure(1, weight=1)

        # GUIの配置
        self.server_name_label = ttk.Label(self, text=t('managed_server') + config.server_name, anchor="w")
        self.server_name_label.grid(row=0, column=0, columnspan=4, sticky="w")

        # ログ欄とスクロールバーを専用フレームに収め、5列目にはみ出さないようにする。
        self.log_frame = ttk.Frame(self)
        self.log_frame.grid(row=1, column=0, columnspan=4, sticky="nsew")
        self.log_frame.grid_columnconfigure(0, weight=1)
        self.log_frame.grid_rowconfigure(0, weight=1)

        self.log_text = tk.Text(self.log_frame, width=40, height=10, wrap="word")
        self.log_text.configure(state="disabled")
        self.log_text.grid(row=0, column=0, sticky="nsew")
        
        self.scrollbar = ttk.Scrollbar(self.log_frame, orient="vertical", command=self.log_text.yview)
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.config(yscrollcommand=self.scrollbar.set)

        self.restart_button = ttk.Button(self, text=t('restart_server'), command=self.server_restart_check_start)
        self.restart_button.grid(row=2, column=0, padx=5, pady=10, sticky="ew")

        self.manual_save_button = ttk.Button(self, text=t('manual_save'), command=self.manual_save_start)
        self.manual_save_button.grid(row=2, column=1, padx=5, pady=10, sticky="ew")

        # メンテナンスモードボタン
        self.maintenance_mode_button = ttk.Button(
            self, text=t('pause_server'), command=self.maintenance_check_start
        )
        self.maintenance_mode_button.grid(row=2, column=2, padx=5, pady=10, sticky="ew")

        self.server_force_stop_button = ttk.Button(
            self,
            text=t('force_stop_server'),
            style="Danger.TButton",
            command=self.server_force_stop_check_start,
        )
        self.server_force_stop_button.grid(row=2, column=3, padx=5, pady=10, sticky="ew")

        self.server_stop_button = ttk.Button(self, text=t('close_session'), command=self.server_close_check_start)
        self.server_stop_button.grid(row=3, column=3, padx=5, pady=(0, 10), sticky="ew")

        self.rollback_button = ttk.Button(
            self, text=t('rollback_data'), command=self.rollback_start
        )
        self.rollback_button.grid(row=3, column=2, padx=5, pady=(0, 10), sticky="ew")

        self.update_schedule_button = ttk.Button(
            self, text=t('schedule_update'), command=self.update_schedule_start
        )
        self.update_schedule_button.grid(row=3, column=0, columnspan=2, padx=5, pady=(0, 10), sticky="ew")

        self.settings_button = ttk.Button(self, text=t('settings'), command=self.open_settings)
        self.settings_button.grid(row=4, column=2, padx=5, pady=(0, 10), sticky="ew")

        self.exit_button = ttk.Button(self, text=t('exit_app'), style='Accent.TButton', command=self.exit_check_start)
        self.exit_button.grid(row=4, column=3, padx=5, pady=(0, 10), sticky="ew")

    def open_settings(self):
        if hasattr(self, "newWindow") and self.newWindow.winfo_exists():
            self.newWindow.lift()
            return
        self.newWindow = config_window(self.master).window

    def apply_language(self):
        """Refresh the already-open main window after a language change."""
        self.master.title(t('app_name'))
        self.server_name_label.config(text=t('managed_server') + config.server_name)
        self.restart_button.config(text=t('restart_server'))
        self.manual_save_button.config(text=t('manual_save'))
        self.server_force_stop_button.config(text=t('force_stop_server'))
        self.server_stop_button.config(text=t('close_session'))
        self.rollback_button.config(text=t('rollback_data'))
        self.update_schedule_button.config(text=t('schedule_update'))
        self.settings_button.config(text=t('settings'))
        self.exit_button.config(text=t('exit_app'))
        self.update_maintenance_button()

    def update_schedule_start(self):
        if hasattr(self, "newWindow") and self.newWindow.winfo_exists():
            self.newWindow.lift()
            return
        self.newWindow = tk.Toplevel(self.master)
        self.newWindow.grab_set()
        update_schedule_window(self.newWindow)

    def rollback_start(self):
        if hasattr(self, "newWindow") and self.newWindow.winfo_exists():
            self.newWindow.lift()
            return
        self.newWindow = tk.Toplevel(self.master)
        self.newWindow.grab_set()
        rollback_window(self.newWindow, self)

    def rollback_execute(self, save_path, timestamp):
        self.rollback_button.config(state="disabled")
        threading.Thread(
            target=rollback_server,
            args=(save_path, timestamp),
            daemon=True,
        ).start()

    def server_restart_check_start(self):
        # 確認ダイアログを開く
        if hasattr(self, "newWindow") and self.newWindow.winfo_exists():
            self.newWindow.lift()
            return

        self.newWindow = tk.Toplevel(self.master)
        self.newWindow.grab_set()
        server_restart_check(self.newWindow)

    def manual_save_start(self):
        # 手動セーブの確認ダイアログを開く
        if hasattr(self, "newWindow") and self.newWindow.winfo_exists():
            self.newWindow.lift()
            return

        self.newWindow = tk.Toplevel(self.master)
        self.newWindow.grab_set()
        manual_save_check(self.newWindow, self)

    def manual_save_execute(self):
        """確認後、告知して30秒待機した手動セーブを実行する。"""
        if hasattr(self, "manual_save_thread") and self.manual_save_thread.is_alive():
            return

        self.manual_save_button.config(state="disabled")
        self.manual_save_thread = threading.Thread(
            target=self.manual_save_threaded,
            daemon=True,
        )
        self.manual_save_thread.start()

    def manual_save_threaded(self):
        try:
            manual_save()
        finally:
            self.after(0, lambda: self.manual_save_button.config(state="normal"))

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

    def server_force_stop_check_start(self):
        # サーバー強制終了の確認ダイアログを開く
        if hasattr(self, "newWindow") and self.newWindow.winfo_exists():
            self.newWindow.lift()
            return

        self.newWindow = tk.Toplevel(self.master)
        self.newWindow.grab_set()
        server_force_stop_check(self.newWindow)

    def update_maintenance_button(self):
            if self.maintenance_mode == 0:
                text = t('pause_server')
            elif self.maintenance_mode == 1:
                text = t('resume_server')
            elif self.maintenance_mode == 2:
                text = t('resume_server')

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
        # 呼び出し元に関係なくキューへ入れ、GUI更新回数を抑える。
        gui_log_queue.put(content)

    def _log_text_insert(self, content):
        self._log_text_insert_batch([content])

    def _log_text_insert_batch(self, messages):
        # 実際にTkinterのUIを更新する処理（必ずメインスレッドで実行）
        self.log_text.configure(state="normal")
        self.log_text.insert('end', '\n'.join(messages) + '\n')

        # 長時間運用時もTextウィジェットの再描画コストが増え続けないようにする。
        line_count = int(self.log_text.index('end-1c').split('.')[0])
        excess_lines = line_count - GUI_LOG_MAX_LINES - 1
        if excess_lines > 0:
            self.log_text.delete('1.0', f'{excess_lines + 1}.0')

        self.log_text.configure(state="disabled")
        self.log_text.see("end")

class update_schedule_window(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.master.title(t('schedule_update'))
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

        ttk.Checkbutton(self.master, text=t('update_application'), style='Switch.TCheckbutton', variable=self.body_var).grid(row=0, column=0, padx=10, pady=8, sticky='w')
        ttk.Entry(self.master, textvariable=self.body_path, width=55).grid(row=1, column=0, padx=10, sticky='w')
        ttk.Button(self.master, text=t('select_application'), command=self.choose_body).grid(row=1, column=1, padx=5)

        ttk.Checkbutton(self.master, text=t('update_pakset'), style='Switch.TCheckbutton', variable=self.pak_var).grid(row=2, column=0, padx=10, pady=8, sticky='w')
        ttk.Entry(self.master, textvariable=self.pak_path, width=55).grid(row=3, column=0, padx=10, sticky='w')
        ttk.Button(self.master, text=t('select_pakset'), command=self.choose_pak).grid(row=3, column=1, padx=5)

        ttk.Label(self.master, text=t('update_datetime')).grid(row=4, column=0, padx=10, pady=(15, 2), sticky='w')
        ttk.Entry(self.master, textvariable=self.time_var, width=25).grid(row=5, column=0, padx=10, sticky='w')
        ttk.Checkbutton(self.master, text=t('backup_before_update'), style='Switch.TCheckbutton', variable=self.backup_var).grid(row=6, column=0, padx=10, pady=12, sticky='w')
        ttk.Checkbutton(self.master, text=t('post_discord_notice'), style='Switch.TCheckbutton', variable=self.discord_notice_var).grid(row=7, column=0, padx=10, pady=4, sticky='w')
        ttk.Label(self.master, text=t('update_after_action')).grid(row=8, column=0, padx=10, pady=(8, 2), sticky='w')
        ttk.Radiobutton(self.master, text=t('restart_after_update'), variable=self.restart_server_var, value=1).grid(row=9, column=0, padx=25, sticky='w')
        ttk.Radiobutton(self.master, text=t('exit_after_update'), variable=self.restart_server_var, value=0).grid(row=10, column=0, padx=25, sticky='w')
        button_frame = ttk.Frame(self.master)
        button_frame.grid(row=11, column=0, columnspan=3, padx=10, pady=5, sticky='w')
        ttk.Button(button_frame, text=t('register_schedule'), style='Accent.TButton', command=self.register).pack(side='left', padx=(0, 5))
        ttk.Button(button_frame, text=t('update_now'), command=self.update_now).pack(side='left', padx=5)
        ttk.Button(button_frame, text=t('cancel_schedule'), command=self.cancel_schedule).pack(side='left', padx=5)
        ttk.Button(button_frame, text=t('cancel'), command=self.close_window).pack(side='left', padx=(20, 5))

    def choose_body(self):
        path = filedialog.askopenfilename(title=t('select_update_application'))
        if path:
            self.body_path.set(path)

    def choose_pak(self):
        path = filedialog.askdirectory(title=t('select_update_pakset'))
        if path:
            if not os.path.isfile(os.path.join(path, 'ground.Outside.pak')):
                messagebox.showerror(t('pakset_validation_title'), t('pakset_validation_message'), parent=self.master)
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
            messagebox.showerror(t('input_confirmation'), t('invalid_update_datetime'), parent=self.master)
            return
        if when <= datetime.datetime.now():
            messagebox.showerror(t('input_confirmation'), t('future_datetime_required'), parent=self.master)
            return
        body, pak = update_data
        schedule_update(when, body, pak, self.backup_var.get(), self.discord_notice_var.get(), self.restart_server_var.get())
        messagebox.showinfo(t('registration_complete'), t('update_registered', when=when.strftime('%Y/%m/%d %H:%M')), parent=self.master)
        self.close_window()

    def validate_update_inputs(self):
        if not self.body_var.get() and not self.pak_var.get():
            messagebox.showwarning(t('input_confirmation'), t('update_target_required'), parent=self.master)
            return None
        if self.body_var.get() and not os.path.isfile(self.body_path.get()):
            messagebox.showerror(t('input_confirmation'), t('update_application_required'), parent=self.master)
            return None
        if self.pak_var.get() and (not os.path.isdir(self.pak_path.get()) or not os.path.isfile(os.path.join(self.pak_path.get(), 'ground.Outside.pak'))):
            messagebox.showerror(t('input_confirmation'), t('update_pakset_required'), parent=self.master)
            return None
        return (self.body_path.get() if self.body_var.get() else None,
                self.pak_path.get() if self.pak_var.get() else None)

    def update_now(self):
        update_data = self.validate_update_inputs()
        if update_data is None:
            return
        if not messagebox.askyesno(t('confirm'), t('confirm_update_now'), parent=self.master):
            return
        body, pak = update_data
        threading.Thread(target=execute_scheduled_update, args=({
            'body': body, 'pak': pak, 'backup': self.backup_var.get(),
            'restart_server': self.restart_server_var.get()
        },), daemon=True).start()
        self.close_window()

    def cancel_schedule(self):
        if not cancel_scheduled_update():
            messagebox.showinfo(t('confirm'), t('no_update_schedule'), parent=self.master)
            return
        messagebox.showinfo(t('cancellation_complete'), t('update_schedule_cancelled'), parent=self.master)
        self.close_window()

    def close_window(self):
        self.master.destroy()


class maintenance_check(tk.Frame):
    # メンテナンスモード確認ダイアログウィンドウ
    def __init__(self, master, main_window):
        super().__init__(master)
        self.master = master  # 既存のToplevelを受け取る
        self.main_window = main_window  # メインウィンドウの参照
        self.master.title(t('app_name'))
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
            text = t('confirm_pause_server')

        elif mode == 1:
            text = t('confirm_resume_server')

        elif mode == 2:
            text = t('confirm_resume_server')

        self.label = ttk.Label(self.master, text=text)
        self.label.pack(padx=10, pady=10, fill="both", expand=True)

        button_frame = ttk.Frame(self.master)
        button_frame.pack(pady=10, fill="x")

        self.exit_button = ttk.Button(
            button_frame,
            text=t('yes'),
            style='Accent.TButton',
            command=self.maintenance_mode_check
        )
        self.exit_button.pack(side="left", padx=5, expand=True)

        self.cancel_button = ttk.Button(
            button_frame,
            text=t('no'),
            command=self.close_window
        )
        self.cancel_button.pack(side="right", padx=5, expand=True)

        # 長期バックアップ用スイッチ（メンテ開始時以外は出さない）
        self.long_backup_var = tk.IntVar(value=0)
        if mode == 0:
            self.switch = ttk.Checkbutton(
                self.master,
                text=t('backup_at_maintenance_start'),
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
        self.master.title(t('app_name'))
        self.master.resizable(False, False)
        self.master.geometry("250x120")
        self.master.protocol('WM_DELETE_WINDOW', self.close_window)

        self.create_widgets()

    def create_widgets(self):
        # ダイアログのウィジェットを配置
        self.label = ttk.Label(self.master, text=t('confirm_exit_app'))
        self.label.pack(padx=10, pady=10, fill="both", expand=True)

        button_frame = ttk.Frame(self.master)
        button_frame.pack(pady=10, fill="x")

        self.exit_button = ttk.Button(button_frame, text=t('yes'), style='Accent.TButton', command=self.exit_app)
        self.exit_button.pack(side="left", padx=5, expand=True)

        self.cancel_button = ttk.Button(button_frame, text=t('no'), command=self.close_window)
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
        self.master.title(t('app_name'))
        self.master.resizable(False, False)
        self.master.geometry("320x120")
        self.master.protocol('WM_DELETE_WINDOW', self.close_window)

        self.create_widgets()

    def create_widgets(self):
        # ダイアログのウィジェットを配置
        self.label = ttk.Label(self.master, text=t('confirm_close_session'))
        self.label.pack(padx=10, pady=10, fill="both", expand=True)

        button_frame = ttk.Frame(self.master)
        button_frame.pack(pady=10, fill="x")

        self.exit_button = ttk.Button(button_frame, text=t('yes'), style='Accent.TButton', command=self.exit_server)
        self.exit_button.pack(side="left", padx=5, expand=True)

        self.cancel_button = ttk.Button(button_frame, text=t('no'), command=self.close_window)
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

class server_force_stop_check(tk.Frame):
    # サーバー強制終了確認ダイアログウィンドウ
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.master.title(t('app_name'))
        self.master.resizable(False, False)
        self.master.geometry("430x140")
        self.master.protocol('WM_DELETE_WINDOW', self.close_window)

        self.create_widgets()

    def create_widgets(self):
        self.label = ttk.Label(
            self.master,
            text=t('confirm_force_stop_server'),
        )
        self.label.pack(padx=10, pady=10, fill="both", expand=True)

        button_frame = ttk.Frame(self.master)
        button_frame.pack(pady=10, fill="x")

        self.force_stop_button = ttk.Button(
            button_frame,
            text=t('yes'),
            style='Accent.TButton',
            command=self.force_stop_server,
        )
        self.force_stop_button.pack(side="left", padx=5, expand=True)

        self.cancel_button = ttk.Button(
            button_frame, text=t('no'), command=self.close_window
        )
        self.cancel_button.pack(side="right", padx=5, expand=True)

    def close_window(self):
        self.master.destroy()

    def force_stop_server(self):
        force_stop_thread = threading.Thread(
            target=force_stop_server,
            daemon=True,
        )
        force_stop_thread.start()
        self.master.destroy()

class manual_save_check(tk.Frame):
    # 手動セーブ確認ダイアログウィンドウ
    def __init__(self, master, app):
        super().__init__(master)
        self.master = master
        self.app = app
        self.master.title(t('app_name'))
        self.master.resizable(False, False)
        self.master.geometry("320x160")
        self.master.protocol('WM_DELETE_WINDOW', self.close_window)

        self.create_widgets()

    def create_widgets(self):
        self.label = ttk.Label(
            self.master,
            text=t('confirm_manual_save'),
        )
        self.label.pack(padx=10, pady=10, fill="both", expand=True)

        button_frame = ttk.Frame(self.master)
        button_frame.pack(pady=10, fill="x")

        self.save_button = ttk.Button(
            button_frame,
            text=t('yes'),
            style='Accent.TButton',
            command=self.start_save,
        )
        self.save_button.pack(side="left", padx=5, expand=True)

        self.cancel_button = ttk.Button(
            button_frame,
            text=t('no'),
            command=self.close_window,
        )
        self.cancel_button.pack(side="right", padx=5, expand=True)

    def close_window(self):
        self.master.destroy()

    def start_save(self):
        self.app.manual_save_execute()
        self.close_window()

class rollback_window(tk.Frame):
    """ロールバック対象のセーブデータを選択する画面。"""
    def __init__(self, master, app):
        super().__init__(master)
        self.master = master
        self.app = app
        self.master.title(t('rollback_data'))
        self.master.resizable(False, False)
        self.master.geometry("610x150")
        self.master.protocol('WM_DELETE_WINDOW', self.close_window)
        self.path_var = tk.StringVar()

        ttk.Label(self.master, text=t('rollback_save_file')).pack(
            padx=10, pady=(10, 4), anchor="w"
        )
        path_frame = ttk.Frame(self.master)
        path_frame.pack(fill="x", padx=10)
        ttk.Entry(path_frame, textvariable=self.path_var, width=60).pack(
            side="left", fill="x", expand=True
        )
        ttk.Button(path_frame, text=t('browse'), command=self.choose_file).pack(
            side="right", padx=(5, 0)
        )
        button_frame = ttk.Frame(self.master)
        button_frame.pack(fill="x", padx=10, pady=12)
        ttk.Button(
            button_frame, text=t('perform_rollback'), style="Danger.TButton",
            command=self.confirm
        ).pack(side="left", expand=True, padx=5)
        ttk.Button(button_frame, text=t('cancel'), command=self.close_window).pack(
            side="right", expand=True, padx=5
        )

    def choose_file(self):
        path = filedialog.askopenfilename(
            title=t('select_rollback_save_file'),
            filetypes=[(t('simutrans_save_data'), "*.sve"), (t('all_files'), "*.*")],
            initialdir=server_folder_path,
            parent=self.master,
        )
        if path:
            self.path_var.set(path)

    def confirm(self):
        path = self.path_var.get().strip()
        if not path or not os.path.isfile(path) or not path.lower().endswith('.sve'):
            messagebox.showerror(t('input_confirmation'), t('sve_file_required'), parent=self.master)
            return
        timestamp = datetime.datetime.fromtimestamp(os.path.getctime(path)).strftime('%Y/%m/%d %H:%M:%S')
        message = t('confirm_rollback', timestamp=timestamp)
        if messagebox.askyesno(t('confirm'), message, parent=self.master):
            self.app.rollback_execute(path, timestamp)
            self.close_window()

    def close_window(self):
        self.master.destroy()

def rollback_server(save_path, timestamp):
    """通知、停止、現行データのバックアップ、置換、再起動を行う。"""
    global start_code
    try:
        nettool_say('Maintenance soon.')
        discord_post(
            t('discord_rollback_title'),
            t('discord_rollback_description', timestamp=timestamp.rsplit(' ', 1)[-1]),
            0xff0000,
        )
        time.sleep(30)
        nettool_forcesync()
        subprocess.run(
            [run_nettool(), '-p', nettool_pw, '-s', server_ip + config.port_number, 'shutdown'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        deadline = time.time() + 60
        while get_pid(config.server_name) is not None and time.time() < deadline:
            time.sleep(1)
        if get_pid(config.server_name) is not None:
            raise RuntimeError('Simutransの終了を確認できませんでした。')

        long_backup(1)
        shutil.copy2(save_path, os.path.join(server_folder_path, server_save))
        print_gui_log(t('log_rollback_completed'))
        start_code = 7
    except Exception as error:
        print_gui_log(t('log_rollback_failed', error=error))
        start_code = 6

class server_restart_check(tk.Frame):
    # 確認ダイアログウィンドウ
    def __init__(self, master):
        super().__init__(master)
        self.master = master  # 既存のToplevelを受け取る
        self.master.title(t('app_name'))
        self.master.resizable(False, False)
        self.master.geometry("250x120")
        self.master.protocol('WM_DELETE_WINDOW', self.close_window)

        self.create_widgets()

    def create_widgets(self):
        # ダイアログのウィジェットを配置
        self.label = ttk.Label(self.master, text=t('confirm_restart_server'))
        self.label.pack(padx=10, pady=10, fill="both", expand=True)

        button_frame = ttk.Frame(self.master)
        button_frame.pack(pady=10, fill="x")

        self.exit_button = ttk.Button(button_frame, text=t('yes'), style='Accent.TButton', command=self.restart_server)
        self.exit_button.pack(side="left", padx=5, expand=True)

        self.cancel_button = ttk.Button(button_frame, text=t('no'), command=self.close_window)
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

    ttk.Style(root).configure("Danger.TButton", foreground="#d13438")

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

def discord_is_enabled():
    """Treat YAML values such as 1 and \"1\" as enabled."""
    try:
        return int(getattr(config, 'use_discord_bot', 0) or 0) in (1, 2)
    except (TypeError, ValueError):
        return False

def manual_save():
    """告知して30秒待機した後、サーバーを停止せずにセーブする。"""
    post_autosave_notice()
    nettool_say('Autosave soon.')
    print_gui_log(t('log_manual_save_notice_sent'))
    time.sleep(30)

    print_gui_log(t('log_saving'))
    nettool_forcesync()
    set_company_pw()
    post_autosave_completed()
    print_gui_log(t('log_save_completed'))

# 関数定義（Discord関連）
async def send_notification(
    title,
    description,
    color=0x00ff00
):

    if not discord_is_enabled():
        return

    try:

        await bot.wait_until_ready()

        channel = bot.get_channel(
            int(config.discord_channel)
        )

        # チャンネル取得失敗
        if channel is None:
            print_with_date(t('log_discord_channel_not_found'))
            return

        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )

        await channel.send(embed=embed)

    except ValueError:
        print_with_date(t('log_discord_channel_integer_required'))

    except discord.errors.Forbidden:
        print_with_date(t('log_discord_channel_permission_denied'))

    except Exception as e:
        print_with_date(t('log_discord_post_failed', error=e))

def discord_post(title, description, color=0x00ff00):
    if not discord_is_enabled():
        return
    if not bot.is_ready():
        with pending_discord_notifications_lock:
            pending_discord_notifications.append((title, description, color))
        return
    try:
        future = asyncio.run_coroutine_threadsafe(
            send_notification(title, description, color), bot.loop
        )
    except RuntimeError as error:
        print_with_date(t('log_notification_send_error', error=error))
        return

    def report_failure(completed_future):
        try:
            completed_future.result()
        except Exception as error:
            print_with_date(t('log_notification_send_error', error=error))

    future.add_done_callback(report_failure)

def post_autosave_notice():
    """設定が有効な場合だけ、オートセーブ予告をDiscordへ送信する。"""
    if str(getattr(config, 'discord_autosave_notice', 0)).strip() in ('1', '2'):
        discord_post(
            t('discord_autosave_soon_title'), t('discord_autosave_soon_description'),
            0xffbf00,
        )

def post_autosave_completed():
    """設定が有効な場合だけ、オートセーブ完了をDiscordへ送信する。"""
    if str(getattr(config, 'discord_autosave_notice', 0)).strip() in ('1', '2'):
        discord_post(
            t('discord_autosave_completed_title'), t('discord_autosave_completed_description'),
            0x00ff00,
        )

# Bot用のスレッドターゲット
def run_discord_bot():

    if not discord_is_enabled():
        return

    try:
        bot.run(config.discord_token)

    except discord.errors.LoginFailure:

        print_gui_log(
            t('log_discord_token_invalid')
        )

    except Exception as e:

        print_gui_log(
            t('log_discord_bot_start_failed', error=e)
        )

@bot.event
async def on_ready():
    if discord_is_enabled():
            print_with_date(t('log_discord_bot_started', user=bot.user))

            channel = bot.get_channel(
                int(config.discord_channel)
            )

            if channel is None:
                print_with_date(t('log_discord_channel_not_found'))

            with pending_discord_notifications_lock:
                pending = list(pending_discord_notifications)
                pending_discord_notifications.clear()
            for title, description, color in pending:
                await send_notification(title, description, color)

# 関数定義（一般）

def start_threads():
    threading.Thread(target=monitoring, daemon=True).start()
    threading.Thread(target=monitor_server_response, daemon=True).start()
    threading.Thread(target=autosave, daemon=True).start()
    threading.Thread(target=auto_restart, daemon=True).start()
    if discord_is_enabled():
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
            update_kind = t('update_kind_application_and_pak')
        elif body_source:
            update_kind = t('update_kind_application')
        else:
            update_kind = t('update_kind_pak')
        time_text = when.strftime('%H:%M') if when.date() == datetime.datetime.now().date() else when.strftime('%Y/%m/%d %H:%M')
        discord_post(t('discord_maintenance_schedule_title'), t('discord_maintenance_schedule_description', kind=update_kind, time=time_text), 0xffbf00)
    print_gui_log(t('log_update_scheduled'))

def cancel_scheduled_update():
    """登録済みの更新スケジュールを取り消す。取り消せた場合はTrueを返す。"""
    global scheduled_updates
    with scheduled_updates_lock:
        if scheduled_updates is None:
            return False
        scheduled_updates = None
    persist_runtime_state()
    print_gui_log(t('log_update_schedule_cancelled'))
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
        print_gui_log(t('log_scheduled_update_started'))
        # 既存の停止処理で同期・バックアップ・サーバー停止を行う
        server_stop(3, item['backup'])
        time.sleep(2)
        replace_update_files(item['body'], item['pak'])
        if item.get('restart_server', 1):
            # 監視ループに通常起動を依頼する
            start_code = 2
            print_gui_log(t('log_update_completed_resume_server'))
        else:
            # 監視ループがサーバーを起動しないようにしてからGUIを終了する。
            start_code = 8
            print_gui_log(t('log_update_completed_exit_app'))
            app.master.after(0, app.master.destroy)
    except Exception as e:
        print_gui_log(t('log_scheduled_update_failed', error=e))
        start_code = 2

def replace_update_files(body_source, pak_source):
    if body_source:
        shutil.copy2(body_source, server_path)
        print_gui_log(t('log_application_updated'))
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
        print_gui_log(t('log_pakset_updated'))

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

    print_with_date(t('log_nettool_detected'))

    return None

def check_os():
    # 実行OSがWindows、Mac、Linuxのいずれかであることを確認する
    os_system = platform.system()
    if os_system == 'Windows' or os_system == 'Linux' or os_system == 'Darwin':
        print_with_date(t('log_supported_os_confirmed'))
    else:
        keywait = input(f'らくらくNS+はお使いのOSには対応していません。らくらくNS+はWindows、Mac、Linuxに対応しています。\n（らくらくNS+を終了します。Enterキーを押してください。）')
        sys.exit()
    return os_system

# 初期化・設定チェック
def check_config(initialize_runtime=True):
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
                print_with_date(t('log_player_password_missing', attribute=attr_name, player=i))

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
    # response_monitor_enabled
    # ====================================================

    try:
        response_monitor_enabled = int(getattr(config, 'response_monitor_enabled', 0))

        if response_monitor_enabled not in (0, 1):
            raise ValueError

    except (NameError, ValueError, TypeError):
        input(
            '設定「response_monitor_enabled」に不正な値が設定されています。'
            '0または1を入力してください。\n'
            '（らくらくNS+を終了します。Enterキーを押してください。）'
        )
        sys.exit()
    config.response_monitor_enabled = response_monitor_enabled

    # ====================================================
    # response_timeout
    # ====================================================

    try:
        response_timeout = int(getattr(config, 'response_timeout', 0))

        if response_timeout < 0:
            raise ValueError

    except (NameError, ValueError, TypeError):
        input(
            '設定「response_timeout」に不正な値が設定されています。'
            '0以上の整数（分）を入力してください。0で無効です。\n'
            '（らくらくNS+を終了します。Enterキーを押してください。）'
        )
        sys.exit()
    config.response_timeout = response_timeout

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
        print_with_date(t('log_discord_setting_missing'))

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
    # 初期変数（起動時のみ。設定保存時は監視状態を維持する）
    # ====================================================

    if initialize_runtime:
        start_code = 0
        exit_code = 0
        nettool_pw = 0

        scheduler = sched.scheduler(time.time, time.sleep)
        scheduler_running = False

        server_ip = '127.0.0.1:'

    print_with_date(t('log_configuration_validated'))

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
    global _nettool_path_cache

    if _nettool_path_cache is not None:
        return _nettool_path_cache

    with _nettool_path_lock:
        # 複数の常駐スレッドが同時に初回呼び出しをしても、準備は1回だけ行う。
        if _nettool_path_cache is not None:
            return _nettool_path_cache

        # Windows
        if platform.system() == 'Windows':

            # PyInstaller実行時
            if getattr(sys, 'frozen', False):

                internal_path = resource_path('nettool.exe')

                # 一時フォルダへのコピーは起動中に1回だけ行う。
                temp_dir = tempfile.gettempdir()
                external_path = os.path.join(temp_dir, 'nettool.exe')
                shutil.copy2(internal_path, external_path)
                _nettool_path_cache = external_path

            # 通常Python実行時
            else:
                _nettool_path_cache = resource_path('nettool.exe')

        # Linux/macOS
        else:
            _nettool_path_cache = 'nettool'

        return _nettool_path_cache

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
        print_with_date(t('log_nettool_password_obtained'))
    else:
        print_gui_log(t('log_nettool_password_obtained'))
    return nettool_password

def print_with_date(content):
    # 日時とcontentを表示する
    date_time = datetime.datetime.now()
    print(date_time.strftime('[%Y/%m/%d %H:%M:%S] ' + content))
    return None

def invalidate_pid_cache(target_name=None):
    """サーバーを起動・停止した直後にプロセス検索結果を破棄する。"""
    with _pid_cache_lock:
        if target_name is None:
            _pid_cache.clear()
        else:
            _pid_cache.pop(target_name, None)

def get_pid(target_name, use_cache=True):

    # 指定したプロセスのPIDを取得し、ゾンビプロセスがあれば回収する。

    now = time.monotonic()
    if use_cache:
        with _pid_cache_lock:
            cached = _pid_cache.get(target_name)
        if cached is not None and now - cached[0] < PROCESS_SCAN_CACHE_SECONDS:
            return cached[1]

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
                break
                
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            # 権限がないプロセスや、途中で消えたプロセスは無視
            continue

    with _pid_cache_lock:
        _pid_cache[target_name] = (now, target_pid)
    return target_pid

def force_stop_server():
    """サーバーのPIDを指定して強制終了する。"""
    server_pid = get_pid(config.server_name, use_cache=False)
    if server_pid is None:
        print_gui_log(t('log_server_not_found_for_force_stop'))
        return None

    if platform.system() == 'Windows':
        command = ['taskkill', '/PID', str(server_pid), '/F']
    elif platform.system() in ('Linux', 'Darwin'):
        command = ['kill', '-KILL', str(server_pid)]
    else:
        print_gui_log(t('log_force_stop_unsupported_os'))
        return None

    result = subprocess.run(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode == 0:
        invalidate_pid_cache(config.server_name)
        print_gui_log(t('log_server_force_stopped'))
    else:
        print_gui_log(t('log_server_force_stop_failed'))
    return None

def set_company_pw():
    # パスワードを設定する
    global nettool_pw
    for i in range(63):
        company_id = str(i)
        company_pw = getattr(config, f'player_{i}_pw', '')
        if company_pw:
            nettool_lockcompany(company_id, company_pw)
    print_gui_log(t('log_company_passwords_set'))

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

    invalidate_pid_cache(config.server_name)

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
        print_gui_log(t('log_space_key_sent'))
    except Exception as error:
        print_gui_log(t('log_space_key_send_failed', error=error))

def nettool_say(content):
    # contentにはASCII文字以外を入れないこと（文字化け対策）
    global nettool_pw
    subprocess.run([run_nettool(), '-p', nettool_pw, '-s', server_ip + config.port_number, 'say', content], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return None

def wait_simutrans_responce():
    # Simutransの応答を待つ
    global nettool_pw
    print_gui_log(t('log_waiting_for_simutrans'))
    while True:
        result = subprocess.run([run_nettool(), '-p', nettool_pw, '-s', server_ip + config.port_number, 'clients'], encoding='utf-8', stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        if result.returncode == 0:
            print_gui_log(t('log_simutrans_responded'))
            break
        time.sleep(1)

def monitor_server_response():
    """有効時、サーバーの応答を常時監視し、無応答が続けば強制終了する。"""
    global nettool_pw
    unresponsive_since = None
    while True:
        try:
            response_timeout = int(config.response_timeout)
        except (AttributeError, TypeError, ValueError):
            response_timeout = 0
        response_monitor_enabled = int(getattr(config, 'response_monitor_enabled', 0))

        # 無効時はプロセス一覧も外部ツールも調べない。
        if response_monitor_enabled == 0 or response_timeout <= 0 or start_code in (3, 6, 8):
            unresponsive_since = None
            time.sleep(RESPONSE_MONITOR_INTERVAL_SECONDS)
            continue

        server_pid = get_pid(config.server_name)
        if server_pid is None:
            unresponsive_since = None
            time.sleep(RESPONSE_MONITOR_INTERVAL_SECONDS)
            continue

        result = subprocess.run(
            [run_nettool(), '-p', nettool_pw, '-s', server_ip + config.port_number, 'clients'],
            encoding='utf-8', stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        )
        if result.returncode == 0:
            unresponsive_since = None
        else:
            if unresponsive_since is None:
                unresponsive_since = time.monotonic()
            elif time.monotonic() - unresponsive_since >= response_timeout * 60:
                print_gui_log(t('log_response_timeout_force_stop', timeout=response_timeout))
                force_stop_server()
                unresponsive_since = None
        time.sleep(RESPONSE_MONITOR_INTERVAL_SECONDS)

def nettool_lockcompany(company_id, company_pw):
    if not company_pw:
        return
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
    print_gui_log(t('log_ban_users_set'))

def delete_old_long_backup_files():
    # 指定日数を超えたファイルを削除する

    print_gui_log(t('log_deleting_old_backups'))

    # -1なら無期限保管
    if long_backup_keep == -1:
        print_gui_log(t('log_backup_deletion_skipped_unlimited'))
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

    print_gui_log(t('log_old_backups_deleted'))

def save_backup():
    # バックアップ
    print_gui_log(t('log_backup_started'))
    # autosaveフォルダがないなら作る
    path = server_folder_path + '/autosave'
    if not os.path.isdir(path):
        print_gui_log(t('log_autosave_folder_created'))
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
    print_gui_log(t('log_backup_completed'))
    return None

def long_backup(force_backup):
    # 0なら長期バックアップ無効
    if long_backup_keep == 0 and force_backup == 0:
        print_gui_log(t('log_long_term_backup_disabled'))
        return
    print_gui_log(t('log_creating_long_term_backup'))

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
            print_gui_log(t('log_long_term_backup_created'))
        else:
            print_gui_log(t('log_backup_file_missing'))

        delete_old_long_backup_files()

    except Exception as e:
        print_gui_log(t('log_long_term_backup_failed', error=e))

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
        print_gui_log(t('log_restart_notice_sent'))
        discord_post(t('discord_restart_soon_title'), t('discord_no_login_description'), 0xffbf00)
    elif set_code == 3:
        nettool_say('Maintenance soon.')
        print_gui_log(t('log_maintenance_notice_sent'))
        discord_post(t('discord_maintenance_soon_title'), t('discord_no_login_description'), 0xffbf00)
    elif set_code == 5:
        nettool_say('Server close soon.')
        print_gui_log(t('log_server_close_notice_sent'))
        discord_post(t('discord_server_close_soon_title'), t('discord_no_login_description'), 0xffbf00)
    time.sleep(30)
    nettool_forcesync()
    if long_backup_code == 1:
        long_backup(1)
    if set_code == 2:
        nettool_say('Server is restarting.')
        print_gui_log(t('log_restarting_notice_sent'))
    elif set_code == 3:
        nettool_say('Maintenance start.')
        print_gui_log(t('log_maintenance_status_sent'))
        discord_post(t('discord_maintenance_active_title'), t('discord_maintenance_active_description'), 0xffbf00)
    elif set_code == 5:
        nettool_say('Server closed. Thank you for playing!')
        print_gui_log(t('log_server_closed_notice_sent'))
        discord_post(t('discord_server_closed_title'), t('discord_server_closed_description'), 0x00ff00)
    start_code = set_code
    subprocess.run([run_nettool(), '-p', nettool_pw, '-s', server_ip + config.port_number, 'shutdown'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    invalidate_pid_cache(config.server_name)
    return None

def auto_restart():
    # サーバー定時再起動
    global nettool_pw
    global start_code
    if config.restart_enabled and config.restart_time != -1:
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
        print_gui_log(t('log_server_already_running'))
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
                    print_gui_log(t('log_server_starting'))
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
                        print_gui_log(t('log_server_down_manual_recovery'))
                        discord_post(t('discord_server_down_title'), t('discord_server_down_manual_recovery'), 0xff0000)
                        start_code = 6
                        app.after(0,app.set_manual_restart_mode)
                        while start_code == 6:
                            time.sleep(1)
                        continue
                    else:
                        # サーバーダウン（自動復旧時）
                        app_start()
                        print_gui_log(t('log_server_down_restarting'))
                        discord_post(t('discord_server_down_title'), t('discord_server_down_auto_recovery', timestamp=save_timestamp), 0xff0000)
                    nettool_pw = get_nettool_pw(1)
                    wait_simutrans_responce()
                    set_company_pw()
                    set_ban_user()
                    print_gui_log(t('log_server_restarted'))
                    discord_post(t('discord_server_recovered_title'), t('discord_orderly_login_description'), 0x00ff00)
                elif start_code == 2:
                    # 再起動した場合
                    app_start()
                    print_gui_log(t('log_server_starting'))
                    nettool_pw = get_nettool_pw(1)
                    wait_simutrans_responce()
                    set_company_pw()
                    set_ban_user()
                    print_gui_log(t('log_server_started'))
                    discord_post(t('discord_server_restarted_title'), t('discord_orderly_login_description'), 0x00ff00)
                    start_code = 1
                elif start_code == 4:
                    # メンテナンス終了時
                    app_start()
                    print_gui_log(t('log_server_resuming'))
                    nettool_pw = get_nettool_pw(1)
                    wait_simutrans_responce()
                    set_company_pw()
                    set_ban_user()
                    print_gui_log(t('log_server_resumed'))
                    discord_post(t('discord_maintenance_completed_title'), t('discord_thanks_description'), 0x00ff00)
                    start_code = 1
                elif start_code == 7:
                    # サーバー手動再開時
                    app_start()
                    print_gui_log(t('log_server_resuming'))
                    nettool_pw = get_nettool_pw(1)
                    wait_simutrans_responce()
                    set_company_pw()
                    set_ban_user()
                    print_gui_log(t('log_server_resumed'))
                    discord_post(t('discord_server_resumed_title'), t('discord_server_resumed_description'), 0x00ff00)
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
            print_gui_log(t('log_autosave_notice_sent'))

            time.sleep(30)

            # ----------------------------------------
            # autosave
            # ----------------------------------------
            print_gui_log(t('log_autosaving'))

            start_time = time.time()

            nettool_forcesync()
            set_company_pw()

            end_time = time.time()

            print_gui_log(t('log_autosave_completed'))
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

                    print_gui_log(t('log_scheduled_backup_started'))

                    save_backup()

                    print_gui_log(t('log_scheduled_backup_completed'))

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
            print_gui_log(t('log_autosave_notice_sent'))

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
            print_gui_log(t('log_autosaving'))

            nettool_forcesync()
            set_company_pw()

            print_gui_log(t('log_autosave_completed'))
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

            print_gui_log(t('log_scheduled_backup_started'))

            save_backup()

            print_gui_log(t('log_scheduled_backup_completed'))

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
