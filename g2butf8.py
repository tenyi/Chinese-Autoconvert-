#!/usr/bin/env python
# -*- coding: utf8 -*-

import sys
import os
import codecs
import shutil
from glob import glob
import configparser
import argparse
from charset_normalizer import detect
from charset_normalizer import from_bytes
from opencc import OpenCC

# global variables
convert_type = "g2bdic"
use_bom = True
backup = True
use_user_dic = True
# user dictionary file
user_dic_file = 'userdic.txt'
dic_tw = {}

# start error message
# MSG_USAGE = u"使用方法： g2butf8 [filename] 會自動偵測編碼，再轉換成有BOM的UTF-8"
MSG_TEXT_FILE_NOT_FOUND = "錯誤 - 檔案找不到："
MSG_CONVERT_FINISH = "轉換成功！\n"
MSG_NO_CONVERT = "檔案長度為零，不做轉換\n"
# end of error message
dir_separator = os.path.sep

# 最大正向匹配
def convert_vocabulary(string_in, dic):
    i = 0
    while i < len(string_in):
        for j in range(len(string_in) - i, 0, -1):
            if string_in[i:][:j] in dic:
                t = dic[string_in[i:][:j]]
                string_in = string_in[:i] + t + string_in[i:][j:]
                i += len(t) - 1
                break
        i += 1
    return string_in


def detect_file_encoding(file_path):
    with open(file_path, "rb") as f:
        content = f.read()
    result = from_bytes(content)
    if result.best():
        print(f"偵測到的編碼: {result.best().encoding}")
        return result.best().encoding
    else:
        print("無法偵測到檔案的編碼")
        return None


def convert_directory(directory, extension, recursive):
    files = os.listdir(directory)
    for f in files:
        fname = directory + dir_separator + f
        if os.path.isdir(fname):
            if recursive:
                convert_directory(fname, extension, recursive)
        else:
            if os.path.isfile(fname):
                doconvert = False
                if extension is None:
                    doconvert = True
                else:
                    for ext in extension:
                        if f.lower().endswith(ext):
                            doconvert = True
                if doconvert:
                    convert_file(fname)
            else:
                print("檔案不存在! File not found")


def convert_file(target_file):
    if os.path.isfile(target_file):
        user_dic = {}
        f_encoding = detect_file_encoding(target_file)
        print("正在轉換", target_file, " 編碼為: ", f_encoding)
        if f_encoding is None:
            print("抱歉, 未能正確判斷編碼！\n\n")
        else:
            if os.path.getsize(target_file) > 0:
                if backup:
                    # do backup
                    backup_file = target_file + '.bak'
                    shutil.copy2(target_file, backup_file)
                result_content = ''
                fp = open(target_file, 'r', encoding=f_encoding)
                original_content = fp.read()
                fp.close()

                path_dir = os.path.dirname(os.path.abspath(target_file))
                user_dic_pathname = path_dir + os.path.sep + user_dic_file

                if os.path.exists(user_dic_pathname):
                    user_dic = get_dictionary(user_dic_pathname)

                if original_content.encode().startswith(codecs.BOM_UTF8):
                    original_content.lstrip(codecs.BOM_UTF8)

                cc = OpenCC('s2tw')  # 簡體字轉台灣繁體字，若要加上詞彙可用 s2twp
                #utf8content = original_content.encode().decode(f_encoding, 'ignore')
                if convert_type == "none" or convert_type == "utf8":
                    new_content = original_content
                else:
                    new_content = cc.convert(original_content)

                origlines = new_content.splitlines(True)
                if use_bom:
                    fpw = open(target_file, 'w', encoding='utf-8-sig')
                else:
                    fpw = open(target_file, 'w', encoding='utf-8')
                for line in origlines:
                    if convert_type == "g2bdic":
                        newline = convert_vocabulary(line, dic_tw)
                        if use_user_dic:
                            newline = convert_vocabulary(newline, user_dic)
                        fpw.write(newline)
                    else:
                        fpw.write(line)
                # fpw.write(new_content.encode('UTF-8'))
                fpw.close()

                print(MSG_CONVERT_FINISH)
            else:
                print(MSG_NO_CONVERT)
    else:
        print("File not found! " + target_file + " 檔案不存在! ")


# get pre-defined dictionary
def get_dictionary(filename):
    dictionary = {}
    if os.path.exists(filename):
        f_encoding = detect_file_encoding(filename)
        if f_encoding is None:
            print("抱歉, 未能正確判斷字典編碼！\n\n")
        else:
            fpr = open(filename, 'r', encoding=f_encoding)
            lines = fpr.readlines()
            fpr.close()

            if lines[0].encode().startswith(codecs.BOM_UTF8):
                lines[0] = lines[0].lstrip(codecs.BOM_UTF8)

            for line in lines:
                if not line.startswith('#'):
                    line = str(line.encode().decode(f_encoding))
                    words = line.split('=')
                    key = words[0].lstrip().rstrip()
                    value = words[1].lstrip().rstrip()
                    dictionary[key] = value
    return dictionary


def my_proc(file_or_dir, extension, recursive):
    if os.path.isdir(file_or_dir):
        convert_directory(file_or_dir, extension, recursive)
    else:
        if os.path.isfile(file_or_dir):
            do_convert = False
            if extension is None:
                do_convert = True
            else:
                for ext in extension:
                    if file_or_dir.lower().endswith(ext):
                        do_convert = True
            if do_convert:
                convert_file(file_or_dir)


def main(): 
    # 主程序
    # start parse parameters
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'files',
        metavar='files',
        type=str,
        nargs='+',
        help='檔案名或目錄名。會自動偵測編碼，再轉換成有BOM的UTF-8')
    parser.add_argument(
        '-r', '--recursive', action="store_true", help='包含子目錄(預設不包括)')
    # parser.add_argument('-b', '--backup', action="store_true", help='產生.bak備份檔')
    parser.add_argument(
        '-nb', '--nobackup', action="store_true", help='不要產生.bak備份檔 (預設有)')
    parser.add_argument(
        '-nobom', '--nobom', action="store_true", help='不要產生BOM標題 (預設有)')
    parser.add_argument(
        '-x', metavar='extension', type=str, nargs='+', help='副檔名, (預設為所有檔案)')
    parser.add_argument(
        '-t',
        "--type",
        metavar='type',
        type=str,
        nargs=1,
        help='轉換方式: g2b 簡轉繁 g2bdic 簡轉繁再加上詞彙轉換 utf8 只轉成utf8')
    parser.add_argument(
        '-u',
        "--userdic",
        metavar='userdic',
        type=str,
        nargs=1,
        help='使用者字典檔名，預設使用 userdic.txt')
    parser.add_argument(
        '-nu',
        '--nouserdic',
        action="store_true",
        help='不使用自訂字典檔 (預設有，使用userdic.txt)')

    argc = len(sys.argv)

    if argc == 1:
        parser.print_help()
        exit(0)
    # end of parse parameters.
    args = parser.parse_args()

    if args.nobackup:
        backup = False
    if args.type is not None:
        convert_type = args.type[0]
    if args.nobom:
        use_bom = False
    if args.nouserdic:
        use_user_dic = False
    if args.userdic:
        user_dic_file = args.u[0]

    config = configparser.ConfigParser()
    configFile = 'g2butf8.cfg'
    if os.path.exists(configFile):
        f_encoding = detect_file_encoding(configFile)
        config.read(configFile, encoding=f_encoding)
        backup = config.getboolean('config', 'backup')
        use_bom = config.getboolean('config', 'use_bom')
        convert_type = config.get('config', 'convert')
    else:
        backup = True
        use_bom = True
        convert_type="g2b"

    dic_tw = get_dictionary("dic_tw.txt")
    file_list = args.files
    for a_file in file_list:
        if '*' in a_file:
            a_list = glob(a_file)
            for bfile in a_list:
                my_proc(bfile, args.x, args.recursive)
        else:
            my_proc(a_file, args.x, args.recursive)

if __name__ == "__main__":
    main()
