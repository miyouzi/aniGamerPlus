#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2019/1/5 16:22
# @Author  : Miyouzi
# @File    : Anime.py @Software: PyCharm
import ftplib
import shutil
import Config
from Danmu import Danmu
from bs4 import BeautifulSoup
import re, time, os, platform, subprocess, requests, random, sys
from ColorPrint import err_print
from ftplib import FTP, FTP_TLS
import socket
import threading
from urllib.parse import quote


class TryTooManyTimeError(BaseException):
    pass


class Anime:
    def __init__(self, sn, debug_mode=False, gost_port=34173):
        self._settings = Config.read_settings()
        self._cookies = Config.read_cookie()
        self._working_dir = self._settings['working_dir']
        self._bangumi_dir = self._settings['bangumi_dir']
        self._temp_dir = self._settings['temp_dir']
        self._gost_port = str(gost_port)

        self._session = requests.session()
        self._title = ''
        self._sn = sn
        self._bangumi_name = ''
        self._episode = ''
        self._episode_list = {}
        self._device_id = ''
        self._playlist = {}
        self._m3u8_dict = {}
        self.local_video_path = ''
        self._video_filename = ''
        self._ffmpeg_path = ''
        self.video_resolution = 0
        self.video_size = 0
        self.realtime_show_file_size = False
        self.upload_succeed_flag = False
        self._danmu = False

        if self._settings['use_mobile_api']:
            err_print(sn, '解析模式', 'APP解析', display=False)
        else:
            err_print(sn, '解析模式', 'Web解析', display=False)

        if debug_mode:
            print('當前為debug模式')
        else:
            if self._settings['use_proxy']:  # 使用代理
                self.__init_proxy()
            self.__init_header()  # http header
            self.__get_src()  # 获取网页, 产生 self._src (BeautifulSoup)
            self.__get_title()  # 提取页面标题
            self.__get_bangumi_name()  # 提取本番名字
            self.__get_episode()  # 提取剧集码，str
            # 提取剧集列表，结构 {'episode': sn}，储存到 self._episode_list, sn 为 int, 考慮到 劇場版 sp 等存在, key 為 str
            self.__get_episode_list()

    def __init_proxy(self):
        if self._settings['use_gost']:
            # 需要使用 gost 的情况, 代理到 gost
            os.environ['HTTP_PROXY'] = 'http://127.0.0.1:' + self._gost_port
            os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:' + self._gost_port
        else:
            # 无需 gost 的情况
            os.environ['HTTP_PROXY'] = self._settings['proxy']
            os.environ['HTTPS_PROXY'] = self._settings['proxy']
        os.environ['NO_PROXY'] = "127.0.0.1,localhost"

    def renew(self):
        self.__get_src()
        self.__get_title()
        self.__get_bangumi_name()
        self.__get_episode()
        self.__get_episode_list()

    def get_sn(self):
        return self._sn

    def get_bangumi_name(self):
        if self._bangumi_name == '':
            self.__get_bangumi_name()
        return self._bangumi_name

    def get_episode(self):
        if self._episode == '':
            self.__get_episode()
        return self._episode

    def get_episode_list(self):
        if self._episode_list == {}:
            self.__get_episode_list()
        return self._episode_list

    def get_title(self):
        return self._title

    def get_filename(self):
        if self.video_resolution == 0:
            return self.__get_filename(self._settings['download_resolution'])
        else:
            return self.__get_filename(str(self.video_resolution))

    def __get_src(self):
        if self._settings['use_mobile_api']:
            self._src = self.__request(f'https://api.gamer.com.tw/mobile_app/anime/v2/video.php?sn={self._sn}', no_cookies=True).json()
        else:
            req = f'https://ani.gamer.com.tw/animeVideo.php?sn={self._sn}'
            f = self.__request(req, no_cookies=True)
            self._src = BeautifulSoup(f.content, "lxml")

    def __get_title(self):
        if self._settings['use_mobile_api']:
            try:
                self._title = self._src['data']['anime']['title']
            except KeyError:
                err_print(self._sn, 'ERROR: 該 sn 下真的有動畫？', status=1)
                self._episode_list = {}
                sys.exit(1)
        else:
            soup = self._src
            try:
                self._title = soup.find('div', 'anime_name').h1.string  # 提取标题（含有集数）
            except (TypeError, AttributeError):
                # 该sn下没有动画
                err_print(self._sn, 'ERROR: 該 sn 下真的有動畫？', status=1)
                self._episode_list = {}
                sys.exit(1)

    def __get_bangumi_name(self):
        self._bangumi_name = self._title.replace('[' + self.get_episode() + ']', '').strip()  # 提取番剧名（去掉集数后缀）
        self._bangumi_name = re.sub(r'\s+', ' ', self._bangumi_name)  # 去除重复空格

    def __get_episode(self):  # 提取集数

        def get_ep():
            # 20210719 动画疯的版本位置又瞎蹦跶
            # https://github.com/miyouzi/aniGamerPlus/issues/109
            # 先查看有沒有數字, 如果沒有再查看有沒有中括號, 如果都沒有直接放棄, 把集數填作 1
            self._episode = re.findall(r'\[\d*\.?\d* *\.?[A-Z,a-z]*(?:電影)?\]', self._title)
            if len(self._episode) > 0:
                self._episode = str(self._episode[0][1:-1])
            elif len(re.findall(r'\[.+?\]', self._title)) > 0:
                self._episode = re.findall(r'\[.+?\]', self._title)
                self._episode = str(self._episode[0][1:-1])
            else:
                self._episode = "1"

        # 20200320 发现多版本标签后置导致原集数提取方法失效
        # https://github.com/miyouzi/aniGamerPlus/issues/36
        # self._episode = re.findall(r'\[.+?\]', self._title)  # 非贪婪匹配
        # self._episode = str(self._episode[-1][1:-1])  # 考虑到 .5 集和 sp、ova 等存在，以str储存
        if self._settings['use_mobile_api']:
            get_ep()
        else:
            soup = self._src
            try:
                #  适用于存在剧集列表
                self._episode = str(soup.find('li', 'playing').a.string)
            except AttributeError:
                # 如果这个sn就一集, 不存在剧集列表的情况
                # https://github.com/miyouzi/aniGamerPlus/issues/36#issuecomment-605065988
                # self._episode = re.findall(r'\[.+?\]', self._title)  # 非贪婪匹配
                # self._episode = str(self._episode[0][1:-1])  # 考虑到 .5 集和 sp、ova 等存在，以str储存
                get_ep()

    def __get_episode_list(self):
        if self._settings['use_mobile_api']:
            for _type in self._src['data']['anime']['volumes']:
                for _sn in self._src['data']['anime']['volumes'][_type]:
                    if _type == '0': # 本篇
                        self._episode_list[str(_sn['volume'])] = int(_sn["video_sn"])
                    elif _type == '1': # 電影
                        self._episode_list['電影'] = int(_sn["video_sn"])
                    elif _type == '2': # 特別篇
                        self._episode_list[f'特別篇{_sn["volume"]}'] = int(_sn["video_sn"])
                    elif _type == '3': # 中文配音
                        self._episode_list[f'中文配音{_sn["volume"]}'] = int(_sn["video_sn"])
                    else: # 中文電影
                        self._episode_list['中文電影'] = int(_sn["video_sn"])
        else:
            try:
                a = self._src.find('section', 'season').find_all('a')
                p = self._src.find('section', 'season').find_all('p')
                # https://github.com/miyouzi/aniGamerPlus/issues/9
                # 样本 https://ani.gamer.com.tw/animeVideo.php?sn=10210
                # 20190413 动画疯将特别篇分离
                index_counter = {}  # 记录剧集数字重复次数, 用作列表类型的索引 ('本篇', '特別篇')
                if len(p) > 0:
                    p = list(map(lambda x: x.contents[0], p))
                for i in a:
                    sn = int(i['href'].replace('?sn=', ''))
                    ep = str(i.string)
                    if ep not in index_counter.keys():
                        index_counter[ep] = 0
                    if ep in self._episode_list.keys():
                        index_counter[ep] = index_counter[ep] + 1
                        ep = p[index_counter[ep]] + ep
                    self._episode_list[ep] = sn
            except AttributeError:
                # 当只有一集时，不存在剧集列表，self._episode_list 只有本身
                self._episode_list[self._episode] = self._sn

    def __init_header(self):
        # 伪装为浏览器
        host = 'ani.gamer.com.tw'
        origin = 'https://' + host
        ua = self._settings['ua']  # cookie 自动刷新需要 UA 一致
        ref = 'https://' + host + '/animeVideo.php?sn=' + str(self._sn)
        lang = 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.6'
        accept = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8'
        accept_encoding = 'gzip, deflate'
        cache_control = 'max-age=0'
        self._mobile_header = {
            "User-Agent": "Animad/1.12.5 (tw.com.gamer.android.animad; build: 222; Android 5.1.1) okHttp/4.4.0",
            "X-Bahamut-App-Android": "tw.com.gamer.android.animad",
            "X-Bahamut-App-Version": "222",
            "Accept-Encoding": "gzip",
            "Connection": "Keep-Alive"
        }
        self._web_header = {
                "user-agent": ua,
                "referer": ref,
                "accept-language": lang,
                "accept": accept,
                "accept-encoding": accept_encoding,
                "cache-control": cache_control,
                "origin": origin
            }
        if self._settings['use_mobile_api']:
            self._req_header = self._mobile_header
        else:
            self._req_header = self._web_header

    def __request(self, req, no_cookies=False, show_fail=True, max_retry=3, addition_header=None):
        # 设置 header
        current_header = self._req_header
        if addition_header is None:
            addition_header = {}
        if len(addition_header) > 0:
            for key in addition_header.keys():
                current_header[key] = addition_header[key]

        # 获取页面
        error_cnt = 0
        while True:
            try:
                if self._cookies and not no_cookies:
                    f = self._session.get(req, headers=current_header, cookies=self._cookies, timeout=10)
                else:
                    f = self._session.get(req, headers=current_header, cookies={}, timeout=10)
            except requests.exceptions.RequestException as e:
                if error_cnt >= max_retry >= 0:
                    raise TryTooManyTimeError('任務狀態: sn=' + str(self._sn) + ' 请求失败次数过多！请求链接：\n%s' % req)
                err_detail = 'ERROR: 请求失败！except：\n' + str(e) + '\n3s后重试(最多重试' + str(
                    max_retry) + '次)'
                if show_fail:
                    err_print(self._sn, '任務狀態', err_detail)
                time.sleep(3)
                error_cnt += 1
            else:
                break
        # 处理 cookie
        if not self._cookies:
            # 当实例中尚无 cookie, 则读取
            self._cookies = f.cookies.get_dict()
        elif 'nologinuser' not in self._cookies.keys() and 'BAHAID' not in self._cookies.keys():
            # 处理游客cookie
            if 'nologinuser' in f.cookies.get_dict().keys():
                # self._cookies['nologinuser'] = f.cookies.get_dict()['nologinuser']
                self._cookies = f.cookies.get_dict()
        else:  # 如果用户提供了 cookie, 则处理cookie刷新
            if 'set-cookie' in f.headers.keys():  # 发现server响应了set-cookie
                if 'deleted' in f.headers.get('set-cookie'):
                    # set-cookie刷新cookie只有一次机会, 如果其他线程先收到, 则此处会返回 deleted
                    # 等待其他线程刷新了cookie, 重新读入cookie

                    if self._settings['use_mobile_api'] and 'X-Bahamut-App-InstanceId' in self._req_header:
                        # 使用移动API将无法进行 cookie 刷新, 改回 header 刷新 cookie
                        self._req_header = self._web_header
                        self.__request('https://ani.gamer.com.tw/')  # 再次尝试获取新 cookie
                    else:
                        err_print(self._sn, '收到cookie重置響應', display=False)
                        time.sleep(2)
                        try_counter = 0
                        succeed_flag = False
                        while try_counter < 3:  # 尝试读三次, 不行就算了
                            old_BAHARUNE = self._cookies['BAHARUNE']
                            self._cookies = Config.read_cookie()
                            err_print(self._sn, '讀取cookie',
                                      'cookie.txt最後修改時間: ' + Config.get_cookie_time() + ' 第' + str(try_counter) + '次嘗試',
                                      display=False)
                            if old_BAHARUNE != self._cookies['BAHARUNE']:
                                # 新cookie读取成功 (因为有可能其他线程接到了新cookie)
                                succeed_flag = True
                                err_print(self._sn, '讀取cookie', '新cookie讀取成功', display=False)
                                break
                            else:
                                err_print(self._sn, '讀取cookie', '新cookie讀取失敗', display=False)
                                random_wait_time = random.uniform(2, 5)
                                time.sleep(random_wait_time)
                                try_counter = try_counter + 1
                        if not succeed_flag:
                            self._cookies = {}
                            err_print(0, '用戶cookie更新失敗! 使用游客身份訪問', status=1, no_sn=True)
                            Config.invalid_cookie()  # 将失效cookie更名

                        if self._settings['use_mobile_api'] and 'X-Bahamut-App-InstanceId' not in self._req_header:
                            # 即使切换 header cookie 也无法刷新, 那么恢复 header, 好歹广告只有 3s
                            self._req_header = self._mobile_header

                else:
                    # 本线程收到了新cookie
                    # 20220115 简化 cookie 刷新逻辑
                    err_print(self._sn, '收到新cookie', display=False)

                    self._cookies.update(f.cookies.get_dict())
                    Config.renew_cookies(self._cookies, log=False)

                    key_list_str = ', '.join(f.cookies.get_dict().keys())
                    err_print(self._sn, f'用戶cookie刷新 {key_list_str} ', display=False)

                    self.__request('https://ani.gamer.com.tw/')
                    # 20210724 动画疯一步到位刷新 Cookie
                    if 'BAHARUNE' in f.headers.get('set-cookie'):
                        err_print(0, '用戶cookie已更新', status=2, no_sn=True)

        return f

    def __get_m3u8_dict(self):
        # m3u8获取模块参考自 https://github.com/c0re100/BahamutAnimeDownloader
        def get_device_id():
            req = 'https://ani.gamer.com.tw/ajax/getdeviceid.php'
            f = self.__request(req)
            self._device_id = f.json()['deviceid']
            return self._device_id

        def get_playlist():
            if self._settings['use_mobile_api']:
                req = f'https://api.gamer.com.tw/mobile_app/anime/v2/m3u8.php?sn={str(self._sn)}&device={self._device_id}'
            else:
                req = 'https://ani.gamer.com.tw/ajax/m3u8.php?sn=' + str(self._sn) + '&device=' + self._device_id
            f = self.__request(req)
            self._playlist = f.json()

        def random_string(num):
            chars = 'abcdefghijklmnopqrstuvwxyz0123456789'
            random.seed(int(round(time.time() * 1000)))
            result = []
            for i in range(num):
                result.append(chars[random.randint(0, len(chars) - 1)])
            return ''.join(result)

        def gain_access():
            if self._settings['use_mobile_api']:
                req = f'https://ani.gamer.com.tw/ajax/token.php?adID=0&sn={str(self._sn)}&device={self._device_id}'
            else:
                req = 'https://ani.gamer.com.tw/ajax/token.php?adID=0&sn=' + str(
                    self._sn) + "&device=" + self._device_id + "&hash=" + random_string(12)
            # 返回基础信息, 用于判断是不是VIP
            return self.__request(req).json()

        def unlock():
            req = 'https://ani.gamer.com.tw/ajax/unlock.php?sn=' + str(self._sn) + "&ttl=0"
            f = self.__request(req)  # 无响应正文

        def check_lock():
            req = 'https://ani.gamer.com.tw/ajax/checklock.php?device=' + self._device_id + '&sn=' + str(self._sn)
            f = self.__request(req)

        def start_ad():
            if self._settings['use_mobile_api']:
                req = f"https://api.gamer.com.tw/mobile_app/anime/v1/stat_ad.php?schedule=-1&sn={str(self._sn)}"
            else:
                req = "https://ani.gamer.com.tw/ajax/videoCastcishu.php?sn=" + str(self._sn) + "&s=194699"
            f = self.__request(req)  # 无响应正文

        def skip_ad():
            if self._settings['use_mobile_api']:
                req = f"https://api.gamer.com.tw/mobile_app/anime/v1/stat_ad.php?schedule=-1&ad=end&sn={str(self._sn)}"
            else:
                req = "https://ani.gamer.com.tw/ajax/videoCastcishu.php?sn=" + str(self._sn) + "&s=194699&ad=end"
            f = self.__request(req)  # 无响应正文

        def video_start():
            req = "https://ani.gamer.com.tw/ajax/videoStart.php?sn=" + str(self._sn)
            f = self.__request(req)

        def check_no_ad(error_count=10):
            if error_count == 0:
                err_print(self._sn, '廣告去除失敗! 請向開發者提交 issue!', status=1)
                sys.exit(1)

            req = "https://ani.gamer.com.tw/ajax/token.php?sn=" + str(
                self._sn) + "&device=" + self._device_id + "&hash=" + random_string(12)
            f = self.__request(req)
            resp = f.json()
            if 'time' in resp.keys():
                if not resp['time'] == 1:
                    err_print(self._sn, '廣告似乎還沒去除, 追加等待2秒, 剩餘重試次數 ' + str(error_count), status=1)
                    time.sleep(2)
                    skip_ad()
                    video_start()
                    check_no_ad(error_count=error_count - 1)
                else:
                    # 通过广告检查
                    if error_count != 10:
                        ads_time = (10-error_count)*2 + ad_time + 2
                        err_print(self._sn, '通过廣告時間' + str(ads_time) + '秒, 記錄到配置檔案', status=2)
                        if self._settings['use_mobile_api']:
                            self._settings['mobile_ads_time'] = ads_time
                        else:
                            self._settings['ads_time'] = ads_time
                        Config.write_settings(self._settings)  # 保存到配置文件
            else:
                err_print(self._sn, '遭到動畫瘋地區限制, 你的IP可能不被動畫瘋認可!', status=1)
                sys.exit(1)

        def parse_playlist():
            req = self._playlist['src']
            f = self.__request(req, no_cookies=True, addition_header={'origin': 'https://ani.gamer.com.tw'})
            url_prefix = re.sub(r'playlist.+', '', self._playlist['src'])  # m3u8 URL 前缀
            m3u8_list = re.findall(r'=\d+x\d+\n.+', f.content.decode())  # 将包含分辨率和 m3u8 文件提取
            m3u8_dict = {}
            for i in m3u8_list:
                key = re.findall(r'=\d+x\d+', i)[0]  # 提取分辨率
                key = re.findall(r'x\d+', key)[0][1:]  # 提取纵向像素数，作为 key
                value = re.findall(r'.*chunklist.+', i)[0]  # 提取 m3u8 文件
                value = url_prefix + value  # 组成完整的 m3u8 URL
                m3u8_dict[key] = value
            self._m3u8_dict = m3u8_dict

        get_device_id()
        user_info = gain_access()
        if not self._settings['use_mobile_api']:
            unlock()
            check_lock()
            unlock()
            unlock()

        # 收到錯誤反饋
        # 可能是限制級動畫要求登陸
        if 'error' in user_info.keys():
            msg = '《' + self._title + '》 '
            msg = msg + 'code=' + str(user_info['error']['code']) + ' message: ' + user_info['error']['message']
            err_print(self._sn, '收到錯誤', msg, status=1)
            sys.exit(1)

        if not user_info['vip']:
            # 如果用户不是 VIP, 那么等待广告(20s)
            # 20200513 网站更新，最低广告更新时间从8s增加到20s https://github.com/miyouzi/aniGamerPlus/issues/41
            # 20200806 网站更新，最低广告更新时间从20s增加到25s https://github.com/miyouzi/aniGamerPlus/issues/55

            if self._settings['only_use_vip']:
                 err_print(self._sn, '非VIP','因為已設定只使用VIP下載，故強制停止', status=1, no_sn=True)
                 sys.exit(1)

            if self._settings['use_mobile_api']:
                ad_time = self._settings['mobile_ads_time']  # APP解析廣告解析時間不同
            else:
                ad_time = self._settings['ads_time']

            err_print(self._sn, '正在等待', '《' + self.get_title() + '》 由於不是VIP賬戶, 正在等待'+str(ad_time)+'s廣告時間')
            start_ad()
            time.sleep(ad_time)
            skip_ad()
        else:
            err_print(self._sn, '開始下載', '《' + self.get_title() + '》 識別到VIP賬戶, 立即下載')

        if not self._settings['use_mobile_api']:
            video_start()
            check_no_ad()
        get_playlist()
        parse_playlist()

    def get_m3u8_dict(self):
        if not self._m3u8_dict:
            self.__get_m3u8_dict()
        return self._m3u8_dict

    def __get_filename(self, resolution, without_suffix=False):
        # 处理剧集名补零
        if re.match(r'^[+-]?\d+(\.\d+){0,1}$', self._episode) and self._settings['zerofill'] > 1:
            # 正则考虑到了带小数点的剧集
            # 如果剧集名为数字, 且用户开启补零
            if re.match(r'^\d+\.\d+$', self._episode):
                # 如果是浮点数
                a = re.findall(r'^\d+\.', self._episode)[0][:-1]
                b = re.findall(r'\.\d+$', self._episode)[0]
                episode = '[' + a.zfill(self._settings['zerofill']) + b + ']'
            else:
                # 如果是整数
                episode = '[' + self._episode.zfill(self._settings['zerofill']) + ']'
        else:
            episode = '[' + self._episode + ']'

        if self._settings['add_bangumi_name_to_video_filename']:
            # 如果用户需要番剧名
            bangumi_name = self._settings['customized_video_filename_prefix'] \
                           + self._bangumi_name \
                           + self._settings['customized_bangumi_name_suffix']

            filename = bangumi_name + episode  # 有番剧名的文件名
        else:
            # 如果用户不要将番剧名添加到文件名
            filename = self._settings['customized_video_filename_prefix'] + episode

        # 添加分辨率后缀
        if self._settings['add_resolution_to_video_filename']:
            filename = filename + '[' + resolution + 'P]'

        if without_suffix:
            return filename  # 截止至清晰度的文件名, 用于 __get_temp_filename()

        # 添加用户后缀及扩展名
        filename = filename + self._settings['customized_video_filename_suffix'] \
                   + '.' + self._settings['video_filename_extension']
        legal_filename = Config.legalize_filename(filename)  # 去除非法字符
        filename = legal_filename
        return filename

    def __get_temp_filename(self, resolution, temp_suffix):
        filename = self.__get_filename(resolution, without_suffix=True)
        # temp_filename 为临时文件名，下载完成后更名正式文件名
        temp_filename = filename + self._settings['customized_video_filename_suffix'] + '.' + temp_suffix \
                        + '.' + self._settings['video_filename_extension']
        temp_filename = Config.legalize_filename(temp_filename)
        return temp_filename

    def __segment_download_mode(self, resolution=''):
        # 设定文件存放路径
        filename = self.__get_filename(resolution)
        merging_filename = self.__get_temp_filename(resolution, temp_suffix='MERGING')

        output_file = os.path.join(self._bangumi_dir, filename)  # 完整输出路径
        merging_file = os.path.join(self._temp_dir, merging_filename)

        url_path = os.path.split(self._m3u8_dict[resolution])[0]  # 用于构造完整 chunk 链接
        temp_dir = os.path.join(self._temp_dir, str(self._sn) + '-downloading-by-aniGamerPlus')  # 临时目录以 sn 命令
        if not os.path.exists(temp_dir):  # 创建临时目录
            os.makedirs(temp_dir)
        m3u8_path = os.path.join(temp_dir, str(self._sn) + '.m3u8')  # m3u8 存放位置
        m3u8_text = self.__request(self._m3u8_dict[resolution], no_cookies=True).text  # 请求 m3u8 文件
        with open(m3u8_path, 'w', encoding='utf-8') as f:  # 保存 m3u8 文件在本地
            f.write(m3u8_text)
            pass
        key_uri = re.search(r'(?<=AES-128,URI=")(.*)(?=")', m3u8_text).group()  # 把 key 的链接提取出来
        original_key_uri = key_uri

        if not re.match(r'http.+', key_uri):
            # https://github.com/miyouzi/aniGamerPlus/issues/46
            # 如果不是完整的URI
            key_uri = url_path + '/' + key_uri  # 组成完成的 URI

        m3u8_key_path = os.path.join(temp_dir, 'key.m3u8key')  # key 的存放位置
        with open(m3u8_key_path, 'wb') as f:  # 保存 key
            f.write(self.__request(key_uri, no_cookies=True).content)

        chunk_list = re.findall(r'media_b.+ts.*', m3u8_text)  # chunk

        limiter = threading.Semaphore(self._settings['multi_downloading_segment'])  # chunk 并发下载限制器
        total_chunk_num = len(chunk_list)
        finished_chunk_counter = 0
        failed_flag = False

        def download_chunk(uri):
            chunk_name = re.findall(r'media_b.+ts', uri)[0]  # chunk 文件名
            chunk_local_path = os.path.join(temp_dir, chunk_name)  # chunk 路径
            nonlocal failed_flag

            try:
                with open(chunk_local_path, 'wb') as f:
                    f.write(self.__request(uri, no_cookies=True,
                                           show_fail=False,
                                           max_retry=self._settings['segment_max_retry']).content)
            except TryTooManyTimeError:
                failed_flag = True
                err_print(self._sn, '下載狀態', 'Bad segment=' + chunk_name, status=1)
                limiter.release()
                sys.exit(1)
            except BaseException as e:
                failed_flag = True
                err_print(self._sn, '下載狀態', 'Bad segment=' + chunk_name + ' 發生未知錯誤: ' + str(e), status=1)
                limiter.release()
                sys.exit(1)

            # 显示完成百分比
            nonlocal finished_chunk_counter
            finished_chunk_counter = finished_chunk_counter + 1
            progress_rate = float(finished_chunk_counter / total_chunk_num * 100)
            progress_rate = round(progress_rate, 2)
            Config.tasks_progress_rate[int(self._sn)]['rate'] = progress_rate

            if self.realtime_show_file_size:
                sys.stdout.write('\r正在下載: sn=' + str(self._sn) + ' ' + filename + ' ' + str(progress_rate) + '%  ')
                sys.stdout.flush()
            limiter.release()

        if self.realtime_show_file_size:
            # 是否实时显示文件大小, 设计仅 cui 下载单个文件或线程数=1时适用
            sys.stdout.write('正在下載: sn=' + str(self._sn) + ' ' + filename)
            sys.stdout.flush()
        else:
            err_print(self._sn, '正在下載', filename + ' title=' + self._title)

        chunk_tasks_list = []
        for chunk in chunk_list:
            chunk_uri = url_path + '/' + chunk
            task = threading.Thread(target=download_chunk, args=(chunk_uri,))
            chunk_tasks_list.append(task)
            task.setDaemon(True)
            limiter.acquire()
            task.start()

        for task in chunk_tasks_list:  # 等待所有任务完成
            while True:
                if failed_flag:
                    err_print(self._sn, '下載失败', filename, status=1)
                    self.video_size = 0
                    return
                if task.is_alive():
                    time.sleep(1)
                else:
                    break

        # m3u8 本地化
        # replace('\\', '\\\\') 为转义win路径
        m3u8_text_local_version = m3u8_text.replace(original_key_uri, os.path.join(temp_dir, 'key.m3u8key')).replace('\\', '\\\\')
        for chunk in chunk_list:
            chunk_filename = re.findall(r'media_b.+ts', chunk)[0]  # chunk 文件名
            chunk_path = os.path.join(temp_dir, chunk_filename).replace('\\', '\\\\')  # chunk 本地路径
            m3u8_text_local_version = m3u8_text_local_version.replace(chunk, chunk_path)
        with open(m3u8_path, 'w', encoding='utf-8') as f:  # 保存本地化的 m3u8
            f.write(m3u8_text_local_version)

        if self.realtime_show_file_size:
            sys.stdout.write('\n')
            sys.stdout.flush()
        err_print(self._sn, '下載狀態', filename + ' 下載完成, 正在解密合并……')
        Config.tasks_progress_rate[int(self._sn)]['status'] = '下載完成'

        # 构造 ffmpeg 命令
        ffmpeg_cmd = [self._ffmpeg_path,
                      '-allowed_extensions', 'ALL',
                      '-i', m3u8_path,
                      '-c', 'copy', merging_file,
                      '-y']

        if self._settings['faststart_movflags']:
            # 将 metadata 移至视频文件头部
            # 此功能可以更快的在线播放视频
            ffmpeg_cmd[7:7] = iter(['-movflags', 'faststart'])

        if self._settings['audio_language']:
            if self._title.find('中文') == -1:
                ffmpeg_cmd[7:7] = iter(['-metadata:s:a:0', 'language=jpn'])
            else:
                ffmpeg_cmd[7:7] = iter(['-metadata:s:a:0', 'language=chi'])

        # 执行 ffmpeg
        run_ffmpeg = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        run_ffmpeg.communicate()
        # 记录文件大小，单位为 MB
        self.video_size = int(os.path.getsize(merging_file) / float(1024 * 1024))
        # 重命名
        err_print(self._sn, '下載狀態', filename + ' 解密合并完成, 本集 ' + str(self.video_size) + 'MB, 正在移至番劇目錄……')
        if os.path.exists(output_file):
            os.remove(output_file)

        if self._settings['use_copyfile_method']:
            shutil.copyfile(merging_file, output_file)  # 适配rclone挂载盘
            os.remove(merging_file)  # 刪除临时合并文件
        else:
            shutil.move(merging_file, output_file)  # 此方法在遇到rclone挂载盘时会出错

        # 删除临时目录
        shutil.rmtree(temp_dir, ignore_errors=True)

        self.local_video_path = output_file  # 记录保存路径, FTP上传用
        self._video_filename = filename  # 记录文件名, FTP上传用

        err_print(self._sn, '下載完成', filename, status=2)

    def __ffmpeg_download_mode(self, resolution=''):
        # 设定文件存放路径
        filename = self.__get_filename(resolution)
        downloading_filename = self.__get_temp_filename(resolution, temp_suffix='DOWNLOADING')

        output_file = os.path.join(self._bangumi_dir, filename)  # 完整输出路径
        downloading_file = os.path.join(self._temp_dir, downloading_filename)

        # 构造 ffmpeg 命令
        ffmpeg_cmd = [self._ffmpeg_path,
                      '-user_agent',
                      self._settings['ua'],
                      '-headers', "Origin: https://ani.gamer.com.tw",
                      '-i', self._m3u8_dict[resolution],
                      '-c', 'copy', downloading_file,
                      '-y']

        if os.path.exists(downloading_file):
            os.remove(downloading_file)  # 清理任务失败的尸体

        # subprocess.call(ffmpeg_cmd, creationflags=0x08000000)  # 仅windows
        run_ffmpeg = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, bufsize=204800, stderr=subprocess.PIPE)

        def check_ffmpeg_alive():
            # 应对ffmpeg卡死, 资源限速等，若 1min 中内文件大小没有增加超过 3M, 则判定卡死
            if self.realtime_show_file_size:  # 是否实时显示文件大小, 设计仅 cui 下载单个文件或线程数=1时适用
                sys.stdout.write('正在下載: sn=' + str(self._sn) + ' ' + filename)
                sys.stdout.flush()
            else:
                err_print(self._sn, '正在下載', filename + ' title=' + self._title)

            time.sleep(2)
            time_counter = 1
            pre_temp_file_size = 0
            while run_ffmpeg.poll() is None:

                if self.realtime_show_file_size:
                    # 实时显示文件大小
                    if os.path.exists(downloading_file):
                        size = os.path.getsize(downloading_file)
                        size = size / float(1024 * 1024)
                        size = round(size, 2)
                        sys.stdout.write(
                            '\r正在下載: sn=' + str(self._sn) + ' ' + filename + '    ' + str(size) + 'MB      ')
                        sys.stdout.flush()
                    else:
                        sys.stdout.write('\r正在下載: sn=' + str(self._sn) + ' ' + filename + '    文件尚未生成  ')
                        sys.stdout.flush()

                if time_counter % 60 == 0 and os.path.exists(downloading_file):
                    temp_file_size = os.path.getsize(downloading_file)
                    a = temp_file_size - pre_temp_file_size
                    if a < (3 * 1024 * 1024):
                        err_msg_detail = downloading_filename + ' 在一分钟内仅增加' + str(
                            int(a / float(1024))) + 'KB 判定为卡死, 任务失败!'
                        err_print(self._sn, '下載失败', err_msg_detail, status=1)
                        run_ffmpeg.kill()
                        return
                    pre_temp_file_size = temp_file_size
                time.sleep(1)
                time_counter = time_counter + 1

        ffmpeg_checker = threading.Thread(target=check_ffmpeg_alive)  # 检查线程
        ffmpeg_checker.setDaemon(True)  # 如果 Anime 线程被 kill, 检查进程也应该结束
        ffmpeg_checker.start()
        run = run_ffmpeg.communicate()
        return_str = str(run[1])

        if self.realtime_show_file_size:
            sys.stdout.write('\n')
            sys.stdout.flush()

        if run_ffmpeg.returncode == 0 and (return_str.find('Failed to open segment') < 0):
            # 执行成功 (ffmpeg正常结束, 每个分段都成功下载)
            if os.path.exists(output_file):
                os.remove(output_file)
            # 记录文件大小，单位为 MB
            self.video_size = int(os.path.getsize(downloading_file) / float(1024 * 1024))
            err_print(self._sn, '下載狀態', filename + '本集 ' + str(self.video_size) + 'MB, 正在移至番劇目錄……')

            if self._settings['use_copyfile_method']:
                shutil.copyfile(downloading_file, output_file)  # 适配rclone挂载盘
                os.remove(downloading_file)  # 刪除临时合并文件
            else:
                shutil.move(downloading_file, output_file)  # 此方法在遇到rclone挂载盘时会出错

            self.local_video_path = output_file  # 记录保存路径, FTP上传用
            self._video_filename = filename  # 记录文件名, FTP上传用
            err_print(self._sn, '下載完成', filename, status=2)
        else:
            err_msg_detail = filename + ' ffmpeg_return_code=' + str(
                run_ffmpeg.returncode) + ' Bad segment=' + str(return_str.find('Failed to open segment'))
            err_print(self._sn, '下載失败', err_msg_detail, status=1)

    def download(self, resolution='', save_dir='', bangumi_tag='', realtime_show_file_size=False, rename='', classify=True):
        self.realtime_show_file_size = realtime_show_file_size
        if not resolution:
            resolution = self._settings['download_resolution']

        if save_dir:
            self._bangumi_dir = save_dir  # 用于 cui 用户指定下载在当前目录

        if rename:
            bangumi_name = self._bangumi_name
            # 适配多版本的番剧
            version = re.findall(r'\[.+?\]', self._bangumi_name)  # 在番剧名中寻找是否存在多版本标记
            if version:  # 如果这个番剧是多版本的
                version = str(version[-1])  # 提取番剧版本名称
                bangumi_name = bangumi_name.replace(version, '').strip()  # 没有版本名称的 bangumi_name, 且头尾无空格
            # 如果设定重命名了番剧
            # 将其中的番剧名换成用户设定的, 且不影响版本号后缀(如果有)
            self._title = self._title.replace(bangumi_name, rename)
            self._bangumi_name = self._bangumi_name.replace(bangumi_name, rename)

        # 下载任务开始
        Config.tasks_progress_rate[int(self._sn)] = {'rate': 0, 'filename': '《'+self.get_title()+'》', 'status': '正在解析'}

        try:
            self.__get_m3u8_dict()  # 获取 m3u8 列表
        except TryTooManyTimeError:
            # 如果在获取 m3u8 过程中发生意外, 则取消此次下载
            err_print(self._sn, '下載狀態', '獲取 m3u8 失敗!', status=1)
            self.video_size = 0
            return

        check_ffmpeg = subprocess.Popen('ffmpeg -h', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if check_ffmpeg.stdout.readlines():  # 查找 ffmpeg 是否已放入系统 path
            self._ffmpeg_path = 'ffmpeg'
        else:
            # print('没有在系统PATH中发现ffmpeg，尝试在所在目录寻找')
            if 'Windows' in platform.system():
                self._ffmpeg_path = os.path.join(self._working_dir, 'ffmpeg.exe')
            else:
                self._ffmpeg_path = os.path.join(self._working_dir, 'ffmpeg')
            if not os.path.exists(self._ffmpeg_path):
                err_print(0, '本項目依賴於ffmpeg, 但ffmpeg未找到', status=1, no_sn=True)
                raise FileNotFoundError  # 如果本地目录下也没有找到 ffmpeg 则丢出异常

        # 创建存放番剧的目录，去除非法字符
        if bangumi_tag:  # 如果指定了番剧分类
            self._bangumi_dir = os.path.join(self._bangumi_dir, Config.legalize_filename(bangumi_tag))
        if classify:  # 控制是否建立番剧文件夹
            self._bangumi_dir = os.path.join(self._bangumi_dir, Config.legalize_filename(self._bangumi_name))
        if not os.path.exists(self._bangumi_dir):
            try:
                os.makedirs(self._bangumi_dir)  # 按番剧创建文件夹分类
            except FileExistsError as e:
                err_print(self._sn, '下載狀態', '慾創建的番劇資料夾已存在 ' + str(e), display=False)

        if not os.path.exists(self._temp_dir):  # 建立临时文件夹
            try:
                os.makedirs(self._temp_dir)
            except FileExistsError as e:
                err_print(self._sn, '下載狀態', '慾創建的臨時資料夾已存在 ' + str(e), display=False)

        # 如果不存在指定清晰度，则选取最近可用清晰度
        if resolution not in self._m3u8_dict.keys():
            if self._settings['lock_resolution']:
                # 如果用户设定锁定清晰度, 則下載取消
                err_msg_detail = '指定清晰度不存在, 因當前鎖定了清晰度, 下載取消. 可用的清晰度: ' + 'P '.join(self._m3u8_dict.keys()) + 'P'
                err_print(self._sn, '任務狀態', err_msg_detail, status=1)
                return

            resolution_list = map(lambda x: int(x), self._m3u8_dict.keys())
            resolution_list = list(resolution_list)
            flag = 9999
            closest_resolution = 0
            for i in resolution_list:
                a = abs(int(resolution) - i)
                if a < flag:
                    flag = a
                    closest_resolution = i
            # resolution_list.sort()
            # resolution = str(resolution_list[-1])  # 选取最高可用清晰度
            resolution = str(closest_resolution)
            err_msg_detail = '指定清晰度不存在, 選取最近可用清晰度: ' + resolution + 'P'
            err_print(self._sn, '任務狀態', err_msg_detail, status=1)
        self.video_resolution = int(resolution)

        # 解析完成, 开始下载
        Config.tasks_progress_rate[int(self._sn)]['status'] = '正在下載'
        Config.tasks_progress_rate[int(self._sn)]['filename'] = self.get_filename()

        if self._settings['segment_download_mode']:
            self.__segment_download_mode(resolution)
        else:
            self.__ffmpeg_download_mode(resolution)

        # 任务完成, 从任务进度表中删除
        del Config.tasks_progress_rate[int(self._sn)]

        # 下載彈幕
        if self._danmu:
            full_filename = os.path.join(self._bangumi_dir, self.__get_filename(resolution)).replace('.' + self._settings['video_filename_extension'], '.ass')
            d = Danmu(self._sn, full_filename, Config.read_cookie())
            d.download(self._settings['danmu_ban_words'])

        # 推送 CQ 通知
        if self._settings['coolq_notify']:
            try:
                msg = '【aniGamerPlus消息】\n《' + self._video_filename + '》下载完成, 本集 ' + str(self.video_size) + ' MB'
                if self._settings['coolq_settings']['message_suffix']:
                    # 追加用户信息
                    msg = msg + '\n\n' + self._settings['coolq_settings']['message_suffix']

                for query in self._settings['coolq_settings']['query']:
                    if '?' not in query:
                        query = query + '?'
                    else:
                        query = query + '&'
                    req = query + self._settings['coolq_settings']['msg_argument_name'] + '=' + quote(msg)
                    self.__request(req, no_cookies=True)
            except BaseException as e:
                err_print(self._sn, 'CQ NOTIFY ERROR', 'Exception: ' + str(e), status=1)

        # 推送 TG 通知
        if self._settings['telebot_notify']:
            try:
                msg = '【aniGamerPlus消息】\n《' + self._video_filename + '》下载完成, 本集 ' + str(self.video_size) + ' MB'
                vApiTokenTelegram = self._settings['telebot_token']
                try:
                    if self._settings['telebot_use_chat_id']: #手动指定发送目标
                        chat_id = self._settings['telebot__chat_id']
                    else:
                        apiMethod = "getUpdates"
                        api_url = "https://api.telegram.org/bot" + vApiTokenTelegram + "/" + apiMethod # Telegram bot api url
                        response = self.__request(api_url).json()
                        chat_id = response["result"][0]["message"]["chat"]["id"] # Get chat id
                    try:
                        api_method = "sendMessage"
                        req = "https://api.telegram.org/bot" \
                                + vApiTokenTelegram \
                                + "/" \
                                + api_method \
                                + "?chat_id=" \
                                + str(chat_id) \
                                + "&text=" \
                                + str(msg)
                        self.__request(req, no_cookies=True) # Send msg to telegram bot
                    except:
                        err_print(self._sn, 'TG NOTIFY ERROR', "Exception: Send msg error\nReq: " + req, status=1) # Send mag error
                except:
                    err_print(self._sn, 'TG NOTIFY ERROR', "Exception: Invalid access token\nToken: " + vApiTokenTelegram, status=1) # Cannot find chat id
            except BaseException as e:
                err_print(self._sn, 'TG NOTIFY ERROR', 'Exception: ' + str(e), status=1)

        # 推送通知至 Discord
        if self._settings['discord_notify']:
            try:
                msg = '【aniGamerPlus消息】\n《' + self._video_filename + '》下載完成，本集 ' + str(self.video_size) + ' MB'
                url = self._settings['discord_token']
                data = {
                    'content': None,
                    'embeds': [{
                        'title': '下載完成',
                        'description': msg,
                        'color': '5814783',
                        'author': {
                            'name': '🔔 動畫瘋'
                        }}]}
                r = requests.post(url, json=data)
                if r.status_code != 204:
                    err_print(self._sn, 'discord NOTIFY ERROR', "Exception: Send msg error\nReq: " + r.text, status=1)
            except:
                err_print(self._sn, 'Discord NOTIFY UNKNOWN ERROR', 'Exception: ' + str(e), status=1)

        # plex 自動更新媒體庫
        if self._settings['plex_refresh']:
            try:
                url = 'https://{plex_url}/library/sections/{plex_section}/refresh?X-Plex-Token={plex_token}'.format(
                    plex_url=self._settings['plex_url'],
                    plex_section=self._settings['plex_section'],
                    plex_token=self._settings['plex_token']
                )
                r = requests.get(url)
                if r.status_code != 200:
                    err_print(self._sn, 'Plex auto Refresh ERROR', status=1)
            except:
                err_print(self._sn, 'Plex auto Refresh UNKNOWN ERROR', 'Exception: ' + str(e), status=1)

    def upload(self, bangumi_tag='', debug_file=''):
        first_connect = True  # 标记是否是第一次连接, 第一次连接会删除临时缓存目录
        tmp_dir = str(self._sn) + '-uploading-by-aniGamerPlus'

        if debug_file:
            self.local_video_path = debug_file

        if not os.path.exists(self.local_video_path):  # 如果文件不存在,直接返回失败
            return self.upload_succeed_flag

        if not self._video_filename:  # 用于仅上传, 将文件名提取出来
            self._video_filename = os.path.split(self.local_video_path)[-1]

        socket.setdefaulttimeout(20)  # 超时时间20s

        if self._settings['ftp']['tls']:
            ftp = FTP_TLS()  # FTP over TLS
        else:
            ftp = FTP()

        def connect_ftp(show_err=True):
            ftp.encoding = 'utf-8'  # 解决中文乱码
            err_counter = 0
            connect_flag = False
            while err_counter <= 3:
                try:
                    ftp.connect(self._settings['ftp']['server'], self._settings['ftp']['port'])  # 连接 FTP
                    ftp.login(self._settings['ftp']['user'], self._settings['ftp']['pwd'])  # 登陆
                    connect_flag = True
                    break
                except ftplib.error_temp as e:
                    if show_err:
                        if 'Too many connections' in str(e):
                            detail = self._video_filename + ' 当前FTP連接數過多, 5分鐘后重試, 最多重試三次: ' + str(e)
                            err_print(self._sn, 'FTP狀態', detail, status=1)
                        else:
                            detail = self._video_filename + ' 連接FTP時發生錯誤, 5分鐘后重試, 最多重試三次: ' + str(e)
                            err_print(self._sn, 'FTP狀態', detail, status=1)
                    err_counter = err_counter + 1
                    for i in range(5 * 60):
                        time.sleep(1)
                except BaseException as e:
                    if show_err:
                        detail = self._video_filename + ' 在連接FTP時發生無法處理的異常:' + str(e)
                        err_print(self._sn, 'FTP狀態', detail, status=1)
                    break

            if not connect_flag:
                err_print(self._sn, '上傳失败', self._video_filename, status=1)
                return connect_flag  # 如果连接失败, 直接放弃

            ftp.voidcmd('TYPE I')  # 二进制模式

            if self._settings['ftp']['cwd']:
                try:
                    ftp.cwd(self._settings['ftp']['cwd'])  # 进入用户指定目录
                except ftplib.error_perm as e:
                    if show_err:
                        err_print(self._sn, 'FTP狀態', '進入指定FTP目錄時出錯: ' + str(e), status=1)

            if bangumi_tag:  # 番剧分类
                try:
                    ftp.cwd(bangumi_tag)
                except ftplib.error_perm:
                    try:
                        ftp.mkd(bangumi_tag)
                        ftp.cwd(bangumi_tag)
                    except ftplib.error_perm as e:
                        if show_err:
                            err_print(self._sn, 'FTP狀態', '創建目錄番劇目錄時發生異常, 你可能沒有權限創建目錄: ' + str(e), status=1)

            # 归类番剧
            ftp_bangumi_dir = Config.legalize_filename(self._bangumi_name)  # 保证合法
            try:
                ftp.cwd(ftp_bangumi_dir)
            except ftplib.error_perm:
                try:
                    ftp.mkd(ftp_bangumi_dir)
                    ftp.cwd(ftp_bangumi_dir)
                except ftplib.error_perm as e:
                    if show_err:
                        detail = '你可能沒有權限創建目錄(用於分類番劇), 視頻文件將會直接上傳, 收到異常: ' + str(e)
                        err_print(self._sn, 'FTP狀態', detail, status=1)

            # 删除旧的临时文件夹
            nonlocal first_connect
            if first_connect:  # 首次连接
                remove_dir(tmp_dir)
                first_connect = False  # 标记第一次连接已完成

            # 创建新的临时文件夹
            # 创建临时文件夹是因为 pure-ftpd 在续传时会将文件名更改成不可预测的名字
            # 正常中斷传输会把名字改回来, 但是意外掉线不会, 为了处理这种情况
            # 需要获取 pure-ftpd 未知文件名的续传缓存文件, 为了不和其他视频的缓存文件混淆, 故建立一个临时文件夹
            try:
                ftp.cwd(tmp_dir)
            except ftplib.error_perm:
                ftp.mkd(tmp_dir)
                ftp.cwd(tmp_dir)

            return connect_flag

        def exit_ftp(show_err=True):
            try:
                ftp.quit()
            except BaseException as e:
                if show_err and self._settings['ftp']['show_error_detail']:
                    err_print(self._sn, 'FTP狀態', '將强制關閉FTP連接, 因爲在退出時收到異常: ' + str(e))
                ftp.close()

        def remove_dir(dir_name):
            try:
                ftp.rmd(dir_name)
            except ftplib.error_perm as e:
                if 'Directory not empty' in str(e):
                    # 如果目录非空, 则删除内部文件
                    ftp.cwd(dir_name)
                    del_all_files()
                    ftp.cwd('..')
                    ftp.rmd(dir_name)  # 删完内部文件, 删除文件夹
                elif 'No such file or directory' in str(e):
                    pass
                else:
                    # 其他非空目录报错
                    raise e

        def del_all_files():
            try:
                for file_need_del in ftp.nlst():
                    if not re.match(r'^(\.|\.\.)$', file_need_del):
                        ftp.delete(file_need_del)
                        # print('删除了文件: ' + file_need_del)
            except ftplib.error_perm as resp:
                if not str(resp) == "550 No files found":
                    raise

        if not connect_ftp():  # 连接 FTP
            return self.upload_succeed_flag  # 如果连接失败

        err_print(self._sn, '正在上傳', self._video_filename + ' title=' + self._title + '……')
        try_counter = 0
        video_filename = self._video_filename  # video_filename 将可能会储存 pure-ftpd 缓存文件名
        max_try_num = self._settings['ftp']['max_retry_num']
        local_size = os.path.getsize(self.local_video_path)  # 本地文件大小
        while try_counter <= max_try_num:
            try:
                if try_counter > 0:
                    # 传输遭中断后处理
                    detail = self._video_filename + ' 发生异常, 重連FTP, 續傳文件, 將重試最多' + str(max_try_num) + '次……'
                    err_print(self._sn, '上傳狀態', detail, status=1)
                    if not connect_ftp():  # 重连
                        return self.upload_succeed_flag

                    # 解决操蛋的 Pure-Ftpd 续传一次就改名导致不能再续传问题.
                    # 一般正常关闭文件传输 Pure-Ftpd 会把名字改回来, 但是遇到网络意外中断, 那么就不会改回文件名, 留着临时文件名
                    # 本段就是处理这种情况
                    try:
                        for i in ftp.nlst():
                            if 'pureftpd-upload' in i:
                                # 找到 pure-ftpd 缓存, 直接抓缓存来续传
                                video_filename = i
                    except ftplib.error_perm as resp:
                        if not str(resp) == "550 No files found":  # 非文件不存在错误, 抛出异常
                            raise
                # 断点续传
                try:
                    # 需要 FTP Server 支持续传
                    ftp_binary_size = ftp.size(video_filename)  # 远程文件字节数
                except ftplib.error_perm:
                    # 如果不存在文件
                    ftp_binary_size = 0
                except OSError:
                    try_counter = try_counter + 1
                    continue

                ftp.voidcmd('TYPE I')  # 二进制模式
                conn = ftp.transfercmd('STOR ' + video_filename, ftp_binary_size)  # ftp服务器文件名和offset偏移地址
                with open(self.local_video_path, 'rb') as f:
                    f.seek(ftp_binary_size)  # 从断点处开始读取
                    while True:
                        block = f.read(1048576)  # 读取1M
                        conn.sendall(block)  # 送出 block
                        if not block:
                            time.sleep(3)  # 等待一下, 让sendall()完成
                            break

                conn.close()

                err_print(self._sn, '上傳狀態', '檢查遠端文件大小是否與本地一致……')
                exit_ftp(False)
                connect_ftp(False)
                # 不重连的话, 下面查询远程文件大小会返回 None, 懵逼...
                # sendall()没有完成将会 500 Unknown command
                err_counter = 0
                remote_size = 0
                while err_counter < 3:
                    try:
                        remote_size = ftp.size(video_filename)  # 远程文件大小
                        break
                    except ftplib.error_perm as e1:
                        err_print(self._sn, 'FTP狀態', 'ftplib.error_perm: ' + str(e1))
                        remote_size = 0
                        break
                    except OSError as e2:
                        err_print(self._sn, 'FTP狀態', 'OSError: ' + str(e2))
                        remote_size = 0
                        connect_ftp(False)  # 掉线重连
                        err_counter = err_counter + 1

                if remote_size is None:
                    err_print(self._sn, 'FTP狀態', 'remote_size is None')
                    remote_size = 0
                # 远程文件大小获取失败, 可能文件不存在或者抽风
                # 那上面获取远程字节数将会是0, 导致重新下载, 那么此时应该清空缓存目录下的文件
                # 避免后续找错文件续传
                if remote_size == 0:
                    del_all_files()

                if remote_size != local_size:
                    # 如果远程文件大小与本地不一致
                    # print('remote_size='+str(remote_size))
                    # print('local_size ='+str(local_size))
                    detail = self._video_filename + ' 在遠端為' + str(
                        round(remote_size / float(1024 * 1024), 2)) + 'MB' + ' 與本地' + str(
                        round(local_size / float(1024 * 1024), 2)) + 'MB 不一致! 將重試最多' + str(max_try_num) + '次'
                    err_print(self._sn, '上傳狀態', detail, status=1)
                    try_counter = try_counter + 1
                    continue  # 续传

                # 顺利上传完后
                ftp.cwd('..')  # 返回上级目录, 即退出临时目录
                try:
                    # 如果同名文件存在, 则删除
                    ftp.size(self._video_filename)
                    ftp.delete(self._video_filename)
                except ftplib.error_perm:
                    pass
                ftp.rename(tmp_dir + '/' + video_filename, self._video_filename)  # 将视频从临时文件移出, 顺便重命名
                remove_dir(tmp_dir)  # 删除临时目录
                self.upload_succeed_flag = True  # 标记上传成功
                break

            except ConnectionResetError as e:
                if self._settings['ftp']['show_error_detail']:
                    detail = self._video_filename + ' 在上傳過程中網絡被重置, 將重試最多' + str(max_try_num) + '次' + ', 收到異常: ' + str(e)
                    err_print(self._sn, '上傳狀態', detail, status=1)
                try_counter = try_counter + 1
            except TimeoutError as e:
                if self._settings['ftp']['show_error_detail']:
                    detail = self._video_filename + ' 在上傳過程中超時, 將重試最多' + str(max_try_num) + '次, 收到異常: ' + str(e)
                    err_print(self._sn, '上傳狀態', detail, status=1)
                try_counter = try_counter + 1
            except socket.timeout as e:
                if self._settings['ftp']['show_error_detail']:
                    detail = self._video_filename + ' 在上傳過程socket超時, 將重試最多' + str(max_try_num) + '次, 收到異常: ' + str(e)
                    err_print(self._sn, '上傳狀態', detail, status=1)
                try_counter = try_counter + 1

        if not self.upload_succeed_flag:
            err_print(self._sn, '上傳失敗', self._video_filename + ' 放棄上傳!', status=1)
            exit_ftp()
            return self.upload_succeed_flag

        err_print(self._sn, '上傳完成', self._video_filename, status=2)
        exit_ftp()  # 登出 FTP
        return self.upload_succeed_flag

    def get_info(self):
        err_print(self._sn, '顯示資訊')
        indent = '                    '
        err_print(0, indent+'影片標題:', '\"' + self.get_title() + '\"', no_sn=True, display_time=False)
        err_print(0, indent+'番劇名稱:', '\"' + self.get_bangumi_name() + '\"', no_sn=True, display_time=False)
        err_print(0, indent+'劇集標題:', '\"' + self.get_episode() + '\"', no_sn=True, display_time=False)
        err_print(0, indent+'参考檔名:', '\"' + self.get_filename() + '\"', no_sn=True, display_time=False)
        err_print(0, indent+'可用解析度', 'P '.join(self.get_m3u8_dict().keys()) + 'P\n', no_sn=True, display_time=False)

    def enable_danmu(self):
        self._danmu = True

    def set_resolution(self, resolution):
        self.video_resolution = int(resolution)


if __name__ == '__main__':
    pass
