#Readme 說明 （內有安裝步驟）

## Introduction ##

Auto convert locae Chinese  vocabulary program.

中文詞彙自動轉檔程式

目前只做簡轉繁，其他需求請自行修改。所以的轉出檔一律採用UTF-8編碼，並加上BOM。

支援 使用者自訂字典 

使用說明: g2butf8 [檔名]

若有特別的轉換需求，可以在要轉檔的目錄下放 userdic.txt ，範例內容:

```
#!text

頭發=頭髮
內存=記憶體
```


 **使用方法** 

Windows:


```
#!shell

g2butf8 c:\城市獵人\*.srt
```



Mac、Linux:


```
#!shell

python g2butf8.py ~/城市獵人/*.srt
```



 **Details　細節**

原本打算用C語言，因為某些庫編譯太麻煩，相依性過高，後來改用Python實作。
目前採用Pyhon 2，有空會修改出Python 3版本

## Install 安裝 ##

### Linux: ###


1. 安裝 Universal Encoding Detector


```
#pip install chardet

```


2. 安裝 python-jianfan

```
#pip install jianfan

```

最後，解開此處的src包，在g2butf8目錄下，執行 python g2butf8.py 即可

### Mac : ###

 
1. 安裝 Universal Encoding Detector


```
#pip install chardet

```


2. 安裝 python-jianfan

```
#pip install jianfan

```


最後，解開此處的src包，在g2butf8目錄下，執行 python g2butf8.py 即可

### Windows: ###
  沒有裝Python也沒關係，下載Windows的zip包解開即可用．

[g2butf8_amd64.zip](https://drive.google.com/file/d/0B_twESMPpEmWSEFMTXRSWTBaZWs/view?usp=sharing  )  （暫未更新）

[g2butf8_win32.zip](https://drive.google.com/file/d/0B_twESMPpEmWdmxyZHVDOUFYemM/view?usp=sharing) （暫未更新）

**Reference 參考資料及函式庫**

[Python简繁转换](http://gerry.lamost.org/blog/?p=603)

[Universal Encoding Detector](http://chardet.feedparser.org/)

[開放中文轉換](http://code.google.com/p/opencc/ opencc)

[Unicode In Python, Completely Demystified](http://farmdev.com/talks/unicode/)