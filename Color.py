#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2019/1/6 22:15
# @Author  : Miyouzi
# @File    : Color.py
# @Software: PyCharm

import ctypes

# 用於Win下染色輸出，代碼來自 https://blog.csdn.net/five3/article/details/7630295
class Color:
    ''' See http://msdn.microsoft.com/library/default.asp?url=/library/en-us/winprog/winprog/windows_api_reference.asp
    for information on Windows APIs.'''

    STD_OUTPUT_HANDLE = -11
    std_out_handle = ctypes.windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)

    def __init__(self):
        self.FOREGROUND_RED = 0x04
        self.FOREGROUND_GREEN= 0x02
        self.FOREGROUND_BLUE = 0x01
        self.FOREGROUND_INTENSITY = 0x08

    def set_cmd_color(self, color, handle=std_out_handle):
        """(color) -> bit
        Example: set_cmd_color(FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_BLUE | FOREGROUND_INTENSITY)
        """
        bool = ctypes.windll.kernel32.SetConsoleTextAttribute(handle, color)
        return bool

    def reset_color(self):
        self.set_cmd_color(self.FOREGROUND_RED | self.FOREGROUND_GREEN | self.FOREGROUND_BLUE)

    def print_red_text(self, print_text):
        self.set_cmd_color(self.FOREGROUND_RED | self.FOREGROUND_INTENSITY)
        print(print_text)
        self.reset_color()