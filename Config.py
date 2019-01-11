#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2019/1/5 20:23
# @Author  : Miyouzi
# @File    : Config.py
# @Software: PyCharm

import os, json, re, sys

working_dir = os.path.dirname(os.path.realpath(__file__))
# working_dir = os.path.dirname(sys.executable)  # 使用 pyinstaller 编译时，打开此项
config_path = os.path.join(working_dir, 'config.json')
sn_list_path = os.path.join(working_dir, 'sn_list.txt')
cookies_path = os.path.join(working_dir, 'cookies.txt')
aniGamerPlus_version = 'v5.1'
latest_config_version = 1.1


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
                    'server': '',
                    'port': '',
                    'protocol': '',
                    'user': '',
                    'pwd': ''
                },
                'ftp': {  # 将文件上传至远程服务器，咕咕咕咕……
                    'server': '',
                    'port': '',
                    'user': '',
                    'pwd': '',
                    'cwd': '',  # 文件存放目录
                },
                'config_version': latest_config_version
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
            settings = json.load(f)
        # 防呆
        settings['check_frequency'] = int(settings['check_frequency'])
        settings['download_resolution'] = str(settings['download_resolution'])
        settings['multi-thread'] = int(settings['multi-thread'])
        if not re.match(r'^(all|latest|largest-sn)$', settings['default_download_mode']):
            settings['default_download_mode'] = 'latest'  # 如果输入非法模式, 将重置为 latest 模式
        # 如果用户没有有自定番剧目录或目录不存在，则保存在本地 bangumi 目录
        if not (settings['bangumi_dir'] and os.path.exists(settings['bangumi_dir'])):
            settings['bangumi_dir'] = os.path.join(working_dir, 'bangumi')
        settings['working_dir'] = working_dir
        settings['aniGamerPlus_version'] = aniGamerPlus_version
        return settings


def read_sn_list():
    settings = read_settings()
    if not os.path.exists(sn_list_path):
        return {}
    with open(sn_list_path, 'r', encoding='utf-8') as f:
        sn_dict = {}
        for i in f.readlines():
            i = re.sub(r'#.+\n', '', i).strip()
            i = re.sub(r' +', ' ', i)  # 去除多余空格
            a = i.split(" ")
            if not a[0]:  # 跳过纯注释行
                continue
            if re.match(r'^\d+$',a[0]):
                if len(a) > 1:  # 如果有特別指定下载模式
                    if re.match(r'^(all|latest|largest-sn)$', a[1]):  # 仅认可合法的模式
                        sn_dict[int(a[0])] = a[1]
                    else:
                        sn_dict[int(a[0])] = settings['default_download_mode']  # 非法模式一律替换成默认模式
                else:  # 没有指定下载模式则使用默认设定
                    sn_dict[int(a[0])] = settings['default_download_mode']
        return sn_dict


def read_cookies():
    # 用户可以将cookie保存在程序所在目录下，保存为 cookies.txt ，UTF-8 编码
    if os.path.exists(cookies_path):
        with open(cookies_path, 'r', encoding='utf-8') as f:
            cookies = f.readline()
            cookies = dict([l.split("=", 1) for l in cookies.split("; ")])
            cookies.pop('ckBH_lastBoard', 404)
            return cookies
    else:
        return {}


if __name__ == '__main__':
    pass
