#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2019/1/5 20:23
# @Author  : Miyouzi
# @File    : Config.py
# @Software: PyCharm

import os, json, re, sys, requests, time, random
import sqlite3

working_dir = os.path.dirname(os.path.realpath(__file__))
# working_dir = os.path.dirname(sys.executable)  # 使用 pyinstaller 编译时，打开此项
config_path = os.path.join(working_dir, 'config.json')
sn_list_path = os.path.join(working_dir, 'sn_list.txt')
cookie_path = os.path.join(working_dir, 'cookie.txt')
logs_dir = os.path.join(working_dir, 'logs')
aniGamerPlus_version = 'v9.4'
latest_config_version = 4.2
latest_database_version = 2.0


def __color_print(sn, err_msg, detail='', status=0, no_sn=False, display=True):
    # 避免与 ColorPrint.py 相互调用产生问题
    try:
        err_print(sn, err_msg, detail=detail, status=status, no_sn=no_sn, display=display)
    except UnboundLocalError:
        from ColorPrint import err_print
        err_print(sn, err_msg, detail=detail, status=status, no_sn=no_sn, display=display)


def get_working_dir():
    return working_dir


def get_config_path():
    return config_path


def __init_settings():
    if os.path.exists(config_path):
        os.remove(config_path)
    settings = {'bangumi_dir': '',
                'temp_dir': '',
                'check_frequency': 5,
                'download_resolution': '1080',
                'lock_resolution': False,  # 锁定分辨率, 如果分辨率不存在, 则宣布下载失败
                'default_download_mode': 'latest',  # 仅下载最新一集，另一个模式是 'all' 下载所有及日后更新
                'multi-thread': 3,  # 最大并发下载数
                'multi_upload': 3,
                'segment_download_mode': True,  # 由 aniGamerPlus 下载分段, False 为 ffmpeg 下载
                'multi_downloading_segment': 2,  # 在上面配置为 True 时有效, 每个视频并发下载分段数
                'add_bangumi_name_to_video_filename': True,
                'add_resolution_to_video_filename': True,  # 是否在文件名中添加清晰度说明
                'customized_video_filename_prefix': '【動畫瘋】',  # 用户自定前缀
                'customized_video_filename_suffix': '',  # 用户自定后缀
                # cookie的自动刷新对 UA 有检查
                'ua': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.96 Safari/537.36",
                'use_proxy': False,
                'proxies': {  # 代理功能
                    1: 'socks5://127.0.0.1:1080',
                    2: 'http://user:passwd@example.com:1000'
                },
                'upload_to_server': False,
                'ftp': {  # 将文件上传至远程服务器
                    'server': '',
                    'port': '',
                    'user': '',
                    'pwd': '',
                    'tls': True,
                    'cwd': '',  # 文件存放目录, 登陆后首先进入的目录
                    'show_error_detail': False,
                    'max_retry_num': 15
                },
                'check_latest_version': True,  # 是否检查新版本
                'read_sn_list_when_checking_update': True,
                'read_config_when_checking_update': True,
                'save_logs': True,
                'quantity_of_logs': 7,
                'config_version': latest_config_version,
                'database_version': latest_database_version
                }
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=4)


def __update_settings(old_settings):  # 升级配置文件
    new_settings = old_settings.copy()
    if 'check_latest_version' not in new_settings.keys():  # v2.0 新增检查更新开关
        new_settings['check_latest_version'] = True

    if 'tls' not in new_settings['ftp'].keys():  # v2.0 新增 FTP over TLS 开关
        new_settings['ftp']['tls'] = True

    if 'upload_to_server' not in new_settings.keys():  # v2.0 新增上传开关
        new_settings['upload_to_server'] = False

    if 'use_proxy' not in new_settings.keys():  # v2.0 新增代理开关
        new_settings['use_proxy'] = False

    if 'show_error_detail' not in new_settings['ftp'].keys():  # v2.0 新增显示FTP传输错误开关
        new_settings['ftp']['show_error_detail'] = False

    if 'max_retry_num' not in new_settings['ftp'].keys():  # v2.0 新增显示FTP重传尝试数
        new_settings['ftp']['max_retry_num'] = 10

    if 'read_sn_list_when_checking_update' not in new_settings.keys():  # v2.0 新增开关: 每次检查更新时读取sn_list
        new_settings['read_sn_list_when_checking_update'] = True

    if 'multi_upload' not in new_settings.keys():  # v2.0 新增最大并行上传任务数
        new_settings['multi_upload'] = 3

    if 'read_config_when_checking_update' not in new_settings.keys():  # v2.0 新增开关: 每次检查更新时读取config.json
        new_settings['read_config_when_checking_update'] = True

    if 'add_bangumi_name_to_video_filename' not in new_settings.keys():  # v3.0 新增开关, 文件名可以单纯用剧集命名
        new_settings['add_bangumi_name_to_video_filename'] = True

    if 'proxies' not in new_settings.keys():  # v3.0 新增代理功能
        new_settings['proxies'] = {1: '', 2: ''}

    if 'proxy' in new_settings.keys():  # v3.0 去掉旧的代理配置
        new_settings.pop('proxy')

    if 'segment_download_mode' not in new_settings.keys():  # v3.1 新增分段下载模式开关
        new_settings['segment_download_mode'] = True

    if 'multi_downloading_segment' not in new_settings.keys():  # v3.1 新增分段下载模式下每个视频并发下载分段数
        new_settings['multi_downloading_segment'] = 2

    new_settings['database_version'] = latest_database_version  # v3.2 新增数据库版本号

    if 'save_logs' not in new_settings.keys():  # v4.0 新增日志开关
        new_settings['save_logs'] = True

    if 'quantity_of_logs' not in new_settings.keys():  # v4.0 新增日志数量配置(一天一日志)
        new_settings['quantity_of_logs'] = 7

    if 'temp_dir' not in new_settings.keys():  # v4.0 新增缓存目录选项
        new_settings['temp_dir'] = ''

    if 'lock_resolution' not in new_settings.keys():
        new_settings['lock_resolution'] = False  # v4.1 新增分辨率锁定开关

    if 'ua' not in new_settings.keys():  # v4.2 新增 UA 配置
        new_settings['ua'] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.96 Safari/537.36"

    new_settings['config_version'] = latest_config_version
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(new_settings, f, ensure_ascii=False, indent=4)
    msg = '配置文件從 v'+str(old_settings['config_version'])+' 升級到 v'+str(latest_config_version)+' 你的有效配置不會丟失!'
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
            # 如果不存在表, 则新建
            creat_table()

    try:
        cursor.execute('SELECT COUNT(local_file_path) FROM anime')
    except sqlite3.OperationalError as e:
        if 'no such column' in str(e):
            # 更早期的数据库没有 local_file_path , 做兼容
            cursor.execute('ALTER TABLE anime ADD local_file_path VARCHAR(500)')

    try:
        cursor.execute('SELECT COUNT(sn) FROM anime')
    except sqlite3.OperationalError as e:
        if 'no such column' in str(e):
            # 数据库 v2.0  将 ns 列改名为 sn
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
    msg = '資料庫從 v'+str(old_version)+' 升級到 v'+str(latest_database_version)+' 内部資料不會丟失'
    __color_print(0, msg, status=2, no_sn=True)


def __read_settings_file():
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            # 转义win路径
            return json.loads(re.sub(r'\\', '\\\\\\\\', f.read()))
    except BaseException as e:
        __color_print(0, '讀取配置發生異常, 將重置配置! '+str(e), status=1, no_sn=True)
        __init_settings()
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)


def read_settings():
    if not os.path.exists(config_path):
        __init_settings()

    settings = __read_settings_file()

    if 'database_version' in settings.keys():
        if settings['database_version'] < latest_database_version:
            __update_database(settings['database_version'])
    else:
        # 如果该版本配置下没有 database_version 项, 则数据库版本应该是1.0
        settings['database_version'] = 1.0
        __update_database(1.0)

    if settings['config_version'] < latest_config_version:
        __update_settings(settings)  # 升级配置
        settings = __read_settings_file()  # 重新载入

    if settings['ftp']['port']:
        settings['ftp']['port'] = int(settings['ftp']['port'])

    # 防呆
    settings['check_frequency'] = int(settings['check_frequency'])
    settings['download_resolution'] = str(settings['download_resolution'])
    settings['multi-thread'] = int(settings['multi-thread'])
    if not re.match(r'^(all|latest|largest-sn)$', settings['default_download_mode']):
        settings['default_download_mode'] = 'latest'  # 如果输入非法模式, 将重置为 latest 模式
    if settings['quantity_of_logs'] < 1:  # 日志数量不可小于 1
        settings['quantity_of_logs'] = 7
    if not settings['ua']:
        # 如果 ua 项目为空
        settings['ua'] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.96 Safari/537.36"

    # 如果用户自定了番剧目录且存在
    if settings['bangumi_dir'] and os.path.exists(settings['bangumi_dir']):
        # 番剧路径规范化
        settings['bangumi_dir'] = os.path.abspath(settings['bangumi_dir'])
    else:
        # 如果用户没有有自定番剧目录或目录不存在，则保存在本地 bangumi 目录
        settings['bangumi_dir'] = os.path.join(working_dir, 'bangumi')

    # 如果用户自定了缓存目录且存在
    if settings['temp_dir'] and os.path.exists(settings['temp_dir']):
        # 缓存路径规范化
        settings['temp_dir'] = os.path.abspath(settings['temp_dir'])
    else:
        # 如果用户没有有自定缓存目录或目录不存在，则保存在本地 temp 目录
        settings['temp_dir'] = os.path.join(working_dir, 'temp')

    settings['working_dir'] = working_dir
    settings['aniGamerPlus_version'] = aniGamerPlus_version
    # 修正 proxies 字典, 使 key 为 int, 方便用于链式代理
    new_proxies = {}
    use_gost = False
    for key, value in settings['proxies'].items():
        if value:
            if not (re.match(r'^http://', value.lower()) or re.match(r'^https://', value.lower())):
                #  如果出现非 http 也非 https 的协议
                use_gost = True
            new_proxies[int(key)]=value
    if len(new_proxies.keys()) > 1:  # 如果代理配置大于 1 , 即使用链式代理, 则同样需要 gost
        use_gost = True
    settings['proxies'] = new_proxies
    settings['use_gost'] = use_gost
    if not new_proxies:
        settings['use_proxy'] = False

    if settings['save_logs']:
        # 刪除过期日志
        __remove_superfluous_logs(settings['quantity_of_logs'])

    return settings


def read_sn_list():
    settings = read_settings()
    if not os.path.exists(sn_list_path):
        return {}
    with open(sn_list_path, 'r', encoding='utf-8') as f:
        sn_dict = {}
        bangumi_tag = ''
        for i in f.readlines():
            if re.match(r'^@.+', i):  # 读取番剧分类
                bangumi_tag = i[1:-1]
                continue
            elif re.match(r'^@ *', i):
                bangumi_tag = ''
                continue
            i = re.sub(r'#.+\n', '', i).strip()  # 刪除注释
            i = re.sub(r' +', ' ', i)  # 去除多余空格
            a = i.split(" ")
            if not a[0]:  # 跳过纯注释行
                continue
            if re.match(r'^\d+$', a[0]):
                rename = ''
                if len(a) > 1:  # 如果有特別指定下载模式
                    if re.match(r'^(all|latest|largest-sn)$', a[1]):  # 仅认可合法的模式
                        sn_dict[int(a[0])] = {'mode': a[1]}
                    else:
                        sn_dict[int(a[0])] = {'mode': settings['default_download_mode']}  # 非法模式一律替换成默认模式
                    # 是否有设定番剧重命名
                    if re.match(r'.*<.*>.*', i):
                        rename = re.findall(r'<.*>', i)[0][1:-1]
                else:  # 没有指定下载模式则使用默认设定
                    sn_dict[int(a[0])] = {'mode': settings['default_download_mode']}
                sn_dict[int(a[0])]['tag'] = bangumi_tag
                sn_dict[int(a[0])]['rename'] = rename
        return sn_dict


def read_cookie():
    old_cookie_path = cookie_path.replace('cookie.txt', 'cookies.txt')
    if os.path.exists(old_cookie_path):
        os.rename(old_cookie_path, cookie_path)
    # 用户可以将cookie保存在程序所在目录下，保存为 cookies.txt ，UTF-8 编码
    if os.path.exists(cookie_path):
        with open(cookie_path, 'r', encoding='utf-8') as f:
            cookies = f.readline()
            cookies = dict([l.split("=", 1) for l in cookies.split("; ")])
            cookies.pop('ckBH_lastBoard', 404)
            return cookies
    else:
        return {}


def time_stamp_to_time(timestamp):
    # 把时间戳转化为时间: 1479264792 to 2016-11-16 10:53:12
    # 代码来自: https://www.cnblogs.com/shaosks/p/5614630.html
    timeStruct = time.localtime(timestamp)
    return time.strftime('%Y-%m-%d %H:%M:%S',timeStruct)


def get_cookie_time():
    # 获取 cookie 修改时间
    cookie_time = os.path.getmtime(cookie_path)
    return time_stamp_to_time(cookie_time)


def renew_cookies(new_cookie):
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
                __color_print(0, '新cookie保存失敗! 发生异常: '+str(e), status=1, no_sn=True)
                break
            random_wait_time = random.uniform(2, 5)
            time.sleep(random_wait_time)
            try_counter = try_counter + 1
        else:
            __color_print(0, '新cookie保存成功', no_sn=True, display=False)
            break


def read_latest_version_on_github():
    req = 'https://api.github.com/repos/miyouzi/aniGamerPlus/releases/latest'
    session = requests.session()
    remote_version = {}
    try:
        latest_releases_info = session.get(req, timeout=3).json()
        remote_version['tag_name'] = latest_releases_info['tag_name']
        remote_version['body'] = latest_releases_info['body']  # 更新内容
        __color_print(0, '檢查更新', '檢查更新成功', no_sn=True, display=False)
    except:
        remote_version['tag_name'] = aniGamerPlus_version  # 拉取github版本号失败
        remote_version['body'] = ''
        __color_print(0, '檢查更新', '檢查更新失敗', no_sn=True, display=False)
    return remote_version


def __remove_superfluous_logs(max_num):
    if os.path.exists(logs_dir):
        logs_list = os.listdir(logs_dir)
        if len(logs_list) > max_num:
            logs_list.sort()
            logs_need_remove = logs_list[0:len(logs_list)-max_num]
            for log in logs_need_remove:
                log_path = os.path.join(logs_dir, log)
                os.remove(log_path)
                __color_print(0, '刪除過期日志: ' + log, no_sn=True, display=False)


if __name__ == '__main__':
    pass
