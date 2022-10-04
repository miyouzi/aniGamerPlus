#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2019/1/6 22:15
# @Author  : Miyouzi
# @File    : Color.py
# @Software: PyCharm

import ctypes, subprocess, platform, os, json, re
from termcolor import cprint
from datetime import datetime
import Config


def read_log_settings():
    settings = {}
    try:
        with open(Config.get_config_path(), 'r', encoding='utf-8') as f:
            # 转义win路径
            settings = json.loads(re.sub(r'\\', '\\\\\\\\', f.read()))
    except json.JSONDecodeError:
        Config.del_bom(Config.get_config_path(), display=False)  # 移除bom
        # 重新载入
        with open(Config.get_config_path(), 'r', encoding='utf-8') as f:
            settings = json.loads(re.sub(r'\\', '\\\\\\\\', f.read()))
    except BaseException as e:
        settings['save_logs'] = True
        settings['quantity_of_logs'] = 7
        print('日志配置讀取失敗, 將使用默認配置: 啓用日志, 最多保存7份 '+str(e))
    if 'save_logs' not in settings.keys():
        settings['save_logs'] = True
    if 'quantity_of_logs' not in settings.keys():
        settings['quantity_of_logs'] = 7
    return settings


log_settings = read_log_settings()


def err_print(sn, err_msg, detail='', status=0, no_sn=False, prefix='', display=True, display_time=True):
    # status 三个设定值, 0 为一般输出, 1 为错误输出, 2 为成功输出
    # err_msg 为信息类型/概要, 最好为四字中文
    # detail 为详细信息描述
    # no_sn 控制是否打印 sn , 默认打印
    # display 是否在 console 显示（False则仅输出在日志文件）
    # display_time 是否显示时间
    # 格式范例:
    # 2019-01-30 17:22:30 更新狀態: sn=12345 檢查更新失敗, 跳過等待下次檢查
    green = False

    def succeed_or_failed_print():
        check_tty = subprocess.Popen('tty', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        check_tty_return_str = check_tty.stdout.read().decode("utf-8")[0:-1]
        if 'Windows' in platform.system() and check_tty_return_str in ('/dev/cons0', ''):
            clr = Color()
            if green:
                clr.print_green_text(msg)
            else:
                clr.print_red_text(msg)
        else:
            if green:
                cprint(msg, 'green', attrs=['bold'])
            else:
                cprint(msg, 'red', attrs=['bold'])

    if display_time:
        msg = prefix + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ' '
    else:
        msg = prefix

    if no_sn:
        msg = msg + err_msg + ' ' + detail
    else:
        msg = msg + err_msg + ': sn=' + str(sn) + '\t' + detail

    if display:
        if status == 0:
            print(msg)
        elif status == 1:
            # 为 1 错误输出
            green = False
            succeed_or_failed_print()
        else:
            # 为 2 成功输出
            green = True
            succeed_or_failed_print()

    if log_settings['save_logs']:
        logs_dir = os.path.join(Config.get_working_dir(), 'logs')
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
        log_path = os.path.join(logs_dir, datetime.now().strftime("%Y-%m-%d") + '.log')
        with open(log_path, 'a+', encoding='utf-8') as log:
            log.write(msg + '\n')


# 用於Win下染色輸出，代碼來自 https://blog.csdn.net/five3/article/details/7630295
class Color:
    ''' See http://msdn.microsoft.com/library/default.asp?url=/library/en-us/winprog/winprog/windows_api_reference.asp
    for information on Windows APIs.'''

    def __init__(self):
        self.FOREGROUND_RED = 0x04
        self.FOREGROUND_GREEN = 0x02
        self.FOREGROUND_BLUE = 0x01
        self.FOREGROUND_INTENSITY = 0x08
        STD_OUTPUT_HANDLE = -11
        self.handle = ctypes.windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)

    def set_cmd_color(self, color):
        """(color) -> bit
        Example: set_cmd_color(FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_BLUE | FOREGROUND_INTENSITY)
        """
        bool = ctypes.windll.kernel32.SetConsoleTextAttribute(self.handle, color)
        return bool

    def reset_color(self):
        self.set_cmd_color(self.FOREGROUND_RED | self.FOREGROUND_GREEN | self.FOREGROUND_BLUE)

    def print_red_text(self, print_text):
        self.set_cmd_color(self.FOREGROUND_RED | self.FOREGROUND_INTENSITY)
        print(print_text)
        self.reset_color()

    def print_green_text(self, print_text):
        self.set_cmd_color(self.FOREGROUND_GREEN | self.FOREGROUND_INTENSITY)
        print(print_text)
        self.reset_color()
