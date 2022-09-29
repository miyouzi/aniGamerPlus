
import requests
import json
import random
import re
import os
import Config
from ColorPrint import err_print


class Danmu():
    def __init__(self, sn, full_filename, cookies):
        self._sn = sn
        self._full_filename = full_filename
        self._cookies = cookies

    def get_BGRcolor(self, RGBcolor):
        r = RGBcolor[0:2]
        g = RGBcolor[2:4]
        b = RGBcolor[4:6]
        return f"{b}{g}{r}"

    def find_ban_word(self, text, ban_word_re):
        result = ban_word_re.search(text)
        # 確認不是匹配到空字串
        return result and result.group(0)

    def download(self, ban_words):
        h = {
            'Content-Type':
            'application/x-www-form-urlencoded;charset=utf-8',
            'origin':
            'https://ani.gamer.com.tw',
            'authority':
            'ani.gamer.com.tw',
            'user-agent':
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.83 Safari/537.36'
        }
        data = {'sn': str(self._sn)}
        r = requests.post(
            'https://ani.gamer.com.tw/ajax/danmuGet.php', data=data, headers=h)

        if r.status_code != 200:
            err_print(self._sn, '彈幕下載失敗', 'status_code=' + str(r.status_code), status=1)
            return

        h = {
            'accept':
            'application/json',
            'origin':
            'https://ani.gamer.com.tw',
            'authority':
            'ani.gamer.com.tw',
            'user-agent':
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.83 Safari/537.36',
        }
        ban_words_response = requests.get(
            'https://ani.gamer.com.tw/ajax/keywordGet.php', headers=h, cookies=self._cookies)

        if ban_words_response.status_code != 200:
            err_print(self._sn, '取得線上過濾彈幕失敗', 'status_code=' +
                      str(r.status_code), status=1)
        else:
            online_ban_words = json.loads(ban_words_response.text)
            for online_ban_word in online_ban_words:
                err_print(self._sn, '取得線上過濾彈幕', detail=online_ban_word['keyword'], status=0, display=False)
                ban_words.append(online_ban_word['keyword'])

        output = open(self._full_filename, 'w', encoding='utf8')
        danmu_template_file = os.path.join(Config.get_working_dir(), 'DanmuTemplate.ass')
        with open(danmu_template_file, 'r', encoding='utf8') as temp:
            for line in temp.readlines():
                output.write(line)

        j = json.loads(r.text)
        height = 50
        roll_channel = list()
        roll_time = list()

        ban_word_re = re.compile("|".join(ban_words), re.IGNORECASE)

        for danmu in j:
            text = danmu['text']
            if self.find_ban_word(text, ban_word_re):
                err_print(self._sn, f'跳過彈幕 [{text}]', self._full_filename, display=False)
                continue

            output.write('Dialogue: ')
            output.write('0,')

            start_time = int(danmu['time'] / 10)
            hundred_ms = danmu['time'] % 10
            m, s = divmod(start_time, 60)
            h, m = divmod(m, 60)
            output.write(f'{h:d}:{m:02d}:{s:02d}.{hundred_ms:d}0,')

            BGRcolor = self.get_BGRcolor(danmu['color'][1:])
            if danmu['position'] == 0:  # Roll danmu
                height = 0
                end_time = 0
                for i in range(len(roll_channel)):
                    if roll_channel[i] <= danmu['time']:
                        height = i * 54 + 27
                        roll_channel[i] = danmu['time'] + \
                            (len(text) * roll_time[i]) / 8 + 1
                        end_time = start_time + roll_time[i]
                        break
                if height == 0:
                    roll_channel.append(0)
                    roll_time.append(random.randint(10, 14))
                    roll_channel[-1] = danmu['time'] + \
                        (len(text) * roll_time[-1]) / 8 + 1
                    height = len(roll_channel) * 54 - 27
                    end_time = start_time + roll_time[-1]

                m, s = divmod(end_time, 60)
                h, m = divmod(m, 60)
                output.write(f'{h:d}:{m:02d}:{s:02d}.{hundred_ms:d}0,')

                output.write(
                    'Roll,,0,0,0,,{\\move(1920,' + str(height) + ',-1000,' + str(height) + ')\\1c&H4C' + BGRcolor + '}')
            elif danmu['position'] == 1:  # Top danmu
                end_time = start_time + 5
                m, s = divmod(end_time, 60)
                h, m = divmod(m, 60)
                output.write(f'{h:d}:{m:02d}:{s:02d}.{hundred_ms:d}0,')
                output.write(
                    'Top,,0,0,0,,{\\1c&H4C' + BGRcolor + '}')
            else:  # Bottom danmu
                end_time = start_time + 5
                m, s = divmod(end_time, 60)
                h, m = divmod(m, 60)
                output.write(f'{h:d}:{m:02d}:{s:02d}.{hundred_ms:d}0,')
                output.write(
                    'Bottom,,0,0,0,,{\\1c&H4C' + BGRcolor + '}')

            output.write(text)
            output.write('\n')

        err_print(self._sn, '彈幕下載完成', self._full_filename, status=2)


if __name__ == '__main__':
    pass
