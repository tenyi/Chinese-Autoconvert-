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
