import pytest
import os
import sys
import tempfile
import shutil
from pathlib import Path

# 添加父目錄到 Python 路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from g2butf8 import (
    detect_file_encoding,
    convert_vocabulary,
    get_dictionary,
    convert_file
)

@pytest.fixture
def temp_dir():
    """建立臨時目錄用於測試"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def sample_dict():
    """建立測試用字典"""
    return {"簡体": "繁體", "测试": "測試"}

def test_convert_vocabulary():
    """測試詞彙轉換功能"""
    test_dict = {"你好": "您好", "世界": "世界"}
    assert convert_vocabulary("你好世界", test_dict) == "您好世界"
    assert convert_vocabulary("沒有轉換", test_dict) == "沒有轉換"

def test_detect_file_encoding(temp_dir):
    """測試檔案編碼偵測功能"""
    # 建立 UTF-8 測試檔案
    test_file = os.path.join(temp_dir, "test_utf8.txt")
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("測試文字")
    
    assert detect_file_encoding(test_file).replace('_', '-') == "utf-8"

def test_get_dictionary(temp_dir):
    """測試讀取字典檔功能"""
    # 建立測試用字典檔
    dict_file = os.path.join(temp_dir, "test_dict.txt")
    with open(dict_file, "w", encoding="utf-8") as f:
        f.write("簡体=繁體\n")
        f.write("测试=測試\n")
    
    result = get_dictionary(dict_file)
    assert result == {"簡体": "繁體", "测试": "測試"}

def test_convert_file(temp_dir):
    """測試檔案轉換功能"""
    # 建立測試用簡體字檔案
    test_file = os.path.join(temp_dir, "test_convert.txt")
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("这是简体字测试")
    
    # 執行轉換
    convert_file(test_file)
    
    # 檢查轉換結果
    with open(test_file, "r", encoding="utf-8") as f:
        content = f.read()
        assert "這是" in content  # 檢查是否有繁體字
