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
            err_print(sn, '解析模式', 'APP 解析', display=False)
        else:
            err_print(sn, '解析模式', 'Web 解析', display=False)

        if debug_mode:
            print('當前為debug模式')
        else:
            if self._settings['use_proxy']:  # 使用代理
                self.__init_proxy()
            self.__init_header()  # http header
            self.__get_src()  # 獲取網頁, 產生 self._src (BeautifulSoup)
            self.__get_title()  # 提取頁面標題
            self.__get_bangumi_name()  # 提取本番名字
            self.__get_episode()  # 提取劇集碼，str
            # 提取劇集列表，結構 {'episode': sn}，儲存到 self._episode_list, sn 為 int, 考慮到 劇場版 sp 等存在, key 為 str
            self.__get_episode_list()

    def __init_proxy(self):
        if self._settings['use_gost']:
            # 需要使用 gost 的情況，代理到 gost
            os.environ['HTTP_PROXY'] = 'http://127.0.0.1:' + self._gost_port
            os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:' + self._gost_port
        else:
            # 無需 gost 的情況
            os.environ['HTTP_PROXY'] = self._settings['proxy']
            os.environ['HTTPS_PROXY'] = self._settings['proxy']
        os.environ['NO_PROXY'] = '127.0.0.1,localhost'

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
            self._src = self.__request(f'https://api.gamer.com.tw/mobile_app/anime/v1/video.php?sn={self._sn}', no_cookies=True).json()
        else:
            req = f'https://ani.gamer.com.tw/animeVideo.php?sn={self._sn}'
            f = self.__request(req, no_cookies=True)
            self._src = BeautifulSoup(f.content, "lxml")

    def __get_title(self):
        if self._settings['use_mobile_api']:
            try:
                self._title = self._src['anime']['title']
            except KeyError:
                err_print(self._sn, 'ERROR：該 sn 下真的有動畫？', status=1)
                self._episode_list = {}
                sys.exit(1)
        else:
            soup = self._src
            try:
                self._title = soup.find('div', 'anime_name').h1.string  # 提取標題（含有集數）
            except (TypeError, AttributeError):
                # 該sn下沒有動畫
                err_print(self._sn, 'ERROR：該 sn 下真的有動畫？', status=1)
                self._episode_list = {}
                sys.exit(1)

    def __get_bangumi_name(self):
        self._bangumi_name = self._title.replace('[' + self.get_episode() + ']', '').strip()  # 提取番劇名（去掉集數字尾）
        self._bangumi_name = re.sub(r'\s+', ' ', self._bangumi_name)  # 去除重複空格

    def __get_episode(self):  # 提取集數

        def get_ep():
            # 20210719 動畫瘋的版本位置又瞎蹦躂
            # https://github.com/miyouzi/aniGamerPlus/issues/109
            # 先檢視有沒有數字, 如果沒有再檢視有沒有中括號, 如果都沒有直接放棄, 把集數填作 1
            self._episode = re.findall(r'\[\d*\.?\d* *\.?[A-Z,a-z]*(?:電影)?\]', self._title)
            if len(self._episode) > 0:
                self._episode = str(self._episode[0][1:-1])
            elif len(re.findall(r'\[.+?\]', self._title)) > 0:
                self._episode = re.findall(r'\[.+?\]', self._title)
                self._episode = str(self._episode[0][1:-1])
            else:
                self._episode = "1"

        # 20200320 發現多版本標籤後置導致原集數提取方法失效
        # https://github.com/miyouzi/aniGamerPlus/issues/36
        # self._episode = re.findall(r'\[.+?\]', self._title)  # 非貪婪匹配
        # self._episode = str(self._episode[-1][1:-1])  # 考慮到 .5 集和 sp、ova 等存在，以 str 儲存
        if self._settings['use_mobile_api']:
            get_ep()
        else:
            soup = self._src
            try:
                #  適用於存在劇集列表
                self._episode = str(soup.find('li', 'playing').a.string)
            except AttributeError:
                # 如果這個 sn 就一集，不存在劇集列表的情況
                # https://github.com/miyouzi/aniGamerPlus/issues/36#issuecomment-605065988
                # self._episode = re.findall(r'\[.+?\]', self._title)  # 非貪婪匹配
                # self._episode = str(self._episode[0][1:-1])  # 考慮到 .5 集和 sp、ova 等存在，以 str 儲存
                get_ep()

    def __get_episode_list(self):
        if self._settings['use_mobile_api']:
            for _type in self._src['anime']['volumes']:
                for _sn in self._src['anime']['volumes'][_type]:
                    if _type == '0':
                        self._episode_list[str(_sn['volume'])] = int(_sn["video_sn"])
                    elif _type == '1' or _type == '4':
                        self._episode_list[self._src["videoTypeList"][int(_type)]["name"]] = int(_sn['video_sn'])
                    else:
                        self._episode_list[f'{self._src["videoTypeList"][int(_type)]["name"]} {_sn["volume"]}'] = int(_sn['video_sn'])
        else:
            try:
                a = self._src.find('section', 'season').find_all('a')
                p = self._src.find('section', 'season').find_all('p')
                # https://github.com/miyouzi/aniGamerPlus/issues/9
                # 樣本 https://ani.gamer.com.tw/animeVideo.php?sn=10210
                # 20190413 動畫瘋將特別篇分離
                index_counter = {}  # 記錄劇集數字重複次數, 用作列表型別的索引 ('本篇', '特別篇')
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
                # 當只有一集時，不存在劇集列表，self._episode_list 只有本身
                self._episode_list[self._episode] = self._sn

    def __init_header(self):
        # 偽裝為瀏覽器
        host = 'ani.gamer.com.tw'
        origin = 'https://' + host
        ua = self._settings['ua']  # cookie 自動重新整理需要 UA 一致
        ref = 'https://' + host + '/animeVideo.php?sn=' + str(self._sn)
        lang = 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.6'
        accept = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8'
        accept_encoding = 'gzip, deflate'
        cache_control = 'max-age=0'
        self._mobile_header = {
            "User-Agent": "Bahadroid (https://www.gamer.com.tw/)",
            "X-Bahamut-App-InstanceId": "cAJB-HprGUg",
            "X-Bahamut-App-Android": "tw.com.gamer.android.animad",
            "X-Bahamut-App-Version": "177",
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
        # 設定 header
        current_header = self._req_header
        if addition_header is None:
            addition_header = {}
        if len(addition_header) > 0:
            for key in addition_header.keys():
                current_header[key] = addition_header[key]

        # 獲取頁面
        error_cnt = 0
        while True:
            try:
                if self._cookies and not no_cookies:
                    f = self._session.get(req, headers=current_header, cookies=self._cookies, timeout=10)
                else:
                    f = self._session.get(req, headers=current_header, cookies={}, timeout=10)
            except requests.exceptions.RequestException as e:
                if error_cnt >= max_retry >= 0:
                    raise TryTooManyTimeError('任務狀態：sn=' + str(self._sn) + ' 請求失敗次數過多！請求連結：\n%s' % req)
                err_detail = 'ERROR：請求失敗：except：\n' + str(e) + '\n3s 後重試 （最多重試' + str(
                    max_retry) + '次）'
                if show_fail:
                    err_print(self._sn, '任務狀態', err_detail)
                time.sleep(3)
                error_cnt += 1
            else:
                break
        # 處理 cookie
        if not self._cookies:
            # 當例項中尚無 cookie，則讀取
            self._cookies = f.cookies.get_dict()
        elif 'nologinuser' not in self._cookies.keys() and 'BAHAID' not in self._cookies.keys():
            # 處理訪客 cookie
            if 'nologinuser' in f.cookies.get_dict().keys():
                # self._cookies['nologinuser'] = f.cookies.get_dict()['nologinuser']
                self._cookies = f.cookies.get_dict()
        else:  # 如果使用者提供了 cookie，則處理 cookie 重新整理
            if 'set-cookie' in f.headers.keys():  # 發現 server 響應了 set-cookie
                if 'deleted' in f.headers.get('set-cookie'):
                    # set-cookie重新整理cookie只有一次機會, 如果其他執行緒先收到, 則此處會返回 deleted
                    # 等待其他執行緒重新整理了cookie, 重新讀入cookie

                    if self._settings['use_mobile_api'] and 'X-Bahamut-App-InstanceId' in self._req_header:
                        # 使用 APP API 將無法進行 cookie 重新整理，改回 header 重新整理 cookie
                        self._req_header = self._web_header
                        self.__request('https://ani.gamer.com.tw/')  # 再次嘗試獲取新 cookie
                    else:
                        err_print(self._sn, '收到 cookie 重置回應', display=False)
                        time.sleep(2)
                        try_counter = 0
                        succeed_flag = False
                        while try_counter < 3:  # 嘗試讀三次，不行就算了
                            old_BAHARUNE = self._cookies['BAHARUNE']
                            self._cookies = Config.read_cookie()
                            err_print(self._sn, '讀取 cookie',
                                      'cookie.txt 最後修改時間: ' + Config.get_cookie_time() + ' 第' + str(try_counter) + '次嘗試',
                                      display=False)
                            if old_BAHARUNE != self._cookies['BAHARUNE']:
                                # 新 cookie 讀取成功（因為有可能其他執行緒接到了新cookie）
                                succeed_flag = True
                                err_print(self._sn, '讀取 cookie', '新 cookie 讀取成功', display=False)
                                break
                            else:
                                err_print(self._sn, '讀取 cookie', '新 cookie 讀取失敗', display=False)
                                random_wait_time = random.uniform(2, 5)
                                time.sleep(random_wait_time)
                                try_counter = try_counter + 1
                        if not succeed_flag:
                            self._cookies = {}
                            err_print(0, '用戶 cookie 更新失敗! 使用訪客身份訪問', status=1, no_sn=True)
                            Config.invalid_cookie()  # 將失效 cookie 更名

                        if self._settings['use_mobile_api'] and 'X-Bahamut-App-InstanceId' not in self._req_header:
                            # 即使切換 header cookie 也無法重新整理，那麼恢復 header, 好歹廣告只有 3s
                            self._req_header = self._mobile_header

                else:
                    # 本執行緒收到了新 cookie
                    # 20220115 簡化 cookie 重新整理邏輯
                    err_print(self._sn, '收到新 cookie', display=False)

                    self._cookies.update(f.cookies.get_dict())
                    Config.renew_cookies(self._cookies, log=False)

                    key_list_str = ', '.join(f.cookies.get_dict().keys())
                    err_print(self._sn, f'使用者 cookie 更新 {key_list_str} ', display=False)

                    self.__request('https://ani.gamer.com.tw/')
                    # 20210724 動畫瘋一步到位重新整理 cookie
                    if 'BAHARUNE' in f.headers.get('set-cookie'):
                        err_print(0, '使用者 cookie 已更新', status=2, no_sn=True)

        return f

    def __get_m3u8_dict(self):
        # m3u8 獲取模組參考自 https://github.com/c0re100/BahamutAnimeDownloader
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
                req = f'https://ani.gamer.com.tw/ajax/token.php?adID=0&sn={str(self._sn)}'
            else:
                req = 'https://ani.gamer.com.tw/ajax/token.php?adID=0&sn=' + str(
                    self._sn) + "&device=" + self._device_id + "&hash=" + random_string(12)
            # 返回基礎資訊，用於判斷是不是 VIP
            return self.__request(req).json()

        def unlock():
            req = 'https://ani.gamer.com.tw/ajax/unlock.php?sn=' + str(self._sn) + "&ttl=0"
            f = self.__request(req)  # 無回應正文

        def check_lock():
            req = 'https://ani.gamer.com.tw/ajax/checklock.php?device=' + self._device_id + '&sn=' + str(self._sn)
            f = self.__request(req)

        def start_ad():
            if self._settings['use_mobile_api']:
                req = f"https://api.gamer.com.tw/mobile_app/anime/v1/stat_ad.php?schedule=-1&sn={str(self._sn)}"
            else:
                req = "https://ani.gamer.com.tw/ajax/videoCastcishu.php?sn=" + str(self._sn) + "&s=194699"
            f = self.__request(req)  # 無回應正文

        def skip_ad():
            if self._settings['use_mobile_api']:
                req = f"https://api.gamer.com.tw/mobile_app/anime/v1/stat_ad.php?schedule=-1&ad=end&sn={str(self._sn)}"
            else:
                req = "https://ani.gamer.com.tw/ajax/videoCastcishu.php?sn=" + str(self._sn) + "&s=194699&ad=end"
            f = self.__request(req)  # 無回應正文

        def video_start():
            req = "https://ani.gamer.com.tw/ajax/videoStart.php?sn=" + str(self._sn)
            f = self.__request(req)

        def check_no_ad(error_count=10):
            if error_count == 0:
                err_print(self._sn, '廣告去除失敗！請向開發者提交 issue！', status=1)
                sys.exit(1)

            req = 'https://ani.gamer.com.tw/ajax/token.php?sn=' + str(
                self._sn) + '&device=' + self._device_id + '&hash=' + random_string(12)
            f = self.__request(req)
            resp = f.json()
            if 'time' in resp.keys():
                if not resp['time'] == 1:
                    err_print(self._sn, '廣告似乎還沒去除，追加等待2秒，剩餘重試次數 ' + str(error_count), status=1)
                    time.sleep(2)
                    skip_ad()
                    video_start()
                    check_no_ad(error_count=error_count - 1)
                else:
                    # 透過廣告檢查
                    if error_count != 10:
                        ads_time = (10-error_count)*2 + ad_time + 2
                        err_print(self._sn, '透過廣告時間' + str(ads_time) + '秒，記錄到設定檔案', status=2)
                        if self._settings['use_mobile_api']:
                            self._settings['mobile_ads_time'] = ads_time
                        else:
                            self._settings['ads_time'] = ads_time
                        Config.write_settings(self._settings)  # 儲存到設定檔案
            else:
                err_print(self._sn, '遭到動畫瘋地區限制，你的 IP 可能不被動畫瘋認可！', status=1)
                sys.exit(1)

        def parse_playlist():
            req = self._playlist['src']
            f = self.__request(req, no_cookies=True, addition_header={'referer': 'https://ani.gamer.com.tw/'})
            url_prefix = re.sub(r'playlist.+', '', self._playlist['src'])  # m3u8 URL 字首
            m3u8_list = re.findall(r'=\d+x\d+\n.+', f.content.decode())  # 將包含解析度和 m3u8 檔案提取
            m3u8_dict = {}
            for i in m3u8_list:
                key = re.findall(r'=\d+x\d+', i)[0]  # 提取解析度
                key = re.findall(r'x\d+', key)[0][1:]  # 提取縱向畫素數，作為 key
                value = re.findall(r'.*chunklist.+', i)[0]  # 提取 m3u8 檔案
                value = url_prefix + value  # 組成完整的 m3u8 URL
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
        # 可能是限制級動畫要求登入
        if 'error' in user_info.keys():
            msg = '《' + self._title + '》 '
            msg = msg + 'code=' + str(user_info['error']['code']) + ' message: ' + user_info['error']['message']
            err_print(self._sn, '收到錯誤', msg, status=1)
            sys.exit(1)

        if not user_info['vip']:
            # 如果使用者不是 VIP, 那麼等待廣告(20s)
            # 20200513 網站更新，最低廣告更新時間從8s增加到20s https://github.com/miyouzi/aniGamerPlus/issues/41
            # 20200806 網站更新，最低廣告更新時間從20s增加到25s https://github.com/miyouzi/aniGamerPlus/issues/55

            if self._settings['only_use_vip']:
                 err_print(self._sn, '非 VIP','因為已設定只使用 VIP 下載，故強制停止', status=1, no_sn=True)
                 sys.exit(1)

            if self._settings['use_mobile_api']:
                ad_time = self._settings['mobile_ads_time']  # APP 解析廣告解析時間不同
            else:
                ad_time = self._settings['ads_time']

            err_print(self._sn, '正在等待', '《' + self.get_title() + '》 由於不是 VIP 帳號，正在等待'+str(ad_time)+'s 廣告時間')
            start_ad()
            time.sleep(ad_time)
            skip_ad()
        else:
            err_print(self._sn, '開始下載', '《' + self.get_title() + '》 識別到 VIP 帳號，立即下載')

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
        # 處理劇集名補零
        if re.match(r'^[+-]?\d+(\.\d+){0,1}$', self._episode) and self._settings['zerofill'] > 1:
            # 正則考慮到了帶小數點的劇集
            # 如果劇集名為數字, 且使用者開啟補零
            if re.match(r'^\d+\.\d+$', self._episode):
                # 如果是浮點數
                a = re.findall(r'^\d+\.', self._episode)[0][:-1]
                b = re.findall(r'\.\d+$', self._episode)[0]
                episode = '[' + a.zfill(self._settings['zerofill']) + b + ']'
            else:
                # 如果是整數
                episode = '[' + self._episode.zfill(self._settings['zerofill']) + ']'
        else:
            episode = '[' + self._episode + ']'

        if self._settings['add_bangumi_name_to_video_filename']:
            # 如果使用者需要番劇名
            bangumi_name = self._settings['customized_video_filename_prefix'] \
                           + self._bangumi_name \
                           + self._settings['customized_bangumi_name_suffix']

            filename = bangumi_name + episode  # 有番劇名的檔名
        else:
            # 如果使用者不要將番劇名新增到檔名
            filename = self._settings['customized_video_filename_prefix'] + episode

        # 新增解析度字尾
        if self._settings['add_resolution_to_video_filename']:
            filename = filename + '[' + resolution + 'P]'

        if without_suffix:
            return filename  # 截止至解析度的檔名, 用於 __get_temp_filename()

        # 新增使用者字尾及副檔名
        filename = filename + self._settings['customized_video_filename_suffix'] \
                   + '.' + self._settings['video_filename_extension']
        legal_filename = Config.legalize_filename(filename)  # 去除非法字元
        filename = legal_filename
        return filename

    def __get_temp_filename(self, resolution, temp_suffix):
        filename = self.__get_filename(resolution, without_suffix=True)
        # temp_filename 為臨時檔名，下載完成後更名正式檔名
        temp_filename = filename + self._settings['customized_video_filename_suffix'] + '.' + temp_suffix \
                        + '.' + self._settings['video_filename_extension']
        temp_filename = Config.legalize_filename(temp_filename)
        return temp_filename

    def __segment_download_mode(self, resolution=''):
        # 設定檔案存放路徑
        filename = self.__get_filename(resolution)
        merging_filename = self.__get_temp_filename(resolution, temp_suffix='MERGING')

        output_file = os.path.join(self._bangumi_dir, filename)  # 完整輸出路徑
        merging_file = os.path.join(self._temp_dir, merging_filename)

        url_path = os.path.split(self._m3u8_dict[resolution])[0]  # 用於構造完整 chunk 連結
        temp_dir = os.path.join(self._temp_dir, str(self._sn) + '-downloading-by-aniGamerPlus')  # 臨時目錄以 sn 命令
        if not os.path.exists(temp_dir):  # 建立臨時目錄
            os.makedirs(temp_dir)
        m3u8_path = os.path.join(temp_dir, str(self._sn) + '.m3u8')  # m3u8 存放位置
        m3u8_text = self.__request(self._m3u8_dict[resolution], no_cookies=True).text  # 請求 m3u8 檔案
        with open(m3u8_path, 'w', encoding='utf-8') as f:  # 儲存 m3u8 檔案在本地
            f.write(m3u8_text)
            pass
        key_uri = re.search(r'(?<=AES-128,URI=")(.*)(?=")', m3u8_text).group()  # 把 key 的連結提取出來
        original_key_uri = key_uri

        if not re.match(r'http.+', key_uri):
            # https://github.com/miyouzi/aniGamerPlus/issues/46
            # 如果不是完整的URI
            key_uri = url_path + '/' + key_uri  # 組成完成的 URI

        m3u8_key_path = os.path.join(temp_dir, 'key.m3u8key')  # key 的存放位置
        with open(m3u8_key_path, 'wb') as f:  # 儲存 key
            f.write(self.__request(key_uri, no_cookies=True).content)

        chunk_list = re.findall(r'media_b.+ts.*', m3u8_text)  # chunk

        limiter = threading.Semaphore(self._settings['multi_downloading_segment'])  # chunk 併發下載限制器
        total_chunk_num = len(chunk_list)
        finished_chunk_counter = 0
        failed_flag = False

        def download_chunk(uri):
            chunk_name = re.findall(r'media_b.+ts', uri)[0]  # chunk 檔案名稱
            chunk_local_path = os.path.join(temp_dir, chunk_name)  # chunk 路徑
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
                err_print(self._sn, '下載狀態', 'Bad segment=' + chunk_name + ' 發生未知錯誤：' + str(e), status=1)
                limiter.release()
                sys.exit(1)

            # 顯示完成百分比
            nonlocal finished_chunk_counter
            finished_chunk_counter = finished_chunk_counter + 1
            progress_rate = float(finished_chunk_counter / total_chunk_num * 100)
            progress_rate = round(progress_rate, 2)
            Config.tasks_progress_rate[int(self._sn)]['rate'] = progress_rate

            if self.realtime_show_file_size:
                sys.stdout.write('\r正在下載：sn=' + str(self._sn) + ' ' + filename + ' ' + str(progress_rate) + '%  ')
                sys.stdout.flush()
            limiter.release()

        if self.realtime_show_file_size:
            # 是否實時顯示檔案大小，設計僅 cui 下載單個檔案或執行緒數 =1 時適用
            sys.stdout.write('正在下載：sn=' + str(self._sn) + ' ' + filename)
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

        for task in chunk_tasks_list:  # 等待所有任務完成
            while True:
                if failed_flag:
                    err_print(self._sn, '下載失敗', filename, status=1)
                    self.video_size = 0
                    return
                if task.is_alive():
                    time.sleep(1)
                else:
                    break

        # m3u8 本地化
        # replace('\\', '\\\\') 為轉譯win路徑
        m3u8_text_local_version = m3u8_text.replace(original_key_uri, os.path.join(temp_dir, 'key.m3u8key')).replace('\\', '\\\\')
        for chunk in chunk_list:
            chunk_filename = re.findall(r'media_b.+ts', chunk)[0]  # chunk 檔名
            chunk_path = os.path.join(temp_dir, chunk_filename).replace('\\', '\\\\')  # chunk 本地路徑
            m3u8_text_local_version = m3u8_text_local_version.replace(chunk, chunk_path)
        with open(m3u8_path, 'w', encoding='utf-8') as f:  # 儲存本地化的 m3u8
            f.write(m3u8_text_local_version)

        if self.realtime_show_file_size:
            sys.stdout.write('\n')
            sys.stdout.flush()
        err_print(self._sn, '下載狀態', filename + ' 下載完成，正在解密合併……')
        Config.tasks_progress_rate[int(self._sn)]['status'] = '下載完成'

        # 構造 ffmpeg 命令
        ffmpeg_cmd = [self._ffmpeg_path,
                      '-allowed_extensions', 'ALL',
                      '-i', m3u8_path,
                      '-c', 'copy', merging_file,
                      '-y']

        if self._settings['faststart_movflags']:
            # 將 metadata 移至影片檔案頭部
            # 此功能可以更快的線上播放影片
            ffmpeg_cmd[7:7] = iter(['-movflags', 'faststart'])

        if self._settings['audio_language']:
            if self._title.find('中文') == -1:
                ffmpeg_cmd[7:7] = iter(['-metadata:s:a:0', 'language=jpn'])
            else:
                ffmpeg_cmd[7:7] = iter(['-metadata:s:a:0', 'language=chi'])

        # 執行 ffmpeg
        run_ffmpeg = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        run_ffmpeg.communicate()
        # 記錄檔案大小，單位為 MB
        self.video_size = int(os.path.getsize(merging_file) / float(1024 * 1024))
        # 重命名
        err_print(self._sn, '下載狀態', filename + ' 解密合併完成，本集 ' + str(self.video_size) + 'MB，正在移至番劇目錄……')
        if os.path.exists(output_file):
            os.remove(output_file)

        if self._settings['use_copyfile_method']:
            shutil.copyfile(merging_file, output_file)  # 配合 rclone 掛載
            os.remove(merging_file)  # 刪除臨時合併檔案
        else:
            shutil.move(merging_file, output_file)  # 此方法在遇到 rclone 掛載時會出錯

        # 刪除臨時目錄
        shutil.rmtree(temp_dir, ignore_errors=True)

        self.local_video_path = output_file  # 記錄儲存路徑，FTP 上傳用
        self._video_filename = filename  # 記錄檔名，FTP 上傳用

        err_print(self._sn, '下載完成', filename, status=2)

    def __ffmpeg_download_mode(self, resolution=''):
        # 設定檔案存放路徑
        filename = self.__get_filename(resolution)
        downloading_filename = self.__get_temp_filename(resolution, temp_suffix='DOWNLOADING')

        output_file = os.path.join(self._bangumi_dir, filename)  # 完整输出路徑
        downloading_file = os.path.join(self._temp_dir, downloading_filename)

        # 建構 ffmpeg 命令
        ffmpeg_cmd = [self._ffmpeg_path,
                      '-user_agent',
                      self._settings['ua'],
                      '-headers', "Origin: https://ani.gamer.com.tw",
                      '-i', self._m3u8_dict[resolution],
                      '-c', 'copy', downloading_file,
                      '-y']

        if os.path.exists(downloading_file):
            os.remove(downloading_file)  # 清理任務失敗的屍體

        # subprocess.call(ffmpeg_cmd, creationflags=0x08000000)  # 僅 windows
        run_ffmpeg = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, bufsize=204800, stderr=subprocess.PIPE)

        def check_ffmpeg_alive():
            # 應對 ffmpeg 卡死，資源限速等，若 1min 中內檔案大小沒有增加超過 3M，則判定卡死
            if self.realtime_show_file_size:  # 是否實時顯示檔案大小，設計僅 cui 下載單個檔案或執行緒數 =1 時適用
                sys.stdout.write('正在下載：sn=' + str(self._sn) + ' ' + filename)
                sys.stdout.flush()
            else:
                err_print(self._sn, '正在下載', filename + ' title=' + self._title)

            time.sleep(2)
            time_counter = 1
            pre_temp_file_size = 0
            while run_ffmpeg.poll() is None:

                if self.realtime_show_file_size:
                    # 即時顯示檔案大小
                    if os.path.exists(downloading_file):
                        size = os.path.getsize(downloading_file)
                        size = size / float(1024 * 1024)
                        size = round(size, 2)
                        sys.stdout.write(
                            '\r正在下載：sn=' + str(self._sn) + ' ' + filename + '    ' + str(size) + 'MB      ')
                        sys.stdout.flush()
                    else:
                        sys.stdout.write('\r正在下載：sn=' + str(self._sn) + ' ' + filename + '    檔案尚未生成  ')
                        sys.stdout.flush()

                if time_counter % 60 == 0 and os.path.exists(downloading_file):
                    temp_file_size = os.path.getsize(downloading_file)
                    a = temp_file_size - pre_temp_file_size
                    if a < (3 * 1024 * 1024):
                        err_msg_detail = downloading_filename + ' 在一分鐘內僅增加' + str(
                            int(a / float(1024))) + 'KB 判定為卡死，任務失敗！'
                        err_print(self._sn, '下載失败', err_msg_detail, status=1)
                        run_ffmpeg.kill()
                        return
                    pre_temp_file_size = temp_file_size
                time.sleep(1)
                time_counter = time_counter + 1

        ffmpeg_checker = threading.Thread(target=check_ffmpeg_alive)  # 檢查執行緒
        ffmpeg_checker.setDaemon(True)  # 如果 Anime 執行緒被 kill, 檢查程式也應該結束
        ffmpeg_checker.start()
        run = run_ffmpeg.communicate()
        return_str = str(run[1])

        if self.realtime_show_file_size:
            sys.stdout.write('\n')
            sys.stdout.flush()

        if run_ffmpeg.returncode == 0 and (return_str.find('Failed to open segment') < 0):
            # 執行成功（ffmpeg正常結束，每個分段都成功下載）
            if os.path.exists(output_file):
                os.remove(output_file)
            # 記錄檔案大小，單位為 MB
            self.video_size = int(os.path.getsize(downloading_file) / float(1024 * 1024))
            err_print(self._sn, '下載狀態', filename + '本集 ' + str(self.video_size) + 'MB，正在移至番劇目錄……')

            if self._settings['use_copyfile_method']:
                shutil.copyfile(downloading_file, output_file)  # 配合 rclone 掛載
                os.remove(downloading_file)  # 刪除臨時合併檔案
            else:
                shutil.move(downloading_file, output_file)  # 此方法在遇到 rclone 掛載時會出錯

                self.local_video_path = output_file  # 記錄儲存路徑，FTP 上傳用
                self._video_filename = filename  # 記錄檔名，FTP 上傳用
            err_print(self._sn, '下載完成', filename, status=2)
        else:
            err_msg_detail = filename + ' ffmpeg_return_code=' + str(
                run_ffmpeg.returncode) + ' Bad segment=' + str(return_str.find('Failed to open segment'))
            err_print(self._sn, '下載失敗', err_msg_detail, status=1)

    def download(self, resolution='', save_dir='', bangumi_tag='', realtime_show_file_size=False, rename='', classify=True):
        self.realtime_show_file_size = realtime_show_file_size
        if not resolution:
            resolution = self._settings['download_resolution']

        if save_dir:
            self._bangumi_dir = save_dir  # 用於 cui 使用者指定下載在當前目錄

        if rename:
            bangumi_name = self._bangumi_name
            # 適配多版本的番劇
            version = re.findall(r'\[.+?\]', self._bangumi_name)  # 在番劇名中尋找是否存在多版本標記
            if version:  # 如果這個番劇是多版本的
                version = str(version[-1])  # 提取番劇版本名稱
                bangumi_name = bangumi_name.replace(version, '').strip()  # 沒有版本名稱的 bangumi_name，且頭尾無空格
            # 如果設定重新命名了番劇
            # 將其中的番劇名換成使用者設定的，且不影響版本號字尾（如果有）
            self._title = self._title.replace(bangumi_name, rename)
            self._bangumi_name = self._bangumi_name.replace(bangumi_name, rename)

        # 下載任務開始
        Config.tasks_progress_rate[int(self._sn)] = {'rate': 0, 'filename': '《'+self.get_title()+'》', 'status': '正在解析'}

        try:
            self.__get_m3u8_dict()  # 獲取 m3u8 列表
        except TryTooManyTimeError:
            # 如果在獲取 m3u8 過程中發生意外, 則取消此次下載
            err_print(self._sn, '下載狀態', '獲取 m3u8 失敗！', status=1)
            self.video_size = 0
            return

        check_ffmpeg = subprocess.Popen('ffmpeg -h', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if check_ffmpeg.stdout.readlines():  # 查詢 ffmpeg 是否已放入系統 path
            self._ffmpeg_path = 'ffmpeg'
        else:
            # print('沒有在系統 PATH 中發現 ffmpeg，嘗試在所在目錄尋找')
            if 'Windows' in platform.system():
                self._ffmpeg_path = os.path.join(self._working_dir, 'ffmpeg.exe')
            else:
                self._ffmpeg_path = os.path.join(self._working_dir, 'ffmpeg')
            if not os.path.exists(self._ffmpeg_path):
                err_print(0, '本專案依賴於 ffmpeg，但 ffmpeg 未找到', status=1, no_sn=True)
                raise FileNotFoundError  # 如果本地目錄下也沒有找到 ffmpeg 則丟出異常

        # 建立存放番劇的目錄，去除非法字元
        if bangumi_tag:  # 如果指定了番劇分類
            self._bangumi_dir = os.path.join(self._bangumi_dir, Config.legalize_filename(bangumi_tag))
        if classify:  # 控制是否建立番劇資料夾
            self._bangumi_dir = os.path.join(self._bangumi_dir, Config.legalize_filename(self._bangumi_name))
        if not os.path.exists(self._bangumi_dir):
            try:
                os.makedirs(self._bangumi_dir)  # 按番劇建立資料夾分類
            except FileExistsError as e:
                err_print(self._sn, '下載狀態', '欲建立的番劇資料夾已存在 ' + str(e), display=False)

        if not os.path.exists(self._temp_dir):  # 建立臨時資料夾
            try:
                os.makedirs(self._temp_dir)
            except FileExistsError as e:
                err_print(self._sn, '下載狀態', '欲建立的臨時資料夾已存在 ' + str(e), display=False)

        # 如果不存在指定解析度，則選取最近可用解析度
        if resolution not in self._m3u8_dict.keys():
            if self._settings['lock_resolution']:
                # 如果使用者設定鎖定解析度，則下載取消
                err_msg_detail = '指定解析度不存在，因當前鎖定了解析度，下載取消，可用的解析度：' + 'P '.join(self._m3u8_dict.keys()) + 'P'
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
            # resolution = str(resolution_list[-1])  # 選取最高可用解析度
            resolution = str(closest_resolution)
            err_msg_detail = '指定解析度不存在，選取最近可用解析度：' + resolution + 'P'
            err_print(self._sn, '任務狀態', err_msg_detail, status=1)
        self.video_resolution = int(resolution)

        # 解析完成，開始下載
        Config.tasks_progress_rate[int(self._sn)]['status'] = '正在下載'
        Config.tasks_progress_rate[int(self._sn)]['filename'] = self.get_filename()

        if self._settings['segment_download_mode']:
            self.__segment_download_mode(resolution)
        else:
            self.__ffmpeg_download_mode(resolution)

        # 任務完成，從任務進度表中刪除
        del Config.tasks_progress_rate[int(self._sn)]

        # 下載彈幕
        if self._danmu:
            full_filename = os.path.join(self._bangumi_dir, self.__get_filename(resolution)).replace('.' + self._settings['video_filename_extension'], '.ass')
            d = Danmu(self._sn, full_filename)
            d.download()

        # 推送 CQ 通知
        if self._settings['coolq_notify']:
            try:
                msg = '【aniGamerPlus消息】\n《' + self._video_filename + '》下载完成，本集 ' + str(self.video_size) + ' MB'
                if self._settings['coolq_settings']['message_suffix']:
                    # 追加使用者資訊
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
                msg = '【aniGamerPlus消息】\n《' + self._video_filename + '》下载完成，本集 ' + str(self.video_size) + ' MB'
                vApiTokenTelegram = self._settings['telebot_token']
                apiMethod = "getUpdates"
                api_url = "https://api.telegram.org/bot" + vApiTokenTelegram + "/" + apiMethod # Telegram bot api url
                try:
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
                        self.__request(req, no_cookies=True)  # Send msg to telegram bot
                    except:
                        err_print(self._sn, 'TG NOTIFY ERROR', "Exception: Send msg error\nReq: " + req, status=1)  # Send mag error
                except:
                    err_print(self._sn, 'TG NOTIFY ERROR', "Exception: Invalid access token\nToken: " + vApiTokenTelegram, status=1) # Cannot find chat id
            except BaseException as e:
                err_print(self._sn, 'TG NOTIFY ERROR', 'Exception: ' + str(e), status=1)

        # 推送通知至 Discord
        if self._settings['discord_notify']:
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
            if r.status_code != 200:
                err_print(self._sn, 'discord NOTIFY ERROR', 'Exception: Send msg error\nReq: ' + req, status=1)

        # plex 自動更新媒體庫
        if self._settings['plex_refresh']:
            url = 'https://{plex_url}/library/sections/{plex_section}/refresh?X-Plex-Token={plex_token}'.format(
                plex_url=self._settings['plex_url'],
                plex_section=self._settings['plex_section'],
                plex_token=self._settings['plex_token']
            )
            r = requests.get(url)
            if r.status_code != 200:
                err_print(self._sn, 'Plex auto Refresh ERROR', status=1)

    def upload(self, bangumi_tag='', debug_file=''):
        first_connect = True  # 標記是否是第一次連線，第一次連線會刪除臨時快取目錄
        tmp_dir = str(self._sn) + '-uploading-by-aniGamerPlus'

        if debug_file:
            self.local_video_path = debug_file

        if not os.path.exists(self.local_video_path):  # 如果檔案不存在,直接返回失敗
            return self.upload_succeed_flag

        if not self._video_filename:  # 用於僅上傳, 將檔名提取出來
            self._video_filename = os.path.split(self.local_video_path)[-1]

        socket.setdefaulttimeout(20)  # 超時時間20s

        if self._settings['ftp']['tls']:
            ftp = FTP_TLS()  # FTP over TLS
        else:
            ftp = FTP()

        def connect_ftp(show_err=True):
            ftp.encoding = 'utf-8'  # 解決中文亂碼
            err_counter = 0
            connect_flag = False
            while err_counter <= 3:
                try:
                    ftp.connect(self._settings['ftp']['server'], self._settings['ftp']['port'])  # 連線 FTP
                    ftp.login(self._settings['ftp']['user'], self._settings['ftp']['pwd'])  # 登入
                    connect_flag = True
                    break
                except ftplib.error_temp as e:
                    if show_err:
                        if 'Too many connections' in str(e):
                            detail = self._video_filename + ' 當前 FTP 連線數過多, 5 分鐘後重試，最多重試三次：' + str(e)
                            err_print(self._sn, 'FTP 狀態', detail, status=1)
                        else:
                            detail = self._video_filename + ' 連線FTP時發生錯誤，5 分鐘後重試，最多重試三次：' + str(e)
                            err_print(self._sn, 'FTP 狀態', detail, status=1)
                        err_counter = err_counter + 1
                        for i in range(5 * 60):
                            time.sleep(1)
                except BaseException as e:
                    if show_err:
                        detail = self._video_filename + ' 在連線 FTP 時發生無法處理的異常：' + str(e)
                        err_print(self._sn, 'FTP 狀態', detail, status=1)
                    break

            if not connect_flag:
                err_print(self._sn, '上傳失敗', self._video_filename, status=1)
                return connect_flag  # 如果連線失敗，直接放棄

            ftp.voidcmd('TYPE I')  # 二進位制模式

            if self._settings['ftp']['cwd']:
                try:
                    ftp.cwd(self._settings['ftp']['cwd'])  # 進入使用者指定目錄
                except ftplib.error_perm as e:
                    if show_err:
                        err_print(self._sn, 'FT P狀態', '進入指定 FTP 目錄時出錯: ' + str(e), status=1)

            if bangumi_tag:  # 番劇分類
                try:
                    ftp.cwd(bangumi_tag)
                except ftplib.error_perm:
                    try:
                        ftp.mkd(bangumi_tag)
                        ftp.cwd(bangumi_tag)
                    except ftplib.error_perm as e:
                        if show_err:
                            err_print(self._sn, 'FTP 狀態', '創建目錄番劇目錄時發生異常，你可能沒有權限創建目錄：' + str(e), status=1)

            # 歸類番劇
            ftp_bangumi_dir = Config.legalize_filename(self._bangumi_name)  # 保證合法
            try:
                ftp.cwd(ftp_bangumi_dir)
            except ftplib.error_perm:
                try:
                    ftp.mkd(ftp_bangumi_dir)
                    ftp.cwd(ftp_bangumi_dir)
                except ftplib.error_perm as e:
                    if show_err:
                        detail = '你可能沒有權限創建目錄（用於分類番劇），影片文件將會直接上傳，收到異常：' + str(e)
                        err_print(self._sn, 'FTP 狀態', detail, status=1)

            # 刪除舊的臨時資料夾
            nonlocal first_connect
            if first_connect:  # 首次連線
                remove_dir(tmp_dir)
                first_connect = False  # 標記第一次連線已完成

            # 建立新的臨時資料夾
            # 建立臨時資料夾是因為 pure-ftpd 在續傳時會將檔名更改成不可預測的名字
            # 正常中斷傳輸會把名字改回來, 但是意外掉線不會, 為了處理這種情況
            # 需要獲取 pure-ftpd 未知檔名的續傳快取檔案, 為了不和其他影片的快取檔案混淆, 故建立一個臨時資料夾
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
                    err_print(self._sn, 'FTP 狀態', '將强制關閉 FTP 連接，因爲在退出時收到異常：' + str(e))
                ftp.close()

        def remove_dir(dir_name):
            try:
                ftp.rmd(dir_name)
            except ftplib.error_perm as e:
                if 'Directory not empty' in str(e):
                    # 如果目錄非空，則刪除內部檔案
                    ftp.cwd(dir_name)
                    del_all_files()
                    ftp.cwd('..')
                    ftp.rmd(dir_name)  # 刪完內部檔案，刪除資料夾
                elif 'No such file or directory' in str(e):
                    pass
                else:
                    # 其他非空目錄報錯
                    raise e

        def del_all_files():
            try:
                for file_need_del in ftp.nlst():
                    if not re.match(r'^(\.|\.\.)$', file_need_del):
                        ftp.delete(file_need_del)
                        # print('刪除了檔案: ' + file_need_del)
            except ftplib.error_perm as resp:
                if not str(resp) == "550 No files found":
                    raise

        if not connect_ftp():  # 連線 FTP
            return self.upload_succeed_flag  # 如果連線失敗

        err_print(self._sn, '正在上傳', self._video_filename + ' title=' + self._title + '……')
        try_counter = 0
        video_filename = self._video_filename  # video_filename 將可能會儲存 pure-ftpd 快取檔名
        max_try_num = self._settings['ftp']['max_retry_num']
        local_size = os.path.getsize(self.local_video_path)  # 本地檔案大小
        while try_counter <= max_try_num:
            try:
                if try_counter > 0:
                    # 傳輸遭中斷後處理
                    detail = self._video_filename + ' 發生異常，重連 FTP，續傳檔案，將重試最多' + str(max_try_num) + '次……'
                    err_print(self._sn, '上傳狀態', detail, status=1)
                    if not connect_ftp():  # 重連
                        return self.upload_succeed_flag

                    # 解決操蛋的 Pure-Ftpd 續傳一次就改名導致不能再續傳問題。
                    # 一般正常關閉檔案傳輸 Pure-Ftpd 會把名字改回來，但是遇到網路意外中斷，那麼就不會改回檔名，留著臨時檔名
                    # 本段就是處理這種情況
                    try:
                        for i in ftp.nlst():
                            if 'pureftpd-upload' in i:
                                # 找到 pure-ftpd 快取，直接抓快取來續傳
                                video_filename = i
                    except ftplib.error_perm as resp:
                        if not str(resp) == "550 No files found":  # 非檔案不存在錯誤，丟擲異常
                            raise
                # 斷點續傳
                try:
                    # 需要 FTP Server 支援續傳
                    ftp_binary_size = ftp.size(video_filename)  # 遠端檔案位元組數
                except ftplib.error_perm:
                    # 如果不存在檔案
                    ftp_binary_size = 0
                except OSError:
                    try_counter = try_counter + 1
                    continue

                ftp.voidcmd('TYPE I')  # 二進位制模式
                conn = ftp.transfercmd('STOR ' + video_filename, ftp_binary_size)  # ftp 伺服器檔名和 offset 偏移地址
                with open(self.local_video_path, 'rb') as f:
                    f.seek(ftp_binary_size)  # 從斷點處開始讀取
                    while True:
                        block = f.read(1048576)  # 讀取 1M
                        conn.sendall(block)  # 送出 block
                        if not block:
                            time.sleep(3)  # 等待一下，等待 sendall() 完成
                            break

                conn.close()

                err_print(self._sn, '上傳狀態', '檢查遠端檔案大小是否與本地一致……')
                exit_ftp(False)
                connect_ftp(False)
                # 不重連的話, 下面查詢遠端檔案大小會返回 None, 懵逼...
                # sendall()沒有完成將會 500 Unknown command
                err_counter = 0
                remote_size = 0
                while err_counter < 3:
                    try:
                        remote_size = ftp.size(video_filename)  # 遠端檔案大小
                        break
                    except ftplib.error_perm as e1:
                        err_print(self._sn, 'FTP 狀態', 'ftplib.error_perm: ' + str(e1))
                        remote_size = 0
                        break
                    except OSError as e2:
                        err_print(self._sn, 'FTP 狀態', 'OSError: ' + str(e2))
                        remote_size = 0
                        connect_ftp(False)  # 斷線重連
                        err_counter = err_counter + 1

                if remote_size is None:
                    err_print(self._sn, 'FTP 狀態', 'remote_size is None')
                    remote_size = 0
                # 遠端檔案大小獲取失敗, 可能檔案不存在或者抽風
                # 那上面獲取遠端位元組數將會是0, 導致重新下載, 那麼此時應該清空快取目錄下的檔案
                # 避免後續找錯檔案續傳
                if remote_size == 0:
                    del_all_files()

                if remote_size != local_size:
                    # 如果遠端檔案大小與本地不一致
                    # print('remote_size='+str(remote_size))
                    # print('local_size ='+str(local_size))
                    detail = self._video_filename + ' 在遠端為' + str(
                        round(remote_size / float(1024 * 1024), 2)) + 'MB' + ' 與本地' + str(
                        round(local_size / float(1024 * 1024), 2)) + 'MB 不一致！將重試最多' + str(max_try_num) + '次'
                    err_print(self._sn, '上傳狀態', detail, status=1)
                    try_counter = try_counter + 1
                    continue  # 續傳

                # 順利上傳後
                ftp.cwd('..')  # 返回上級目錄，即退出臨時目錄
                try:
                    # 如果同名檔案存在，則刪除
                    ftp.size(self._video_filename)
                    ftp.delete(self._video_filename)
                except ftplib.error_perm:
                    pass
                ftp.rename(tmp_dir + '/' + video_filename, self._video_filename)  # 將影片從臨時檔案移出, 順便重新命名
                remove_dir(tmp_dir)  # 刪除臨時目錄
                self.upload_succeed_flag = True  # 標記上傳成功
                break

            except ConnectionResetError as e:
                if self._settings['ftp']['show_error_detail']:
                    detail = self._video_filename + ' 在上傳過程中網絡被重置，將重試最多' + str(max_try_num) + '次' + ', 收到異常：' + str(e)
                    err_print(self._sn, '上傳狀態', detail, status=1)
                try_counter = try_counter + 1
            except TimeoutError as e:
                if self._settings['ftp']['show_error_detail']:
                    detail = self._video_filename + ' 在上傳過程中超時，將重試最多' + str(max_try_num) + '次，收到異常：' + str(e)
                    err_print(self._sn, '上傳狀態', detail, status=1)
                try_counter = try_counter + 1
            except socket.timeout as e:
                if self._settings['ftp']['show_error_detail']:
                    detail = self._video_filename + ' 在上傳過程 socket 超時，將重試最多' + str(max_try_num) + '次，收到異常：' + str(e)
                    err_print(self._sn, '上傳狀態', detail, status=1)
                try_counter = try_counter + 1

        if not self.upload_succeed_flag:
            err_print(self._sn, '上傳失敗', self._video_filename + ' 放棄上傳！', status=1)
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
