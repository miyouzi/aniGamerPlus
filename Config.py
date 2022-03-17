#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2019/1/5 20:23
# @Author  : Miyouzi
# @File    : Config.py
# @Software: PyCharm

import os, json, re, sys, requests, time, random, codecs, chardet
import sqlite3
import socket
from urllib.parse import quote
from urllib.parse import urlencode

# 你猜猜看我是 .exe 或是 .py 檔案
if getattr(sys, 'frozen', False):
    working_dir = os.path.dirname(sys.executable)
else:
    working_dir = os.path.dirname(os.path.realpath(__file__))

config_path = os.path.join(working_dir, 'config.json')
sn_list_path = os.path.join(working_dir, 'sn_list.txt')
cookie_path = os.path.join(working_dir, 'cookie.txt')
logs_dir = os.path.join(working_dir, 'logs')
aniGamerPlus_version = 'v22.7'
latest_config_version = 15.3
latest_database_version = 2.0
cookie = None
max_multi_thread = 5
max_multi_downloading_segment = 5
tasks_progress_rate = {}  # 儲存任務進度，供面板使用，
# 格式: {sn: {'rate': 任務進度百分比(float), 'status': 任務狀態, 'filename': 檔名} }
# 任務狀態有:  '正在下載' '正在解密合並' '正在移至番劇目錄' '任務失敗, 等待重啟' '等待下載'


def __color_print(sn, err_msg, detail='', status=0, no_sn=False, display=True):
    # 避免與 ColorPrint.py 相互呼叫產生問題
    try:
        err_print(sn, err_msg, detail=detail, status=status, no_sn=no_sn, display=display)
    except UnboundLocalError:
        from ColorPrint import err_print
        err_print(sn, err_msg, detail=detail, status=status, no_sn=no_sn, display=display)


def get_max_multi_thread():
    return max_multi_thread


def legalize_filename(filename):
    # 檔名合法化
    legal_filename = re.sub(r'\|+', '｜', filename)  # 處理 | , 轉全型｜
    legal_filename = re.sub(r'\?+', '？', legal_filename)  # 處理 ? , 轉中文 ？
    legal_filename = re.sub(r'\*+', '＊', legal_filename)  # 處理 * , 轉全型＊
    legal_filename = re.sub(r'<+', '＜', legal_filename)  # 處理 < , 轉全型＜
    legal_filename = re.sub(r'>+', '＞', legal_filename)  # 處理 < , 轉全型＞
    legal_filename = re.sub(r'\"+', '＂', legal_filename)  # 處理 " , 轉全型＂
    legal_filename = re.sub(r':+', '：', legal_filename)  # 處理 : , 轉中文：
    legal_filename = re.sub(r'\\', '＼', legal_filename)  # 處理 \ , 轉全型＼
    legal_filename = re.sub(r'/', '／', legal_filename)  # 處理 / , 轉全型／
    return legal_filename


def get_working_dir():
    return working_dir


def get_config_path():
    return config_path


def get_sn_list_content():
    # 返回 sn_list 所有內容, 包括註釋, 提供給 Web 控制檯
    if not os.path.exists(sn_list_path):
        return ''
    with open(sn_list_path, 'r', encoding='utf-8') as f:
        return f.read()


def __init_settings():
    if os.path.exists(config_path):
        os.remove(config_path)
    settings = {'bangumi_dir': '',
                'temp_dir': '',
                'classify_bangumi': True,  # 控制是否建立番劇目錄
                'check_frequency': 5,  # 檢查 cd 時間, 單位分鐘
                'download_resolution': '1080',  # 下載解析度
                'lock_resolution': False,  # 鎖定解析度, 如果解析度不存在, 則宣吿下載失敗
                'only_use_vip': False,  # 鎖定 VIP 帳號下載
                'default_download_mode': 'latest',  # 僅下載最新一集，另一個模式是 'all' 下載所有及日後更新
                'use_copyfile_method': False,  # 轉移影片至番劇目錄時是否使用複製法, 使用 True 以相容 rclone 掛載硬碟
                'multi-thread': 1,  # 最大併發下載數
                'multi_upload': 3,  # 最大併發上傳數
                'segment_download_mode': True,  # 由 aniGamerPlus 下載分段, False 為 ffmpeg 下載
                'multi_downloading_segment': 2,  # 在上面設定為 True 時有效, 每個影片併發下載分段數
                'segment_max_retry': 8,  # 在分段下載模式時有效, 每個分段最大重試次數, -1 為 無限重試
                'add_bangumi_name_to_video_filename': True,
                'add_resolution_to_video_filename': True,  # 是否在檔名中新增解析度說明
                'customized_video_filename_prefix': '【動畫瘋】',  # 使用者自定字首
                'customized_bangumi_name_suffix': '',  # 使用者自定義番劇名字尾 (在劇集名之前)
                'customized_video_filename_suffix': '',  # 使用者自定字尾
                'video_filename_extension': 'mp4',  # 影片副檔名/封裝格式
                'zerofill': 1,  # 劇集名補零, 此項填補足位數, 小於等於 1 即不補零
                # cookie 的自動重新整理對 UA 有檢查
                'ua': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.96 Safari/537.36',
                'use_proxy': False,
                'proxy': 'http://user:passwd@example.com:1000',  # 代理功能，config_version v13.0 刪除鏈式代理
                'upload_to_server': False,
                'ftp': {  # 將檔案上傳至遠端伺服器
                    'server': '',
                    'port': '',
                    'user': '',
                    'pwd': '',
                    'tls': True,
                    'cwd': '',  # 檔案存放目錄，登入後首先進入的目錄
                    'show_error_detail': False,
                    'max_retry_num': 15
                },
                'user_command': 'shutdown -s -t 60',
                'coolq_notify': False,
                'coolq_settings': {
                    'msg_argument_name': 'message',
                    'message_suffix': '追加的資訊',
                    'query': [
                        'http://127.0.0.1:5700/send_group_msg?access_token=abc&group_id=12345678',
                        'http://127.0.0.1:5700/send_group_msg?access_token=abc&group_id=87654321'
                    ]
                },
                'telebot_notify': False,
                'telebot_token': '',
                'discord_notify': False,
                'discord_token': '',
                'plex_refresh': False,
                'plex_url': '',
                'plex_token': '',
                'plex_section': '',
                'faststart_movflags': False,
                'audio_language': False,
                'use_mobile_api': False,
                'danmu': False,
                'check_latest_version': True,  # 是否檢查新版本
                'read_sn_list_when_checking_update': True,
                'read_config_when_checking_update': True,
                'ads_time': 25,
                'mobile_ads_time': 3,
                'use_dashboard': True,
                'dashboard': {
                    'host': '127.0.0.1',
                    'port': 5000,
                    'SSL': False,
                    'BasicAuth': False,
                    'username': 'admin',
                    'password': 'admin'
                },
                'save_logs': True,
                'quantity_of_logs': 7,
                'config_version': latest_config_version,
                'database_version': latest_database_version
                }
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=4)


def __update_settings(old_settings):  # 升級設定檔案
    new_settings = old_settings.copy()
    if 'check_latest_version' not in new_settings.keys():  # v2.0 新增檢查更新開關
        new_settings['check_latest_version'] = True

    if 'tls' not in new_settings['ftp'].keys():  # v2.0 新增 FTP over TLS 開關
        new_settings['ftp']['tls'] = True

    if 'upload_to_server' not in new_settings.keys():  # v2.0 新增上傳開關
        new_settings['upload_to_server'] = False

    if 'use_proxy' not in new_settings.keys():  # v2.0 新增代理開關
        new_settings['use_proxy'] = False

    if 'show_error_detail' not in new_settings['ftp'].keys():  # v2.0 新增顯示 FTP 傳輸錯誤開關
        new_settings['ftp']['show_error_detail'] = False

    if 'max_retry_num' not in new_settings['ftp'].keys():  # v2.0 新增顯示 FTP 重傳嘗試數
        new_settings['ftp']['max_retry_num'] = 10

    if 'read_sn_list_when_checking_update' not in new_settings.keys():  # v2.0 新增開關：每次檢查更新時讀取s n_list
        new_settings['read_sn_list_when_checking_update'] = True

    if 'multi_upload' not in new_settings.keys():  # v2.0 新增最大並行上傳任務數
        new_settings['multi_upload'] = 3

    if 'read_config_when_checking_update' not in new_settings.keys():  # v2.0 新增開關：每次檢查更新時讀取 config.json
        new_settings['read_config_when_checking_update'] = True

    if 'add_bangumi_name_to_video_filename' not in new_settings.keys():  # v3.0 新增開關，檔名可以單純用劇集命名
        new_settings['add_bangumi_name_to_video_filename'] = True

    if 'segment_download_mode' not in new_settings.keys():  # v3.1 新增分段下載模式開關
        new_settings['segment_download_mode'] = True

    if 'multi_downloading_segment' not in new_settings.keys():  # v3.1 新增分段下載模式下每個影片併發下載分段數
        new_settings['multi_downloading_segment'] = 2

    new_settings['database_version'] = latest_database_version  # v3.2 新增資料庫版本號

    if 'save_logs' not in new_settings.keys():  # v4.0 新增日誌開關
        new_settings['save_logs'] = True

    if 'quantity_of_logs' not in new_settings.keys():  # v4.0 新增日誌數量設定（一天一日誌）
        new_settings['quantity_of_logs'] = 7

    if 'temp_dir' not in new_settings.keys():  # v4.0 新增快取目錄選項
        new_settings['temp_dir'] = ''

    if 'lock_resolution' not in new_settings.keys():
        new_settings['lock_resolution'] = False  # v4.1 新增解析度鎖定開關

    if 'ua' not in new_settings.keys():  # v4.2 新增 UA 設定
        new_settings['ua'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.96 Safari/537.36'

    if 'classify_bangumi' not in new_settings.keys():
        new_settings['classify_bangumi'] = True  # v5.0 新增是否建立番劇目錄開關

    if 'use_copyfile_method' not in new_settings.keys():
        # v6.0 新增影片轉移方法開關，設定 True 以配合 rclone 掛載
        new_settings['use_copyfile_method'] = False

    if 'zerofill' not in new_settings.keys():
        # v6.0 新增劇集名補零，該項數字為補足位數，預設為 1，小於等於 1 即不補 0
        new_settings['zerofill'] = 1

    if 'customized_bangumi_name_suffix' not in new_settings.keys():
        # v7.0 新增自定義番劇名字尾
        new_settings['customized_bangumi_name_suffix'] = ''

    if 'user_command' not in new_settings.keys():
        # v8.0 新增命令列模式完成後，執行自定義命令
        # 預設命令為一分鐘後關機
        new_settings['user_command'] = 'shutdown -s -t 60'

    if 'segment_download_max_retry' not in new_settings.keys():
        # v9.0 新增分段模式下，分段重試次數
        new_settings['segment_max_retry'] = 8

    if 'coolq_notify' not in new_settings.keys():
        # v9.0 新增推送通知到 CQ 的功能
        new_settings['coolq_notify'] = False
        new_settings['coolq_settings'] = {
            'host': '127.0.0.1',
            'port': '5700',
            'SSL': False,
            'api': 'send_group_msg',
            'query': {
                'group_id': '123456789',
            },
            'user_message': ''
        }

    if 'telebot_notify' not in new_settings.keys():
        # 新增推送通知到 TG 的功能
        new_settings['telebot_notify'] = False
        new_settings['telebot_token'] = '1'

    if 'discord_notify' not in new_settings.keys():
        # 新增推送通知到 Discord 的功能
        new_settings['discord_notify'] = False
        new_settings['discord_token'] = ''

    if 'plex_refresh' not in new_settings.keys():
        # 新增 plex 自動更新
        new_settings['plex_refresh'] = False
        new_settings['plex_url'] = ''
        new_settings['plex_token'] = ''
        new_settings['plex_section'] = ''

    if 'faststart_movflags' not in new_settings.keys():
        # v9.0 新增功能：將 metadata 移至影片檔案頭部
        # 此功能可以更快的線上播放影片
        new_settings['faststart_movflags'] = False

    if 'video_filename_extension' not in new_settings.keys():
        # v17 新增使用者自定義影片副檔名
        new_settings['video_filename_extension'] = 'mp4'

    if 'audio_language' not in new_settings.keys():
        # v19 新增音軌日語標籤  #37
        new_settings['audio_language'] = False

    if 'audio_language_jpn' in new_settings.keys():
        del new_settings['audio_language_jpn']

    if 'proxy' not in new_settings.keys() or 'proxies' in new_settings.keys():
        # v20 刪除鏈式代理功能
        if new_settings['proxies']['1']:
            # 轉移使用者原有設定
            new_settings['proxy'] = new_settings['proxies']['1']
        else:
            new_settings['proxy'] = 'http://user:passwd@example.com:1000'
        del new_settings['proxies']

    if 'use_dashboard' not in new_settings.keys():
        # v20 上線 Web 控制檯
        new_settings['use_dashboard'] = True

    if 'dashboard' not in new_settings.keys():
        new_settings['dashboard'] = {
            'host': '127.0.0.1',
            'port': 5000,
            'SSL': False,
            'BasicAuth': False,
            'username': 'admin',
            'password': 'admin'
        }

    if 'ads_time' not in new_settings.keys():
        new_settings['ads_time'] = 25

    if 'danmu' not in new_settings.keys():
        # 支援下載彈幕
        # https://github.com/miyouzi/aniGamerPlus/pull/66
        new_settings['danmu'] = False

    if 'use_mobile_api' not in new_settings.keys():
        # v21.0 新增使用 APP API #69
        new_settings['use_mobile_api'] = False

    if 'mobile_ads_time' not in new_settings.keys():
        new_settings['mobile_ads_time'] = 3  # 使用APP API 非會員廣告等待時間可低至 3s

    if 'message_suffix' not in new_settings['coolq_settings'].keys():
        # v21.1 新增
        new_settings['coolq_settings']['message_suffix'] = '追加的資訊'

    if 'user_message' in new_settings['coolq_settings'].keys():
        # QQ 機器人推送通知可以透過設定追加通知內容
        new_settings['coolq_settings']['message_suffix'] = new_settings['coolq_settings']['user_message']
        del new_settings['coolq_settings']['user_message']

    if 'msg_argument_name' not in new_settings['coolq_settings'].keys():
        # v21.1 讓使用者自行構造 QQ 機器人 URL
        new_settings['coolq_settings']['msg_argument_name'] = 'message'

    if 'SSL' in new_settings['coolq_settings'].keys():
        # 繼承使用者設定
        if new_settings['coolq_settings']['SSL']:
            req = 'https://'
        else:
            req = 'http://'
        req = req + new_settings['coolq_settings']['host'] + ':' + new_settings['coolq_settings']['port'] + '/' \
              + new_settings['coolq_settings']['api'] + '?' + urlencode(new_settings['coolq_settings']['query'])

        new_settings['coolq_settings']['query'] = [req]
        del new_settings['coolq_settings']['host']
        del new_settings['coolq_settings']['port']
        del new_settings['coolq_settings']['api']
        del new_settings['coolq_settings']['SSL']

    if 'only_use_vip' not in new_settings.keys():
        new_settings['only_use_vip'] = False

    new_settings['config_version'] = latest_config_version
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(new_settings, f, ensure_ascii=False, indent=4)
    msg = '設定檔案從 v' + str(old_settings['config_version']) + ' 升級到 v' + str(latest_config_version) + ' 你的有效設定檔不會遺失！'
    __color_print(0, msg, status=2, no_sn=True)


def __update_database(old_version):
    db_path = os.path.join(working_dir, 'aniGamer.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    def creat_table():
        cursor.execute('CREATE TABLE IF NOT EXISTS anime ('
                       'sn INTEGER PRIMARY KEY NOT NULL,'
                       'title VARCHAR(100) NOT NULL,'
                       'anime_name VARCHAR(100) NOT NULL, '
                       'episode VARCHAR(10) NOT NULL,'
                       'status TINYINT DEFAULT 0,'
                       'remote_status INTEGER DEFAULT 0,'
                       'resolution INTEGER DEFAULT 0,'
                       'file_size INTEGER DEFAULT 0,'
                       'local_file_path VARCHAR(500),'
                       "[CreatedTime] TimeStamp NOT NULL DEFAULT (datetime('now','localtime')))")

    try:
        cursor.execute('SELECT COUNT(*) FROM anime')
    except sqlite3.OperationalError as e:
        if 'no such table' in str(e):
            # 如果不存在表，則新建
            creat_table()

    try:
        cursor.execute('SELECT COUNT(local_file_path) FROM anime')
    except sqlite3.OperationalError as e:
        if 'no such column' in str(e):
            # 更早期的資料庫沒有 local_file_path，做相容
            cursor.execute('ALTER TABLE anime ADD local_file_path VARCHAR(500)')

    try:
        cursor.execute('SELECT COUNT(sn) FROM anime')
    except sqlite3.OperationalError as e:
        if 'no such column' in str(e):
            # 資料庫 v2.0  將 ns 列改名為 sn
            cursor.execute('ALTER TABLE anime RENAME TO animeOld')
            creat_table()
            cursor.execute("INSERT INTO "
                           "anime (sn,title,anime_name,episode,status,remote_status,resolution,file_size,local_file_path,[CreatedTime]) "
                           "SELECT "
                           "ns,title,anime_name,episode,status,remote_status,resolution,file_size,local_file_path,[CreatedTime] "
                           "FROM animeOld")
            cursor.execute('DROP TABLE animeOld')

    cursor.close()
    conn.commit()
    conn.close()
    msg = '資料庫從 v' + str(old_version) + ' 升級到 v' + str(latest_database_version) + ' 内部資料不會遺失'
    __color_print(0, msg, status=2, no_sn=True)


def __read_settings_file():
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            # 轉譯 win 路徑
            return json.loads(re.sub(r'\\', '\\\\\\\\', f.read()))
    except json.JSONDecodeError:
        # 如果帶有 BOM 頭，則去除
        try:
            # del_bom(config_path)
            check_encoding(config_path)
            # 重新讀取
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.loads(re.sub(r'\\', '\\\\\\\\', f.read()))
        except BaseException as e:
            __color_print(0, '讀取設定發生異常，將重設設定! ' + str(e), status=1, no_sn=True)
            __init_settings()
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except BaseException as e:
        __color_print(0, '讀取設定發生異常, 將重置設定！' + str(e), status=1, no_sn=True)
        __init_settings()
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)


def del_bom(path, display=True):
    # 處理 UTF-8-BOM
    have_bom = False
    with open(path, 'rb') as f:
        content = f.read()
        if content.startswith(codecs.BOM_UTF8):
            content = content[len(codecs.BOM_UTF8):]
            have_bom = True
    if have_bom:
        filename = os.path.split(path)[1]
        if display:
            __color_print(0, '發現 ' + filename + ' 帶有 BOM 頭，將移除後儲存', no_sn=True)
        try_counter = 0
        while True:
            try:
                with open(path, 'wb') as f:
                    f.write(content)
            except BaseException as e:
                if try_counter > 3:
                    if display:
                        __color_print(0, '無 BOM ' + filename + ' 儲存失敗！發生異常：' + str(e), status=1, no_sn=True)
                    raise e
                random_wait_time = random.uniform(2, 5)
                time.sleep(random_wait_time)
                try_counter = try_counter + 1
            else:
                if display:
                    __color_print(0, '無 BOM ' + filename + ' 儲存成功', status=2, no_sn=True)
                break


def read_settings(config=''):
    if config == '':
        if not os.path.exists(config_path):
            __init_settings()

        settings = __read_settings_file()
    else:
        # 用於檢查 web 控制檯回傳的設定是否正確
        settings = config

    if 'database_version' in settings.keys():
        if settings['database_version'] < latest_database_version:
            __update_database(settings['database_version'])
    else:
        # 如果該版本設定下沒有 database_version 項，則資料庫版本應該是 1.0
        settings['database_version'] = 1.0
        __update_database(1.0)

    if settings['config_version'] < latest_config_version:
        __update_settings(settings)  # 升級設定
        settings = __read_settings_file()  # 重新載入

    if settings['ftp']['port']:
        settings['ftp']['port'] = int(settings['ftp']['port'])

    # 防呆
    settings['check_frequency'] = int(settings['check_frequency'])
    settings['download_resolution'] = str(settings['download_resolution'])
    settings['multi-thread'] = int(settings['multi-thread'])
    settings['zerofill'] = int(settings['zerofill'])  # 保證為整數
    if not re.match(r'^(all|latest|largest-sn)$', settings['default_download_mode']):
        settings['default_download_mode'] = 'latest'  # 如果輸入非法模式，將重置為 latest 模式
    if settings['quantity_of_logs'] < 1:  # 日誌數量不可小於 1
        settings['quantity_of_logs'] = 7

    if not settings['ua']:
        # 如果 ua 選項為空
        settings['ua'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.96 Safari/537.36'

    # 如果使用者自定了番劇目錄且存在
    if settings['bangumi_dir'] and os.path.exists(settings['bangumi_dir']):
        # 番劇路徑規範化
        settings['bangumi_dir'] = os.path.abspath(settings['bangumi_dir'])
    else:
        # 如果使用者沒有有自定番劇目錄或目錄不存在，則儲存在本地 bangumi 目錄
        settings['bangumi_dir'] = os.path.join(working_dir, 'bangumi')

    # 如果使用者自定了快取目錄且存在
    if settings['temp_dir'] and os.path.exists(settings['temp_dir']):
        # 快取路徑規範化
        settings['temp_dir'] = os.path.abspath(settings['temp_dir'])
    else:
        # 如果使用者沒有有自定快取目錄或目錄不存在，則儲存在本地 temp 目錄
        settings['temp_dir'] = os.path.join(working_dir, 'temp')

    settings['working_dir'] = working_dir
    settings['aniGamerPlus_version'] = aniGamerPlus_version

    use_gost = False
    if not (re.match(r'^http://', settings['proxy'].lower())
            or re.match(r'^https://', settings['proxy'].lower())
            or re.match(r'^socks5://', settings['proxy'].lower())  # v12 開始原生支援 socks5 代理
            or re.match(r'^socks5h://', settings['proxy'].lower())):  # socks5h 遠端解析域名
        #  如果出現非自身支援的協議
        use_gost = True  # 則啟用 gost
    settings['use_gost'] = use_gost
    if not settings['proxy']:
        settings['use_proxy'] = False

    if settings['multi-thread'] > max_multi_thread:
        # 如果執行緒數超限
        settings['multi-thread'] = max_multi_thread

    if settings['multi_downloading_segment'] > max_multi_downloading_segment:
        # 如果併發分段數超限
        settings['multi_downloading_segment'] = max_multi_downloading_segment

    if settings['video_filename_extension'].lower() == 'flv':
        # flv 格式會輸出異常，強制重置
        settings['video_filename_extension'] = 'mp4'

    if settings['video_filename_extension'].lower() != 'mp4':
        # 如果封裝格式不是 mp4 則強制關閉 metadata 前置
        settings['faststart_movflags'] = False

    if settings['save_logs']:
        # 刪除過期日誌
        __remove_superfluous_logs(settings['quantity_of_logs'])

    if settings['use_dashboard']:
        # 如果啟用的控制檯，那麼檢查是否存在 Dashboard 目錄
        if not os.path.exists(os.path.join(working_dir, 'Dashboard')):
            settings['use_dashboard'] = False
            __color_print(0, 'Web控制面板', '未發現控制面板所必須的 Dashboard 資料夾，强制禁用控制面板！', no_sn=True, status=1)
            write_settings(settings)

    return settings


def check_encoding(file_path):
    # 識別檔案編碼，將非 UTF-8 編碼轉為 UTF-8
    with open(file_path, 'rb') as f:
        data = f.read()
        file_encoding = chardet.detect(data)['encoding']  # 識別檔案編碼
        if file_encoding == 'utf-8' or file_encoding == 'ascii':
            # 如果為 UTF-8 編碼，無需操作
            return
        else:
            # 如果為其他編碼，則轉為 UTF-8 編碼，包含處理 BOM 頭
            with open(file_path, 'wb') as f2:
                __color_print(0, '檔案讀取', file_path + ' 編碼為 ' + file_encoding + ' 將轉碼為 UTF-8', no_sn=True, status=1)
                data = data.decode(file_encoding)  # 解碼
                data = data.encode('utf-8')  # 編碼
                f2.write(data)  # 寫入檔案
                __color_print(0, '檔案讀取', file_path + ' 轉碼成功', no_sn=True, status=2)


def read_sn_list():
    settings = read_settings()

    # 防呆 https://github.com/miyouzi/aniGamerPlus/issues/5
    error_sn_list_path = sn_list_path.replace('sn_list.txt', 'sn_list.txt.txt')
    if os.path.exists(error_sn_list_path):
        os.rename(error_sn_list_path, sn_list_path)

    if not os.path.exists(sn_list_path):
        return {}

    if not os.path.getsize(sn_list_path):
        # 如果檔案是空的，https://github.com/miyouzi/aniGamerPlus/issues/38
        return {}

    # del_bom(sn_list_path)  # 去除 BOM
    check_encoding(sn_list_path)
    with open(sn_list_path, 'r', encoding='utf-8') as f:
        sn_dict = {}
        bangumi_tag = ''
        for i in f.readlines():
            if re.match(r'^@.+', i):  # 讀取番劇分類
                bangumi_tag = i[1:-1]
                continue
            elif re.match(r'^@ *', i):
                bangumi_tag = ''
                continue
            i = re.sub(r'#.+\n', '', i).strip()  # 刪除註釋
            i = re.sub(r' +', ' ', i)  # 去除多餘空格
            a = i.split(' ')
            if not a[0]:  # 跳過純註釋行
                continue
            if re.match(r'^\d+$', a[0]):
                rename = ''
                if len(a) > 1:  # 如果有特別指定下載模式
                    if re.match(r'^(all|latest|largest-sn)$', a[1]):  # 僅認可合法的模式
                        sn_dict[int(a[0])] = {'mode': a[1]}
                    else:
                        sn_dict[int(a[0])] = {'mode': settings['default_download_mode']}  # 非法模式一律替換成預設模式
                    # 是否有設定番劇重新命名
                    if re.match(r'.*<.*>.*', i):
                        rename = re.findall(r'<.*>', i)[0][1:-1]
                else:  # 沒有指定下載模式則使用預設設定
                    sn_dict[int(a[0])] = {'mode': settings['default_download_mode']}
                bangumi_tag = re.sub(r'( )+$', '', bangumi_tag)
                sn_dict[int(a[0])]['tag'] = bangumi_tag
                sn_dict[int(a[0])]['rename'] = rename
        return sn_dict


def test_cookie():
    # 測試 cookie.txt 是否存在，是否能正常讀取，並記錄日誌
    read_cookie(log=True)


def read_cookie(log=False):
    # 如果 cookie 已讀入記憶體，則直接返回
    global cookie
    if cookie is not None:
        return cookie
    # 相容舊版 cookie 命名
    old_cookie_path = cookie_path.replace('cookie.txt', 'cookies.txt')
    if os.path.exists(old_cookie_path):
        os.rename(old_cookie_path, cookie_path)
    # 防呆 https://github.com/miyouzi/aniGamerPlus/issues/5
    error_cookie_path = cookie_path.replace('cookie.txt', 'cookie.txt.txt')
    if os.path.exists(error_cookie_path):
        os.rename(error_cookie_path, cookie_path)
    # 使用者可以將cookie儲存在程式所在目錄下，儲存為 cookies.txt ，UTF-8 編碼
    if os.path.exists(cookie_path):
        # del_bom(cookie_path)  # 移除 bom
        check_encoding(cookie_path)  # 移除 bom
        if log:
            __color_print(0, '讀取 cookie', detail='發現 cookie 檔案', no_sn=True, display=False)
        with open(cookie_path, 'r', encoding='utf-8') as f:
            for line in f.readlines():
                if not line.isspace():  # 跳過空白行
                    cookies = line.replace('\n', '')  # 刪除換行符
                    cookies = dict([list(map(lambda x: quote(x, safe='') if re.match(r'[\u4e00-\u9fa5]', x) else x,  l.split('=', 1))) for l in cookies.split('; ')])
                    cookies.pop('ckBH_lastBoard', 404)
                    cookie = cookies
                    if log:
                        __color_print(0, '讀取 cookie', detail='已讀取 cookie', no_sn=True, display=False)
                    return cookie  # cookie 僅一行，讀到後馬上 return
    else:
        __color_print(0, '讀取 cookie', detail='未發現 cookie 檔案', no_sn=True, display=False)
        cookie = {}
        return cookie
    # 如果什么也没读到(空文件)
    __color_print(0, '讀取 cookie', detail='cookie 檔案為空', no_sn=True, status=1)
    invalid_cookie()
    cookie = {}
    return cookie


def invalid_cookie():
    # 當 cookie 失效時，將 cookie 改名，避免重複嘗試失效的 cookie
    if os.path.exists(cookie_path):
        invalid_cookie_path = cookie_path.replace('cookie.txt', 'invalid_cookie.txt')
        try:
            global cookie
            cookie = None  # 重置已读取的cookie
            if os.path.exists(invalid_cookie_path):
                os.remove(invalid_cookie_path)
            os.rename(cookie_path, invalid_cookie_path)
        except BaseException as e:
            __color_print(0, 'cookie 狀態', '嘗試標記失效 cookie 時遇到未知錯誤: ' + str(e), no_sn=True, status=1)
        else:
            __color_print(0, 'cookie 狀態', '已成功標記失效 cookie', no_sn=True, display=False)


def time_stamp_to_time(timestamp):
    # 把時間戳轉化為時間: 1479264792 to 2016-11-16 10:53:12
    # 程式碼來自: https://www.cnblogs.com/shaosks/p/5614630.html
    time_struct = time.localtime(timestamp)
    return time.strftime('%Y-%m-%d %H:%M:%S', time_struct)


def get_cookie_time():
    # 獲取 cookie 修改時間
    cookie_time = os.path.getmtime(cookie_path)
    return time_stamp_to_time(cookie_time)


def renew_cookies(new_cookie, log=True):
    global cookie
    cookie = None  # 重置 cookie
    new_cookie_str = ''
    for key, value in new_cookie.items():
        new_cookie_str = new_cookie_str + key + '=' + value + '; '
    new_cookie_str = new_cookie_str[0:-2]
    # print(new_cookie_str)
    try_counter = 0
    while True:
        try:
            with open(cookie_path, 'w', encoding='utf-8') as f:
                f.write(new_cookie_str)
        except BaseException as e:
            if try_counter > 3:
                __color_print(0, '新 cookie 儲存失敗！發生異常：' + str(e), status=1, no_sn=True)
                break
            random_wait_time = random.uniform(2, 5)
            time.sleep(random_wait_time)
            try_counter = try_counter + 1
        else:
            if log:
                __color_print(0, '新 cookie 儲存成功', no_sn=True, display=False)
            break


def read_latest_version_on_github():
    req = 'https://api.github.com/repos/miyouzi/aniGamerPlus/releases/latest'
    session = requests.session()
    remote_version = {}
    try:
        latest_releases_info = session.get(req, timeout=3).json()
        remote_version['tag_name'] = latest_releases_info['tag_name']
        remote_version['body'] = latest_releases_info['body']  # 更新內容
        __color_print(0, '檢查更新', '檢查更新成功', no_sn=True, display=False)
    except:
        remote_version['tag_name'] = aniGamerPlus_version  # 拉取 github 版本號失敗
        remote_version['body'] = ''
        __color_print(0, '檢查更新', '檢查更新失敗', no_sn=True, display=False)
    return remote_version


def __remove_superfluous_logs(max_num):
    if os.path.exists(logs_dir):
        logs_list = [x for x in os.listdir(logs_dir) if 'web' not in x]
        if len(logs_list) > max_num:
            logs_list.sort()
            logs_need_remove = logs_list[0:len(logs_list) - max_num]
            for log in logs_need_remove:
                log_path = os.path.join(logs_dir, log)
                os.remove(log_path)
                __color_print(0, '刪除過期日誌：' + log, no_sn=True, display=False)


def write_settings(web_config):
    web_config = read_settings(web_config)  # 正規化設定

    # 還原設定
    a = os.path.join(working_dir, 'bangumi')  # 預設番劇目錄
    b = os.path.join(working_dir, 'temp')  # 預設快取目錄
    if os.path.normcase(web_config['bangumi_dir']) == os.path.normcase(a):
        web_config['bangumi_dir'] = ''
    if os.path.normcase(web_config['temp_dir']) == os.path.normcase(b):
        web_config['temp_dir'] = ''
    del web_config['working_dir']
    del web_config['aniGamerPlus_version']
    del web_config['use_gost']

    # 設定寫入磁碟
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(web_config, f, ensure_ascii=False, indent=4)


def write_sn_list(sn_list_content):
    with open(sn_list_path, 'w', encoding='utf-8') as f:
        f.write(sn_list_content)


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
    except:
        local_ip.close()
    return local_ip


if __name__ == '__main__':
    pass
