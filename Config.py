#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2019/1/5 20:23
# @Author  : Miyouzi
# @File    : Config.py
# @Software: PyCharm

import os, json, pprint, re

working_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)))
config_path = os.path.join(working_dir, 'config.json')
sn_list_path = os.path.join(working_dir, 'sn_list.txt')
cookies_path = os.path.join(working_dir, 'cookies.txt')
latest_config_version = 0.1


def __init_settings():
    if os.path.exists(config_path):
        os.remove(config_path)
    settings = {'bangumi_dir': '',
                'check_frequency': 5,
                'download_resolution': '1080',
                'default_download_mode': 'latest',  # 仅下载最新一集，另一个模式是 'all' 下载所有及日后更新
                'multi-thread': 3,  # 最大并发下载数
                'add_resolution_to_video_filename': True,  # 是否在文件名中添加清晰度说明
                'customized_video_filename_prefix': '【動畫瘋】',  # 用户自定前缀
                'customized_video_filename_suffix': '',  # 用户自定后缀
                'proxy': {  # 代理功能，咕咕咕……
                    'proxy_server': '',
                    'proxy_port': '',
                    'proxy_protocol': '',
                    'proxy_username': '',
                    'proxy_password': ''
                },
                'ftp': {  # 将文件上传至远程服务器，咕咕咕咕……
                    'host': '',
                    'port': '',
                    'user': '',
                    'pwd': '',
                    'cwd': '',  # 文件存放目录
                },
                'config_version': 1.0
                }
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=4)


def read_settings():
    if not os.path.exists(config_path):
        __init_settings()

    with open(config_path, 'r', encoding='utf-8') as f:
        settings = json.load(f)
        if settings['config_version'] != latest_config_version:
            __init_settings()
        # 防呆
        settings['check_frequency'] = int(settings['check_frequency'])
        settings['download_resolution'] = str(settings['download_resolution'])
        settings['multi-thread'] = int(settings['multi-thread'])
        return settings


def read_sn_list():
    settings = read_settings()
    with open(sn_list_path, 'r', encoding='utf-8') as f:
        sn_dict = {}
        for i in f.readlines():
            i = re.sub(r'#.+\n', '', i).strip()
            a = [l for l in i.split(" ")]
            try:
                sn_dict[int(a[0])] = a[1]
            except IndexError:
                sn_dict[int(a[0])] = settings['default_download_mode']
        return sn_dict


def read_cookies():
    # 用户可以将cookie保存在程序所在目录下，保存为 cookies.txt ，UTF-8 编码
    if os.path.exists(cookies_path):
        with open(cookies_path, 'r', encoding='utf-8') as f:
            cookies = f.readline()
            cookies = dict([l.split("=", 1) for l in cookies.split("; ")])
            return cookies
    else:
        return {}


if __name__=='__main__':
    pprint.pprint(read_cookies())
    pprint.pprint(read_settings())
