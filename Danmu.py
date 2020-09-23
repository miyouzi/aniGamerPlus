
import requests
import json
import random
from ColorPrint import err_print


class Danmu():
    def __init__(self, sn, full_filename):
        self._sn = sn
        self._full_filename = full_filename

    def download(self):
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
            err_print(self._sn, '彈幕下載失敗','status_code=' + str(status_code), status=1)
            return

        output = open(self._full_filename, 'w', encoding='utf8')
        with open('DanmuTemplate.ass', 'r', encoding='utf8') as temp:
            for line in temp.readlines():
                output.write(line)

        j = json.loads(r.text)

        height = 50
        last_time = 0
        for danmu in j:
            output.write('Dialogue: ')
            output.write('0,')

            start_time = int(danmu['time'] / 10)
            hundred_ms = danmu['time'] % 10
            m, s = divmod(start_time, 60)
            h, m = divmod(m, 60)
            output.write(f'{h:d}:{m:02d}:{s:02d}.{hundred_ms:d}0,')

            end_time = start_time + random.randint(13, 18)
            m, s = divmod(end_time, 60)
            h, m = divmod(m, 60)
            output.write(f'{h:d}:{m:02d}:{s:02d}.{hundred_ms:d}0,')

            if start_time - last_time >= 5:
                height = 50

            last_time = start_time

            output.write(
                'Default,,0,0,0,,{\\move(1920,' + str(height) + ',-500,' + str(height) + ')\\1c&H4C' + danmu['color'][1:] + '}')
            height = (height % 500) + 50
            output.write(danmu['text'])
            output.write('\n')

        err_print(self._sn, '彈幕下載完成', self._full_filename, status=2)

if __name__ == '__main__':
    pass
