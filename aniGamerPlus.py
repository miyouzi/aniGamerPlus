#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2019/1/4 1:00
# @Author  : Miyouzi
# @File    : aniGamerPlus.py
# @Software: PyCharm

import datetime
import os
import queue
import sqlite3
import sys
import threading
import time
import argparse

import Config
from Anime import Anime
from Color import err_print


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
            for ep in anime.get_episode_list().values():
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
            # 如果用户选择仅下载最新 download_mode = 'latest'
            latest_sn = list(anime.get_episode_list().values())  # 本番剧剧集列表
            latest_sn.sort()
            latest_sn = latest_sn[-1]  # 选出 sn 值最高的，即最新的
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


def __download_only(sn, resolution='', save_dir=''):
    thread_limiter.acquire()
    err_counter = 0
    anime = Anime(sn)
    if resolution:
        anime.download(resolution, save_dir)
    else:
        anime.download(settings['download_resolution'], save_dir)
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
            if resolution:
                anime.download(resolution, save_dir)
            else:
                anime.download(settings['download_resolution'], save_dir)
    thread_limiter.release()


def __cui(sn, resolution, download_mode, thread_limit, save_dir=''):
    if download_mode == 'single':
        print('當前下載模式: 僅下載本集')
        Anime(sn).download(resolution, save_dir)

    elif download_mode == 'latest':
        print('當前下載模式: 下載本番劇最新一集')
        anime = Anime(sn)
        bangumi_list = list(anime.get_episode_list().values())
        bangumi_list.sort()
        if bangumi_list[-1] == sn:
            anime.download(resolution, save_dir)
        else:
            Anime(bangumi_list[-1]).download(resolution, save_dir)

    elif download_mode == 'all':
        print('當前下載模式: 下載本番劇所有劇集')
        anime = Anime(sn)
        bangumi_list = list(anime.get_episode_list().values())
        bangumi_list.sort()
        for a in bangumi_list:
            b = threading.Thread(target=__download_only, args=(a, resolution, save_dir,))
            b.start()
            print('添加任务列隊: sn=' + str(a))
        print('所有下載任務已添加至列隊, 執行緒數: ' + str(thread_limit))
    sys.exit(0)


if __name__ == '__main__':
    settings = Config.read_settings()
    sn_dict = Config.read_sn_list()
    working_dir = settings['working_dir']
    db_path = os.path.join(working_dir, 'aniGamer.db')
    queue = []
    processing_queue = []
    thread_limiter = threading.Semaphore(settings['multi-thread'])

    if len(sys.argv) > 1:  # 支持命令行使用
        print('當前aniGamerPlus版本: ' + settings['aniGamerPlus_version'])
        parser = argparse.ArgumentParser()
        parser.add_argument('--sn', '-s', type=int, help='視頻sn碼(數字)', required=True)
        parser.add_argument('--resolution', '-r', type=int, help='指定下載清晰度(數字)', choices=[360, 480, 540, 720, 1080])
        parser.add_argument('--download_mode', '-m', type=str, help='下載模式', default='single',
                            choices=['single', 'latest', 'all'])
        parser.add_argument('--thread_limit', '-t', type=int, help='最高并發下載數(數字)')
        parser.add_argument('--current_path', '-c', action='store_true', help='下載到當前工作目錄')
        arg = parser.parse_args()

        save_dir = ''
        if arg.current_path:
            save_dir = os.getcwd()
            print('使用命令行模式, 指定下載到當前目錄:\n    ' + save_dir)
        else:
            print('使用命令行模式, 文件將保存在配置文件中指定的目錄下:\n    ' + settings['bangumi_dir'])

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
        __cui(arg.sn, resolution, arg.download_mode, thread_limit, save_dir)

    if not os.path.exists(db_path):
        # 初始化 sqlite3 数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('create table anime ('
                       'ns INTEGER primary key  NOT NULL,'
                       'title VARCHAR(100) NOT NULL,'
                       'anime_name VARCHAR(100) NOT NULL, '
                       'episode VARCHAR(10) NOT NULL,'
                       'status TINYINT DEFAULT 0,'
                       'remote_statu INTEGER DEFAULT 0,'
                       'resolution INTEGER DEFAULT 0,'
                       'file_size INTEGER DEFAULT 0,'
                       "[CreatedTime] TimeStamp NOT NULL DEFAULT (datetime('now','localtime')))")

    while True:
        check_tasks()  # 检查更新，生成任务列队
        if queue:
            for task_sn in queue:
                if task_sn not in processing_queue:  # 如果该任务没有在进行中，则启动
                    task = threading.Thread(target=worker, args=(task_sn,))
                    task.start()
                    processing_queue.append(task_sn)
                    print('加入任务列隊: sn=' + str(task_sn))
        print(str(datetime.datetime.now()) + ' 更新终了\n')
        time.sleep(settings['check_frequency'] * 60)  # cool down
