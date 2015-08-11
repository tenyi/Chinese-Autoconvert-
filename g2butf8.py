#!/usr/bin/env python
# -*- coding: utf8 -*-

import sys
import os
import codecs
import shutil
from glob import glob
import ConfigParser
from jianfan import jtof
# http://code.google.com/p/python-jianfan/
#import chardet
from chardet.universaldetector import UniversalDetector
# http://chardet.feedparser.org
from dic_tw import dic_tw
import argparse


#global variables
convertType = "g2bdic"
use_bom = True
backup = True

# 最大正向匹配
def convertVocabulary(string_in, dic):
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

def getEncoding(filename):
    fp = open(filename, 'r')
    orig_content = fp.read()
    detector = UniversalDetector()
    detector.feed(orig_content)
    detector.close()
    fp.close()
    return detector.result["encoding"]

def getEncodingByContent(content):
    detector = UniversalDetector()
    detector.feed(content)
    detector.close()
    return detector.result["encoding"]

# start error message
#MSG_USAGE = u"使用方法： g2butf8 [filename] 會自動偵測編碼，再轉換成有BOM的UTF-8"
MSG_TEXT_FILE_NOT_FOUND = u"錯誤 - 檔案找不到："
MSG_CONVERT_FINISH = u"轉換成功！\n"
MSG_NO_CONVERT = u"檔案長度為零，不做轉換\n"
# end of error message

dir_separator = os.path.sep

def convertDirectory(directory, extension, recursive):
    files = os.listdir(directory)
    for f in files:
        fname = directory + dir_separator + f
        if os.path.isdir(fname):
            if recursive:
                convertDirectory(fname, extension, recursive)
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
                    convertFile(fname)
            else:
                print "檔案不存在! File not found"

def convertFile(target_file):
    if os.path.isfile(target_file):
        f_encoding = getEncoding(target_file)
        print u"正在轉換", target_file, u" 編碼為: ", f_encoding
        if f_encoding is None:
            print (u"抱歉, 未能正確判斷編碼！\n\n");
        else:
            if os.path.getsize(target_file) > 0:
                if backup:
                    # do backup
                    backup_file = target_file + '.bak'
                    shutil.copy2(target_file, backup_file)

                result_content = u''
                original_content = u''
                fp = open(target_file, 'r')
                original_content = fp.read()
                fp.close()

                if original_content.startswith(codecs.BOM_UTF8):
                    original_content.lstrip(codecs.BOM_UTF8)

                utf8content = original_content.decode(f_encoding, 'ignore')
                if convertType != "none":
                    newcontent = jtof(utf8content)
                else:
                    newcontent = utf8content

                origlines = newcontent.splitlines(True)
                fpw = open(target_file, 'w')
                if(use_bom):
                    if not newcontent.startswith(codecs.BOM_UTF8.decode("utf8")):
                        fpw.write(codecs.BOM_UTF8)
                for line in origlines:
                    if convertType == "g2bdic":
                        fpw.write(convertVocabulary(line, dic_tw()).encode('UTF-8'))
                    else:
                        fpw.write(line.encode('UTF-8'))
                #fpw.write(newcontent.encode('UTF-8'))
                fpw.close()

                print (MSG_CONVERT_FINISH)
            else:
                print MSG_NO_CONVERT
    else:
        print "File not found! "+target_file+" 檔案不存在! "

def myproc(file_or_dir, extension, recursive):
    if os.path.isdir(file_or_dir):
        convertDirectory(file_or_dir, extension, recursive)
    else:
        if os.path.isfile(file_or_dir):
            doconvert = False
            if extension is None:
                doconvert = True
            else:
                for ext in extension:
                    if file_or_dir.lower().endswith(ext):
                        doconvert = True
            if doconvert:
                convertFile(file_or_dir)


if __name__ == "__main__":
    #主程序
    config = ConfigParser.ConfigParser()
    config.read('g2butf8.cfg')
    backup = config.getboolean('config', 'backup')
    use_bom = config.getboolean('config', 'use_bom')
    convertType = config.get('config', 'convert')

    # start parse parameters

    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--recursive', action="store_true", help='包含子目錄(預設不包括)')
    #parser.add_argument('-b', '--backup', action="store_true", help='產生.bak備份檔')
    parser.add_argument('-nb', '--nobackup',  action="store_true", help='不要產生.bak備份檔 (預設有)')
    parser.add_argument('-nobom', '--nobom',  action="store_true", help='不要產生BOM標題 (預設有)')
    parser.add_argument('-x', metavar='extension', type=str, nargs='+', help='副檔名, (預設為所有檔案)')
    parser.add_argument('-t', "--type", metavar='type', type=str, nargs=1, help='轉換方式: g2b 簡轉繁 g2bdic 簡轉繁再加上詞彙轉換')
    parser.add_argument('files', metavar='files', type=str, nargs='+',
                   help='會自動偵測編碼，再轉換成有BOM的UTF-8')
    argc = len(sys.argv)

    if argc == 1:
        parser.print_help()
        #sys.exit(MSG_USAGE);
        exit()

    # end of parse parameters.
    args = parser.parse_args()
    recursive = False

    if args.nobackup:
        backup = False
    if args.type is not None:
        convertType = args.type[0]
    if args.nobom is not None:
        use_bom = False

    filelist = args.files
    for afile in filelist:
        if '*' in afile:
            aflist = glob(afile)
            for bfile in aflist:
                myproc(bfile, args.x, args.recursive)
        else:
            myproc(afile, args.x, args.recursive)


