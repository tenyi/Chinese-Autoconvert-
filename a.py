import charset_normalizer


def detect_file_encoding(file_path):
    with open(file_path, "rb") as f:
        content = f.read()
    result = charset_normalizer.from_bytes(content)
    if result.best():
        print(f"偵測到的編碼: {result.best().encoding}")
        return result.best().encoding
    else:
        print("無法偵測到檔案的編碼")
        return None


def detect_encoding(file_path):
    """偵測檔案編碼

    Args:
      file_path: 檔案路徑

    Returns:
      str: 偵測到的編碼
    """

    with open(file_path, "rb") as f:
        rawdata = f.read()
        result = charset_normalizer.detect(rawdata)
        return result.encoding


# 使用範例
file_path = "gb.txt"
encoding = detect_file_encoding(file_path)
print("偵測到的編碼為：", encoding)

# 以偵測到的編碼讀取檔案
with open(file_path, "r", encoding=encoding) as f:
    text = f.read()
    # 對 text 進行處理 (例如：使用 OpenCC 轉換)
