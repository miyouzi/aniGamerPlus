# aniGamerPlus
巴哈姆特動畫瘋自動下載工具

## 鳴謝

本項目m3u8获取模塊參考自 [BahamutAnimeDownloader](https://github.com/c0re100/BahamutAnimeDownloader) 

## 特性

 - 支持多綫程下載
 - 支持cookie，支持下載 1080P
 - 下載模式有僅下載最新, 下載全部可選.
 - 自定義檢查更新間隔時間
 - 自定義番劇下載目錄
 - 自定義下載文件名前綴後綴及是否添加清晰度
 
 
## **注意**:warning:

**本項目依賴ffmpeg, 請事先將ffmpeg放入系統PATH或者本程序目錄下!**

**使用前确认已安装好依赖**
```
pip install requests beautifulsoup4
```
 
## 待完成
 - [ ] 下載使用代理
 - [ ] 使用ftp上傳至遠程伺服器
 
 ~~咕咕咕~~
 
 
## 配置説明

:warning: **以下所有配置請使用UTF-8無BOM編碼** :warning:

### config.json

**config-sample.json**为范例配置文件, 可以将其修改后改名为**config.json**.

若不存在**config.json**, 则程序在运行时将会使用默认配置创建.

```
{
    "bangumi_dir": "",  # 下載存放目錄, 動畫將會以番劇為單位分文件夾存放
    "check_frequency": 5,  # 檢查更新頻率, 單位為分鐘
    "download_resolution": "1080",  # 下載選取清晰度, 若該清晰度不存在將會選取最高清晰度, 可選 360 480 720 1080
    "default_download_mode": "latest",  # 默認下載模式, 另一可選參數為 all. latest 為僅下載最新, all 下載番劇全部劇集
    "multi-thread": 3,  # 最大并發下載數
    "add_resolution_to_video_filename": true,  # 是否在影片文件名中添加清晰度, 格式舉例: [1080P]
    "customized_video_filename_prefix": "【動畫瘋】",  # 影片文件名前綴
    "customized_video_filename_suffix": "",  # 影片文件名後綴
    "config_version": 0.1
}
```

### cookies.txt

用戶cookie文件, 將瀏覽器的cookie字段複製, 已**cookies.txt**為文件名保存在程序目錄下即可


### sn_list.txt

需要自動下載的番劇列表,一個番劇中選任一sn填入即可

可以對個別番劇配置下載模式, 未配置下載模式將會使用**config.json**定義的默認下載模式

支持注釋 **#** 後面的所有字符程序均不會讀取, 可以標記番劇名

格式:
```
sn碼 下載模式(可空) #注釋(可空)
```

範例:
```
10147 all # 前進吧！登山少女 第三季 [1]
11285 # 關於我轉生變成史萊姆這檔事
11390 all #笑容的代價 01
11388 # BanG Dream！第二季
11317 lastest # SSSS.GRIDMAN
```

### aniGamer.db

sqlite3資料庫, 可以使用 [SQLite Expert](http://www.sqliteexpert.com/) 等工具打開

記錄視頻下載狀態等相關信息, 一般無需改動

## 命令行使用

支持命令行使用, 文件將保存在**config.json**中指定的目錄下

參數:
```
>python aniGamerPlus.py -h
usage: sn [resolution] [download_mode] [thread_limit]

optional arguments:
  -h, --help            show this help message and exit
  --sn SN, -s SN        視頻sn碼(數字)
  --resolution {360,480,720,1080}, -r {360,480,720,1080}
                        指定下載清晰度(數字)
  --download_mode {single,latest,all}, -m {single,latest,all}
                        下載模式
  --thread_limit THREAD_LIMIT, -t THREAD_LIMIT
                        最高并發下載數(數字)
python aniGamerPlus.py -s SN -r RESOLUTION -m DOWNLOAD_MODE -t THREAD_LIMIT
```

**-s** 接要下載視頻的sn碼,不可空

**-r** 接要下載的清晰度, 可空, 空則讀取**config.json**中的定義

**-m** 接下載模式, 可空, 空則下載傳入sn碼的視頻, 另有 **all** 下載此番劇所有劇集 和 **latest** 下載此番劇最新一集可選

**-t** 接最大并發下載數, 可空, 空則讀取**config.json**中的定義