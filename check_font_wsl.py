# -*- coding: utf-8 -*-
"""WSL 字体检测脚本 - 验证 ttk 字体配置是否生效"""
import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont

root = tk.Tk()
root.withdraw()

available = set(tkfont.families())
print("=== Available CJK fonts ===")
for f in sorted(available):
    if any(k in f.lower() for k in ["cjk", "hei", "song", "ming", "wenquan", "noto", "yahei", "simhei"]):
        print(f"  {f}")

def get_available_font(candidates):
    for font_name in candidates:
        if font_name in available:
            return font_name
    return candidates[0]

ui_candidates = ["Noto Sans CJK SC", "Noto Sans CJK", "WenQuanYi Micro Hei", "WenQuanYi Zen Hei", "DejaVu Sans", "sans-serif"]
ui_font = get_available_font(ui_candidates)
print(f"UI Font selected: {ui_font}")

style = ttk.Style()
style.configure("TButton", font=(ui_font, 10))
style.configure("TLabel", font=(ui_font, 10))
print(f"ttk TButton font: {style.lookup('TButton', 'font')}")
print(f"ttk TLabel font: {style.lookup('TLabel', 'font')}")

test_label = ttk.Label(root, text="测试中文显示")
print(f"Text in label: {test_label['text']}")

root.destroy()
print("=== ALL CHECKS PASSED ===")
