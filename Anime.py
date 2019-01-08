#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2019/1/5 16:22
# @Author  : Miyouzi
# @File    : Anime.py @Software: PyCharm
import Config
from bs4 import BeautifulSoup
import re, time, os, platform, subprocess, requests, random, sys
from Color import err_print


class TryTooManyTimeError(BaseException):
    pass


class Anime():
    def __init__(self, sn):
        self._settings = Config.read_settings()
        self._cookies = Config.read_cookies()
        self._working_dir = self._settings['working_dir']
        self._bangumi_dir = self._settings['bangumi_dir']

        self._session = requests.session()
        self._title = ''
        self._sn = sn
        self._bangumi_name = ''
        self._episode = ''
        self._episode_list = {}
        self._device_id = ''
        self._playlist = {}
        self._m3u8_dict = {}
        self.video_resolution = 0
        self.video_size = 0

        self.__init_header()  # http header
        self.__get_src()  # 获取网页, 产生 self._src (BeautifulSoup)
        self.__get_title()  # 提取页面标题
        self.__get_bangumi_name()  # 提取本番名字
        self.__get_episode()  # 提取剧集码，str
        self.__get_episode_list()  # 提取剧集列表，结构 {'episode': sn}，储存到 self._episode_list, sn 为 int

    def renew(self):
        self.__get_src()
        self.__get_title()
        self.__get_bangumi_name()
        self.__get_episode()
        self.__get_episode_list()

    def get_sn(self):
        return self._sn

    def get_bangumi_name(self):
        return self._bangumi_name

    def get_episode(self):
        return self._episode

    def get_episode_list(self):
        return self._episode_list

    def get_title(self):
        return self._title

    def __get_src(self):
        host = 'ani.gamer.com.tw'
        req = 'https://' + host + '/animeVideo.php?sn=' + str(self._sn)
        f = self.__request(req)
        self._src = BeautifulSoup(f.content, "lxml")

    def __get_title(self):
        soup = self._src
        try:
            self._title = soup.find('meta', property="og:title")['content']  # 提取标题（含有集数）
        except TypeError:
            # 该sn下没有动画
            err_msg = 'ERROR: 該 sn='+str(self._sn)+' 下真的有動畫？'
            err_print(err_msg)
            self._episode_list = {}
            sys.exit(1)

    def __get_bangumi_name(self):
        self._bangumi_name = re.sub(r'\[.+\]$', '', self._title)  # 提取番剧名（去掉集数后缀）

    def __get_episode(self):  # 提取集数
        self._episode = re.findall(r'\[.+\]$', self._title)
        self._episode = str(self._episode[0][1:-1])  # 考虑到 .5 集和 sp、ova 等存在，以str储存

    def __get_episode_list(self):
        try:
            a = self._src.find('section', 'season').find_all('a')
            for i in a:
                sn = int(i['href'].replace('?sn=', ''))
                ep = str(i.string)
                self._episode_list[ep] = sn
        except AttributeError:
            # 当只有一集时，不存在剧集列表，self._episode_list 只有本身
            self._episode_list[self._episode] = self._sn

    def __init_header(self):
        # 伪装为Chrome
        host = 'ani.gamer.com.tw'
        origin = 'https://' + host
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36"
        ref = 'https://' + host + '/animeVideo.php?sn=' + str(self._sn)
        lang = 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.6'
        accept = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8'
        accept__encoding = 'gzip, deflate, br'
        cache_control = 'no-cache'
        header = {
            "User-Agent": ua,
            "Referer": ref,
            "Accept-Language": lang,
            "Accept": accept,
            "Accept_Encoding": accept__encoding,
            "cache-control": cache_control,
            "origin": origin
        }
        self._req_header = header

    def __request(self, req, no_cookies=False):
        # 获取页面
        error_cnt = 0
        while True:
            try:
                if self._cookies and not no_cookies:
                    f = self._session.get(req, headers=self._req_header, cookies=self._cookies, timeout=5)
                else:
                    f = self._session.get(req, headers=self._req_header, cookies={}, timeout=5)
            except requests.exceptions.RequestException as e:
                if error_cnt >= 3:
                    raise TryTooManyTimeError('请求失败次数过多！请求链接：\n%s' % req)
                err_msg = 'ERROR: 请求失败！except：\n'+str(e)+'\n3s后重试(最多重试三次)'
                err_print(err_msg)
                time.sleep(3)
                error_cnt += 1
            else:
                break
        # 处理 cookie
        if not self._cookies:
            self._cookies = f.cookies.get_dict()
        # 如果用户有提供 cookie，则跳过
        elif ('nologinuser' not in self._cookies.keys() and 'BAHAID' not in self._cookies.keys()):
            if 'nologinuser' in f.cookies.get_dict().keys():
                self._cookies['nologinuser'] = f.cookies.get_dict()['nologinuser']
        return f

    def download(self, resolution=''):
        if not resolution:
            resolution = self._settings['download_resolution']

        # m3u8获取模块参考自 https://github.com/c0re100/BahamutAnimeDownloader
        def get_device_id():
            req = 'https://ani.gamer.com.tw/ajax/getdeviceid.php'
            f = self.__request(req)
            self._device_id = f.json()['deviceid']
            return self._device_id

        def get_playlist():
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
            req = 'https://ani.gamer.com.tw/ajax/token.php?adID=0&sn=' + str(
                self._sn) + "&device=" + self._device_id + "&hash=" + random_string(12)
            f = self.__request(req)

        def unlock():
            req = 'https://ani.gamer.com.tw/ajax/unlock.php?sn=' + str(self._sn) + "&ttl=0"
            f = self.__request(req)  # 无响应正文

        def check_lock():
            req = 'https://ani.gamer.com.tw/ajax/checklock.php?device=' + self._device_id + '&sn=' + str(self._sn)
            f = self.__request(req)

        def start_ad():
            req = "https://ani.gamer.com.tw/ajax/videoCastcishu.php?sn=" + str(self._sn) + "&s=194699"
            f = self.__request(req)  # 无响应正文

        def skip_ad():
            req = "https://ani.gamer.com.tw/ajax/videoCastcishu.php?sn=" + str(self._sn) + "&s=194699&ad=end"
            f = self.__request(req)  # 无响应正文

        def video_start():
            req = "https://ani.gamer.com.tw/ajax/videoStart.php?sn=" + str(self._sn)
            f = self.__request(req)

        def check_no_ad():
            req = "https://ani.gamer.com.tw/ajax/token.php?sn=" + str(
                self._sn) + "&device=" + self._device_id + "&hash=" + random_string(12)
            f = self.__request(req)
            resp = f.json()
            if 'time' in resp.keys():
                if resp['time'] == 1:
                    # print('check_no_ad: Adaway!')
                    pass
                else:
                    print('check_no_ad: Ads not away?')
            else:
                print('check_no_ad: Not in right area.')

        def parse_playlist():
            req = 'https:' + self._playlist['src']
            f = self.__request(req, no_cookies=True)
            url_prefix = re.sub(r'playlist.+', '', self._playlist['src'])  # m3u8 URL 前缀
            m3u8_list = re.findall(r'=\d+x\d+\n.+', f.content.decode())  # 将包含分辨率和 m3u8 文件提取
            m3u8_dict = {}
            for i in m3u8_list:
                key = re.findall(r'=\d+x\d+', i)[0]  # 提取分辨率
                key = re.findall(r'x\d+', key)[0][1:]  # 提取纵向像素数，作为 key
                value = re.findall(r'chunklist.+', i)[0]  # 提取 m3u8 文件
                value = 'https:' + url_prefix + value  # 组成完整的 m3u8 URL
                m3u8_dict[key] = value
            self._m3u8_dict = m3u8_dict

        def download_video(resolution):
            check_ffmpeg = subprocess.Popen('ffmpeg -h', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if check_ffmpeg.stdout.readlines():  # 查找 ffmpeg 是否已放入系统 path
                ffmpeg_path = 'ffmpeg'
            else:
                # print('没有在系统PATH中发现ffmpeg，尝试在所在目录寻找')
                if 'Windows' in platform.system():
                    ffmpeg_path = os.path.join(self._working_dir, 'ffmpeg.exe')
                else:
                    ffmpeg_path = os.path.join(self._working_dir, 'ffmpeg')
                if not os.path.exists(ffmpeg_path):
                    raise FileNotFoundError  # 如果本地目录下也没有找到 ffmpeg 则丢出异常

            # 创建存放番剧的目录，去除非法字符
            bangumi_dir = os.path.join(self._bangumi_dir, re.sub(r'[\|\?\*<\":>/\'\\]+', '', self._bangumi_name))
            if not os.path.exists(bangumi_dir):
                os.makedirs(bangumi_dir)  # 按番剧创建文件夹分类

            # 如果不存在指定清晰度，则选取最近可用清晰度
            if resolution not in self._m3u8_dict.keys():
                resolution_list = map(lambda x: int(x), self._m3u8_dict.keys())
                resolution_list = list(resolution_list)
                flag = 9999
                closest_resolution = 0
                for i in resolution_list:
                    a = abs(int(resolution)-i)
                    if a < flag:
                        flag = a
                        closest_resolution = i
                # resolution_list.sort()
                # resolution = str(resolution_list[-1])  # 选取最高可用清晰度
                resolution = str(closest_resolution)
                err_msg = 'ERROR: 指定清晰度不存在，選取最近可用清晰度: ' + resolution + 'P'
                err_print(err_msg)
            self.video_resolution = int(resolution)

            # 设定文件存放路径
            filename = self._settings['customized_video_filename_prefix'] + self._title  # 添加用户自定义前缀
            if self._settings['add_resolution_to_video_filename']:
                filename = filename + '[' + resolution + 'P]'  # 添加分辨率后缀
            # downloading_filename 为下载时文件名，下载完成后更名为 output_file
            downloading_filename = filename + self._settings['customized_video_filename_suffix'] + '.DOWNLOADING.mp4'
            filename = filename + self._settings['customized_video_filename_suffix'] + '.mp4'  # 添加用户后缀及扩展名
            legal_filename = re.sub(r'[\|\?\*<\":>/\'\\]+', '', filename)  # 去除非法字符
            downloading_filename = re.sub(r'[\|\?\*<\":>/\'\\]+', '', downloading_filename)
            output_file = os.path.join(bangumi_dir, legal_filename)  # 完整输出路径
            downloading_file = os.path.join(bangumi_dir, downloading_filename)

            # 构造 ffmpeg 命令
            ffmpeg_cmd = [ffmpeg_path,
                          '-user_agent',
                          "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:64.0) Gecko/20100101 Firefox/64.0",
                          '-headers', "Origin: https://ani.gamer.com.tw",
                          '-i', self._m3u8_dict[resolution],
                          '-c', 'copy', downloading_file,
                          '-y']
            print('正在下載: sn=' + str(self._sn) + ' ' + filename)
            # subprocess.call(ffmpeg_cmd, creationflags=0x08000000)  # 仅windows
            run_ffmpeg = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            run = run_ffmpeg.communicate()
            if os.path.exists(output_file):
                os.remove(output_file)
            os.renames(downloading_file, output_file)  # 下载完成，更改文件名
            self.video_size = int(os.path.getsize(output_file) / float(1024 * 1024))  # 记录文件大小，单位为 MB
            print('下載完成: sn=' + str(self._sn) + ' ' + filename)

        get_device_id()
        gain_access()
        unlock()
        check_lock()
        unlock()
        unlock()
        start_ad()
        time.sleep(3)
        skip_ad()
        video_start()
        check_no_ad()
        get_playlist()
        parse_playlist()
        download_video(resolution)