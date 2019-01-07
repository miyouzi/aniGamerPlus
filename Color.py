#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2019/1/6 22:15
# @Author  : Miyouzi
# @File    : Color.py
# @Software: PyCharm

import ctypes, subprocess, platform
from termcolor import cprint


def err_print(err_msg):
    check_tty = subprocess.Popen('tty', shell=True, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE).stdout.read().decode("utf-8")[0:-1]
    if 'Windows' in platform.system() and check_tty == '/dev/cons0':
        clr = Color()
        clr.print_red_text(err_msg)
    else:
        cprint(err_msg, 'red', attrs=['bold'])


# 用於Win下染色輸出，代碼來自 https://blog.csdn.net/five3/article/details/7630295
class Color:
    ''' See http://msdn.microsoft.com/library/default.asp?url=/library/en-us/winprog/winprog/windows_api_reference.asp
    for information on Windows APIs.'''

    def __init__(self):
        self.FOREGROUND_RED = 0x04
        self.FOREGROUND_GREEN= 0x02
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