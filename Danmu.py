
import requests
import json
import random
import os
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
            err_print(self._sn, '彈幕下載失敗', 'status_code=' + str(r.status_code), status=1)
            return

        output = open(self._full_filename, 'w', encoding='utf8')
        danmu_template_file = os.path.join(os.path.dirname(__file__), 'DanmuTemplate.ass')
        with open(danmu_template_file, 'r', encoding='utf8') as temp:
            for line in temp.readlines():
                output.write(line)

        j = json.loads(r.text)
        height = 50
        roll_channel = list()
        roll_time = list()

        for danmu in j:
            output.write('Dialogue: ')
            output.write('0,')

            start_time = int(danmu['time'] / 10)
            hundred_ms = danmu['time'] % 10
            m, s = divmod(start_time, 60)
            h, m = divmod(m, 60)
            output.write(f'{h:d}:{m:02d}:{s:02d}.{hundred_ms:d}0,')

            if danmu['position'] == 0:  # Roll danmu
                height = 0
                end_time = 0
                for i in range(len(roll_channel)):
                    if roll_channel[i] <= danmu['time']:
                        height = i * 54 + 27
                        roll_channel[i] = danmu['time'] + \
                            (len(danmu['text']) * roll_time[i]) / 8 + 1
                        end_time = start_time + roll_time[i]
                        break
                if height == 0:
                    roll_channel.append(0)
                    roll_time.append(random.randint(10, 14))
                    roll_channel[-1] = danmu['time'] + (len(danmu['text']) * roll_time[-1]) / 8 + 1
                    height = len(roll_channel) * 54 - 27
                    end_time = start_time + roll_time[-1]

                m, s = divmod(end_time, 60)
                h, m = divmod(m, 60)
                output.write(f'{h:d}:{m:02d}:{s:02d}.{hundred_ms:d}0,')

                output.write(
                    'Roll,,0,0,0,,{\\move(1920,' + str(height) + ',-1000,' + str(height) + ')\\1c&H4C' + danmu['color'][1:] + '}')
            elif danmu['position'] == 1:  # Top danmu
                end_time = start_time + 5
                m, s = divmod(end_time, 60)
                h, m = divmod(m, 60)
                output.write(f'{h:d}:{m:02d}:{s:02d}.{hundred_ms:d}0,')
                output.write(
                    'Top,,0,0,0,,{\\1c&H4C' + danmu['color'][1:] + '}')
            else:  # Bottom danmu
                end_time = start_time + 5
                m, s = divmod(end_time, 60)
                h, m = divmod(m, 60)
                output.write(f'{h:d}:{m:02d}:{s:02d}.{hundred_ms:d}0,')
                output.write(
                    'Bottom,,0,0,0,,{\\1c&H4C' + danmu['color'][1:] + '}')

            output.write(danmu['text'])
            output.write('\n')

        err_print(self._sn, '彈幕下載完成', self._full_filename, status=2)


if __name__ == '__main__':
    pass
