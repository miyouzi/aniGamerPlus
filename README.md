<h1 align="center">aniGamerPlus</h1>

<p align="center">
 <img alt="GitHub" src="https://img.shields.io/github/license/miyouzi/aniGamerPlus.svg?style=flat-square">
 <img alt="GitHub release" src="https://img.shields.io/github/release/miyouzi/aniGamerPlus.svg?style=flat-square">
 <img alt="GitHub Release Date" src="https://img.shields.io/github/release-date/miyouzi/aniGamerPlus.svg?style=flat-square">
 <img alt="GitHub Releases" src="https://img.shields.io/github/downloads/miyouzi/aniGamerPlus/latest/total.svg?style=flat-square">
</p>

巴哈姆特動畫瘋自動下載工具, 可隨著番劇更新自動下載, 適合部署在全天開機的伺服器或NAS上.

同時支援命令行, 也適用於需要大批量下載的使用者, 如: 下載整部番劇. 命令行模式支援顯示下載進度, 但要求 **最大并發下載數** 設置為 **1** .

## **注意**:warning:

**本專案依賴ffmpeg, 請事先將ffmpeg放入系統PATH或者本程序目錄下!**

ffmpeg 需要另外下載, [**點擊這裡前往下載頁**](https://ffmpeg.org/download.html). 若不知道如何將 ffmpeg 放入 PATH 則直接將 **ffmpeg.exe** 放在和本程式同一個資料夾下即可.

## EXE 檔案運行(對於不熟悉Python的使用者)

windows 使用者可以[**點擊這裡**](https://github.com/miyouzi/aniGamerPlus/releases/latest)下載exe文件使用.

## 源碼運行

Python 版本 3 以上

下載源碼
```bash
git clone https://github.com/miyouzi/aniGamerPlus.git
```

**第一次使用前，進入原始碼所在資料夾，安裝依賴（重要）**
```bash
cd aniGamerPlus
pip3 install -r requirements.txt
```

升級
```bash
git pull https://github.com/miyouzi/aniGamerPlus.git
```

使用
```bash
python3 aniGamerPlus.py
```

## Docker 運行

### (可選) 建構自己的 Image

下載原始碼

```bash
git clone https://github.com/miyouzi/aniGamerPlus.git
```

Build Image

```bash
docker build -t anigamerplus .
```

## 下載官方 Image

目前官方 Image 放在 `tonypepe/anigamerplus`

使用前需在本地先創建好 config.json，並綁定 config.json 和下載目錄至 Container 內。

注意：

1. confg.json 中的 Dashboard Host 請設定成 `0.0.0.0`，切勿設定 `127.0.0.1`.
2. config.json 勿設定下載目錄 `bangumi_dir: ""`，請保持為空，以免目錄綁定失敗。
3. 可綁定 cookie.txt 至 `/app/cookie.txt`

使用：

```bash
docker run -td --name anigamerplus \
    -v /path/to/config.json:/app/config.json \
    -v /path/to/download:/app/bangumi \
    -v /path/to/aniGamer.db:/app/aniGamer.db \
    -p 5000:5000 \
    tonypepe/anigamerplus
```

啟動後可至 `localhost:5000` 使用 [Dashboard](#dashboard)。

## 鳴謝

本專案m3u8获取模塊參考自 [BahamutAnimeDownloader](https://github.com/c0re100/BahamutAnimeDownloader)

## 第三方拓展工具
 - [aniGamerPlus-swapHistorySnList](https://github.com/chumicat/aniGamerPlus-swapHistorySnList)
    - 將資料庫中的番劇導出到sn_list, 可方便的與原來的sn_list相互切換, 適用於你想檢查過往番劇是否有更新時.

## 目錄

* [特性](#特性)
* [注意](#注意warning)
* [任務列表](#任務列表)
* [配置説明](#配置説明)
    * [主配置 config.json](#configjson)
    * [使用代理](#使用代理)
    * [下載模式説明](#下載模式説明)
    * [使用 cookie](#cookietxt)
    * [自動下載配置 sn_list.txt](#sn_listtxt)
    * [任務狀態資料庫 aniGamer.db](#anigamerdb)
* [命令行使用](#命令行使用)
* [Web控制臺使用](#Dashboard)

## 特性

 - 支援多綫程下載
 - 支援cookie，支援下載 1080P
 - 下載模式有僅下載最新一集, 下載最新上傳, 下載全部可選.
 - 自定義檢查更新間隔時間
 - 自定義番劇下載目錄
 - 自定義下載檔名前綴後綴及是否添加清晰度
 - 下載失敗, 下載過慢自動重啓任務
 - 支援使用FTP上傳至伺服器, 支援斷點續傳(適配Pure-Ftpd), 掉綫重傳, 支援 FTP over TLS
 - 檢查程序更新功能
 - 支援新番分類
 - v6.0 開始支援cookie自動刷新
 - v7.0 開始支援使用(鏈式)代理
 - v9.0 開始支援記錄日志
 - v9.0 開始自動下載支援自定義番劇名
 - v16 支援向酷Q推送下載完成訊息
 - v16 支援将影片 metadata 前置, 此功能會在綫觀看时更快播放
 - v20 上綫Web控制面板
 - v20.2 支援命令行下載時同時下載彈幕

## 任務列表
 - [x] 下載使用代理
 - [x] 使用ftp上傳至遠程伺服器
 - [x] Web控制臺(持續完善中)

## 配置説明

### config.json

**config-sample.json**为范例配置文件, 可以将其修改后改名为**config.json**.

若不存在**config.json**, 则程序在运行时将会使用默认配置创建.

```jsonc
{
    "bangumi_dir": "",  // 下載存放目錄, 動畫將會以番劇為單位分資料夾存放
    "temp_dir": "",  // 臨時目錄位置, v9.0 開始下載中文件將會放在這裏, 完成後再轉移至番劇目錄, 留空默認在程序所在目錄的 temp 資料夾下
    "classify_bangumi": true,  // 控制是否建立番劇資料夾
    "classify_season": false,  // 控制是否建立季度子目錄
    "check_frequency": 5,  // 檢查更新頻率, 單位為分鐘
    "download_resolution": "1080",  // 下載選取清晰度, 若該清晰度不存在將會選取最近可用清晰度, 可選 360 480 540 576 720 1080
    "lock_resolution": false,  // 鎖定清晰度, 如果指定清晰度不存在, 則放棄下載
    "only_use_vip": false,  // 锁定 VIP 账号下载
    "default_download_mode": "latest",  // 默認下載模式, 另一可選參數為 all 和 largest-sn. latest 為僅下載最後一集, all 下載番劇全部劇集, largest-sn 下載最近上傳的一集
    "use_copyfile_method": false,  // 轉移影片至番劇資料夾時使用複製方法, 適用於保存到 rclone 掛載盤的情況
    "multi-thread": 1,  // 最大并發下載數, 最高為 5, 超過將重置為 5
    "multi_upload": 3,  // 最大并發上傳數
    "segment_download_mode": true,  // 分段下載模式, 速度更快, 容錯率更高
    "segment_max_retry": 8,  // 在分段下載模式時有效, 每個分段最大重試次數, -1 為無限重試
    "multi_downloading_segment": 3,  // 每個影片最大并發下載分段數, 僅在 "segment_download_mode" 為 true 時有效, 最高為 5, 超過將重置為 5
    "add_bangumi_name_to_video_filename": true,  // 如果為 false, 則只有劇集名, 若劇集名為個位數字, 則補零
    "add_resolution_to_video_filename": true,  // 是否在影片檔名中添加清晰度, 格式舉例: [1080P]
    "customized_video_filename_prefix": "【動畫瘋】",  // 影片檔名前綴
    "customized_bangumi_name_suffix": "",  // 影片檔名中番劇名的后缀, 在劇集名之前
    "customized_video_filename_suffix": "",  // 影片檔名後綴
    "video_filename_extension": "mp4",  // 影片檔副檔名, ts, mov, mkv 經過測試可以使用, 但 flv 不支援, 非 mp4 副檔名 faststart_movflags 將强制為 false
    "zerofill": 1,  // 劇集名補零, 填寫補足位數, 例: 填寫 2 劇集名為 01, 填寫 3 劇集名為 001
    "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.96 Safari/537.36",  //  請求UA, 需要和獲取cookie的瀏覽器相同
    "use_proxy": false,  // 代理開關
    "proxy": {"http://user:passwd@example.com:1000"},  // 代理配置
    "upload_to_server": false,  // 上傳功能開關
    "ftp": {  // FTP配置
        "server": "",  // FTP Server IP
        "port": "",  // 端口
        "user": "",  // 使用者名
        "pwd": "",  // 密碼
        "tls": true,  // 是否是 FTP over TLS
        "cwd": "",  // 登陸後首先進入的目錄
        "show_error_detail": false,  // 是否顯示細節錯誤信息
        "max_retry_num": 15  // 最大重傳數, 支援續傳
    },
    "user_command": "shutdown -s -t 60"  // 命令行模式使用 -u 參數有效, 在命令行模式下完成所有任務后執行的命令
    "coolq_notify": false,  // 是否向酷Q推送下載完成訊息
    "coolq_settings": {
        "msg_argument_name": "message",
        "message_suffix": "追加的資訊",
        "query": [
            "http://127.0.0.1:5700/send_group_msg?access_token=abc&group_id=12345678",
            "http://127.0.0.1:5700/send_group_msg?access_token=abc&group_id=87654321"
        ]
    },
    "plex_naming": false, // 適配PLEX命名規則
    "faststart_movflags": false,  // 是否將影片 metadata 前置, 啓用此功能時在綫觀看會更快播放, 僅在 video_filename_extension 為 mp4 時有效
    "audio_language": false,  // 是否添加音軌標簽
    "use_mobile_api": false,  // 使用移動端API進行影片解析
    "danmu": false, // 是否下載彈幕(已包含動畫瘋內建的關鍵字過濾)
    "danmu_ban_words": [], // 額外過濾彈幕關鍵字(支援python的正規表示式、英文不區分大小寫)
    "check_latest_version": true,  // 是否檢查更新
    "read_sn_list_when_checking_update": true,  // 是否在檢查更新時讀取sn_list.txt, 開啓後對sn_list.txt的更改將會在下次檢查更新時生效而不用重啓程序
    "read_config_when_checking_update": true,  // 是否在檢查更新時讀取配置文件, 開啓後對配置文件的更改將會在下次檢查時更新生效而不用重啓程序
    "ads_time": 25,  // 非VIP廣告等待時間, 如果等待時間不足, 程式會自行追加時間 (最大20秒)
    "mobile_ads_time":3  // 使用移動端API解析的廣告等待時間
    "use_dashboard": true  // Web 控制台開關
    "dashboard": {  // Web控制面板配置
        "host": "127.0.0.1",  // 監聽地址, 如果需要允許外部訪問, 請填寫 "0.0.0.0"
        "port": 5000,  // 監聽端口
        "SSL": false,  // 是否開啓SSL, 證書保存在 Dashboard\sslkey, 如果有需要可以自行替換證書
        "BasicAuth": false,  // 是否使用 BasicAuth 進行認證, 注意, 用戶密碼是明文傳輸的, 如有需要建議同時啓用 SSL
        "username": "admin",  // BasicAuth 用戶名
        "password": "admin"  // BasicAuth 密碼
    },
    "save_logs": true,  // 是否記錄日志, 一天一個日志
    "quantity_of_logs": 7,  // 日志保留數量, 正整數值, 必須大於等於 1, 默認為 7
    "config_version": 14.0,  // 配置文件版本
    "database_version": 2.0  // 資料庫版本
}
```

模式僅支援在 **latest**, **all**, **largest-sn** 三個中選一個, 錯詞及其他詞將會重置為**latest**模式

### 使用代理
aniGamerPlus本身支援使用單個```http```或```https```或```socks5```(v12開始支援)代理.

無密碼驗證的代理使用以下格式:
```
http://example.com:1000
```

有密碼驗證的代理使用以下格式:
```
http://user:passwd@example.com:1000
```

使用socks5代理支援遠端DNS, 配置時使用```socks5h```代替```socks5```, 如:
```
socks5h://127.0.0.1:1483
```

如果想使用其他的代理協議或使用鏈式代理, 需要下載 [**Gost**](https://github.com/ginuerzh/gost) 放置在系統PATH, 或本程序目錄下, 並命名爲 ```gost```, windows平臺為```gost.exe```

若想使用鏈式代理, 請使用整數作爲 key, 代理出口將會是 key 最大的代理服務器.

Gost 支援 Shadowsocks 協議, 其實現是基於[shadowsocks-go](https://github.com/shadowsocks/shadowsocks-go), 目前僅支援這幾種加密方式: ```aes-128-cfb``` ```aes-192-cfb``` ```aes-256-cfb``` ```bf-cfb``` ```cast5-cfb``` ```des-cfb``` ```rc4-md5``` ```rc4-md5-6``` ```chacha20``` ```salsa20``` ```rc4``` ```table```

**注意: ```read_config_when_checking_update``` 配置對代理配置無效**

**使用代理建議使用分段下載模式**

**如果代理網路不穩定, 建議```multi-thread```配置為```1```**

### 下載模式説明

v8.0 影片下載模式新增分段下載, 其工作流程: 由 aniGamerPlus 讀取 m3u8 文件, 下載 key 及所有影片分段至臨時資料夾, 再使用 ffmpeg 解密合并.

**分段下載模式特點:**

- 分段下載模式速度更快
- 個別分段下載失敗會自動重試, 最多重試8次
- aniGamerPlus本身消耗的記憶體將略高於舊下載模式
- aniGamerPlus本身性能消耗將會略高
- 短時間内(解密合并階段)將會占用2倍影片大小的磁盤空間
- 命令行模式下下載單個視頻時, 實時顯示已下載分段數占總分段數百分比

舊下載模式, 即 ffmpeg 下載模式的工作流程: 直接將 m3u8 文件交給 ffmpeg, 下載解密合并全由 ffmpeg 完成.

**ffmpeg下載模式特點:**

- 一個分段下載失敗即判斷爲下載失敗
- 在下載過程中可能出現 ffmpeg 卡死的情況
- 不會生成臨時資料夾
- 命令行模式下下載單個視頻時, 實時顯示已下載的大小


除非你通往動畫瘋的網路足夠穩, 否則建議使用分段下載模式, 配置 ```segment_download_mode``` 為 ```true``` 開啓分段下載模式

儅開啓分段下載模式時, 配置 ```multi_downloading_segment``` 將有效, 這個值指定一個影片同時最多下載幾個分段, 一般設定在```3```左右速度就足夠快了

### cookie.txt

1.  使用者cookie文件, 將瀏覽器的cookie字段複製, 以**cookie.txt**為檔名保存在程序目錄下
2.  將獲取cookie的瀏覽器UA, 写入```config.json```的```ua```項目

**v6.0版本開始支援自動刷新cookie, 爲了不與正常使用的cookie衝突, 請從使用瀏覽器的無痕模式取得僅供aniGamerPlus使用的cookie**

取得cookie后, 登陸狀態會顯示在 **https://home.gamer.com.tw/login_devices.php** , 你可以從這裏點擊```退出```來失效你的cookie, 其顯示的信息來自與你取得cookie的瀏覽器(UA)

使用cookie后所抓取的影片記錄會記錄在你的[觀看紀錄](https://ani.gamer.com.tw/viewList.php)中

:warning: **登陸時請勾選"保持登入狀態"**

#### 使用Chrome舉例如何獲取 Cookie:

 - 開啓Chrome的**無痕模式**, 登陸動畫瘋, 記得勾選**保持登入狀態**

 - 按 F12 調出開發者工具, 前往動畫瘋首頁, 切換到 Network 標簽, 在下方選中 "ani.gamer.com.tw" 在右側即可看到 Cookie, 如圖:
    ![](screenshot/WhereIsCookie.png)

 - 在程序所在目錄新建一個名爲**cookie.txt**的文本文件, 打開將上面的Cookie複製貼上保存即可
    ![](screenshot/CookiesFormat.png)

#### 使用Chrome舉例如何獲取 UA:

 - 訪問 **https://developers.whatismybrowser.com/useragents/parse/?analyse-my-user-agent=yes** 即可查看該瀏覽器 UA
 - 如果此網址失效，以下為可查詢UA的備用網址：
    - https://www.whatsmyua.info/
    - http://service.spiritsoft.cn/ua.html
    ![](screenshot/how_to_get_my_ua.png)

 - 將 UA 複製粘貼到```config.json```的```ua```項目
    ![](screenshot/how_to_use_my_ua.png)

### sn_list.txt

需要自動下載的番劇列表,一個番劇中選任一sn填入即可

可以對個別番劇配置下載模式, 未配置下載模式將會使用**config.json**定義的默認下載模式

支援注釋 **#** 後面的所有字符程序均不會讀取, 可以標記番劇名

模式僅支援在 **latest**, **all**, **largest-sn** 三個中選一個, 錯詞及其他詞將會重置為**config.json**中定義的默認下載模式

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

自v6.0開始, 新增對番劇進行分類功能, 在一排番劇列表的上方 **@** 開頭後面的字符將會作爲番劇的分類名, 番劇會歸類在此分類名的資料夾下

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
上面表示將會把**ENDRO**和**上野**放在**2019一月番**資料夾裏, 將**刀劍**放在**2019十月番**資料夾裏, **動物朋友** 不分類, 直接放在番劇目錄下

自 v9.0 開始, 支援重命名番劇, 在注釋之前, 模式之後, 用 ```<``` 與 ```>``` 將自定義的番劇名框起來, 下載時將會使用這個名字作爲番劇目錄名

PS: 連續多個空格將會被替換爲單個空格, 和模式需要間隔一個空格

範例:
```
11415 <魔法少女特殊战明日香> # 魔法少女特殊戰明日香
11433 <えんどろ～！> # ENDRO！
11354 latest <刀剑神域3> # 刀劍神域 Alicization
11398 # 粉彩回憶
```

### aniGamer.db

sqlite3資料庫, 可以使用 [SQLite Expert](http://www.sqliteexpert.com/) 等工具打開編輯

記錄視頻下載狀態等相關信息, 一般無需改動

欄位設計:
- ```sn``` sn值 (PK)
- ```title``` 完整標題
- ```anime_name``` 番劇名
- ```episode``` 劇集名, 一般爲數字, 也可能是```特別篇``` ```電影``` 等
- ```status``` 下載狀態, ```0``` 為未成功下載, ```1``` 為已成功下載
- ```remote_status``` 上傳状态, ```0``` 為未成功上傳, ```1``` 為已成功上傳
- ```resolution``` 下載的影片檔解析度
- ```file_size``` 影片檔大小, 整數, 單位MB
- ```local_file_path``` 影片檔路徑
- ```CreatedTime``` 資料創建時間

截图:
![](screenshot/db.png)


## 命令行使用

支援命令行使用, 文件默認將保存在**config.json**中指定的目錄下

**配置文件中的代理配置同樣適用於命令行模式!**

**除了使用 list 模式的情況, 命令行模式將不會和資料庫進行交互, 將會無視數據庫中下載狀態標記强制下載**

**EXE 檔的 aniGamerPlus.exe 也是支援命令行使用的, 將下方演示的 ```python3 aniGamerPlus.py``` 換成 ```aniGamerPlus``` 就行**

參數:
```
>python3 aniGamerPlus.py -h
當前aniGamerPlus版本: v24.0
usage: aniGamerPlus.py [-h] [--sn SN]
                       [--resolution {360,480,540,576,720,1080}]
                       [--download_mode {single,latest,largest-sn,multi,all,range,list,sn-list,sn-range}]
                       [--thread_limit THREAD_LIMIT] [--current_path]
                       [--episodes EPISODES] [--no_classify]
                       [--information_only] [--user_command] [--danmu] [--my_anime]

optional arguments:
  -h, --help            show this help message and exit
  --sn SN, -s SN        視頻sn碼(數字)
  --resolution {360,480,540,576,720,1080}, -r {360,480,540,576,720,1080}
                        指定下載清晰度(數字)
  --download_mode {single,latest,largest-sn,multi,all,range,list,sn-list,sn-range}, -m {single,latest,largest-sn,multi,all,range,list,sn-list,sn-range}
                        下載模式
  --thread_limit THREAD_LIMIT, -t THREAD_LIMIT
                        最高并發下載數(數字)
  --current_path, -c    下載到當前工作目錄
  --episodes EPISODES, -e EPISODES
                        僅下載指定劇集
  --no_classify, -n     不建立番劇資料夾
  --information_only, -i
                        僅查詢資訊
  --user_command, -u    所有下載完成后執行用戶命令
  --danmu, -d           以 `.ass` 下載彈幕
  --my_anime            匯出「我的動畫」至 `my_anime.txt`，和 sn_list 所需的格式相同
```

 - **-s** 接要下載視頻的sn碼,不可空

 - **-r** 接要下載的清晰度, 可空, 空則讀取**config.json**中的定義, 不存在則選取最近可用清晰度

 - **-m** 接下載模式, 可空, 空則下載傳入sn碼的視頻

    - **single** 下載此 sn 單集(默認)

    - **multi** 下載多個sn, 啓用此模式時, 通過```-e```傳入多個sn, sn之間使用英文```,```分割

    - **all** 下載此番劇所有劇集

    - **latest** 下載此番劇最後一集(即網頁上顯示排最後的一集)

    - **largest-sn** 下載此番劇最近上傳的一集(即sn最大的一集)

    - **range** 下載此番指定的劇集

    - **list** 讀取 sn_list 中的内容進行下載, 並會將任務狀態記錄在資料庫中, 重啓自動下載未完成的集數, 該功能用於單次大量下載. **此模式無法通過```-r```參數指定解析度**

    - **sn-list** 讀取 sn_list 中的指定sn進行下載, sn後面的模式設定會被忽略，僅下載單個sn, 並會將任務狀態記錄在資料庫中. **此模式無法通過```-r```參數指定解析度**
    
    - **sn-range** 下載此番据指定sn範圍的劇集, 對於劇集名稱不是正整數的番劇, 可以用此模式

 - **-t** 接最大并發下載數, 可空, 空則讀取**config.json**中的定義

 - **-c** 開關, 指定時將會下載到當前工作路徑下

 - **-n** 不建立番劇資料夾

 - **-i** 僅顯示影片資訊, 當爲```list```模式時, 會獲取 sn_list 中的單個 sn 的資訊.

 - **-u** 所有任務完成后執行使用者命令 (配置在```config.json```的```user_command```中),  用於實現下載完成后關機等操作

 - **-d** 下載 `.ass` 彈幕，推薦使用 XySubFilter 進行字幕渲染

 - **-e**
    - **在 ```range``` 模式下, 下載此番劇指定劇集, 支援範圍輸入, 支援多個不連續聚集下載, 僅支援整數命名的劇集**

    - **在 ```multi``` 模式下, 用於指定多個sn**

    - ```-e``` 參數優先于 ```-m``` 參數, 若使用 ```-e``` 參數時不指定模式, 則默認為 ```range``` 模式

    - 若使用 ```-m range``` 則必須使用 ```-e``` 指定需要下載的劇集

    - 在 ```range``` 模式下, 若指定了不存在的劇集會警告並跳過, 僅下載存在的劇集

    - 指定不連續劇集或sn時, 請用英文逗號```,```分隔, 中間無空格

    - 在 ```range``` 模式下, 指定連續劇集格式: 起始劇集-終止劇集. 舉例想下載第5到9集, 則格式為 5-9
    
    - 在 ```sn-range``` 模式下, 格式同 ```range``` 模式, 不過將劇集改成 sn 碼

    - 將會按sn順序下載

    - 舉例:

        - 想下載某番劇第1,2,3集
        ```python3 aniGamerPlus.py -s 10218 -e 1,2,3```

        - 想下載某番劇第5到8集
        ```python3 aniGamerPlus.py -s 10218 -e 5-8```

        - 想下載某番劇第2集, 第5到8集, 第12集
        ```python3 aniGamerPlus.py -s 10218 -e 2,5-8,12```
        
        - 想下載某番劇sn範圍 14440 到 14459 的劇集, 外加 sn 為 14670 和 14746 的兩集
        ```python3 aniGamerPlus.py -s 14440 -m sn-range -e 14670,14746,14440-14459```

        - 想下載sn為 14479,14518,14511 的動畫
        ```aniGamerPlus.py -m multi -e 14479,14518,14511```

    - 截圖:

        ![](screenshot/cui_range_mode.png)

        ![](screenshot/cui_range_mode_err.png)

        在Android中使用 (使用Termux)

        ![](screenshot/cui_on_android.jpg)

## Dashboard

在 v20 版本首次啓用了 Web 控制臺, 相關配置在 ```config.json``` 的 ```dashboard``` 項目中.

Web 控制臺默認啓用, 默認端口 5000, 支援 SSL (https), 證書保存在 Dashboard\sslkey, 如果有需要可以自行替換證書.

如果想開放外部訪問, 可以將 ```dashboard``` 配置中的 ```host``` 設置成 ```0.0.0.0```

支援使用 BasicAuth 進行認證, **注意**:warning: **用戶密碼是明文傳輸的, 如有需要建議同時啓用 SSL**.

支援在 Web 控制臺下達手動任務(即命令行模式啓動的任務), 爲了控制臺輸出工整, 控制臺不會顯示下載進度.

**目前控制臺僅能配置部分主要配置, 另外Web任務進度顯示等其他擴展功能正在銳意製作中……**

相關配置:
```
"use_dashboard": true  # Web 控制台開關
# Web控制面板配置
"dashboard": {
    "host": "127.0.0.1",  # 監聽地址, 如果需要允許外部訪問, 請填寫 "0.0.0.0"
    "port": 5000,  # 監聽端口
    "SSL": false,  # 是否開啓SSL
    "BasicAuth": false,  # 是否使用 BasicAuth 進行認證
    "username": "admin",  # BasicAuth 用戶名
    "password": "admin"  # BasicAuth 密碼
}
```

Web控制臺截圖:
 - 主界面:
    ![](screenshot/Dashboard_UI.png)
 - 手動任務:
    ![](screenshot/Dashboard_manualTask.png)
 - 在綫編輯 sn_list
    ![](screenshot/Dashboard_sn_list.png)
 - 控制臺輸出:
    ![](screenshot/Dashboard_Console.png)
