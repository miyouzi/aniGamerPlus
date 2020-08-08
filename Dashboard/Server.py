#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2019/6/26 16:12
# @Author  : Miyouzi
# @File    : Server.py
# @Software: PyCharm

import json, sys, os, re
import threading, traceback

from aniGamerPlus import Config
from flask import Flask, request
from flask import render_template
from flask_basicauth import BasicAuth
from aniGamerPlus import __cui as cui
import logging, termcolor
from ColorPrint import err_print
from logging.handlers import TimedRotatingFileHandler
import mimetypes


mimetypes.add_type('text/css', '.css')
mimetypes.add_type('application/x-javascript', '.js')
template_path = os.path.join(Config.get_working_dir(), 'Dashboard', 'templates')
static_path = os.path.join(Config.get_working_dir(), 'Dashboard', 'static')
app = Flask(__name__, template_folder=template_path, static_folder=static_path)

# 日志处理
logger = logging.getLogger('werkzeug')
web_log_path = os.path.join(Config.get_working_dir(), 'logs', 'web.log')
handler = TimedRotatingFileHandler(filename=web_log_path, when='midnight', backupCount=7, encoding='utf-8')
handler.suffix = '%Y-%m-%d.log'
handler.extMatch = re.compile(r'^\d{4}-\d{2}-\d{2}.log')
logger.addHandler(handler)


# 处理 Flask 写日志到文件带有颜色控制符的问题
def colored(text, color=None, on_color=None, attrs=None):
    who_invoked = traceback.extract_stack()[-2][2]  # 函数调用人
    if who_invoked == 'log_request':
        # 如果是来自 Flask/werkzeug 的调用
        return text
    else:
        # 来自其他的调用正常高亮
        COLORS = termcolor.COLORS
        HIGHLIGHTS = termcolor.HIGHLIGHTS
        ATTRIBUTES = termcolor.ATTRIBUTES
        RESET = termcolor.RESET
        if os.getenv('ANSI_COLORS_DISABLED') is None:
            fmt_str = '\033[%dm%s'
            if color is not None:
                text = fmt_str % (COLORS[color], text)
            if on_color is not None:
                text = fmt_str % (HIGHLIGHTS[on_color], text)
            if attrs is not None:
                for attr in attrs:
                    text = fmt_str % (ATTRIBUTES[attr], text)
            text += RESET
        return text


termcolor.colored = colored
app.logger.addHandler(handler)


# 读取web需要的配置名称列表
id_list_path = os.path.join(Config.get_working_dir(), 'Dashboard', 'static', 'js', 'settings_id_list.js')
with open(id_list_path, 'r', encoding='utf-8') as f:
    id_list = re.sub(r'(var id_list\s*=\s*|\s*\n?)', '', f.read()).replace('\'', '"')
    id_list = json.loads(id_list)


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/data/config.json', methods=['GET'])
def config():
    settings = Config.read_settings()
    web_settings = {}
    for id in id_list:
        web_settings[id] = settings[id]  # 仅返回 web 需要的配置

    return json.dumps(web_settings)


@app.route('/uploadConfig', methods=['POST'])
def recv_config():
    data = json.loads(request.get_data(as_text=True))
    new_settings = Config.read_settings()
    for id in id_list:
        new_settings[id] = data[id]  # 更新配置
    Config.write_settings(new_settings)  # 保存配置
    err_print(0, 'Dashboard', '通過 Web 控制臺更新了 config.json', no_sn=True, status=2)
    return '{"status":"200"}'


@app.route('/manualTask', methods=['POST'])
def manual_task():
    data = json.loads(request.get_data(as_text=True))
    settings = Config.read_settings()

    # 下载清晰度
    if data['resolution'] not in ('360', '480', '540', '720', '1080'):
        # 如果不是合法清晰度
        resolution = settings['download_resolution']
    else:
        resolution = data['resolution']

    # 下载模式
    if data['mode'] not in ('single', 'latest', 'all', 'largest-sn'):
        mode = 'single'
    else:
        mode = data['mode']

    # 下载线程数
    thread = int(data['thread'])
    if thread > Config.get_max_multi_thread():
        # 是否超过最大允许线程数
        thread_limit = Config.get_max_multi_thread()
    else:
        thread_limit = thread

    def run_cui():
        cui(data['sn'], resolution, mode, thread_limit, [], classify=data['classify'], realtime_show=False)

    server = threading.Thread(target=run_cui)
    err_print(0, 'Dashboard', '通過 Web 控制臺下達了手動任務', no_sn=True, status=2)
    server.start()  # 启动手动任务线程
    return '{"status":"200"}'


def run():
    settings = Config.read_settings()  # 读取配置

    if settings['dashboard']['BasicAuth']:
        # BasicAuth 配置
        app.config['BASIC_AUTH_USERNAME'] = settings['dashboard']['username']  # BasicAuth user
        app.config['BASIC_AUTH_PASSWORD'] = settings['dashboard']['password']  # BasicAuth password
        app.config['BASIC_AUTH_FORCE'] = True  # 全站验证
        basic_auth = BasicAuth(app)

    port = settings['dashboard']['port']
    host = settings['dashboard']['host']

    if settings['dashboard']['SSL']:
        # SSL 配置
        ssl_path = os.path.join(Config.get_working_dir(), 'Dashboard', 'sslkey')
        ssl_crt = os.path.join(ssl_path, 'server.crt')
        ssl_key = os.path.join(ssl_path, 'server.key')
        ssl_keys = (ssl_crt, ssl_key)
        app.run(debug=False, use_reloader=False, port=port, host=host, ssl_context=ssl_keys)
    else:
        app.run(debug=False, use_reloader=False, port=port, host=host)


if __name__ == '__main__':
    pass
