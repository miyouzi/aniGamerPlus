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
        # 如果該埠不可用
        random_port = random.randint(40000, 60000)
    return random_port


def build_anime(sn):
    anime = {'anime': None, 'failed': True}
    try:
        if settings['use_gost']:
            # 如果使用 gost，則隨機一個 gost 監聽埠
            anime['anime'] = Anime(sn, gost_port=gost_port)
        else:
            anime['anime'] = Anime(sn)
        anime['failed'] = False

        if danmu:
            anime['anime'].enable_danmu()

    except TryTooManyTimeError:
        err_print(sn, '抓取失敗', '影片資訊抓取失敗！', status=1)
    except BaseException as e:
        err_print(sn, '抓取失敗', '抓取影片資訊時發生未知錯誤: ' + str(e), status=1)
        err_print(sn, '抓取異常', '異常詳情:\n' + traceback.format_exc(), status=1, display=False)
    return anime


def read_db(sn):
    db_locker.acquire()
    # 傳入sn(int)，讀取該 sn 資料，返回 dict
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
    # 向資料庫插入新資料
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
        err_print(anime_dict['sn'], '資料庫錯誤', 'title=' + anime_dict['title'] + ' 資料已存在！' + str(e), status=1)

    cursor.close()
    conn.commit()
    conn.close()
    db_locker.release()


def update_db(anime):
    db_locker.acquire()
    # 更新資料庫 status, resolution, file_size 資料
    anime_dict = {}
    if anime.video_size > 5:
        anime_dict['status'] = 1
    else:
        # 下載失敗
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
        upload_limiter.release()  # 併發上傳限制器
        sys.exit(0)

    anime_in_db = read_db(sn)
    # 如果使用者設定要上傳且已經下載好了但還沒有上傳成功, 那麼僅上傳
    if settings['upload_to_server'] and anime_in_db['status'] == 1 and anime_in_db['remote_status'] == 0:
        upload_limiter.acquire()  # 併發上傳限制器
        anime = build_anime(sn)
        if anime['failed']:
            err_print(sn, '任務失敗', '從任務列隊中移除, 等待下次更新重試.', status=1)
            upload_quit()

        # 影片資訊抓取成功
        anime = anime['anime']
        if not os.path.exists(anime_in_db['local_file_path']):
            # 如果資料庫中記錄的檔案路徑已失效
            update_db(anime)
            err_msg_detail = 'title=\"' + anime.get_title() + '\" 本地檔案丟失, 從任務列隊中移除, 等待下次更新重試.'
            err_print(sn, '上傳失敗', err_msg_detail, status=1)
            upload_quit()

        anime.local_video_path = anime_in_db['local_file_path']  # 告知檔案位置
        anime.video_size = anime_in_db['file_size']  # 透過 update_db() 下載狀態檢查
        anime.video_resolution = anime_in_db['resolution']  # 避免更新時把解析度變成0

        try:
            if not anime.upload(bangumi_tag):  # 如果上傳失敗
                err_msg_detail = 'title=\"' + anime.get_title() + '\" 從任務列隊中移除，等待下次更新重試。'
                err_print(sn, '上傳失敗', err_msg_detail, 1)
            else:
                update_db(anime)
                err_print(sn, '任務完成', status=2)
        except BaseException as e:
            err_msg_detail = 'title=\"' + anime.get_title() + '\" 發生未知錯誤，等待下次更新重試：' + str(e)
            err_print(sn, '上傳失敗', '異常詳情:\n'+traceback.format_exc(), status=1, display=False)
            err_print(sn, '上傳失敗', err_msg_detail, 1)

        upload_quit()

    # ===== 下載模組 =====
    thread_limiter.acquire()  # 併發下載限制器
    anime = build_anime(sn)

    if anime['failed']:
        queue.pop(sn)
        processing_queue.remove(sn)
        thread_limiter.release()
        err_print(sn, '任務失敗', '從任務列隊中移除，等待下次更新重試。', status=1)
        sys.exit(1)

    anime = anime['anime']

    try:
        anime.download(settings['download_resolution'], bangumi_tag=bangumi_tag, rename=rename,
                       realtime_show_file_size=realtime_show_file_size, classify=settings['classify_bangumi'])
    except BaseException as e:
        # 兜一下各種奇奇怪怪的錯誤
        err_print(sn, '下載異常', '發生未知錯誤: ' + str(e), status=1)
        err_print(sn, '下載異常', '異常詳情:\n' + traceback.format_exc(), status=1, display=False)
        anime.video_size = 0

    if anime.video_size < 5:
        # 下载失败
        queue.pop(sn)
        processing_queue.remove(sn)
        thread_limiter.release()
        err_msg_detail = 'title=\"' + anime.get_title() + '\" 從任務列隊中移除，等待下次更新重試。'
        err_print(sn, '任務失敗', err_msg_detail, status=1)
        if int(sn) in Config.tasks_progress_rate.keys():
            del Config.tasks_progress_rate[int(sn)]  # 任務失敗，不在監控此任務進度
        sys.exit(1)

    update_db(anime)  # 下載完成後，更新資料庫
    thread_limiter.release()  # 併發下載限制器
    # ===== 下载模組結束 =====

    # ===== 上傳模組 =====
    if settings['upload_to_server']:
        upload_limiter.acquire()  # 併發上傳限制器

        try:
            anime.upload(bangumi_tag)  # 上傳至伺服器
        except BaseException as e:
            # 兜一下各種奇奇怪怪的錯誤
            err_print(sn, '上傳異常', '發生未知錯誤，從任務列隊中移除，等待下次更新重試：' + str(e), status=1)
            err_print(sn, '上傳異常', '異常詳情:\n' + traceback.format_exc(), status=1, display=False)
            upload_quit()

        update_db(anime)  # 上傳完成後, 更新資料庫
        upload_limiter.release()  # 併發上傳限制器
        # =====上傳模組結束=====

    queue.pop(sn)  # 從任務列隊中移除
    processing_queue.remove(sn)  # 從當前任務列隊中移除
    err_print(sn, '任務完成', status=2)


def check_tasks():
    for sn in sn_dict.keys():
        anime = build_anime(sn)
        if anime['failed']:
            err_print(sn, '更新狀態', '檢查更新失敗，跳過等待下次檢查', status=1)
            continue
        anime = anime['anime']
        err_print(sn, '更新資訊', '正在檢查《' + anime.get_bangumi_name() + '》')
        episode_list = list(anime.get_episode_list().values())

        if sn_dict[sn]['mode'] == 'all':
            # 如果使用者選擇全部下載 download_mode = 'all'
            for ep in episode_list:  # 遍歷劇集列表
                try:
                    db = read_db(ep)
                    #           未下載的   或                設定要上傳但是沒上傳的                         並且  還沒在列隊中
                    if (db['status'] == 0 or (db['remote_status'] == 0 and settings['upload_to_server'])) and ep not in queue.keys():
                        queue[ep] = sn_dict[sn]  # 新增至下載列隊
                except IndexError:
                    # 如果資料庫中尚不存在此條記錄
                    if anime.get_sn() == ep:
                        new_anime = anime  # 如果是本身則不用重複建立例項
                    else:
                        new_anime = build_anime(ep)
                        if new_anime['failed']:
                            err_print(ep, '更新狀態', '更新數據失敗，跳過等待下次檢查', status=1)
                            continue
                        new_anime = new_anime['anime']
                    insert_db(new_anime)
                    queue[ep] = sn_dict[sn]  # 新增至列隊
        else:
            if sn_dict[sn]['mode'] == 'largest-sn':
                # 如果使用者選擇僅下載最新上傳, download_mode = 'largest_sn', 則對 sn 進行排序
                episode_list.sort()
                latest_sn = episode_list[-1]
                # 否則使用者選擇僅下載最後劇集, download_mode = 'latest', 即下載網頁上顯示在最右的劇集
            elif sn_dict[sn]['mode'] == 'single':
                latest_sn = sn  # 適配命令列 sn-list 模式
            else:
                latest_sn = episode_list[-1]
            try:
                db = read_db(latest_sn)
                #           未下載的   或                設定要上傳但是沒上傳的                         並且  還沒在列隊中
                if (db['status'] == 0 or (db['remote_status'] == 0 and settings['upload_to_server'])) and latest_sn not in queue.keys():
                    queue[latest_sn] = sn_dict[sn]  # 新增至下載列隊
            except IndexError:
                # 如果資料庫中尚不存在此條記錄
                if anime.get_sn() == latest_sn:
                    new_anime = anime  # 如果是本身則不用重複建立例項
                else:
                    new_anime = build_anime(latest_sn)
                    if new_anime['failed']:
                        err_print(latest_sn, '更新狀態', '更新數據失敗，跳過等待下次檢查', status=1)
                        continue
                    new_anime = new_anime['anime']
                insert_db(new_anime)
                queue[latest_sn] = sn_dict[sn]


def __download_only(sn, dl_resolution='', dl_save_dir='', realtime_show_file_size=False, classify=True):
    # 僅下載，不操作資料庫
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
        err_print(sn, '下載異常', '發生未知異常：' + str(e), status=1)
        err_print(sn, '下載異常', '異常詳情：\n'+traceback.format_exc(), status=1, display=False)
        anime.video_size = 0

    while anime.video_size < 5:
        if err_counter >= 3:
            err_print(sn, '終止任務', 'title=' + anime.get_title()+' 任務失敗達三次！終止任務！', status=1)
            thread_limiter.release()
            if int(sn) in Config.tasks_progress_rate.keys():
                del Config.tasks_progress_rate[int(sn)]
            return
        else:
            err_print(sn, '任務失敗', 'title=' + anime.get_title() + ' 10s 後自動重啟，最多重試三次', status=1)
            err_counter = err_counter + 1
            if int(sn) in Config.tasks_progress_rate.keys():
                Config.tasks_progress_rate[int(sn)]['status'] = '失敗！重啟中'
            time.sleep(10)
            anime.renew()

            try:
                if dl_resolution:
                    anime.download(dl_resolution, dl_save_dir, realtime_show_file_size=realtime_show_file_size, classify=classify)
                else:
                    anime.download(settings['download_resolution'], dl_save_dir, realtime_show_file_size=realtime_show_file_size, classify=classify)
            except BaseException as e:
                err_print(sn, '下載異常', '發生未知異常：' + str(e), status=1)
                err_print(sn, '下載異常', '異常詳情：\n'+traceback.format_exc(), status=1, display=False)
                anime.video_size = 0

    thread_limiter.release()


def __get_info_only(sn):
    thread_limiter.acquire()

    anime = build_anime(sn)
    if anime['failed']:
        sys.exit(1)
    anime = anime['anime']
    anime.set_resolution(resolution)
    anime.get_info()
    download_dir = settings['bangumi_dir']
    if classify:  # 控制是否建立番劇資料夾
        download_dir = os.path.join(download_dir, Config.legalize_filename(anime.get_bangumi_name()))

    if danmu:
        full_filename = os.path.join(download_dir, anime.get_filename()).replace('.' + settings['video_filename_extension'], '.ass')
        d = Danmu(sn, full_filename)
        d.download()

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
            print('當前模式：查詢本集資訊\n')
        else:
            print('當前下載模式：僅下載本集\n')

        if get_info:
            __get_info_only(sn)
        else:
            __download_only(sn, cui_resolution, cui_save_dir, realtime_show_file_size=realtime_show_file_size, classify=classify)

    elif cui_download_mode == 'latest' or cui_download_mode == 'largest-sn':
        if cui_download_mode == 'latest':
            if get_info:
                print('當前模式：查詢本番劇最後一集資訊\n')
            else:
                print('當前下載模式：下載本番劇最後一集\n')
        else:
            if get_info:
                print('當前模式：查詢本番劇最近上傳一集資訊\n')
            else:
                print('當前下載模式：下載本番劇最近上傳的一集\n')

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
            print('當前模式：查詢本番劇所有劇集資訊\n')
        else:
            print('當前下載模式：下載本番劇所有劇集\n')

        anime = build_anime(sn)
        if anime['failed']:
            sys.exit(1)
        anime = anime['anime']

        bangumi_list = list(anime.get_episode_list().values())
        bangumi_list.sort()
        tasks_counter = 0  # 任務計數器
        for anime_sn in bangumi_list:
            if get_info:
                task = threading.Thread(target=__get_info_only, args=(anime_sn,))
            else:
                task = threading.Thread(target=__download_only, args=(anime_sn, cui_resolution, cui_save_dir, realtime_show_file_size, classify))
            task.setDaemon(True)
            thread_tasks.append(task)
            task.start()
            tasks_counter = tasks_counter + 1
            print('添加任务列隊：sn=' + str(anime_sn))
        if get_info:
            print('所有查詢任務已添加至列隊，共 '+str(tasks_counter)+' 個任務\n')
        else:
            print('所有下載任務已添加至列隊，共 '+str(tasks_counter)+' 個任務，'+'執行緒數：' + str(cui_thread_limit) + '\n')

    elif cui_download_mode == 'range':
        if get_info:
            print('當前模式：查詢本番劇指定劇集資訊\n')
        else:
            print('當前下載模式：下載本番劇指定劇集\n')

        anime = build_anime(sn)
        if anime['failed']:
            sys.exit(1)
        anime = anime['anime']

        episode_dict = anime.get_episode_list()
        bangumi_ep_list = list(episode_dict.keys())  # 本番劇集列表
        tasks_counter = 0  # 任務計數器
        for ep in ep_range:
            if ep in bangumi_ep_list:
                if get_info:
                    a = threading.Thread(target=__get_info_only, args=(episode_dict[ep],))
                else:
                    a = threading.Thread(target=__download_only, args=(episode_dict[ep], cui_resolution, cui_save_dir, realtime_show_file_size))
                a.setDaemon(True)
                thread_tasks.append(a)
                a.start()
                tasks_counter = tasks_counter + 1
                if get_info:
                    print('添加查詢列隊：sn=' + str(episode_dict[ep]) + ' 《' + anime.get_bangumi_name() + '》 第 ' + ep + ' 集')
                else:
                    print('添加任务列隊：sn='+str(episode_dict[ep])+' 《'+anime.get_bangumi_name()+'》 第 '+ep+' 集')
            else:
                err_print(0, '《'+anime.get_bangumi_name()+'》 第 '+ep+' 集不存在！', status=1, no_sn=True)
        print('所有任務已添加至列隊, 共 '+str(tasks_counter)+' 個任務, '+'執行緒數：' + str(cui_thread_limit) + '\n')

    elif cui_download_mode == 'sn-range':
        if get_info:
            print('當前模式：查詢本番劇指定 sn 範圍資訊\n')
        else:
            print('當前下載模式：下載本番劇指定 sn 範圍劇集\n')

        anime = build_anime(sn)
        if anime['failed']:
            sys.exit(1)
        anime = anime['anime']

        # 劇集列表 key value 互換, {'sn', '劇集名'}
        episode_dict = {value:key for key,value in anime.get_episode_list().items()}
        ep_sn_list = list(episode_dict.keys())  # 本番劇集sn列表
        tasks_counter = 0  # 任務計數器
        ep_range = list(map(lambda x: int(x), ep_range))
        for sn in ep_sn_list:
            if sn in ep_range:
                # 如果該 sn 在使用者指定的 sn 範圍裡
                if get_info:
                    a = threading.Thread(target=__get_info_only, args=(sn,))
                else:
                    a = threading.Thread(target=__download_only, args=(sn, cui_resolution, cui_save_dir, realtime_show_file_size))
                a.setDaemon(True)
                thread_tasks.append(a)
                a.start()
                tasks_counter = tasks_counter + 1
                if get_info:
                    print('添加查詢列隊：sn=' + str(sn) + ' 《' + anime.get_bangumi_name() + '》 第 ' + episode_dict[sn] + ' 集')
                else:
                    print('添加任务列隊：sn='+str(sn)+' 《'+anime.get_bangumi_name()+'》 第 ' + episode_dict[sn] + ' 集')
        print('所有任務已添加至列隊，共 ' + str(tasks_counter) + ' 個任務，' + '執行緒數：' + str(cui_thread_limit) + '\n')

    elif cui_download_mode == 'multi':
        if get_info:
            print('當前模式：查詢指定 sn 資訊\n')
        else:
            print('當前下載模式：下載指定 sn 劇集\n')

        tasks_counter = 0
        for sn in ep_range:
            if get_info:
                a = threading.Thread(target=__get_info_only, args=(sn,))
            else:
                a = threading.Thread(target=__download_only, args=(sn, cui_resolution, cui_save_dir, realtime_show_file_size))
            a.setDaemon(True)
            thread_tasks.append(a)
            a.start()
            tasks_counter = tasks_counter + 1

        print('所有任務已添加至列隊，共 ' + str(tasks_counter) + ' 個任務，' + '執行緒數：' + str(cui_thread_limit) + '\n')

    elif cui_download_mode in ('list', 'sn-list'):
        if get_info:
            # 如果為list模式也僅查詢名單中的sn資訊，可用於檢查sn是否輸入正確
            print('當前模式：查詢 sn_list.txt 中指定 sn 的資訊\n')
            ep_range = Config.read_sn_list().keys()
            for sn in ep_range:
                anime = build_anime(sn)
                if anime['failed']:
                    sys.exit(1)
                anime = anime['anime']
                anime.get_info()
        else:
            if cui_download_mode == 'sn-list':
                print('當前下載模式：下載 sn_list.txt 中指定的 sn 劇集\n')
                for i in sn_dict:
                    sn_dict[i]['mode'] = 'single'
            else:
                print('當前下載模式：單次下載 sn_list.txt 中的番劇\n')

            check_tasks()  # 檢查更新，生成任務列隊
            for sn in queue.keys():  # 遍歷任務列隊
                processing_queue.append(sn)
                task = threading.Thread(target=worker, args=(sn, queue[sn], realtime_show_file_size))
                task.setDaemon(True)
                thread_tasks.append(task)
                task.start()
                err_print(sn, '加入任務列隊')
            msg = '共 ' + str(len(queue)) + ' 個任務'
            err_print(0, '任務資訊', msg, no_sn=True)
            print()

    __kill_thread_when_ctrl_c()
    kill_gost()  # 結束 gost

    # 結束後執行使用者自定義命令
    if user_cmd:
        print()
        os.popen(settings['user_command'])
        err_print(0, '任務完成', '已執行使用者自定義命令', no_sn=True, status=2)

    sys.exit(0)


def __kill_thread_when_ctrl_c():
    # 等待所有任務完成
    for t in thread_tasks:  # 當用戶 Ctrl+C 可以 kill 執行緒
        while True:
            if t.is_alive():
                time.sleep(1)
            else:
                break


def kill_gost():
    if gost_subprocess is not None:
        gost_subprocess.kill()  # 結束 gost


def user_exit(signum, frame):
    err_print(0, '你終止了程式！', '\n', status=1, no_sn=True, prefix='\n\n')
    kill_gost()  # 結束 gost
    sys.exit(255)


def check_new_version():
    # 检查GitHub上是否有新版
    remote_version = Config.read_latest_version_on_github()
    if float(settings['aniGamerPlus_version'][1:]) < float(remote_version['tag_name'][1:]):
        msg = '發現 GitHub 上有新版本: '+remote_version['tag_name']+'\n更新内容：\n'+remote_version['body']+'\n'
        err_print(0, msg, status=1, no_sn=True)


def __init_proxy():
    if settings['use_gost']:
        print('使用代理連線動畫瘋，使用擴充套件的代理協議')
        # 需要使用 gost 的情況
        # 尋找 gost
        check_gost = subprocess.Popen('gost -h', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if check_gost.stderr.readlines():  # 查詢 gost 是否已放入系統 path
            gost_path = 'gost'
        else:
            # print('沒有在系統PATH中發現gost，嘗試在所在目錄尋找')
            if 'Windows' in platform.system():
                gost_path = os.path.join(working_dir, 'gost.exe')
            else:
                gost_path = os.path.join(working_dir, 'gost')
            if not os.path.exists(gost_path):
                err_print(0, '當前代理使用擴展協議, 需要使用gost, 但是gost未找到', status=1, no_sn=True)
                raise FileNotFoundError  # 如果本地目錄下也沒有找到 gost 則丟出異常
        # 建構 gost 指令
        gost_cmd = [gost_path, '-L=:'+str(gost_port), '-F=' + settings['proxy']]  # 本地監聽埠 34173

        def run_gost():
            # gost 執行緒
            global gost_subprocess
            gost_subprocess = subprocess.Popen(gost_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            gost_subprocess.communicate()

        run_gost_threader = threading.Thread(target=run_gost)
        run_gost_threader.setDaemon(True)
        run_gost_threader.start()  # 啟動 gost
        time.sleep(3)  # 給時間讓 gost 啟動

    else:
        print('使用代理連接動畫瘋，使用http/https/socks5 協議')


def run_dashboard():
    # 檢測埠是否佔用
    if not port_is_available(settings['dashboard']['port']):
        err_print(0, 'Web控制面板啟動失敗', 'Port已被佔用！請到設定檔案更換', status=1, no_sn=True)
        return

    from Dashboard.Server import run as dashboard
    server = threading.Thread(target=dashboard)
    server.setDaemon(True)
    server.start()
    if settings['dashboard']['SSL']:
        dashboard_address = 'https://'
    else:
        dashboard_address = 'http://'
    if settings['dashboard']['host'] == '0.0.0.0':
        host = Config.get_local_ip()
        dashboard_address = '【開放外部存取】存取地址: ' + dashboard_address
    else:
        host = settings['dashboard']['host']
        dashboard_address = '存取地址: ' + dashboard_address

    dashboard_address = dashboard_address + host + ':' + str(settings['dashboard']['port'])
    err_print(0, 'Web 控制面板已啟動', dashboard_address, no_sn=True, status=2)


signal.signal(signal.SIGINT, user_exit)
signal.signal(signal.SIGTERM, user_exit)
settings = Config.read_settings()
working_dir = settings['working_dir']
db_path = os.path.join(working_dir, 'aniGamer.db')
queue = {}  # 儲存 sn 相關資訊, {'tag': TAG, 'rename': RENAME}, rename,
processing_queue = []
thread_limiter = threading.Semaphore(settings['multi-thread'])  # 下載併發限制器
upload_limiter = threading.Semaphore(settings['multi_upload'])  # 併發上傳限制器
db_locker = threading.Semaphore(1)
thread_tasks = []
gost_subprocess = None  # 存放 gost 的 subprocess.Popen 物件, 用於結束時 kill gost
gost_port = gost_port()  # gost 埠
sn_dict = Config.read_sn_list()
danmu = settings['danmu']

if __name__ == '__main__':
    if settings['check_latest_version']:
        check_new_version()  # 檢查新版
        version_msg = '當前aniGamerPlus版本: ' + settings['aniGamerPlus_version']
        print(version_msg)

        # 初始化 sqlite3 資料庫
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

    if len(sys.argv) > 1:  # 支援命令列使用
        parser = argparse.ArgumentParser()
        parser.add_argument('--sn', '-s', type=int, help='影片 sn 碼（數字）')
        parser.add_argument('--resolution', '-r', type=int, help='指定下載解析度（數字）', choices=[360, 480, 540, 576, 720, 1080])
        parser.add_argument('--download_mode', '-m', type=str, help='下載模式', default='single',
                            choices=['single', 'latest', 'largest-sn', 'multi', 'all', 'range', 'list', 'sn-list', 'sn-range'])
        parser.add_argument('--thread_limit', '-t', type=int, help='最高併發下載數（數字）')
        parser.add_argument('--current_path', '-c', action='store_true', help='下載到當前工作目錄')
        parser.add_argument('--episodes', '-e', type=str, help='僅下載指定劇集')
        parser.add_argument('--no_classify', '-n', action='store_true', help='不建立番劇資料夾')
        parser.add_argument('--user_command', '-u', action='store_true', help='所有下載完成後執行使用者命令')
        parser.add_argument('--information_only', '-i', action='store_true', help='僅查詢資訊，可搭配 -d 更新彈幕')
        parser.add_argument('--danmu', '-d', action='store_true', help='以 .ass 下載彈幕(beta)')
        arg = parser.parse_args()

        if (arg.download_mode not in ('list', 'multi', 'sn-list')) and arg.sn is None:
            err_print(0, '引數錯誤', '非 list/multi 模式需要提供 sn ', no_sn=True, status=1)
            sys.exit(1)

        save_dir = ''
        download_mode = arg.download_mode
        if arg.current_path:
            save_dir = os.getcwd()
            info = '使用命令列模式，指定下載到當前目錄：'
            print(info + '\n    ' + save_dir)
            err_print(0, info + save_dir, no_sn=True, display=False)
        else:
            info = '使用命令列模式，檔案將儲存在設定檔案中指定的目錄下：'
            print(info + '\n    ' + settings['bangumi_dir'])
            err_print(0, info + settings['bangumi_dir'], no_sn=True, display=False)

        classify = True
        if arg.no_classify:
            classify = False
            print('將不會建立番劇資料夾')

        if not arg.episodes and arg.download_mode == 'range':
            err_print(0, 'ERROR：當前為指定範圍模式，但範圍未指定！', status=1, no_sn=True)
            sys.exit(1)

        download_episodes = []
        if arg.episodes or arg.download_mode == 'sn-list':
            if arg.download_mode == 'multi':
                # 如果此時為 multi 模式，則 download_episodes 裝的是 sn 碼
                for i in arg.episodes.split(','):
                    if re.match(r'^\d+$', i):
                        download_episodes.append(int(i))
                if arg.sn:
                    download_episodes.append(arg.sn)

            elif arg.download_mode == 'sn-list':
                # 如果此時為 sn-list 模式，則 download_episodes 裝的是 sn_list.txt 裡的 sn 碼
                download_episodes = list(Config.read_sn_list().keys())

            else:
                for i in arg.episodes.split(','):
                    if re.match(r'^\d+-\d+$', i):
                        episodes_range_start = int(i.split('-')[0])
                        episodes_range_end = int(i.split('-')[1])
                        if episodes_range_start > episodes_range_end:  # 如果有 zz 從大到小寫
                            episodes_range_start, episodes_range_end = episodes_range_end, episodes_range_start
                        download_episodes.extend(list(range(episodes_range_start, episodes_range_end + 1)))
                    if re.match(r'^\d+$', i):
                        download_episodes.append(int(i))
                if arg.download_mode != 'sn-range':
                    download_mode = 'range'  # 如果帶 -e 引數沒有指定 multi 模式, 則預設為 range 模式

            download_episodes = list(set(download_episodes))  # 去重複
            download_episodes.sort()  # 排序, 任務將會按集數順序下載
            # 轉為 str, 方便作為 Anime.get_episode_list() 的 key
            download_episodes = list(map(lambda x: str(x), download_episodes))

        if not arg.resolution:
            resolution = settings['download_resolution']
            print('未設定下載解析度，將使用設定檔案指定的解析度：' + resolution + 'P')
        else:
            if arg.download_mode in ('sn-list', 'list'):
                err_print(0,'無效參數:', 'list 及 sn-list 模式無法透過命令列指定解析度', 1, no_sn=True, display_time=False)
                resolution = settings['download_resolution']
                print('將使用設定檔案指定的解析度：' + resolution + 'P')
            else:
                resolution = str(arg.resolution)
                print('指定下載解析度: ' + resolution + 'P')

        if arg.information_only:
            # 為避免排版混亂，僅顯示資訊時強制為單執行緒
            thread_limit = 1
            thread_limiter = threading.Semaphore(thread_limit)
        else:
            if arg.thread_limit:
                # 使用者設定並發數
                if arg.thread_limit > Config.get_max_multi_thread():
                    # 是否超過最大允許執行緒數
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

    err_print(0, '自動模式啟動 aniGamerPlus ' + version_msg, no_sn=True, display=False)
    err_print(0, '工作目錄：' + working_dir, no_sn=True, display=False)

    if settings['use_proxy']:
        __init_proxy()

    if settings['use_dashboard']:
        run_dashboard()

    while True:
        print()
        err_print(0, '開始更新', no_sn=True)
        Config.test_cookie()  # 測試 cookie
        if settings['read_sn_list_when_checking_update']:
            sn_dict = Config.read_sn_list()
        if settings['read_config_when_checking_update']:
            settings = Config.read_settings()
        danmu = settings['danmu']  # 避免手動加入工作時，global 覆寫掉 config 的 danmu 設定
        check_tasks()  # 檢查更新，生成任務列隊
        new_tasks_counter = 0  # 新增任務計數器
        if queue:
            for task_sn in queue.keys():
                if task_sn not in processing_queue:  # 如果該任務沒有在進行中，則啟動
                    task = threading.Thread(target=worker, args=(task_sn, queue[task_sn]))
                    task.setDaemon(True)
                    task.start()
                    processing_queue.append(task_sn)
                    new_tasks_counter = new_tasks_counter + 1
                    err_print(task_sn, '加入任務列隊')
                    info = '本次新增了 ' + str(new_tasks_counter) + ' 個新任務, 目前列隊中共有 ' + str(len(processing_queue)) + ' 個任務'
        err_print(0, '更新資訊', info, no_sn=True)
        err_print(0, '更新终了', no_sn=True)
        print()
        for i in range(settings['check_frequency'] * 60):
            time.sleep(1)  # cool down, 這麽寫是爲了可以 Ctrl+C 馬上退出
