# aniGamerPlus
巴哈姆特動畫瘋自動下載工具

windows 用戶可以[**點擊這裡**](https://github.com/miyouzi/aniGamerPlus/releases/tag/v5.1)下載exe文件使用.

ffmpeg 需要另外下載, [**點擊這裡前往下載頁**](https://ffmpeg.zeranoe.com/builds/). 若不知道如何將 ffmpeg 放入 PATH 則直接將 **ffmpeg.exe** 放在和本程式同一個文件夾下即可.

## 鳴謝

本項目m3u8获取模塊參考自 [BahamutAnimeDownloader](https://github.com/c0re100/BahamutAnimeDownloader) 

## 特性

 - 支持多綫程下載
 - 支持cookie，支持下載 1080P
 - 下載模式有僅下載最新一集, 下載最新上傳, 下載全部可選.
 - 自定義檢查更新間隔時間
 - 自定義番劇下載目錄
 - 自定義下載文件名前綴後綴及是否添加清晰度
 - 下載失敗, 下載過慢自動重啓任務
 - v6.0 開始支持cookie自動刷新
 - 支持使用FTP上傳至伺服器, 支持斷點續傳(適配Pure-Ftpd), 掉綫重傳, 支持 FTP over TLS
 - 檢查程序更新功能
 - 支持新番分類
 
 
## **注意**:warning:

Python 版本 3 以上

**本項目依賴ffmpeg, 請事先將ffmpeg放入系統PATH或者本程序目錄下!**

**使用前确认已安装好依赖**
```
pip3 install requests beautifulsoup4 lxml termcolor
```
 
## 任務列表
 - [ ] 下載使用代理
 - [x] 使用ftp上傳至遠程伺服器
 
 ~~咕咕咕~~
 
 
## 配置説明

:warning: **以下所有配置請使用UTF-8無BOM編碼** :warning:

**推薦使用 [notepad++](https://notepad-plus-plus.org/) 進行編輯**

### config.json

**config-sample.json**为范例配置文件, 可以将其修改后改名为**config.json**.

若不存在**config.json**, 则程序在运行时将会使用默认配置创建.

```
{
    "bangumi_dir": "",  # 下載存放目錄, 動畫將會以番劇為單位分文件夾存放
    "check_frequency": 5,  # 檢查更新頻率, 單位為分鐘
    "download_resolution": "1080",  # 下載選取清晰度, 若該清晰度不存在將會選取最近可用清晰度, 可選 360 480 720 1080
    "default_download_mode": "latest",  # 默認下載模式, 另一可選參數為 all 和 largest-sn. latest 為僅下載最後一集, all 下載番劇全部劇集, largest-sn 下載最近上傳的一集
    "multi-thread": 3,  # 最大并發下載數
    "multi_upload": 3,  # 最大并發上傳數
    "add_resolution_to_video_filename": true,  # 是否在影片文件名中添加清晰度, 格式舉例: [1080P]
    "customized_video_filename_prefix": "【動畫瘋】",  # 影片文件名前綴
    "customized_video_filename_suffix": "",  # 影片文件名後綴
    "check_latest_version": true,  # 檢查更新開關, 默認為 true
    "upload_to_server": true,  # 上傳功能開關
    "ftp": {  # FTP配置
        "server": "",  # FTP Server IP
        "port": "",  # 端口
        "user": "",  # 用戶名
        "pwd": "",  # 密碼
        "cwd": "",  # 登陸後首先進入的目錄
        "tls": true,  # 是否是 FTP over TLS
        "show_error_detail": false,  # 是否顯示細節錯誤信息
        "max_retry_num": 10  # 最大重傳數, 支持續傳
    },
    "config_version": 2.0,  # 配置文件版本
    "check_latest_version": true,  # 是否檢查更新
    "read_sn_list_when_checking_update": true,  # 是否在檢查更新時讀取sn_list.txt, 開啓後對sn_list.txt的更改將會在下次檢查更新時生效而不用重啓程序
    "read_config_when_checking_update": true  # 是否在檢查更新時讀取配置文件, 開啓後對配置文件的更改將會在下次檢查時更新生效而不用重啓程序
}
```

模式僅支持在 **latest**, **all**, **largest-sn** 三個中選一個, 錯詞及其他詞將會重置為**latest**模式

### cookie.txt

用戶cookie文件, 將瀏覽器的cookie字段複製, 已**cookie.txt**為文件名保存在程序目錄下即可

**v6.0版本開始支持自動刷新cookie, 爲了不與正常使用的cookie衝突, 請從使用瀏覽器的無痕模式取得僅供aniGamerPlus使用的cookie**

:warning: **登陸時請勾選"保持登入狀態"**

#### 使用Chrome舉例如何獲取 Cookie:

 - 開啓Chrome的無痕模式, 登陸動畫瘋, 記得勾選**保持登入狀態**

 - 按 F12 調出開發者工具, 前往動畫瘋, 切換到 Network 標簽, 在下方選中 "ani.gamer.com.tw" 在右側即可看到 Cookie, 如圖:
    ![](screenshot/WhereIsCookie.png)
    
 - 在程序所在目錄新建一個名爲**cookie.txt**的文本文件, 打開將上面的Cookie複製貼上保存即可
    ![](screenshot/CookiesFormat.png)

### sn_list.txt

需要自動下載的番劇列表,一個番劇中選任一sn填入即可

可以對個別番劇配置下載模式, 未配置下載模式將會使用**config.json**定義的默認下載模式

支持注釋 **#** 後面的所有字符程序均不會讀取, 可以標記番劇名

模式僅支持在 **latest**, **all**, **largest-sn** 三個中選一個, 錯詞及其他詞將會重置為**config.json**中定義的默認下載模式

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

自v6.0開始, 新增對番劇進行分類功能, 在一排番劇列表的上方 **@** 開頭後面的字符將會作爲番劇的分類名, 番劇會歸類在此分類名的文件夾下

若單獨 **@** 表示不分類

範例:
```
@2019一月番
11433 # ENDRO！
11392 # 笨拙之極的上野
@2019十月番
11354 latest # 刀劍神域 Alicization
@
11468 # 動物朋友
```
上面表示將會把**ENDRO**和**上野**放在**2019一月番**文件夾裏, 將**刀劍**放在**2019十月番**文件夾裏, **動物朋友** 不分類, 直接放在番劇目錄下

### aniGamer.db

:warning: v6.0版本與之前版本不兼容, 需要刪除舊版**aniGamer.db**

sqlite3資料庫, 可以使用 [SQLite Expert](http://www.sqliteexpert.com/) 等工具打開

記錄視頻下載狀態等相關信息, 一般無需改動

## 命令行使用

支持命令行使用, 文件默認將保存在**config.json**中指定的目錄下

**命令行模式將不會和資料庫進行交互, 將會無視數據庫中下載狀態標記强制下載**

參數:
```
>python3 aniGamerPlus.py -h
當前aniGamerPlus版本: v6.0
usage: aniGamerPlus.py [-h] --sn SN [--resolution {360,480,540,720,1080}]
                       [--download_mode {single,latest,largest-sn,all,range}]
                       [--thread_limit THREAD_LIMIT] [--current_path]
                       [--episodes EPISODES]

optional arguments:
  -h, --help            show this help message and exit
  --sn SN, -s SN        視頻sn碼(數字)
  --resolution {360,480,540,720,1080}, -r {360,480,540,720,1080}
                        指定下載清晰度(數字)
  --download_mode {single,latest,largest-sn,all,range}, -m {single,latest,largest-sn,all,range}
                        下載模式
  --thread_limit THREAD_LIMIT, -t THREAD_LIMIT
                        最高并發下載數(數字)
  --current_path, -c    下載到當前工作目錄
  --episodes EPISODES, -e EPISODES
                        僅下載指定劇集
```

 - **-s** 接要下載視頻的sn碼,不可空

 - **-r** 接要下載的清晰度, 可空, 空則讀取**config.json**中的定義, 不存在則選取最近可用清晰度

 - **-m** 接下載模式, 可空, 空則下載傳入sn碼的視頻
 
    - **single** 下載此 sn 單集(默認)
 
    - **all** 下載此番劇所有劇集
    
    - **latest** 下載此番劇最後一集(即網頁上顯示排最後的一集)
    
    - **largest-sn** 下載此番劇最近上傳的一集(即sn最大的一集)
    
    - **range** 下載此番指定的劇集

 - **-t** 接最大并發下載數, 可空, 空則讀取**config.json**中的定義
 
 - **-c** 開關, 指定時將會下載到當前工作路徑下

 - **-e** 下載此番劇指定劇集, 支持範圍輸入, 支持多個不連續聚集下載, 僅支持整數命名的劇集
    
    - -e 參數優先于 -m 參數, 使用 -e 參數時, 强制為 range 模式
    
    - 若使用 -m range 則必須使用 -e 指定需要下載的劇集
    
    - 若指定了不存在的劇集會警告並跳過, 僅下載存在的劇集
    
    - 指定不連續劇集請用英文逗號","分隔, 中間無空格
    
    - 指定連續劇集格式: 起始劇集-終止劇集. 舉例想下載第5到9集, 則格式為 5-9
    
    - 將會按劇集順序下載

    - 舉例:
    
        - 想下載第1,2,3集
        ```python3 aniGamerPlus.py -s 10218 -e 1,2,3```
        
        - 想下載第5到8集
        ```python3 aniGamerPlus.py -s 10218 -e 5-8```
        
        - 想下載第2集, 第5到8集, 第12集
        ```python3 aniGamerPlus.py -s 10218 -e 2,5-8,12```
    
    - 截圖:
    
        ![](screenshot/cui_range_mode.png)
        
        ![](screenshot/cui_range_mode_err.png)