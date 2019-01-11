#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2019/1/4 1:00
# @Author  : Miyouzi
# @File    : aniGamerPlus.py
# @Software: PyCharm

import datetime
import os
import queue
import signal
import sqlite3
import sys
import threading
import time
import argparse
import re

import Config
from Anime import Anime
from ColorPrint import err_print


def read_db(ns):
    # 传入sn(int)，读取该 sn 资料，返回 dict
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("select * FROM anime WHERE ns=:ns", {'ns': ns})

    try:
        values = cursor.fetchall()[0]
    except IndexError as e:
        raise e
    anime_db = {}
    anime_db['sn'] = values[0]
    anime_db['title'] = values[1]
    anime_db['anime_name'] = values[2]
    anime_db['episode'] = values[3]
    anime_db['status'] = values[4]
    anime_db['remote_statu'] = values[5]
    anime_db['resolution'] = values[6]
    anime_db['file_size'] = values[7]

    cursor.close()
    conn.close()
    return anime_db


def insert_db(anime):
    # 向数据库插入新资料
    anime_dict = {}
    anime_dict['ns'] = str(anime.get_sn())
    anime_dict['title'] = anime.get_title()
    anime_dict['anime_name'] = anime.get_bangumi_name()
    anime_dict['episode'] = anime.get_episode()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("INSERT INTO anime (ns, title, anime_name, episode) VALUES (:ns, :title, :anime_name, :episode)",
                       anime_dict)
    except sqlite3.IntegrityError as e:
        err_msg = 'ERROR: sn=' + anime_dict['ns'] + ' title=' + anime_dict['title'] + ' 数据已存在！' + str(e)
        err_print(err_msg)

    cursor.close()
    conn.commit()
    conn.close()


def update_db(anime):
    # 更新数据库 status, resolution, file_size 资料
    anime_dict = {}
    if anime.video_size > 10:
        anime_dict['status'] = 1
    else:
        # 下载失败
        sys.exit(1)
    anime_dict['ns'] = anime.get_sn()
    anime_dict['title'] = anime.get_title()
    anime_dict['anime_name'] = anime.get_bangumi_name()
    anime_dict['episode'] = anime.get_episode()
    anime_dict['file_size'] = anime.video_size
    anime_dict['resolution'] = anime.video_resolution

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("UPDATE anime SET status=:status, resolution=:resolution, file_size=:file_size WHERE ns=:ns",
                   anime_dict)

    cursor.close()
    conn.commit()
    conn.close()


def worker(sn):
    thread_limiter.acquire()
    anime = Anime(sn)
    anime.download(settings['download_resolution'])

    if anime.video_size < 10:
        # 下载失败
        queue.remove(sn)
        processing_queue.remove(sn)
        thread_limiter.release()
        err_print('sn=' + str(anime.get_sn()) + ' title=\"' + anime.get_title() + '\" 下載失敗! 從任務列隊中移除, 等待下次更新重試.')
        sys.exit(1)

    update_db(anime)
    queue.remove(sn)
    processing_queue.remove(sn)
    thread_limiter.release()
    print('sn=' + str(sn) + ' 任务完成')


def check_tasks():
    for sn in sn_dict.keys():
        anime = Anime(sn)
        if sn_dict[sn] == 'all':
            # 如果用户选择全部下载 download_mode = 'all'
            for ep in anime.get_episode_list().values():  # 遍历剧集列表
                try:
                    db = read_db(ep)
                    if db['status'] == 0 and ep not in queue:
                        # 如果该视频在库中但未完成且不在下载列队
                        queue.append(ep)  # 添加至下载列队
                except IndexError:
                    # 如果数据库中尚不存在此条记录
                    if anime.get_sn() == ep:
                        new_anime = anime  # 如果是本身则不用重复创建实例
                    else:
                        new_anime = Anime(ep)
                    insert_db(new_anime)
                    queue.append(ep)
        else:
            latest_sn = list(anime.get_episode_list().values())  # 本番剧剧集列表
            if sn_dict[sn] == 'largest-sn':
                # 如果用户选择仅下载最新上传, download_mode = 'largest_sn', 则对 sn 进行排序
                latest_sn.sort()
                # 否则用户选择仅下载最后剧集, download_mode = 'latest', 即下载网页上显示在最右的剧集
            latest_sn = latest_sn[-1]
            try:
                db = read_db(latest_sn)
                if db['status'] == 0 and latest_sn not in queue:
                    # 如果该视频在库中但未完成且不在下载列队
                    queue.append(latest_sn)  # 添加至下载列队
            except IndexError:
                # 如果数据库中尚不存在此条记录
                if anime.get_sn() == latest_sn:
                    new_anime = anime  # 如果是本身则不用重复创建实例
                else:
                    new_anime = Anime(latest_sn)
                insert_db(new_anime)
                queue.append(latest_sn)


def __download_only(sn, dl_resolution='', dl_save_dir='', realtime_show_file_size=False):
    # 仅下载,不操作数据库
    thread_limiter.acquire()
    err_counter = 0
    anime = Anime(sn)
    if dl_resolution:
        anime.download(dl_resolution, dl_save_dir, realtime_show_file_size)
    else:
        anime.download(settings['download_resolution'], dl_save_dir, realtime_show_file_size)
    while anime.video_size < 10:
        if err_counter >= 3:
            err_print('任務失敗達三次! 終止任務! sn=' + str(anime.get_sn()) + ' title=' + anime.get_title())
            thread_limiter.release()
            return
        else:
            err_print('任務失敗! sn=' + str(anime.get_sn()) + ' title=' + anime.get_title() + '10s后自動重啓,最多重試三次')
            err_counter = err_counter + 1
            time.sleep(10)
            anime.renew()
            if dl_resolution:
                anime.download(dl_resolution, dl_save_dir, realtime_show_file_size)
            else:
                anime.download(settings['download_resolution'], dl_save_dir, realtime_show_file_size)
    thread_limiter.release()


def __cui(sn, cui_resolution, cui_download_mode, cui_thread_limit, ep_range, cui_save_dir=''):
    if cui_thread_limit == 1:
        realtime_show_file_size = True
    else:
        realtime_show_file_size = False

    if cui_download_mode == 'single':
        print('當前下載模式: 僅下載本集\n')
        Anime(sn).download(cui_resolution, cui_save_dir, True)  # True 是实时显示文件大小, 仅一个下载任务时适用

    elif cui_download_mode == 'latest' or cui_download_mode == 'largest-sn':
        if cui_download_mode == 'latest':
            print('當前下載模式: 下載本番劇最後一集\n')
        else:
            print('當前下載模式: 下載本番劇最近上傳的一集\n')

        anime = Anime(sn)
        bangumi_list = list(anime.get_episode_list().values())

        if cui_download_mode == 'largest-sn':
            bangumi_list.sort()

        if bangumi_list[-1] == sn:
            anime.download(cui_resolution, cui_save_dir, True)
        else:
            Anime(bangumi_list[-1]).download(cui_resolution, cui_save_dir, True)

    elif cui_download_mode == 'all':
        print('當前下載模式: 下載本番劇所有劇集\n')
        anime = Anime(sn)
        bangumi_list = list(anime.get_episode_list().values())
        bangumi_list.sort()
        for anime_sn in bangumi_list:
            task = threading.Thread(target=__download_only, args=(anime_sn, cui_resolution, cui_save_dir, realtime_show_file_size))
            task.setDaemon(True)
            thread_tasks.append(task)
            task.start()
            print('添加任务列隊: sn=' + str(anime_sn))
        print('所有下載任務已添加至列隊, 執行緒數: ' + str(cui_thread_limit) + '\n')

    elif cui_download_mode == 'range':
        print('當前下載模式: 下載本番劇指定劇集\n')
        anime = Anime(sn)
        episode_dict = anime.get_episode_list()
        bangumi_ep_list = list(episode_dict.keys())  # 本番剧集列表
        for ep in ep_range:
            if ep in bangumi_ep_list:
                a = threading.Thread(target=__download_only, args=(episode_dict[ep], cui_resolution, cui_save_dir, realtime_show_file_size))
                a.setDaemon(True)
                thread_tasks.append(a)
                a.start()
                print('添加任务列隊: sn='+str(episode_dict[ep])+' 《'+anime.get_bangumi_name()+'》 第 '+ep+' 集')
            else:
                err_print('《'+anime.get_bangumi_name()+'》 第 '+ep+' 集不存在!')
        print('所有下載任務已添加至列隊, 執行緒數: ' + str(cui_thread_limit) + '\n')

    __kill_thread_when_ctrl_c()
    sys.exit(0)


def __kill_thread_when_ctrl_c():
    for t in thread_tasks:  # 当用户 Ctrl+C 可以 kill 线程
        while True:
            if t.isAlive():
                time.sleep(1)
            else:
                break


def user_exit(signum, frame):
    err_print('\n\n你終止了程序!')
    sys.exit(255)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, user_exit)
    signal.signal(signal.SIGTERM, user_exit)
    settings = Config.read_settings()
    sn_dict = Config.read_sn_list()
    working_dir = settings['working_dir']
    db_path = os.path.join(working_dir, 'aniGamer.db')
    queue = []
    processing_queue = []
    thread_limiter = threading.Semaphore(settings['multi-thread'])
    thread_tasks = []

    if len(sys.argv) > 1:  # 支持命令行使用
        print('當前aniGamerPlus版本: ' + settings['aniGamerPlus_version'])
        parser = argparse.ArgumentParser()
        parser.add_argument('--sn', '-s', type=int, help='視頻sn碼(數字)', required=True)
        parser.add_argument('--resolution', '-r', type=int, help='指定下載清晰度(數字)', choices=[360, 480, 540, 720, 1080])
        parser.add_argument('--download_mode', '-m', type=str, help='下載模式', default='single',
                            choices=['single', 'latest', 'largest-sn', 'all', 'range'])
        parser.add_argument('--thread_limit', '-t', type=int, help='最高并發下載數(數字)')
        parser.add_argument('--current_path', '-c', action='store_true', help='下載到當前工作目錄')
        parser.add_argument('--episodes', '-e', type=str, help='僅下載指定劇集')
        arg = parser.parse_args()

        save_dir = ''
        download_mode = arg.download_mode
        if arg.current_path:
            save_dir = os.getcwd()
            print('使用命令行模式, 指定下載到當前目錄:\n    ' + save_dir)
        else:
            print('使用命令行模式, 文件將保存在配置文件中指定的目錄下:\n    ' + settings['bangumi_dir'])

        if not arg.episodes and arg.download_mode == 'range':
            err_print('ERROR: 當前指定範圍下載模式, 但下載範圍未指定!')
            sys.exit(1)

        download_episodes = []
        if arg.episodes:
            for i in arg.episodes.split(','):
                if re.match(r'^\d+-\d+$', i):
                    episodes_range_start = int(i.split('-')[0])
                    episodes_range_end = int(i.split('-')[1])
                    if episodes_range_start > episodes_range_end:  # 如果有zz从大到小写
                        episodes_range_start, episodes_range_end = episodes_range_end, episodes_range_start
                    download_episodes.extend(list(range(episodes_range_start, episodes_range_end + 1)))
                if re.match(r'^\d+$', i):
                    download_episodes.append(int(i))
            download_episodes = list(set(download_episodes))  # 去重复
            download_episodes.sort()  # 排序, 任务将会按集数顺序下载
            download_episodes = list(map(lambda x: str(x), download_episodes))
            # 转为 str, 方便作为 Anime.get_episode_list() 的 key
            download_mode = 'range'

        if not arg.resolution:
            resolution = settings['download_resolution']
            print('未设定下载清晰度, 将使用配置文件指定的清晰度: ' + resolution + 'P')
        else:
            resolution = str(arg.resolution)
            print('指定下载清晰度: ' + resolution + 'P')

        if arg.thread_limit:
            # 用戶設定并發數
            thread_limit = arg.thread_limit
            thread_limiter = threading.Semaphore(arg.thread_limit)
        else:
            thread_limit = settings['multi-thread']
        __cui(arg.sn, resolution, download_mode, thread_limit, download_episodes, save_dir)

    # 初始化 sqlite3 数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS anime ('
                   'ns INTEGER PRIMARY KEY NOT NULL,'
                   'title VARCHAR(100) NOT NULL,'
                   'anime_name VARCHAR(100) NOT NULL, '
                   'episode VARCHAR(10) NOT NULL,'
                   'status TINYINT DEFAULT 0,'
                   'remote_statu INTEGER DEFAULT 0,'
                   'resolution INTEGER DEFAULT 0,'
                   'file_size INTEGER DEFAULT 0,'
                   "[CreatedTime] TimeStamp NOT NULL DEFAULT (datetime('now','localtime')))")
    conn.commit()
    conn.close()

    while True:
        check_tasks()  # 检查更新，生成任务列队
        if queue:
            for task_sn in queue:
                if task_sn not in processing_queue:  # 如果该任务没有在进行中，则启动
                    task = threading.Thread(target=worker, args=(task_sn,))
                    task.setDaemon(True)
                    task.start()
                    processing_queue.append(task_sn)
                    print('加入任务列隊: sn=' + str(task_sn))
        print(str(datetime.datetime.now()) + ' 更新终了\n')
        for i in range(settings['check_frequency'] * 60):
            time.sleep(1)  # cool down, 這麽寫是爲了可以 Ctrl+C 馬上退出
