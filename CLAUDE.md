# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 專案本質

`chinese-autoconvert` 是一個「簡轉繁」批次轉檔 CLI，會自動偵測來源編碼、把簡體中文轉成繁體中文（OpenCC `s2twp`，含台灣慣用詞彙），再套用自訂詞彙表，輸出成 UTF-8（是否加 BOM 可選）。

主要使用情境：把簡體字幕、文本檔批次轉成繁體中文供繁體使用者使用。

## 執行入口

- **`g2butf8.py`** — CLI 主程式（`python g2butf8.py [files...]`，入口為 `main()`）。
- **`Tests/test_g2butf8.py`** — pytest 測試。
- **`g2butf8.sh`** — Linux/macOS 上批次跑 `*.ass` 的範例 shell script。
- **`g2butf8.spec`** — PyInstaller 打包設定（產出 Windows 單檔執行檔）。
- **`setup.py`** — 舊版 py2exe 設定，僅供歷史相容。

## 常用指令

```powershell
# 安裝依賴（含 dev 群組的 pytest）
uv sync

# 跑測試
uv run pytest Tests

# 跑轉檔（最常用）
python g2butf8.py path\to\file.srt
python g2butf8.py -r path\to\dir          # 遞迴子目錄
python g2butf8.py -t g2b file.txt         # 僅簡轉繁，不套詞彙表
python g2butf8.py -t utf8 file.txt        # 只重新編碼成 UTF-8，不轉簡繁
python g2butf8.py -nu -x .srt .ass file   # 關閉 userdic、限制副檔名
python g2butf8.py *.srt                   # 支援 glob（目前僅相對路徑，見下方已知問題）

# 打包成 Windows 執行檔
pyinstaller g2butf8.spec
```

> 沒有 lint 設定、沒有 CI。修改後請跑 `uv run pytest Tests`，並至少手動跑一次 `python g2butf8.py <某個 .srt>`。
> 新增的測試要驗證業務意圖：對應邏輯被改壞時測試必須失敗。

## 架構與資料流

```
main() → argparse → my_proc() → convert_directory() / convert_file()
                                       │
                                       ├─ detect_file_encoding() ← charset-normalizer 偵測編碼
                                       ├─ looks_binary()         ← 疑似二進位檔就略過
                                       ├─ OpenCC("s2twp")        ← 簡→繁（台灣用語）
                                       ├─ get_dictionary()       ← 讀 dic_tw.txt / userdic.txt
                                       ├─ convert_vocabulary()   ← 最大正向匹配套詞彙
                                       ├─ 備份 .bak（已存在則不覆蓋）
                                       └─ 寫回檔案（utf-8-sig 或 utf-8）
```

關鍵模組：

| 函式 / 變數 | 位置 | 角色 |
|---|---|---|
| `GlobalConfig` / `config` | `g2butf8.py:40` / `:50` | 全域設定（轉換方式、BOM、備份、使用者字典） |
| `CONVERT_TYPES` | `g2butf8.py:53` | `g2b` / `g2bdic`（預設）/ `utf8` / `none`；`-t` 以此限制合法值 |
| `BASE_DIR` | `g2butf8.py:57` | 程式所在目錄（打包後為 exe 所在目錄）；`dic_tw.txt` 從這裡讀，不受工作目錄影響 |
| `convert_vocabulary()` | `g2butf8.py:78` | 最大正向匹配，每個位置只試到字典最長詞長度（`get_max_len()`）；規則見 `dic_history.csv` |
| `looks_binary()` | `g2butf8.py:118` | 解碼後可疑字元（Cc/Cn/Cs）比例超過 `BINARY_THRESHOLD`（1%）即視為二進位檔 |
| `detect_file_encoding()` | `g2butf8.py:139` | charset-normalizer 偵測編碼 |
| `convert_file()` | `g2butf8.py:186` | 單檔流程：解碼 → 二進位檢查 → 轉換 → 套字典 → 備份 → 寫回；全部在記憶體完成後才寫檔 |
| `get_dictionary()` | `g2butf8.py:271` | 讀字典；略過註解、空行與沒有 `=` 的行，只切第一個 `=` |

- `userdic.txt` 從**被轉換檔案所在目錄**讀取，每個檔案只讀一次。
- 遍歷目錄與 glob 展開時會略過 `.bak` 備份檔（避免產生 `.bak.bak`）。

## 詞彙轉換的最大正向匹配陷阱

`convert_vocabulary()` 是「由長到短」貪婪掃描。`dic_tw.txt` 與 `userdic.txt` 中詞彙**順序無關**（是用 dict 查找），但**短詞會在長詞的子字串中先被吃掉的問題**要靠 `dic_history.csv` 紀錄的人工補丁解掉——例如為了不讓「這只」先吃掉「這只是」、不讓「布達」先吃掉「布達佩斯」，會刻意補一條同前綴的長詞。

詞彙表是在 OpenCC 轉換**之後**才套用，所以字典的鍵要寫**繁體**（OpenCC 轉出來的結果），不是簡體原文。

**修改詞彙表前請先看 `dic_history.csv`**：它記錄了歷次新增/刪除/編輯的原因（直譯詞另有意義、錯字、量詞特例等），新詞彙要沿用同樣的命名與排版紀律。

## ⚠ 已知問題 / 不一致（尚未處理）

1. **`g2butf8.cfg` 目前沒有被讀取**：重構成 `GlobalConfig` 後設定檔讀取邏輯已移除，cfg 內的值不生效，預設值全由 `GlobalConfig` 決定。
2. **BOM 預設值說法不一**：`GlobalConfig.use_bom = True`（實際會加 BOM），但 `README.md`、模組 docstring、`-nobom`/`-bom` 的 help 都說「預設不加 BOM」。
3. **絕對路徑 glob 會崩潰**：`Path().glob()` 不支援絕對路徑樣式（如 `D:\dir\*.srt`），會拋 `NotImplementedError`。
4. **短文字編碼誤判**：charset-normalizer 對很短的文字可能誤判（例如 4 個字的 GB18030 被判成 cp949），轉出亂碼。
5. **依賴宣告有兩份**：`pyproject.toml` + `uv.lock`（以此為準）與舊的 `requirements.txt`（其中 `configparser`、`argparse` 是標準函式庫，不需安裝）。`requirements.txt` 待清理。

## 環境

- Python：`requires-python >= 3.11`（使用 `match/case`）；本機開發版本由 `.python-version` 固定為 3.14
- 套件管理：`uv`（`uv.lock` 存在；不要換成 pip / poetry，會破壞 lockfile）
- `.venv` 依平台建立，不可在 Windows 與 WSL/Linux 之間共用
- 目標平台：Windows / macOS / Linux 都跑得動；PyInstaller spec 為 Windows 設計

## 編碼慣例

- 所有新寫的程式碼註解請用 **繁體中文（zh-TW）**。
- 不要在 repo 裡放簡體中文註解或 docstring（測試資料中的簡體原文除外）。
- 字串中的 BOM 請寫成轉義 `"\ufeff"`，不要放字面的不可見字元。
- 詞彙表 `dic_tw.txt` / `userdic.txt` 為 UTF-8，**有無 BOM、LF/CRLF 都必須能正常讀取**（不同人的編輯器/環境存檔習慣不同，例如 Windows 記事本、Excel 會加 BOM），且 BOM 不可黏在第一個鍵上。`Tests/` 有對應測試。
