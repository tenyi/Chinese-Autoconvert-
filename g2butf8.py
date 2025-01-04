#!/usr/bin/env python
# -*- coding: utf8 -*-

"""
中文詞彙自動轉碼程式 (Chinese Text Auto-Converter)

本程式提供以下功能：
1. 自動偵測文字檔案編碼
2. 將檔案轉換為 UTF-8 編碼（預設不帶 BOM）
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
import codecs
import shutil
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

# 錯誤訊息定義
class ConversionMessages:
    """轉換過程相關訊息"""
    FILE_NOT_FOUND = "錯誤 - 檔案找不到："
    CONVERT_FINISH = "轉換成功！"
    NO_CONVERT = "檔案長度為零，不做轉換"
    ENCODING_DETECT_FAILED = "無法偵測到檔案的編碼"

def convert_vocabulary(text: str, dictionary: Dict[str, str]) -> str:
    """
    使用最大正向匹配算法進行詞彙轉換
    
    Args:
        text: 要轉換的文字
        dictionary: 轉換用字典
    
    Returns:
        轉換後的文字
    """
    i = 0
    while i < len(text):
        for j in range(len(text) - i, 0, -1):
            if text[i:][:j] in dictionary:
                replacement = dictionary[text[i:][:j]]
                text = text[:i] + replacement + text[i+j:]
                i += len(replacement) - 1
                break
        i += 1
    return text

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
        if result.best():
            detected_encoding = result.best().encoding
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

    # 建立備份
    if config.backup:
        backup_path = target_path.with_suffix(target_path.suffix + ".bak")
        shutil.copy2(target_path, backup_path)

    try:
        # 讀取檔案內容
        with open(target_path, "r", encoding=file_encoding) as fp:
            content = fp.read()

        # 處理 BOM
        if content.encode().startswith(codecs.BOM_UTF8):
            content = content.lstrip(codecs.BOM_UTF8.decode())

        # 進行轉換
        match config.convert_type:
            case "none" | "utf8":
                new_content = content
            case _:
                cc = OpenCC("s2twp")
                new_content = cc.convert(content)

        # 套用字典轉換
        if config.convert_type == "g2bdic":
            for line in new_content.splitlines(True):
                converted_line = convert_vocabulary(line, config.dic_tw)
                if config.use_user_dic:
                    user_dic_path = target_path.parent / config.user_dic_file
                    if user_dic_path.exists():
                        user_dic = get_dictionary(user_dic_path)
                        converted_line = convert_vocabulary(converted_line, user_dic)

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
            if not line.startswith("#"):
                key, value = line.strip().split("=")
                dictionary[key] = value

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

def main() -> None:
    """
    主程式
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "files",
        metavar="files",
        type=str,
        nargs="+",
        help="檔案名或目錄名。會自動偵測編碼，再轉換成有BOM的UTF-8",
    )
    parser.add_argument(
        "-r", "--recursive", action="store_true", help="包含子目錄(預設不包括)"
    )
    parser.add_argument(
        "-nb", "--nobackup", action="store_true", help="不要產生.bak備份檔 (預設有)"
    )
    parser.add_argument(
        "-nobom", "--nobom", action="store_true", help="不要產生BOM標題 (預設沒有)"
    )
    parser.add_argument(
        "-bom", "--bom", action="store_true", help="產生BOM標題 (預設沒有)"
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

    config.dic_tw = get_dictionary("dic_tw.txt")

    for file in args.files:
        if "*" in file:
            for path in Path().glob(file):
                my_proc(path, args.x, args.recursive)
        else:
            my_proc(file, args.x, args.recursive)

if __name__ == "__main__":
    main()
