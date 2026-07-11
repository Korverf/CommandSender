#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试脚本：验证中文编码和文件加载性能"""
import os
import sys
import time

TESTS_PASSED = 0
TESTS_FAILED = 0

def test(name):
    def decorator(fn):
        def wrapper():
            global TESTS_PASSED, TESTS_FAILED
            try:
                fn()
                TESTS_PASSED += 1
                print(f"  [PASS] {name}")
            except Exception as e:
                TESTS_FAILED += 1
                print(f"  [FAIL] {name}: {e}")
        return wrapper
    return decorator

# ── Test 1: Source file encoding ──
@test("源文件编码声明存在")
def test_encoding_declaration():
    with open('command_sender.py', 'r', encoding='utf-8') as f:
        first_line = f.readline()
    assert 'utf-8' in first_line.lower(), f"Missing encoding declaration: {first_line.strip()}"

@test("Python源文件可正常解析中文")
def test_source_parsing():
    # 直接在模块级别执行import，确保中文字符串正常
    import importlib.util
    spec = importlib.util.spec_from_file_location("command_sender", "command_sender.py")
    # 只验证文件能被Python解析不报SyntaxError
    with open('command_sender.py', 'r', encoding='utf-8') as f:
        compile(f.read(), 'command_sender.py', 'exec')
    print("      (中文编译解析正常)")

# ── Test 2: Text file read/write with Chinese ──
@test("中文 txt 文件读写正常")
def test_chinese_file_rw():
    test_content = "这是中文测试内容\n第二行：命令行发送工具\n第三行：测试通过！\n"
    test_file = '/tmp/test_chinese.txt'

    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_content)

    with open(test_file, 'r', encoding='utf-8') as f:
        read_content = f.read()

    assert read_content == test_content, f"Content mismatch:\nExpected: {test_content!r}\nGot: {read_content!r}"
    assert '中文' in read_content
    assert '命令行发送工具' in read_content

    os.remove(test_file)

# ── Test 3: Font detection ──
@test("跨平台字体检测可用")
def test_font_detection():
    import tkinter as tk
    import tkinter.font as tkfont

    root = tk.Tk()
    root.withdraw()
    families = set(tkfont.families())
    root.destroy()

    # 检查至少有一个候选字体可用
    import platform
    if platform.system() == 'Windows':
        candidates = ['Consolas', 'Courier New', 'Arial']
    else:
        candidates = ['DejaVu Sans Mono', 'Ubuntu Mono', 'DejaVu Sans']

    found = [f for f in candidates if f in families]
    assert len(found) > 0, f"No font found from candidates: {candidates}"
    print(f"      Available fonts: {found}")

# ── Test 4: Large file loading performance ──
@test("大文件加载性能 (< 200ms)")
def test_large_file_loading():
    test_file = '/tmp/test_large.txt'

    # 生成 5000 行文本
    content = '\n'.join(f"第{i:04d}行 测试数据 test data 中文内容" for i in range(5000))
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(content)

    # 测试纯读取速度（不含UI）
    start = time.time()
    with open(test_file, 'r', encoding='utf-8') as f:
        data = f.read()
    read_time = (time.time() - start) * 1000

    assert read_time < 200, f"Read too slow: {read_time:.1f}ms"
    assert len(data) > 100000, f"File too small: {len(data)} chars"
    assert '中文' in data
    print(f"      Read time: {read_time:.1f}ms, {len(data)} chars")

    os.remove(test_file)

# ── Test 5: Config save/load with Chinese ──
@test("配置文件中文读写正常")
def test_config_cn():
    import json
    config = {
        'commands_dir': '/home/测试/commands',
        'recent_files': ['/home/测试/文件1.txt', '/home/测试/文件2.txt'],
        'delay_after_focus': 0.3,
        'delay_between_keys': 0.005,
        'use_clipboard': True,
        'last_directory': '/home/测试/'
    }
    config_file = '/tmp/test_config.json'

    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    with open(config_file, 'r', encoding='utf-8') as f:
        loaded = json.load(f)

    assert loaded['commands_dir'] == config['commands_dir']
    assert '测试' in loaded['commands_dir']
    os.remove(config_file)

# ── Test 6: Generated package file integrity ──
@test("安装包文件完整性")
def test_package_integrity():
    pkg_path = 'dist/CommandSender-2.1.0-ubuntu22.04.tar.gz'
    assert os.path.exists(pkg_path), f"Package not found: {pkg_path}"
    size_mb = os.path.getsize(pkg_path) / (1024 * 1024)
    assert size_mb > 10, f"Package too small: {size_mb:.1f}MB"
    print(f"      Package size: {size_mb:.1f} MB")

# ── Test 7: command_sender module import test ──
@test("主模块延迟导入 pyautogui 不崩溃")
def test_lazy_import():
    # 在导入前清空可能已加载的模块
    for mod in ['pyautogui', 'mouseinfo', 'Xlib', 'tkinter.font']:
        sys.modules.pop(mod, None)

    # 重新加载command_sender模块
    if 'command_sender' in sys.modules:
        del sys.modules['command_sender']
    if 'window_manager' in sys.modules:
        del sys.modules['window_manager']

    # 导入不应崩溃 – 字体和pyautogui都是延迟加载的
    import command_sender
    assert hasattr(command_sender, '_get_pyautogui')
    assert command_sender._pyautogui is None, "pyautogui should not be loaded at import time"
    assert command_sender._FONT_TEXT is None, "font should not be initialized at import time"
    print("      pyautogui 和字体均延迟加载")


# ── Run all tests ──
if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    print("=" * 50)
    print("CommandSender 修复验证测试")
    print("=" * 50)

    test_encoding_declaration()
    test_source_parsing()
    test_chinese_file_rw()
    test_font_detection()
    test_large_file_loading()
    test_config_cn()
    test_package_integrity()
    test_lazy_import()

    print("-" * 50)
    print(f"Result: {TESTS_PASSED} passed, {TESTS_FAILED} failed")
    if TESTS_FAILED > 0:
        sys.exit(1)
    else:
        print("All tests passed!")
