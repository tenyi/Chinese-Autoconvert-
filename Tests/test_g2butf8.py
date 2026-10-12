import pytest
import os
import sys
import tempfile
import shutil
from pathlib import Path

# 添加父目錄到 Python 路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import g2butf8
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


# 以下測試鎖定業務意圖：對應的邏輯被改壞時應該失敗

# 足夠長的簡體文字；太短時編碼偵測可能誤判（例如 4 個字會被判成 cp949）
LONG_GB_TEXT = "这只是一个测试，我们在这里进行一些测试，布达佩斯。"


@pytest.fixture
def isolated_config(monkeypatch):
    """每個測試使用獨立的全域設定，避免測試之間互相影響"""
    monkeypatch.setattr(g2butf8, "config", g2butf8.GlobalConfig())
    return g2butf8.config


def test_convert_vocabulary_longest_match_first():
    """最大正向匹配：長詞優先，短詞不可先吃掉長詞的前綴"""
    test_dict = {"布達": "X", "布達佩斯": "Y"}
    assert convert_vocabulary("布達佩斯與布達", test_dict) == "Y與X"


def test_convert_vocabulary_no_rescan_after_replace():
    """替換後的文字不會再被掃描（避免連鎖替換）"""
    test_dict = {"甲": "乙", "乙": "丙"}
    assert convert_vocabulary("甲乙", test_dict) == "乙丙"


def test_g2bdic_applies_dictionary(temp_dir, isolated_config):
    """g2bdic 模式必須真的把詞彙表套用到輸出檔"""
    test_file = os.path.join(temp_dir, "dic.txt")
    with open(test_file, "w", encoding="gb18030") as f:
        f.write(LONG_GB_TEXT)
    isolated_config.dic_tw = {"布達佩斯": "【字典生效】"}
    isolated_config.backup = False

    convert_file(test_file)

    with open(test_file, "r", encoding="utf-8-sig") as f:
        assert "【字典生效】" in f.read()


def test_g2bdic_applies_user_dictionary(temp_dir, isolated_config):
    """同目錄的 userdic.txt 也必須套用"""
    with open(os.path.join(temp_dir, "userdic.txt"), "w", encoding="utf-8") as f:
        f.write("測試=【使用者字典】\n")
    test_file = os.path.join(temp_dir, "user.txt")
    with open(test_file, "w", encoding="gb18030") as f:
        f.write(LONG_GB_TEXT)
    isolated_config.backup = False

    convert_file(test_file)

    with open(test_file, "r", encoding="utf-8-sig") as f:
        assert "【使用者字典】" in f.read()


@pytest.mark.parametrize("bom", [b"", b"\xef\xbb\xbf"], ids=["無BOM", "有BOM"])
@pytest.mark.parametrize("newline", [b"\n", b"\r\n"], ids=["LF", "CRLF"])
def test_get_dictionary_bom_and_newline_agnostic(temp_dir, bom, newline):
    """字典有無 BOM、LF/CRLF 都要讀出相同結果，BOM 不可黏在第一個鍵上；註解、空行、格式錯誤行略過"""
    lines = ["# 註解", "布達=甲", "", "格式錯誤的行", "a=b=c"]
    dict_file = os.path.join(temp_dir, "bom_dict.txt")
    with open(dict_file, "wb") as f:
        f.write(bom + newline.join(l.encode("utf-8") for l in lines) + newline)

    assert get_dictionary(dict_file) == {"布達": "甲", "a": "b=c"}


def test_get_dictionary_bom_on_first_entry(temp_dir):
    """有 BOM 且第一行就是詞彙時，鍵不可帶 U+FEFF"""
    dict_file = os.path.join(temp_dir, "bom_first.txt")
    with open(dict_file, "wb") as f:
        f.write(b"\xef\xbb\xbf" + "布達=甲\n".encode("utf-8"))

    assert get_dictionary(dict_file) == {"布達": "甲"}


def test_backup_not_overwritten(temp_dir, isolated_config):
    """重複轉換時 .bak 不可被覆蓋，必須保留最早的原檔"""
    original = LONG_GB_TEXT.encode("gb18030")
    test_file = os.path.join(temp_dir, "twice.txt")
    with open(test_file, "wb") as f:
        f.write(original)

    convert_file(test_file)
    convert_file(test_file)

    with open(test_file + ".bak", "rb") as f:
        assert f.read() == original


def test_binary_file_untouched(temp_dir, isolated_config, monkeypatch):
    """被誤判為文字編碼的二進位檔不可被改寫"""
    raw = bytes([0x80, 0x81, 0xFF, 0xFE, 0x00, 0x9F]) * 50
    bin_file = os.path.join(temp_dir, "bin.dat")
    with open(bin_file, "wb") as f:
        f.write(raw)
    # 模擬編碼偵測把二進位檔猜成 latin-1（任何位元組都能解碼）
    monkeypatch.setattr(g2butf8, "detect_file_encoding", lambda _: "latin-1")

    convert_file(bin_file)

    with open(bin_file, "rb") as f:
        assert f.read() == raw
    assert not os.path.exists(bin_file + ".bak")


def test_directory_skips_backup_files(temp_dir, isolated_config):
    """遍歷目錄時略過 .bak，不可產生 .bak.bak"""
    with open(os.path.join(temp_dir, "a.txt"), "w", encoding="gb18030") as f:
        f.write(LONG_GB_TEXT)

    g2butf8.convert_directory(temp_dir, None, False)
    g2butf8.convert_directory(temp_dir, None, False)

    assert not os.path.exists(os.path.join(temp_dir, "a.txt.bak.bak"))


# ---- 設定檔、glob、編碼偵測、BOM 預設 ----

def write_cfg(path, body, bom=False):
    """寫出設定檔；bom=True 時模擬記事本存檔加上 BOM"""
    with open(path, "wb") as f:
        f.write((b"\xef\xbb\xbf" if bom else b"") + body.encode("utf-8"))


@pytest.mark.parametrize("bom", [False, True], ids=["無BOM", "有BOM"])
def test_load_config_overrides_defaults(temp_dir, isolated_config, bom):
    """設定檔的值必須覆寫 GlobalConfig 預設值（有無 BOM 皆可）"""
    cfg = os.path.join(temp_dir, "g2butf8.cfg")
    write_cfg(cfg, "[config]\nconvert = g2b\nbackup = false\nuse_bom = false\n", bom)

    g2butf8.load_config(cfg)

    assert (isolated_config.convert_type, isolated_config.backup, isolated_config.use_bom) == ("g2b", False, False)


def test_load_config_missing_keys_keep_defaults(temp_dir, isolated_config):
    """設定檔缺欄位時沿用預設值，不可拋例外"""
    cfg = os.path.join(temp_dir, "g2butf8.cfg")
    write_cfg(cfg, "[config]\nbackup = false\n")

    g2butf8.load_config(cfg)

    assert isolated_config.backup is False
    assert isolated_config.use_bom is True
    assert isolated_config.convert_type == "g2bdic"


def run_main(monkeypatch, cfg_path, argv):
    """以指定設定檔與命令列參數執行 main()"""
    monkeypatch.setattr(g2butf8, "CONFIG_FILE", Path(cfg_path))
    monkeypatch.setattr(sys, "argv", ["g2butf8.py"] + argv)
    g2butf8.main()


def test_cli_overrides_config(temp_dir, isolated_config, monkeypatch):
    """命令列參數優先於設定檔"""
    cfg = os.path.join(temp_dir, "g2butf8.cfg")
    write_cfg(cfg, "[config]\nuse_bom = false\nbackup = true\n")
    target = os.path.join(temp_dir, "cli.txt")
    with open(target, "w", encoding="gb18030") as f:
        f.write(LONG_GB_TEXT)

    run_main(monkeypatch, cfg, ["-bom", "-nb", target])

    with open(target, "rb") as f:
        assert f.read().startswith(b"\xef\xbb\xbf")
    assert not os.path.exists(target + ".bak")


def test_invalid_convert_in_config_rejected(temp_dir, isolated_config, monkeypatch):
    """設定檔的 convert 打錯字時必須報錯結束，不可默默執行"""
    cfg = os.path.join(temp_dir, "g2butf8.cfg")
    write_cfg(cfg, "[config]\nconvert = g2bdc\n")

    with pytest.raises(SystemExit) as exc:
        run_main(monkeypatch, cfg, [os.path.join(temp_dir, "none.txt")])
    assert exc.value.code != 0


def test_default_output_has_bom(temp_dir, isolated_config):
    """預設輸出帶 BOM 的 UTF-8"""
    target = os.path.join(temp_dir, "bom.txt")
    with open(target, "w", encoding="gb18030") as f:
        f.write(LONG_GB_TEXT)
    isolated_config.backup = False

    convert_file(target)

    with open(target, "rb") as f:
        assert f.read().startswith(b"\xef\xbb\xbf")


def test_expand_file_args_absolute_glob(temp_dir):
    """絕對路徑的萬用字元要能展開，且略過 .bak"""
    for name in ["a.srt", "b.srt", "a.srt.bak", "c.txt"]:
        open(os.path.join(temp_dir, name), "w").close()

    result = g2butf8.expand_file_args([os.path.join(temp_dir, "*.srt*")])

    assert sorted(os.path.basename(p) for p in result) == ["a.srt", "b.srt"]


def test_expand_file_args_bracket_filename(temp_dir):
    """含方括號的實際檔名不可被當成 glob 字元集合"""
    name = os.path.join(temp_dir, "[字幕組] 第*集.srt")
    try:
        open(name, "w").close()
    except OSError:
        pytest.skip("此檔案系統不允許檔名含 *")
    assert g2butf8.expand_file_args([name]) == [name]


@pytest.mark.parametrize("text,encoding", [
    ("这是软件", "gb18030"),
    ("我们的字幕", "gb18030"),
    ("這是軟體", "big5"),
    ("繁體中文字幕檔案", "big5"),
    ("这是软件", "utf-8"),
    ("日本語のテキストです", "shift_jis"),
])
def test_detect_short_text_encoding(temp_dir, text, encoding):
    """短文字也要偵測出能正確解碼的編碼（原本 GB/Big5 短文字會被誤判成 cp949 / utf_16_be）"""
    target = os.path.join(temp_dir, "short.txt")
    with open(target, "wb") as f:
        f.write(text.encode(encoding))

    detected = detect_file_encoding(target)

    with open(target, "rb") as f:
        assert f.read().decode(detected) == text


@pytest.mark.parametrize("simplified,expected", [
    # 副詞「只要」：OpenCC 會在這些字後誤轉成「隻要」，須由詞彙表修正
    ("这只要努力就好", "這只要努力就好"),
    ("那只要你愿意", "那只要你願意"),
    ("别只要求别人", "別只要求別人"),
    ("不单只要钱", "不單只要錢"),
    ("但是只要有钱就好", "但是只要有錢就好"),
    ("还是只要你", "還是只要你"),
    ("最多只要三天", "最多只要三天"),
    ("差不多只要一小时", "差不多只要一小時"),
    # 量詞用法仍要轉成「隻」
    ("这只猫很可爱", "這隻貓很可愛"),
    ("一只要飞的鸟", "一隻要飛的鳥"),
    ("每只要多少钱", "每隻要多少錢"),
    # 既有補丁不可退化
    ("这只是测试", "這只是測試"),
])
def test_real_dictionary_zhi_yao(simplified, expected):
    """用實際的 dic_tw.txt 驗證「只」的量詞與副詞用法"""
    from opencc import OpenCC
    dic_tw = get_dictionary(g2butf8.BASE_DIR / "dic_tw.txt")
    assert convert_vocabulary(OpenCC("s2twp").convert(simplified), dic_tw) == expected
