# 變更記錄

## 2025-01-04
1. 檢查了 `g2butf8.py` 的程式碼，發現以下可改進之處：
   - 型別標註（Type Hints）不完整
   - 錯誤處理機制可以加強
   - 全域變數使用過多
   - 命名規範不一致
   - 註解風格混用
   - 配置文件處理方式可以改進

2. 新增測試
   - 建立 `Tests` 目錄
   - 新增 `test_g2butf8.py` 測試檔案，包含以下測試：
     - test_convert_vocabulary: 測試詞彙轉換功能
     - test_detect_file_encoding: 測試檔案編碼偵測功能
     - test_get_dictionary: 測試讀取字典檔功能
     - test_convert_file: 測試檔案轉換功能
   - 所有測試都已通過

3. 環境設定
   - 建立虛擬環境 `venv`
   - 安裝必要套件：pytest, opencc-python-reimplemented, charset-normalizer

4. 改進 `g2butf8.py`
   - 加入完整的中文文件說明（docstring）
     - 程式功能說明
     - 使用方法和參數說明
     - 版本資訊
   - 使用 Python 3.11+ 的新特性
     - 使用 `match/case` 語法進行條件判斷
     - 完整的型別提示（Type Hints）
     - 使用 `dataclass` 管理全域設定
     - 使用 `pathlib.Path` 替代舊的 `os.path` 操作
   - 程式碼結構優化
     - 使用類別封裝全域設定和錯誤訊息
     - 改善錯誤處理機制
     - 使用 `with` 語句處理檔案操作
     - 移除重複程式碼
   - 改進程式碼可讀性
     - 加入詳細的中文註解
     - 統一變數命名風格
     - 優化程式碼格式
