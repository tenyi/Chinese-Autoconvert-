#Readme 說明 （內有安裝步驟）

## Introduction ##

Auto convert locae Chinese  vocabulary program.

中文詞彙自動轉檔程式

目前只做簡轉繁，其他需求請自行修改。所有的轉出檔一律採用UTF-8編碼，並加上BOM。

支援 使用者自訂字典 

使用說明: g2butf8 [檔名]

usage: g2butf8.py [-h] [-r] [-nb] [-nobom] [-x extension [extension ...]] [-t type] [-u userdic] [-nu] files [files ...]

positional arguments:
  files                 會自動偵測編碼，再轉換成有BOM的UTF-8

optional arguments:
  -h, --help            show this help message and exit
  -r, --recursive       包含子目錄(預設不包括)
  -nb, --nobackup       不要產生.bak備份檔 (預設有)
  -nobom, --nobom       不要產生BOM標題 (預設有)
  -x extension [extension ...]  副檔名, (預設為所有檔案)
  -t type, --type type  轉換方式: g2b 簡轉繁   g2bdic 簡轉繁再加上詞彙轉換
  -u userdic, --userdic userdic  使用者字典檔名，預設使用 userdic.txt
  -nu, --nouserdic      不使用自訂字典檔  (預設有，使用userdic.txt)
若有特別的轉換需求，可以在要轉檔的目錄下放 userdic.txt ，範例內容:

```
頭發=頭髮
內存=記憶體
```


 **使用方法** 

Windows:


```
g2butf8 c:\城市獵人\*.srt
```



Mac、Linux:


```
python g2butf8.py ~/城市獵人/*.srt
```



 **Details　細節**

原本打算用C語言，因為某些庫編譯太麻煩，相依性過高，要跨平台太麻煩；因此改用Python實作。
原本因函式庫限制採用Pyhon 2，現在改用Python 3。

## Install 安裝 ##

### Linux 或 Mac : ###


1. 安裝 HanziConv與Universal Encoding Detector 


```
> sudo pip install -U  chardet hanziconv 

```


### Windows: ###
C:\> pip install -U chardet hanziconv 

  沒有裝Python也沒關係，下載Windows的zip包解開即可用．

[g2butf8_amd64.zip](https://drive.google.com/file/d/0B_twESMPpEmWSEFMTXRSWTBaZWs/view?usp=sharing)  （暫未更新）

[g2butf8_win32.zip](https://drive.google.com/file/d/0B_twESMPpEmWdmxyZHVDOUFYemM/view?usp=sharing) （暫未更新）

**Reference 參考資料及函式庫**

[Python简繁转换](http://gerry.lamost.org/blog/?p=603)

[Jianfan](https://pypi.python.org/pypi/Jianfan)

[Universal Encoding Detector](http://chardet.feedparser.org/)

[開放中文轉換](http://code.google.com/p/opencc/opencc)

[Unicode In Python, Completely Demystified](http://farmdev.com/talks/unicode/)