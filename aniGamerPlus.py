#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2019/1/4 1:00
# @Author  : Miyouzi
# @File    : aniGamerPlus.py
# @Software: PyCharm

# 非阻塞 (Web)
from gevent import monkey
monkey.patch_all()


import os, sys, time, re, random, traceback, argparse
import signal
import sqlite3
import threading
import subprocess
import platform
import socket
import requests

import Config
from Anime import Anime, TryTooManyTimeError
from ColorPrint import err_print
from Danmu import Danmu


def port_is_available(port):
    # 检测端口是否可用(未占用), 可用返回 True
    # 参考: https://blog.csdn.net/roger_royer/article/details/79519826
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    if result == 0:
        return False
    else:
        return True


def gost_port():
    random_port = random.randint(40000, 60000)
    while not port_is_available(random_port):
        # 如果该端口不可用
        random_port = random.randint(40000, 60000)
    return random_port


def build_anime(sn):
    anime = {'anime': None, 'failed': True}
    try:
        if settings['use_gost']:
            # 如果使用 gost, 则随机一个 gost 监听端口
            anime['anime'] = Anime(sn, gost_port=gost_port)
        else:
            anime['anime'] = Anime(sn)
        anime['failed'] = False

        if danmu:
            anime['anime'].enable_danmu()

    except TryTooManyTimeError:
        err_print(sn, '抓取失敗', '影片信息抓取失敗!', status=1)
    except BaseException as e:
        err_print(sn, '抓取失敗', '抓取影片信息時發生未知錯誤: '+str(e), status=1)
        err_print(sn, '抓取異常', '異常詳情:\n'+traceback.format_exc(), status=1, display=False)

    # sn 解析冷却
    if settings['parse_sn_cd'] > 0:
        err_print("更新資訊", "SN 解析冷卻 " + str(settings['parse_sn_cd']) + " 秒", no_sn=True)
        time.sleep(settings['parse_sn_cd'])

    return anime


def read_db_all():
    db_locker.acquire()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("select * FROM anime")

    try:
        values = cursor.fetchall()
    except IndexError as e:
        cursor.close()
        conn.close()
        db_locker.release()
        raise e

    anime_db = [0] * len(values)
    for i in range(len(values)):
        anime_db[i] = {'sn': values[i][0],
                    'title': values[i][1],
                    'anime_name': values[i][2],
                    'episode': values[i][3],
                    'status': values[i][4],
                    'remote_status': values[i][5],
                    'resolution': values[i][6],
                    'file_size': values[i][7],
                    'local_file_path': values[i][8]}

    cursor.close()
    conn.close()
    db_locker.release()
    return anime_db


def read_db(sn):
    db_locker.acquire()
    # 传入sn(int)，读取该 sn 资料，返回 dict
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("select * FROM anime WHERE sn=:sn", {'sn': sn})

    try:
        values = cursor.fetchall()[0]
    except IndexError as e:
        cursor.close()
        conn.close()
        db_locker.release()
        raise e
    anime_db = {'sn': values[0],
                'title': values[1],
                'anime_name': values[2],
                'episode': values[3],
                'status': values[4],
                'remote_status': values[5],
                'resolution': values[6],
                'file_size': values[7],
                'local_file_path': values[8]}

    cursor.close()
    conn.close()
    db_locker.release()
    return anime_db


def insert_db(anime):
    db_locker.acquire()
    # 向数据库插入新资料
    anime_dict = {'sn': str(anime.get_sn()),
                  'title': anime.get_title(),
                  'anime_name': anime.get_bangumi_name(),
                  'episode': anime.get_episode()}

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("INSERT INTO anime (sn, title, anime_name, episode) VALUES (:sn, :title, :anime_name, :episode)",
                       anime_dict)
    except sqlite3.IntegrityError as e:
        err_print(anime_dict['sn'], 'ＤＢ错误', 'title=' + anime_dict['title'] + ' 数据已存在！' + str(e), status=1)

    cursor.close()
    conn.commit()
    conn.close()
    db_locker.release()


def update_db(anime):
    db_locker.acquire()
    # 更新数据库 status, resolution, file_size 资料
    anime_dict = {}
    if anime.video_size > 5:
        anime_dict['status'] = 1
    else:
        # 下载失败
        anime_dict['status'] = 0

    if anime.upload_succeed_flag:
        anime_dict['remote_status'] = 1
    else:
        anime_dict['remote_status'] = 0

    anime_dict['sn'] = anime.get_sn()
    anime_dict['title'] = anime.get_title()
    anime_dict['anime_name'] = anime.get_bangumi_name()
    anime_dict['episode'] = anime.get_episode()
    anime_dict['file_size'] = anime.video_size
    anime_dict['resolution'] = anime.video_resolution
    anime_dict['local_file_path'] = anime.local_video_path

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "UPDATE anime SET status=:status,"
            "remote_status=:remote_status,"
            "resolution=:resolution,"
            "file_size=:file_size,"
            "local_file_path=:local_file_path WHERE sn=:sn",
            anime_dict)
    except IndexError as e:
        cursor.close()
        conn.commit()
        conn.close()
        db_locker.release()
        raise e

    cursor.close()
    conn.commit()
    conn.close()
    db_locker.release()


def worker(sn, sn_info, realtime_show_file_size=False):
    bangumi_tag = sn_info['tag']
    rename = sn_info['rename']

    def upload_quit():
        queue.pop(sn)
        processing_queue.remove(sn)
        upload_limiter.release()  # 并发上传限制器
        sys.exit(0)

    anime_in_db = read_db(sn)
    # 如果用户设定要上传且已经下载好了但还没有上传成功, 那么仅上传
    if settings['upload_to_server'] and anime_in_db['status'] == 1 and anime_in_db['remote_status'] == 0:
        upload_limiter.acquire()  # 并发上传限制器
        anime = build_anime(sn)
        if anime['failed']:
            err_print(sn, '任务失敗', '從任務列隊中移除, 等待下次更新重試.', status=1)
            upload_quit()

        # 视频信息抓取成功
        anime = anime['anime']
        if not os.path.exists(anime_in_db['local_file_path']):
            # 如果数据库中记录的文件路径已失效
            update_db(anime)
            err_msg_detail = 'title=\"' + anime.get_title() + '\" 本地文件丢失, 從任務列隊中移除, 等待下次更新重試.'
            err_print(sn, '上传失敗', err_msg_detail, status=1)
            upload_quit()

        anime.local_video_path = anime_in_db['local_file_path']  # 告知文件位置
        anime.video_size = anime_in_db['file_size']  # 通過 update_db() 下载状态检查
        anime.video_resolution = anime_in_db['resolution']  # 避免更新时把分辨率变成0

        try:
            if not anime.upload(bangumi_tag):  # 如果上传失败
                err_msg_detail = 'title=\"' + anime.get_title() + '\" 從任務列隊中移除, 等待下次更新重試.'
                err_print(sn, '上传失敗', err_msg_detail, 1)
            else:
                update_db(anime)
                err_print(sn, '任務完成', status=2)
        except BaseException as e:
            err_msg_detail = 'title=\"' + anime.get_title() + '\" 發生未知錯誤, 等待下次更新重試: ' + str(e)
            err_print(sn, '上傳失敗', '異常詳情:\n'+traceback.format_exc(), status=1, display=False)
            err_print(sn, '上傳失敗', err_msg_detail, 1)

        upload_quit()

    # =====下载模块 =====
    thread_limiter.acquire()  # 并发下载限制器
    anime = build_anime(sn)

    if anime['failed']:
        queue.pop(sn)
        processing_queue.remove(sn)
        thread_limiter.release()
        err_print(sn, '任务失敗', '從任務列隊中移除, 等待下次更新重試.', status=1)
        sys.exit(1)

    anime = anime['anime']

    try:
        anime.download(settings['download_resolution'], bangumi_tag=bangumi_tag, rename=rename,
                       realtime_show_file_size=realtime_show_file_size, classify=settings['classify_bangumi'])
    except BaseException as e:
        # 兜一下各种奇奇怪怪的错误
        err_print(sn, '下載異常', '發生未知錯誤: '+str(e), status=1)
        err_print(sn, '下載異常', '異常詳情:\n'+traceback.format_exc(), status=1, display=False)
        anime.video_size = 0

    if anime.video_size < 5:
        # 下载失败
        queue.pop(sn)
        processing_queue.remove(sn)
        thread_limiter.release()
        err_msg_detail = 'title=\"' + anime.get_title() + '\" 從任務列隊中移除, 等待下次更新重試.'
        err_print(sn, '任务失敗', err_msg_detail, status=1)
        if int(sn) in Config.tasks_progress_rate.keys():
            del Config.tasks_progress_rate[int(sn)]  # 任务失败, 不在监控此任务进度
        sys.exit(1)

    update_db(anime)  # 下载完成后, 更新数据库
    download_cd = threading.Thread(target=download_cd_counter)
    download_cd.start()
    # =====下载模块结束 =====

    # =====上传模块=====
    if settings['upload_to_server']:
        upload_limiter.acquire()  # 并发上传限制器

        try:
            anime.upload(bangumi_tag)  # 上传至服务器
        except BaseException as e:
            # 兜一下各种奇奇怪怪的错误
            err_print(sn, '上傳異常', '發生未知錯誤, 從任務列隊中移除, 等待下次更新重試: ' + str(e), status=1)
            err_print(sn, '上傳異常', '異常詳情:\n'+traceback.format_exc(), status=1, display=False)
            upload_quit()

        update_db(anime)  # 上传完成后, 更新数据库
        upload_limiter.release()  # 并发上传限制器
    # =====上传模块结束=====

    download_cd.join()
    queue.pop(sn)  # 从任务列队中移除
    processing_queue.remove(sn)  # 从当前任务列队中移除 
    err_print(sn, '任務完成', status=2)
    

def download_cd_counter():
    seconds = settings['download_cd']
    while(seconds > 0):
        err_print('', '下載冷卻:', '下載冷卻時間剩餘 ' + str(seconds) + ' 秒', status=0, no_sn=True)
        wait_time = min(30, seconds)
        time.sleep(wait_time)
        seconds -= wait_time
    thread_limiter.release()  # 并发下载限制器


def check_tasks():
    for sn in sn_dict.keys():
        anime = build_anime(sn)
        if anime['failed']:
            err_print(sn, '更新狀態', '檢查更新失敗, 跳過等待下次檢查', status=1)
            # # sn 解析冷却
            # if settings['parse_sn_cd'] > 0:
            #     err_print("更新資訊", "SN 解析冷卻 " + str(settings['parse_sn_cd']) + " 秒", no_sn=True)
            #     time.sleep(settings['parse_sn_cd'])
            continue
        anime = anime['anime']
        err_print(sn, '更新資訊', '正在檢查《' + anime.get_bangumi_name() + '》')
        episode_list = list(anime.get_episode_list().values())

        if sn_dict[sn]['mode'] == 'all':
            # 如果用户选择全部下载 download_mode = 'all'
            for ep in episode_list:  # 遍历剧集列表
                try:
                    db = read_db(ep)
                    #           未下载的   或                设定要上传但是没上传的                         并且  还没在列队中
                    if (db['status'] == 0 or (db['remote_status'] == 0 and settings['upload_to_server'])) and ep not in queue.keys():
                        queue[ep] = sn_dict[sn]  # 添加至下载列队
                except IndexError:
                    # 如果数据库中尚不存在此条记录
                    if anime.get_sn() == ep:
                        new_anime = anime  # 如果是本身则不用重复创建实例
                    else:
                        new_anime = build_anime(ep)
                        if new_anime['failed']:
                            err_print(ep, '更新狀態', '更新數據失敗, 跳過等待下次檢查', status=1)
                            continue
                        new_anime = new_anime['anime']
                    insert_db(new_anime)
                    queue[ep] = sn_dict[sn]  # 添加至列队
        else:
            if sn_dict[sn]['mode'] == 'largest-sn':
                # 如果用户选择仅下载最新上传, download_mode = 'largest_sn', 则对 sn 进行排序
                episode_list.sort()
                latest_sn = episode_list[-1]
                # 否则用户选择仅下载最后剧集, download_mode = 'latest', 即下载网页上显示在最右的剧集
            elif sn_dict[sn]['mode'] == 'single':
                latest_sn = sn  # 适配命令行 sn-list 模式
            else:
                latest_sn = episode_list[-1]
            try:
                db = read_db(latest_sn)
                #           未下载的   或                设定要上传但是没上传的                         并且  还没在列队中
                if (db['status'] == 0 or (db['remote_status'] == 0 and settings['upload_to_server'])) and latest_sn not in queue.keys():
                    queue[latest_sn] = sn_dict[sn]  # 添加至下载列队
            except IndexError:
                # 如果数据库中尚不存在此条记录
                if anime.get_sn() == latest_sn:
                    new_anime = anime  # 如果是本身则不用重复创建实例
                else:
                    new_anime = build_anime(latest_sn)
                    if new_anime['failed']:
                        err_print(latest_sn, '更新狀態', '更新數據失敗, 跳過等待下次檢查', status=1)
                        continue
                    new_anime = new_anime['anime']
                insert_db(new_anime)
                queue[latest_sn] = sn_dict[sn]

        # # sn 解析冷却
        # if settings['parse_sn_cd'] > 0:
        #     err_print("更新資訊", "SN 解析冷卻 " + str(settings['parse_sn_cd']) + " 秒", no_sn=True)
        #     time.sleep(settings['parse_sn_cd'])


def __download_only(sn, dl_resolution='', dl_save_dir='', realtime_show_file_size=False, classify=True):
    # 仅下载,不操作数据库
    thread_limiter.acquire()
    err_counter = 0

    anime = build_anime(sn)
    if anime['failed']:
        sys.exit(1)
    anime = anime['anime']

    try:
        if dl_resolution:
            anime.download(dl_resolution, dl_save_dir, realtime_show_file_size=realtime_show_file_size, classify=classify)
        else:
            anime.download(settings['download_resolution'], dl_save_dir, realtime_show_file_size=realtime_show_file_size, classify=classify)
    except BaseException as e:
        err_print(sn, '下載異常', '發生未知異常: ' + str(e), status=1)
        err_print(sn, '下載異常', '異常詳情:\n'+traceback.format_exc(), status=1, display=False)
        anime.video_size = 0

    while anime.video_size < 5:
        if err_counter >= 3:
            err_print(sn, '終止任務', 'title=' + anime.get_title()+' 任務失敗達三次! 終止任務!', status=1)
            thread_limiter.release()
            if int(sn) in Config.tasks_progress_rate.keys():
                del Config.tasks_progress_rate[int(sn)]
            return
        else:
            err_print(sn, '任務失敗', 'title=' + anime.get_title() + ' 10s后自動重啓,最多重試三次', status=1)
            err_counter = err_counter + 1
            if int(sn) in Config.tasks_progress_rate.keys():
                Config.tasks_progress_rate[int(sn)]['status'] = '失敗! 重啓中'
            time.sleep(10)
            anime.renew()

            try:
                if dl_resolution:
                    anime.download(dl_resolution, dl_save_dir, realtime_show_file_size=realtime_show_file_size, classify=classify)
                else:
                    anime.download(settings['download_resolution'], dl_save_dir, realtime_show_file_size=realtime_show_file_size, classify=classify)
            except BaseException as e:
                err_print(sn, '下載異常', '發生未知異常: ' + str(e), status=1)
                err_print(sn, '下載異常', '異常詳情:\n'+traceback.format_exc(), status=1, display=False)
                anime.video_size = 0

    download_cd = threading.Thread(target=download_cd_counter)
    download_cd.start()


def __get_info_only(sn):
    thread_limiter.acquire()

    anime = build_anime(sn)
    if anime['failed']:
        sys.exit(1)
    anime = anime['anime']
    anime.set_resolution(resolution)
    anime.get_info()
    download_dir = settings['bangumi_dir']
    if classify:  # 控制是否建立番剧文件夹
        download_dir = os.path.join(download_dir, Config.legalize_filename(anime.get_bangumi_name()))

    if danmu:
        if os.path.exists(download_dir):
            full_filename = os.path.join(download_dir, anime.get_filename()).replace('.' + settings['video_filename_extension'], '.ass')
            d = Danmu(sn, full_filename, Config.read_cookie())
            d.download(settings['danmu_ban_words'])
        else:
            err_print(sn, '彈幕下載異常', '番劇資料夾不存在: ' + download_dir, status=1)

    thread_limiter.release()


def __get_danmu_only(sn, bangumi_name, video_path):
    thread_limiter.acquire()

    download_dir = settings['bangumi_dir']
    if classify:  # 控制是否建立番剧文件夹
        download_dir = os.path.join(download_dir, Config.legalize_filename(bangumi_name))

    if os.path.exists(download_dir):
        d = Danmu(sn, video_path.replace('.' + settings['video_filename_extension'], '.ass'), Config.read_cookie())
        d.download(settings['danmu_ban_words'])
    else:
        err_print(sn, '彈幕下載異常', '番劇資料夾不存在: ' + download_dir, status=1)

    thread_limiter.release()


def __cui(sn, cui_resolution, cui_download_mode, cui_thread_limit, ep_range,
          cui_save_dir='', classify=True, get_info=False, user_cmd=False, realtime_show=True, cui_danmu=False):
    global thread_limiter
    thread_limiter = threading.Semaphore(cui_thread_limit)

    global danmu
    danmu = cui_danmu

    if realtime_show:
        if cui_thread_limit == 1 or cui_download_mode in ('single', 'latest', 'largest-sn'):
            realtime_show_file_size = True
        else:
            realtime_show_file_size = False
    else:
        realtime_show_file_size = False

    if cui_download_mode == 'single':
        if get_info:
            print('當前模式: 查詢本集資訊\n')
        else:
            print('當前下載模式: 僅下載本集\n')

        if get_info:
            __get_info_only(sn)
        else:
            __download_only(sn, cui_resolution, cui_save_dir, realtime_show_file_size=realtime_show_file_size, classify=classify)

    elif cui_download_mode == 'latest' or cui_download_mode == 'largest-sn':
        if cui_download_mode == 'latest':
            if get_info:
                print('當前模式: 查詢本番劇最後一集資訊\n')
            else:
                print('當前下載模式: 下載本番劇最後一集\n')
        else:
            if get_info:
                print('當前模式: 查詢本番劇最近上傳一集資訊\n')
            else:
                print('當前下載模式: 下載本番劇最近上傳的一集\n')

        anime = build_anime(sn)
        if anime['failed']:
            sys.exit(1)
        anime = anime['anime']

        bangumi_list = list(anime.get_episode_list().values())

        if cui_download_mode == 'largest-sn':
            bangumi_list.sort()

        if get_info:
            __get_info_only(bangumi_list[-1])
        else:
            __download_only(bangumi_list[-1], cui_resolution, cui_save_dir, realtime_show_file_size=realtime_show_file_size, classify=classify)

    elif cui_download_mode == 'all':
        if get_info:
            print('當前模式: 查詢本番劇所有劇集資訊\n')
        else:
            print('當前下載模式: 下載本番劇所有劇集\n')

        anime = build_anime(sn)
        if anime['failed']:
            sys.exit(1)
        anime = anime['anime']

        bangumi_list = list(anime.get_episode_list().values())
        bangumi_list.sort()
        tasks_counter = 0  # 任务计数器
        for anime_sn in bangumi_list:
            if get_info:
                task = threading.Thread(target=__get_info_only, args=(anime_sn,))
            else:
                task = threading.Thread(target=__download_only, args=(anime_sn, cui_resolution, cui_save_dir, realtime_show_file_size, classify))
            task.daemon = True
            thread_tasks.append(task)
            task.start()
            tasks_counter = tasks_counter + 1
            print('添加任务列隊: sn=' + str(anime_sn))
        if get_info:
            print('所有查詢任務已添加至列隊, 共 '+str(tasks_counter)+' 個任務\n')
        else:
            print('所有下載任務已添加至列隊, 共 '+str(tasks_counter)+' 個任務, '+'執行緒數: ' + str(cui_thread_limit) + '\n')

    elif cui_download_mode == 'range':
        if get_info:
            print('當前模式: 查詢本番劇指定劇集資訊\n')
        else:
            print('當前下載模式: 下載本番劇指定劇集\n')

        anime = build_anime(sn)
        if anime['failed']:
            sys.exit(1)
        anime = anime['anime']

        episode_dict = anime.get_episode_list()
        bangumi_ep_list = list(episode_dict.keys())  # 本番剧集列表
        tasks_counter = 0  # 任务计数器
        for ep in ep_range:
            if ep in bangumi_ep_list:
                if get_info:
                    a = threading.Thread(target=__get_info_only, args=(episode_dict[ep],))
                else:
                    a = threading.Thread(target=__download_only, args=(episode_dict[ep], cui_resolution, cui_save_dir, realtime_show_file_size))
                a.daemon = True
                thread_tasks.append(a)
                a.start()
                tasks_counter = tasks_counter + 1
                if get_info:
                    print('添加查詢列隊: sn=' + str(episode_dict[ep]) + ' 《' + anime.get_bangumi_name() + '》 第 ' + ep + ' 集')
                else:
                    print('添加任务列隊: sn='+str(episode_dict[ep])+' 《'+anime.get_bangumi_name()+'》 第 '+ep+' 集')
            else:
                err_print(0, '《'+anime.get_bangumi_name()+'》 第 '+ep+' 集不存在!', status=1, no_sn=True)
        print('所有任務已添加至列隊, 共 '+str(tasks_counter)+' 個任務, '+'執行緒數: ' + str(cui_thread_limit) + '\n')

    elif cui_download_mode == 'sn-range':
        if get_info:
            print('當前模式: 查詢本番劇指定sn範圍資訊\n')
        else:
            print('當前下載模式: 下載本番劇指定sn範圍劇集\n')

        anime = build_anime(sn)
        if anime['failed']:
            sys.exit(1)
        anime = anime['anime']

        # 剧集列表 key value 互换, {'sn', '剧集名'}
        episode_dict = {value:key for key,value in anime.get_episode_list().items()}
        ep_sn_list = list(episode_dict.keys())  # 本番剧集sn列表
        tasks_counter = 0  # 任务计数器
        ep_range = list(map(lambda x: int(x), ep_range))
        for sn in ep_sn_list:
            if sn in ep_range:
                # 如果该 sn 在用户指定的 sn 范围里
                if get_info:
                    a = threading.Thread(target=__get_info_only, args=(sn,))
                else:
                    a = threading.Thread(target=__download_only, args=(sn, cui_resolution, cui_save_dir, realtime_show_file_size))
                a.daemon = True
                thread_tasks.append(a)
                a.start()
                tasks_counter = tasks_counter + 1
                if get_info:
                    print('添加查詢列隊: sn=' + str(sn) + ' 《' + anime.get_bangumi_name() + '》 第 ' + episode_dict[sn] + ' 集')
                else:
                    print('添加任务列隊: sn='+str(sn)+' 《'+anime.get_bangumi_name()+'》 第 ' + episode_dict[sn] + ' 集')
        print('所有任務已添加至列隊, 共 ' + str(tasks_counter) + ' 個任務, ' + '執行緒數: ' + str(cui_thread_limit) + '\n')

    elif cui_download_mode == 'multi':
        if get_info:
            print('當前模式: 查詢指定sn資訊\n')
        else:
            print('當前下載模式: 下載指定sn劇集\n')

        tasks_counter = 0
        for sn in ep_range:
            if get_info:
                a = threading.Thread(target=__get_info_only, args=(sn,))
            else:
                a = threading.Thread(target=__download_only,args=(sn, cui_resolution, cui_save_dir, realtime_show_file_size))
            a.daemon = True
            thread_tasks.append(a)
            a.start()
            tasks_counter = tasks_counter + 1

        print('所有任務已添加至列隊, 共 ' + str(tasks_counter) + ' 個任務, ' + '執行緒數: ' + str(cui_thread_limit) + '\n')

    elif cui_download_mode in ('list', 'sn-list'):
        if get_info:
            # 如果為list模式也仅查询名单中的sn信息, 可用于检查sn是否输入正确
            print('當前模式: 查詢sn_list.txt中指定sn的資訊\n')
            ep_range = Config.read_sn_list().keys()
            for sn in ep_range:
                anime = build_anime(sn)
                if anime['failed']:
                    sys.exit(1)
                anime = anime['anime']
                anime.get_info()
        else:
            if cui_download_mode == 'sn-list':
                print('當前下載模式: 下載sn_list.txt中指定的sn劇集\n')
                for i in sn_dict:
                    sn_dict[i]['mode'] = 'single'
            else:
                print('當前下載模式: 單次下載sn_list.txt中的番劇\n')

            check_tasks()  # 检查更新，生成任务列队
            for sn in queue.keys():  # 遍历任务列队
                processing_queue.append(sn)
                task = threading.Thread(target=worker, args=(sn, queue[sn], realtime_show_file_size))
                task.daemon = True
                thread_tasks.append(task)
                task.start()
                err_print(sn, '加入任务列隊')
            msg = '共 ' + str(len(queue)) + ' 個任務'
            err_print(0, '任務資訊', msg, no_sn=True)
            print()

    elif cui_download_mode == 'danmu':
        tasks_counter = 0
        for anime_db in ep_range:
            if anime_db["status"] == 1:
                if not anime_db["anime_name"] is None \
                and not anime_db["local_file_path"] is None :
                    a = threading.Thread(target=__get_danmu_only,args=(anime_db["sn"], anime_db["anime_name"], anime_db["local_file_path"]))
                    a.setDaemon(True)
                    thread_tasks.append(a)
                    a.start()
                    tasks_counter = tasks_counter + 1
                else:
                    err_print(anime_db["sn"], '彈幕更新失敗', "資料庫不存在番劇名稱或影片路徑", status=1)

        print('所有任務已添加至列隊, 共 ' + str(tasks_counter) + ' 個任務, ' + '執行緒數: ' + str(cui_thread_limit) + '\n')

    __kill_thread_when_ctrl_c()
    kill_gost()  # 结束 gost

    # 结束后执行用户自定义命令
    if user_cmd:
        print()
        os.popen(settings['user_command'])
        err_print(0, '任務完成', '已執行用戶命令', no_sn=True, status=2)

    sys.exit(0)


def __kill_thread_when_ctrl_c():
    # 等待所有任务完成
    for t in thread_tasks:  # 当用户 Ctrl+C 可以 kill 线程
        while True:
            if t.is_alive():
                time.sleep(1)
            else:
                break


def kill_gost():
    if gost_subprocess is not None:
        gost_subprocess.kill()  # 结束 gost


def user_exit(signum, frame):
    err_print(0, '你終止了程序!', '\n', status=1, no_sn=True, prefix='\n\n')
    kill_gost()  # 结束 gost
    sys.exit(255)


def check_new_version():
    # 检查GitHub上是否有新版
    remote_version = Config.read_latest_version_on_github()
    if float(settings['aniGamerPlus_version'][1:]) < float(remote_version['tag_name'][1:]):
        msg = '發現GitHub上有新版本: '+remote_version['tag_name']+'\n更新内容:\n'+remote_version['body']+'\n'
        err_print(0, msg, status=1, no_sn=True)


def __init_proxy():
    if settings['use_gost']:
        print('使用代理連接動畫瘋, 使用擴展的代理協議')
        # 需要使用 gost 的情况
        # 寻找 gost
        check_gost = subprocess.Popen('gost -h', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if check_gost.stderr.readlines():  # 查找 gost 是否已放入系统 path
            gost_path = 'gost'
        else:
            # print('没有在系统PATH中发现gost，尝试在所在目录寻找')
            if 'Windows' in platform.system():
                gost_path = os.path.join(working_dir, 'gost.exe')
            else:
                gost_path = os.path.join(working_dir, 'gost')
            if not os.path.exists(gost_path):
                err_print(0, '當前代理使用擴展協議, 需要使用gost, 但是gost未找到', status=1, no_sn=True)
                raise FileNotFoundError  # 如果本地目录下也没有找到 gost 则丢出异常
        # 构造 gost 命令
        gost_cmd = [gost_path, '-L=:'+str(gost_port), '-F=' + settings['proxy']]  # 本地监听端口 34173

        def run_gost():
            # gost 线程
            global gost_subprocess
            gost_subprocess = subprocess.Popen(gost_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            gost_subprocess.communicate()

        run_gost_threader = threading.Thread(target=run_gost)
        run_gost_threader.daemon = True
        run_gost_threader.start()  # 启动 gost
        time.sleep(3)  # 给时间让 gost 启动

    else:
        print('使用代理連接動畫瘋, 使用http/https/socks5協議')


def do_request(url, headers, cookies, params=None):
    return requests.get(url, headers=headers, cookies=cookies, params=params)


def parse_anime(soup, animes, headers, cookies):
    if soup.text.find("目前沒有訂閱內容") != -1:
        return False
    for animeInfo in soup.select_one(".theme-list-block").select("a"):
        response = do_request(f"https://ani.gamer.com.tw/{animeInfo['href']}", headers, cookies)
        sn = response.url.split("=")[-1]
        name = animeInfo.select_one(".theme-name").text
        animes.append({"sn": sn, "name": name})
    return True


def export_my_anime():
    from bs4 import BeautifulSoup

    url = "https://ani.gamer.com.tw/mygather.php"
    header = {
        'accept':
        'application/json',
        'origin':
        'https://ani.gamer.com.tw',
        'authority':
        'ani.gamer.com.tw',
        'user-agent':
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.83 Safari/537.36',
    }

    cookies = Config.read_cookie()
    if not cookies:
        err_print(0, f"請先設定cookie後再執行此指令", status=1, no_sn=True)
        return

    page = 1
    animes = []
    while True:
        params = {'page': page, 'sort': 0}
        bahamygatherPage = do_request(url, headers=header, cookies=cookies, params=params)
        if bahamygatherPage.status_code == requests.codes.ok:
            soup = BeautifulSoup(bahamygatherPage.text, 'html.parser')
            if not parse_anime(soup, animes, header, cookies):
                break
        else:
            err_print(0, f"匯入我的動畫失敗，狀態碼{bahamygatherPage.status_code}", status=1, no_sn=True)
        page += 1

    with open("my_anime.txt", "w", encoding="utf-8") as f:
        for anime in animes:
            f.write(f"{anime['sn']} all <{anime['name']}>\n")


def run_dashboard():
    # 检测端口是否占用
    if not port_is_available(settings['dashboard']['port']):
        err_print(0, 'Web控制面板啓動失敗', 'Port已被占用! 請到配置文件更換', status=1, no_sn=True)
        return

    from Dashboard.Server import run as dashboard
    server = threading.Thread(target=dashboard)
    server.daemon = True
    server.start()
    if settings['dashboard']['SSL']:
        dashboard_address = 'https://'
    else:
        dashboard_address = 'http://'
    if settings['dashboard']['host'] == '0.0.0.0':
        host = Config.get_local_ip()
        dashboard_address = '【開放外部訪問】訪問地址: ' + dashboard_address
    else:
        host = settings['dashboard']['host']
        dashboard_address = '訪問地址: ' + dashboard_address

    dashboard_address = dashboard_address + host + ':' + str(settings['dashboard']['port'])
    err_print(0, 'Web控制面板已啓動', dashboard_address, no_sn=True, status=2)


signal.signal(signal.SIGINT, user_exit)
signal.signal(signal.SIGTERM, user_exit)
settings = Config.read_settings()
working_dir = settings['working_dir']
db_path = os.path.join(working_dir, 'aniGamer.db')
queue = {}  # 储存 sn 相关信息, {'tag': TAG, 'rename': RENAME}, rename,
processing_queue = []
thread_limiter = threading.Semaphore(settings['multi-thread'])  # 下载并发限制器
upload_limiter = threading.Semaphore(settings['multi_upload'])  # 并发上传限制器
db_locker = threading.Semaphore(1)
thread_tasks = []
gost_subprocess = None  # 存放 gost 的 subprocess.Popen 对象, 用于结束时 kill gost
gost_port = gost_port()  # gost 端口
sn_dict = Config.read_sn_list()
danmu = settings['danmu']

if __name__ == '__main__':
    if settings['check_latest_version']:
        check_new_version()  # 检查新版
    version_msg = '當前aniGamerPlus版本: ' + settings['aniGamerPlus_version']
    print(version_msg)

    # 初始化 sqlite3 数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
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
    conn.commit()
    conn.close()

    if len(sys.argv) > 1:  # 支持命令行使用
        parser = argparse.ArgumentParser()
        parser.add_argument('--sn', '-s', type=int, help='視頻sn碼(數字)')
        parser.add_argument('--resolution', '-r', type=int, help='指定下載清晰度(數字)', choices=[360, 480, 540, 576, 720, 1080])
        parser.add_argument('--download_mode', '-m', type=str, help='下載模式', default='single',
                            choices=['single', 'latest', 'largest-sn', 'multi', 'all', 'range', 'list', 'sn-list', 'sn-range', 'db'])
        parser.add_argument('--thread_limit', '-t', type=int, help='最高并發下載數(數字)')
        parser.add_argument('--current_path', '-c', action='store_true', help='下載到當前工作目錄')
        parser.add_argument('--episodes', '-e', type=str, help='僅下載指定劇集')
        parser.add_argument('--no_classify', '-n', action='store_true', help='不建立番劇資料夾')
        parser.add_argument('--user_command', '-u', action='store_true', help='所有下載完成后執行用戶命令')
        parser.add_argument('--information_only', '-i', action='store_true', help='僅查詢資訊，可搭配 -d 更新彈幕')
        parser.add_argument('--danmu', '-d', action='store_true', help='以 .ass 下載彈幕')
        parser.add_argument('--my_anime', action='store_true', help='匯出「我的動畫」至my_anime.txt')
        arg = parser.parse_args()

        if arg.my_anime:
            export_my_anime()
            sys.exit(0)

        if (arg.download_mode not in ('list', 'multi', 'sn-list', 'db')) and arg.sn is None:
            err_print(0, '參數錯誤', '非 list/multi 模式需要提供 sn ', no_sn=True, status=1)
            sys.exit(1)

        save_dir = ''
        download_mode = arg.download_mode
        if arg.current_path:
            save_dir = os.getcwd()
            info = '使用命令行模式, 指定下載到當前目錄: '
            print(info + '\n    ' + save_dir)
            err_print(0, info + save_dir, no_sn=True, display=False)
        else:
            info = '使用命令行模式, 文件將保存在配置文件中指定的目錄下: '
            print(info + '\n    ' + settings['bangumi_dir'])
            err_print(0, info + settings['bangumi_dir'], no_sn=True, display=False)

        classify = True
        if arg.no_classify:
            classify = False
            print('將不會建立番劇資料夾')

        if not arg.episodes and arg.download_mode == 'range':
            err_print(0, 'ERROR: 當前為指定範圍模式, 但範圍未指定!', status=1, no_sn=True)
            sys.exit(1)

        download_episodes = []
        if arg.episodes or arg.download_mode == 'sn-list':
            if arg.download_mode == 'multi':
                # 如果此时为 multi 模式, 则 download_episodes 装的是 sn 码
                for i in arg.episodes.split(','):
                    if re.match(r'^\d+$', i):
                        download_episodes.append(int(i))
                if arg.sn:
                    download_episodes.append(arg.sn)

            elif arg.download_mode == 'sn-list':
                # 如果此时为 sn-list 模式, 则 download_episodes 装的是 sn_list.txt 里的 sn 码
                download_episodes = list(Config.read_sn_list().keys())

            else:
                for i in arg.episodes.split(','):
                    if re.match(r'^\d+-\d+$', i):
                        episodes_range_start = int(i.split('-')[0])
                        episodes_range_end = int(i.split('-')[1])
                        if episodes_range_start > episodes_range_end:  # 如果有zz从大到小写
                            episodes_range_start, episodes_range_end = episodes_range_end, episodes_range_start
                        download_episodes.extend(list(range(episodes_range_start, episodes_range_end + 1)))
                    if re.match(r'^\d+$', i):
                        download_episodes.append(int(i))
                if arg.download_mode != 'sn-range':
                    download_mode = 'range'  # 如果带 -e 参数没有指定 multi 模式, 则默认为 range 模式

            download_episodes = list(set(download_episodes))  # 去重复
            download_episodes.sort()  # 排序, 任务将会按集数顺序下载
            # 转为 str, 方便作为 Anime.get_episode_list() 的 key
            download_episodes = list(map(lambda x: str(x), download_episodes))

        if not arg.resolution:
            resolution = settings['download_resolution']
            print('未设定下载解析度, 将使用配置文件指定的清晰度: ' + resolution + 'P')
        else:
            if arg.download_mode in ('sn-list', 'list'):
                err_print(0,'無效參數:', 'list 及 sn-list 模式無法通過命令行指定清晰度', 1, no_sn=True, display_time=False)
                resolution = settings['download_resolution']
                print('将使用配置文件指定的清晰度: ' + resolution + 'P')
            else:
                resolution = str(arg.resolution)
                print('指定下载解析度: ' + resolution + 'P')

        if arg.download_mode == "db":
            download_mode = "danmu"
            download_episodes = read_db_all()

        if arg.information_only:
            # 为避免排版混乱, 仅显示信息时强制为单线程
            thread_limit = 1
            thread_limiter = threading.Semaphore(thread_limit)
        else:
            if arg.thread_limit:
                # 用戶設定并發數
                if arg.thread_limit > Config.get_max_multi_thread():
                    # 是否超过最大允许线程数
                    thread_limit = Config.get_max_multi_thread()
                else:
                    thread_limit = arg.thread_limit
            else:
                thread_limit = settings['multi-thread']

        if settings['use_proxy']:
            __init_proxy()

        if arg.user_command:
            user_command = True
        else:
            user_command = False

        if arg.danmu:
            danmu = True

        Config.test_cookie()  # 测试cookie
        __cui(arg.sn, resolution, download_mode, thread_limit, download_episodes, save_dir, classify,
              get_info=arg.information_only, user_cmd=user_command, cui_danmu=danmu)

    err_print(0, '自動模式啓動aniGamerPlus '+version_msg, no_sn=True, display=False)
    err_print(0, '工作目錄: ' + working_dir, no_sn=True, display=False)

    if settings['use_proxy']:
        __init_proxy()

    if settings['use_dashboard']:
        run_dashboard()

    while True:
        print()
        err_print(0, '開始更新', no_sn=True)
        Config.test_cookie()  # 测试cookie
        if settings['read_sn_list_when_checking_update']:
            sn_dict = Config.read_sn_list()
        if settings['read_config_when_checking_update']:
            settings = Config.read_settings()
        danmu = settings['danmu'] # 避免手動加入工作時，global 覆寫掉 config 的 danmu 設定
        check_tasks()  # 检查更新，生成任务列队
        new_tasks_counter = 0  # 新增任务计数器
        if queue:
            for task_sn in queue.keys():
                if task_sn not in processing_queue:  # 如果该任务没有在进行中，则启动
                    task = threading.Thread(target=worker, args=(task_sn, queue[task_sn]))
                    task.daemon = True
                    task.start()
                    processing_queue.append(task_sn)
                    new_tasks_counter = new_tasks_counter + 1
                    err_print(task_sn, '加入任务列隊')
        info = '本次更新添加了 '+str(new_tasks_counter)+' 個新任務, 目前列隊中共有 ' + str(len(processing_queue)) + ' 個任務'
        err_print(0, '更新資訊', info, no_sn=True)
        err_print(0, '更新终了', no_sn=True)
        print()
        for i in range(settings['check_frequency'] * 60):
            time.sleep(1)  # cool down, 這麽寫是爲了可以 Ctrl+C 馬上退出
