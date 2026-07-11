# -*- coding: utf-8 -*-
"""快速验证 tkinter 中文渲染"""
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

root = tk.Tk()
root.title("字体测试")

# 检测可用字体
fam_set = set(tkfont.families())
candidates_ui = [
    'WenQuanYi Micro Hei', 'WenQuanYi Zen Hei',
    'Noto Sans CJK SC', 'Noto Sans CJK',
    'DejaVu Sans', 'sans-serif'
]
selected = next((f for f in candidates_ui if f in fam_set), candidates_ui[-1])
print(f"Selected UI font: {selected}")

# 测试 tk.Label (tk 原生)
tk.Label(root, text="tk.Label: 这是中文测试 命令行发送工具", font=(selected, 12)).pack(pady=5)

# 测试 ttk.Label
ttk.Label(root, text="ttk.Label: 这是中文测试 命令行发送工具", font=(selected, 12)).pack(pady=5)

# 测试 ttk.Button
ttk.Button(root, text="发送 (Ctrl+Enter)").pack(pady=5)

# 测试 ttk.Combobox
cb = ttk.Combobox(root, values=["最近文件: /home/测试/文件.txt", "选择一个命令文件..."], font=(selected, 10))
cb.pack(pady=5)
cb.current(0)

# 字体实际信息
font_obj = tkfont.Font(family=selected, size=12)
print(f"Font actual: {font_obj.actual()}")
print(f"Font measure of '中文测试': {font_obj.measure('中文测试')}")

# 输出各widget的字体信息以验证
root.update()
print(f"\ntk.Label font: {root.winfo_children()[0].cget('font')}")
try:
    print(f"ttk style font: {ttk.Style().lookup('TButton', 'font')}")
except:
    print("ttk style font: (not available)")

print("\n如果上方窗口中的中文正常显示，则修复成功。")
print("关闭窗口继续...")
root.mainloop()
