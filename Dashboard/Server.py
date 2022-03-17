#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2019/6/26 16:12
# @Author  : Miyouzi
# @File    : Server.py
# @Software: PyCharm

# 非阻塞
from gevent import monkey; monkey.patch_all()
from gevent import spawn

import json, sys, os, re, time
import threading, traceback
import random, string

from aniGamerPlus import Config
from flask import Flask, request, jsonify
from flask import render_template
from flask_basicauth import BasicAuth
from aniGamerPlus import __cui as cui
import logging, termcolor
from ColorPrint import err_print
from logging.handlers import TimedRotatingFileHandler
import mimetypes
# ws 支援
import ssl
from flask_sockets import Sockets
from gevent.pywsgi import WSGIServer
from geventwebsocket.exceptions import WebSocketError
from geventwebsocket.handler import WebSocketHandler

mimetypes.add_type('text/css', '.css')
mimetypes.add_type('application/x-javascript', '.js')
template_path = os.path.join(Config.get_working_dir(), 'Dashboard', 'templates')
static_path = os.path.join(Config.get_working_dir(), 'Dashboard', 'static')
app = Flask(__name__, template_folder=template_path, static_folder=static_path)
app.debug = False
sockets = Sockets(app)

# 日誌處理
# logger = logging.getLogger('werkzeug')
logger = logging.getLogger('geventwebsocket')
logging.basicConfig(level=logging.INFO)  # 記錄訪問
web_log_path = os.path.join(Config.get_working_dir(), 'logs', 'web.log')
handler = TimedRotatingFileHandler(filename=web_log_path, when='midnight', backupCount=7, encoding='utf-8')
handler.suffix = '%Y-%m-%d.log'
handler.extMatch = re.compile(r'^\d{4}-\d{2}-\d{2}.log')
logger.addHandler(handler)
logger.propagate = False  # 不在控制檯上輸出

# websocket 鑑權需要的 token，隨機一個 32 位初始 token
websocket_token = ''.join(random.sample(string.ascii_letters + string.digits, 32))


# 處理 Flask 寫日誌到檔案帶有顏色控制符的問題
def colored(text, color=None, on_color=None, attrs=None):
    who_invoked = traceback.extract_stack()[-2][2]  # 函式呼叫人
    if who_invoked == 'log_request':
        # 如果是來自 Flask/werkzeug 的呼叫
        return text
    else:
        # 來自其他的呼叫正常提示
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


# 讀取 web 需要的設定名稱列表
id_list_path = os.path.join(Config.get_working_dir(), 'Dashboard', 'static', 'js', 'settings_id_list.js')
with open(id_list_path, 'r', encoding='utf-8') as f:
    id_list = re.sub(r'(var id_list\s*=\s*|\s*\n?)', '', f.read()).replace('\'', '"')
    id_list = json.loads(id_list)


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/monitor')
def monitor():
    return render_template('monitor.html')


@app.route('/data/config.json', methods=['GET'])
def config():
    settings = Config.read_settings()
    web_settings = {}
    for id in id_list:
        web_settings[id] = settings[id]  # 僅返回 web 需要的設定

    return jsonify(web_settings)


@app.route('/uploadConfig', methods=['POST'])
def recv_config():
    data = json.loads(request.get_data(as_text=True))
    new_settings = Config.read_settings()
    for id in id_list:
        new_settings[id] = data[id]  # 更新設定
    Config.write_settings(new_settings)  # 儲存設定
    err_print(0, 'Dashboard', '通過 Web 控制臺更新了 config.json', no_sn=True, status=2)
    return '{"status":"200"}'


@app.route('/manualTask', methods=['POST'])
def manual_task():
    data = json.loads(request.get_data(as_text=True))
    settings = Config.read_settings()

    # 下载解析度
    if data['resolution'] not in ('360', '480', '540', '720', '1080'):
        # 如果不是合法解析度
        resolution = settings['download_resolution']
    else:
        resolution = data['resolution']

    # 下載模式
    if data['mode'] not in ('single', 'latest', 'all', 'largest-sn'):
        mode = 'single'
    else:
        mode = data['mode']

    # 下載執行緒數
    thread = int(data['thread'])
    if thread > Config.get_max_multi_thread():
        # 是否超過最大允許執行緒數
        thread_limit = Config.get_max_multi_thread()
    else:
        thread_limit = thread

    def run_cui():
        cui(data['sn'], resolution, mode, thread_limit, [], classify=data['classify'], realtime_show=False, cui_danmu=data['danmu'])

    server = threading.Thread(target=run_cui)
    err_print(0, 'Dashboard', '通過 Web 控制臺下達了手動任務', no_sn=True, status=2)
    server.start()  # 啟動手動任務執行緒
    return '{"status":"200"}'


@app.route('/data/sn_list', methods=['GET'])
def show_sn_list():
    return Config.get_sn_list_content()


@app.route('/data/get_token', methods=['GET'])
def get_token():
    global websocket_token
    # 生成 32 位隨機字串作為 token
    websocket_token = ''.join(random.sample(string.ascii_letters + string.digits, 32))
    return websocket_token, '200 ok'


@sockets.route('/data/tasks_progress')
def tasks_progress(ws):
    # 鑑權
    global websocket_token
    token = request.args.get('token')
    if token != websocket_token:
        ws.send('Unauthorized')
        ws.close()
    else:
        # 一次性 token
        websocket_token = ''

    # 推送任務進度資料
    # https://blog.csdn.net/sinat_32651363/article/details/87912701
    while not ws.closed:
        msg = json.dumps(Config.tasks_progress_rate)
        try:
            ws.send(msg)
            time.sleep(1)
        except WebSocketError:
            # 連線中斷
            ws.close()
            break


@app.route('/sn_list', methods=['POST'])
def set_sn_list():
    data = request.get_data(as_text=True)
    Config.write_sn_list(data)
    err_print(0, 'Dashboard', '通過 Web 控制臺更新了 sn_list', no_sn=True, status=2)
    return '{"status":"200"}'


def run():
    settings = Config.read_settings()  # 讀取設定

    if settings['dashboard']['BasicAuth']:
        # BasicAuth 設定
        app.config['BASIC_AUTH_USERNAME'] = settings['dashboard']['username']  # BasicAuth user
        app.config['BASIC_AUTH_PASSWORD'] = settings['dashboard']['password']  # BasicAuth password
        app.config['BASIC_AUTH_FORCE'] = True  # 全站驗證
        basic_auth = BasicAuth(app)

    port = settings['dashboard']['port']
    host = settings['dashboard']['host']

    if settings['dashboard']['SSL']:
        # SSL 設定
        ssl_path = os.path.join(Config.get_working_dir(), 'Dashboard', 'sslkey')
        ssl_crt = os.path.join(ssl_path, 'server.crt')
        ssl_key = os.path.join(ssl_path, 'server.key')
        # ssl_keys = (ssl_crt, ssl_key)
        # app.run(use_reloader=False, port=port, host=host, ssl_context=ssl_keys)
        server = WSGIServer((host, port), app, handler_class=WebSocketHandler, certfile=ssl_crt, keyfile=ssl_key)

        wrap_socket = server.wrap_socket
        wrap_socket_and_handle = server.wrap_socket_and_handle

        # 處理一些瀏覽器（例如Chrome）嘗試 SSL v3 存取時報錯
        def my_wrap_socket(sock, **_kwargs):
            try:
                # print('my_wrap_socket')
                return wrap_socket(sock, **_kwargs)
            except ssl.SSLError:
                # print('my_wrap_socket ssl.SSLError')
                pass

        # 此方法依賴上面的返回值，Ｍ因此當嘗試訪問 SSL v3 時，這個也會出錯
        def my_wrap_socket_and_handle(client_socket, address):
            try:
                # print('my_wrap_socket_and_handle')
                return wrap_socket_and_handle(client_socket, address)
            except AttributeError:
                # print('my_wrap_socket_and_handle AttributeError')
                pass

        server.wrap_socket = my_wrap_socket
        server.wrap_socket_and_handle = my_wrap_socket_and_handle

    else:
        # app.run(use_reloader=False, port=port, host=host)
        server = WSGIServer((host, port), app, handler_class=WebSocketHandler)

    server.serve_forever()


if __name__ == '__main__':
    run()
    pass
