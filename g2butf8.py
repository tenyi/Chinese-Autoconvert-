#!/usr/bin/env python
# -*- coding: utf8 -*-

"""
中文詞彙自動轉碼程式 (Chinese Text Auto-Converter)

本程式提供以下功能：
1. 自動偵測文字檔案編碼
2. 將檔案轉換為 UTF-8 編碼（預設帶 BOM，可用 -nobom 或設定檔關閉）
3. 將簡體中文轉換為繁體中文（使用 OpenCC）
4. 支援自定義詞典進行詞彙轉換

使用方法：
    python g2butf8.py [檔案或目錄] [-r] [-nb] [-nobom]

參數說明：
    -r, --recursive: 遞迴處理子目錄
    -nb, --nobackup: 不建立備份檔案
    -nobom, --nobom: 不在輸出檔案加入 BOM 標記

作者：Tenyi
版本：2.0.0
Python版本要求：3.11+
"""

from __future__ import annotations
import configparser
import glob
import shutil
import sys
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
import argparse
from charset_normalizer import CharsetMatches
from charset_normalizer import from_bytes
from opencc import OpenCC

# 全域變數設定
@dataclass
class GlobalConfig:
    """全域設定類別"""
    convert_type: str = "g2bdic"  # 轉換類型
    use_bom: bool = True         # 是否使用 BOM
    backup: bool = True          # 是否建立備份
    use_user_dic: bool = True    # 是否使用使用者字典
    user_dic_file: str = "userdic.txt"  # 使用者字典檔名
    dic_tw: Dict[str, str] = field(default_factory=dict)     # 繁體中文字典

# 初始化全域設定
config = GlobalConfig()

# 合法的轉換方式
CONVERT_TYPES = ("g2b", "g2bdic", "utf8", "none")

# 程式所在目錄：dic_tw.txt 一律從這裡找，不受執行時的工作目錄（CWD）影響。
# PyInstaller 打包後 __file__ 會指向暫存解壓目錄，因此改用執行檔所在位置。
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

# 設定檔：與 dic_tw.txt 同樣放在程式所在目錄
CONFIG_FILE = BASE_DIR / "g2butf8.cfg"

# 中文編碼與日文編碼名稱（charset-normalizer 的命名），供編碼偵測時調整候選順序
CHINESE_ENCODINGS = ("gb18030", "gb2312", "gbk", "cp936", "hz", "big5", "big5hkscs", "cp950")
JAPANESE_ENCODINGS = (
    "cp932", "shift_jis", "shift_jis_2004", "shift_jisx0213",
    "euc_jp", "euc_jis_2004", "euc_jisx0213", "iso2022_jp",
)

# 備份檔副檔名；遍歷目錄或展開 glob 時會略過，避免把備份再轉一次而產生 .bak.bak
BACKUP_EXT = ".bak"

# 解碼後「可疑字元」比例超過此門檻即視為二進位檔
BINARY_THRESHOLD = 0.01
# 文字檔常見的控制字元（tab、換行、換頁等），不算可疑
TEXT_CONTROL_CHARS = set("\t\n\r\x0b\x0c")

# 錯誤訊息定義
class ConversionMessages:
    """轉換過程相關訊息"""
    FILE_NOT_FOUND = "錯誤 - 檔案找不到："
    CONVERT_FINISH = "轉換成功！"
    NO_CONVERT = "檔案長度為零，不做轉換"
    ENCODING_DETECT_FAILED = "無法偵測到檔案的編碼"

def convert_vocabulary(text: str, dictionary: Dict[str, str], max_len: Optional[int] = None) -> str:
    """
    使用最大正向匹配算法進行詞彙轉換

    每個位置最多只嘗試到字典最長詞的長度，不必從整行長度往下試；
    結果以 list 收集再 join，避免每次替換都重組整個字串。
    替換後的文字不會再被掃描，從被替換詞之後繼續比對。

    Args:
        text: 要轉換的文字
        dictionary: 轉換用字典
        max_len: 字典最長詞長度；未提供時自動計算（大量呼叫時請預先算好傳入）

    Returns:
        轉換後的文字
    """
    if not dictionary:
        return text
    if max_len is None:
        max_len = get_max_len(dictionary)
    result: List[str] = []
    i = 0
    n = len(text)
    while i < n:
        for j in range(min(max_len, n - i), 0, -1):
            word = text[i:i + j]
            if word in dictionary:
                result.append(dictionary[word])
                i += j
                break
        else:
            # 此位置沒有任何詞命中，原字保留
            result.append(text[i])
            i += 1
    return "".join(result)

def get_max_len(dictionary: Dict[str, str]) -> int:
    """取得字典最長詞長度（空字典回傳 0）"""
    return max(map(len, dictionary), default=0)

def looks_binary(content: str) -> bool:
    """
    判斷解碼後的內容是否像二進位檔

    編碼偵測對二進位檔不一定回傳 None，可能猜成某個「什麼都能解」的編碼，
    解出來的內容會夾雜大量控制字元（Cc）、未定義字元（Cn）或代理字元（Cs），以此判別。

    Args:
        content: 解碼後的文字

    Returns:
        可疑字元比例超過 BINARY_THRESHOLD 時回傳 True
    """
    if not content:
        return False
    suspicious = sum(
        1 for c in content
        if c not in TEXT_CONTROL_CHARS and unicodedata.category(c) in ("Cc", "Cn", "Cs")
    )
    return suspicious / len(content) > BINARY_THRESHOLD

def detect_file_encoding(file_path: Union[str, Path]) -> Optional[str]:
    """
    偵測檔案編碼
    
    Args:
        file_path: 檔案路徑
    
    Returns:
        檔案編碼，如果無法偵測則回傳 None
    """
    try:
        with open(file_path, "rb") as f:
            content = f.read()
        result: CharsetMatches = from_bytes(content)
        best = result.best()
        if best:
            detected_encoding = best.encoding
            # 短文字時 charset-normalizer 常把 GB18030 / Big5 誤判成 cp949（韓文）或 utf_16_be，
            # 轉出亂碼。本程式處理的是中文檔，因此只要候選清單裡有中文編碼，就優先採用。
            # 以下情況維持原判斷，不套用中文優先：
            #   - 有 BOM：編碼已由 BOM 確定
            #   - utf_8 / ascii：嚴格解碼成功即幾乎可確定，且 UTF-8 中文也可能被列出 gb18030 候選
            #   - 日文編碼：避免把日文檔誤當成 GB18030
            if not (best.bom or detected_encoding in ("utf_8", "ascii") or detected_encoding in JAPANESE_ENCODINGS):
                detected_encoding = next(
                    (match.encoding for match in result if match.encoding in CHINESE_ENCODINGS),
                    detected_encoding,
                )
            print(f"偵測到的編碼: {detected_encoding}")
            return detected_encoding
        print(ConversionMessages.ENCODING_DETECT_FAILED)
        return None
    except Exception as e:
        print(f"偵測編碼時發生錯誤: {e}")
        return None

def convert_directory(directory: Union[str, Path], extension: Optional[List[str]], recursive: bool) -> None:
    """
    轉換目錄下的檔案
    
    Args:
        directory: 目錄路徑
        extension: 檔案副檔名
        recursive: 是否遞迴處理子目錄
    """
    dir_path = Path(directory)
    if not dir_path.is_dir():
        print(f"{ConversionMessages.FILE_NOT_FOUND} {directory}")
        return

    for file in dir_path.iterdir():
        if file.is_file():
            if file.name.lower().endswith(BACKUP_EXT):
                continue
            if extension is None or file.suffix.lstrip('.').lower() in [ext.lstrip('.').lower() for ext in extension]:
                convert_file(file)
        elif file.is_dir() and recursive:
            convert_directory(file, extension, recursive)

def convert_file(target_file: Union[str, Path]) -> None:
    """
    轉換單一檔案的編碼和內容
    
    Args:
        target_file: 目標檔案路徑
    """
    target_path = Path(target_file)
    if not target_path.is_file():
        print(f"{ConversionMessages.FILE_NOT_FOUND} {target_file}")
        return

    # 檢查檔案大小
    if target_path.stat().st_size == 0:
        print(ConversionMessages.NO_CONVERT)
        return

    # 偵測檔案編碼
    file_encoding = detect_file_encoding(target_path)
    if file_encoding is None:
        return

    print(f"正在轉換 {target_file} 編碼為: {file_encoding}")

    # 先在記憶體中完成全部轉換，成功後才備份並寫回；
    # 避免轉換途中出錯時留下錯誤的備份或被清空的原檔。
    try:
        # 讀取檔案內容
        with open(target_path, "r", encoding=file_encoding) as fp:
            content = fp.read()

        if looks_binary(content):
            print("看起來是二進位檔，略過此檔")
            return

        # 處理 BOM：部分編碼名稱（如 utf_8）解碼後會保留 U+FEFF，在此移除
        content = content.removeprefix("\ufeff")

        # 進行轉換
        match config.convert_type:
            case "none" | "utf8":
                new_content = content
            case _:
                cc = OpenCC("s2twp")
                new_content = cc.convert(content)

        # 套用字典轉換
        if config.convert_type == "g2bdic":
            # 使用者字典每個檔案只讀一次（不在每一行重讀）
            user_dic: Dict[str, str] = {}
            if config.use_user_dic:
                user_dic_path = target_path.parent / config.user_dic_file
                if user_dic_path.exists():
                    user_dic = get_dictionary(user_dic_path)
            # 最長詞長度每個檔案只算一次，不在每一行重算
            dic_tw_max = get_max_len(config.dic_tw)
            user_dic_max = get_max_len(user_dic)
            converted_lines: List[str] = []
            for line in new_content.splitlines(True):
                converted_line = convert_vocabulary(line, config.dic_tw, dic_tw_max)
                converted_line = convert_vocabulary(converted_line, user_dic, user_dic_max)
                converted_lines.append(converted_line)
            # 必須把轉換結果寫回 new_content，否則字典轉換等於沒做
            new_content = "".join(converted_lines)

        # 建立備份
        # 備份已存在時不覆蓋：重複轉換同一檔案時，保留最早（未轉換）的原檔，
        # 否則第二次轉換會用已轉過的內容蓋掉唯一的原始備份。
        if config.backup:
            backup_path = target_path.with_suffix(target_path.suffix + BACKUP_EXT)
            if backup_path.exists():
                print(f"備份檔已存在，保留原備份不覆蓋：{backup_path}")
            else:
                shutil.copy2(target_path, backup_path)

        # 寫入檔案
        encoding = "utf-8-sig" if config.use_bom else "utf-8"
        with open(target_path, "w", encoding=encoding) as fpw:
            fpw.write(new_content)

        print(ConversionMessages.CONVERT_FINISH)

    except Exception as e:
        print(f"轉換過程發生錯誤: {e}")

def get_dictionary(filename: Union[str, Path]) -> Dict[str, str]:
    """
    讀取字典檔案
    
    Args:
        filename: 字典檔案路徑
    
    Returns:
        字典內容
    """
    dictionary = {}
    file_path = Path(filename)
    if file_path.exists():
        file_encoding = detect_file_encoding(file_path)
        if file_encoding is None:
            print(ConversionMessages.ENCODING_DETECT_FAILED)
            return dictionary

        with open(file_path, "r", encoding=file_encoding) as fp:
            lines = fp.readlines()

        for line in lines:
            # 字典有無 BOM 都要能讀：移除殘留的 U+FEFF，否則第一行的「#」註解或詞彙會比對失敗
            line = line.removeprefix("\ufeff")
            # 略過註解、空行，以及沒有「=」的格式錯誤行
            if line.startswith("#") or "=" not in line:
                continue
            # 只切第一個「=」，讓替換詞本身可以包含「=」
            key, value = line.split("=", 1)
            key = key.strip()
            if key:
                dictionary[key] = value.strip()

    return dictionary

def my_proc(file_or_dir: Union[str, Path], extension: Optional[List[str]], recursive: bool) -> None:
    """
    處理檔案或目錄
    
    Args:
        file_or_dir: 檔案或目錄路徑
        extension: 檔案副檔名
        recursive: 是否遞迴處理子目錄
    """
    path = Path(file_or_dir)
    if path.is_dir():
        convert_directory(path, extension, recursive)
    elif path.is_file():
        if extension is None or path.suffix.lstrip('.').lower() in [ext.lstrip('.').lower() for ext in extension]:
            convert_file(path)

def load_config(config_file: Union[str, Path]) -> None:
    """
    讀取設定檔，覆寫 GlobalConfig 的預設值

    優先順序：GlobalConfig 預設值 < 設定檔 < 命令列參數。
    設定檔不存在、缺少 [config] 區段或某個欄位時，沿用目前的值。

    Args:
        config_file: 設定檔路徑
    """
    path = Path(config_file)
    if not path.exists():
        return
    parser = configparser.ConfigParser()
    # 設定檔可能有 BOM（例如用記事本存檔），以 utf-8-sig 讀取兩種都能處理
    parser.read(path, encoding="utf-8-sig")
    config.backup = parser.getboolean("config", "backup", fallback=config.backup)
    config.use_bom = parser.getboolean("config", "use_bom", fallback=config.use_bom)
    config.convert_type = parser.get("config", "convert", fallback=config.convert_type)

def expand_file_args(files: List[str]) -> List[str]:
    """
    展開命令列的檔案參數

    - 檔案或目錄確實存在時直接使用，不當成萬用字元樣式；
      避免「[字幕組] 第01集.srt」這類含方括號的檔名被 glob 誤解成字元集合。
    - 含「*」的參數用 glob.glob 展開（支援絕對路徑，Path().glob 不支援），
      並略過備份檔；使用者明確指定 .bak 檔名時仍照常處理。

    Args:
        files: 命令列傳入的檔案參數

    Returns:
        展開後的路徑清單
    """
    expanded: List[str] = []
    for file in files:
        if "*" in file and not Path(file).exists():
            expanded.extend(
                path for path in sorted(glob.glob(file))
                if not path.lower().endswith(BACKUP_EXT)
            )
        else:
            expanded.append(file)
    return expanded

def main() -> None:
    """
    主程式
    """
    load_config(CONFIG_FILE)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "files",
        metavar="files",
        type=str,
        nargs="+",
        help="檔案名或目錄名。會自動偵測編碼，再轉換成 UTF-8（預設帶 BOM）",
    )
    parser.add_argument(
        "-r", "--recursive", action="store_true", help="包含子目錄(預設不包括)"
    )
    parser.add_argument(
        "-nb", "--nobackup", action="store_true", help="不要產生.bak備份檔 (預設有)"
    )
    parser.add_argument(
        "-nobom", "--nobom", action="store_true", help="不要產生BOM標題 (預設有)"
    )
    parser.add_argument(
        "-bom", "--bom", action="store_true", help="產生BOM標題 (預設有；可覆寫設定檔的 use_bom = false)"
    )
    parser.add_argument(
        "-x", metavar="extension", type=str, nargs="+", help="副檔名, (預設為所有檔案)"
    )
    parser.add_argument(
        "-t",
        "--type",
        metavar="type",
        type=str,
        nargs=1,
        choices=CONVERT_TYPES,
        help="轉換方式: g2b 簡轉繁 g2bdic 簡轉繁再加上詞彙轉換 utf8 只轉成utf8",
    )
    parser.add_argument(
        "-u",
        "--userdic",
        metavar="userdic",
        type=str,
        nargs=1,
        help="使用者字典檔名，預設使用 userdic.txt",
    )
    parser.add_argument(
        "-nu",
        "--nouserdic",
        action="store_true",
        help="不使用自訂字典檔 (預設有，使用userdic.txt)",
    )

    args = parser.parse_args()

    if args.nobackup:
        config.backup = False
    if args.type is not None:
        config.convert_type = args.type[0]
    if args.nobom:
        config.use_bom = False
    if args.bom:
        config.use_bom = True
    if args.nouserdic:
        config.use_user_dic = False
    if args.userdic:
        config.user_dic_file = args.userdic[0]

    # 設定檔中的值不經 argparse 檢查，打錯字時明確報錯，而不是默默當成 g2b
    if config.convert_type not in CONVERT_TYPES:
        parser.error(
            f"設定檔 {CONFIG_FILE.name} 的 convert = {config.convert_type} 不合法"
            f"（可用：{', '.join(CONVERT_TYPES)}）"
        )

    # 從程式所在目錄讀取詞彙表，不依賴執行時的工作目錄
    config.dic_tw = get_dictionary(BASE_DIR / "dic_tw.txt")

    for file in expand_file_args(args.files):
        my_proc(file, args.x, args.recursive)

if __name__ == "__main__":
    main()
