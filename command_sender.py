# -*- coding: utf-8 -*-
"""
跨平台命令行发送工具
支持 Windows 和 Linux (Ubuntu 22.04)
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import time
import json
import os
import sys
import glob

if sys.platform == 'win32':
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

_pyautogui = None


def _get_pyautogui():
    """延迟导入 pyautogui，避免在无 X11 环境中启动即崩溃"""
    global _pyautogui
    if _pyautogui is None:
        import pyautogui
        pyautogui.FAILSAFE = True
        _pyautogui = pyautogui
    return _pyautogui

# 平台抽象层
from window_manager import create_window_manager, SYSTEM
import tkinter.font as tkfont

# 配置文件
CONFIG_FILE = 'app_config.json'
COMMANDS_DIR = 'commands'

# 跨平台字体配置
_FONT_TEXT = None
_FONT_UI = None


def _get_available_font(candidates):
    """从候选字体列表中选择第一个可用的字体"""
    available = set(tkfont.families())
    for font_name in candidates:
        if font_name in available:
            return font_name
    return candidates[0]  # 回退到第一个候选


def _get_system_cjk_font():
    """通过 fontconfig 获取系统最佳 CJK 无衬线字体"""
    import subprocess
    try:
        result = subprocess.run(
            ['fc-match', '-f', '%{family[0]}', 'sans-serif:lang=zh-cn'],
            capture_output=True, text=True, timeout=3
        )
        family = result.stdout.strip()
        if family and ',' in family:
            family = family.split(',')[0].strip()
        if family:
            return family
    except Exception:
        pass
    return None


def _get_system_mono_font():
    """通过 fontconfig 获取系统最佳 CJK 等宽字体"""
    import subprocess
    try:
        result = subprocess.run(
            ['fc-match', '-f', '%{family[0]}', 'monospace:lang=zh-cn'],
            capture_output=True, text=True, timeout=3
        )
        family = result.stdout.strip()
        if family and ',' in family:
            family = family.split(',')[0].strip()
        if family:
            return family
    except Exception:
        pass
    return None


def _init_fonts():
    """延迟初始化字体，避免模块导入时调用 tkfont.families() 崩溃"""
    global _FONT_TEXT, _FONT_UI
    if _FONT_TEXT is not None:
        return
    if SYSTEM == 'Windows':
        _FONT_TEXT = _get_available_font(['Consolas', 'Courier New', 'DejaVu Sans Mono', 'monospace'])
        _FONT_UI = _get_available_font(['Microsoft YaHei', 'SimHei', 'Arial', 'sans-serif'])
    else:
        # Linux: 优先通过 fontconfig 查询系统最佳 CJK 字体
        sys_cjk = _get_system_cjk_font()
        sys_mono = _get_system_mono_font()

        _FONT_UI = _get_available_font([
            sys_cjk if sys_cjk else 'Noto Sans CJK SC',
            'Noto Sans CJK HK', 'Noto Sans CJK JP',
            'Noto Sans CJK SC', 'Noto Sans CJK',
            'AR PL UKai CN', 'WenQuanYi Micro Hei',
            'WenQuanYi Zen Hei', 'DejaVu Sans',
            'DejaVu Serif', 'sans-serif'
        ])
        _FONT_TEXT = _get_available_font([
            sys_mono if sys_mono else 'Noto Sans Mono CJK SC',
            'Noto Sans Mono CJK HK', 'Noto Sans Mono CJK JP',
            'Noto Sans Mono CJK', 'DejaVu Sans Mono',
            'Ubuntu Mono', 'monospace'
        ])


def get_font_text():
    _init_fonts()
    return _FONT_TEXT


def get_font_ui():
    _init_fonts()
    return _FONT_UI

# 应用标题
APP_TITLE = '命令行发送工具 v2.1.0'
if SYSTEM == 'Windows':
    APP_TITLE = 'Windows 命令发送工具 v2.1.0'
elif SYSTEM == 'Linux':
    APP_TITLE = 'Linux 命令发送工具 v2.1.0 (Ubuntu 22.04)'


class CommandSenderApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry('900x650')
        self.root.minsize(700, 500)

        # 平台窗口管理器
        self.wm = create_window_manager()

        # 配置
        self.commands_dir = COMMANDS_DIR
        self.target_window = None
        self.current_file = None
        self.current_file_origin = None
        self.recent_files = []
        self.max_recent = 10
        self.last_directory = ''
        self.selecting = False

        # 默认配置
        self.delay_after_focus = 0.3
        self.delay_between_keys = 0.005
        self.use_clipboard = True
        self._save_pending = False  # 延迟保存标志

        # 创建命令目录
        if not os.path.exists(self.commands_dir):
            os.makedirs(self.commands_dir)
            self.create_sample_files()

        self.load_config()
        self.setup_ui()
        self.refresh_file_list()
        self.update_recent_files_display()
        
        if self.recent_files:
            self.load_file_content(self.recent_files[0])

    def create_sample_files(self):
        """创建示例文件"""
        shell_cmd = ""
        if SYSTEM == 'Linux':
            sample1 = f"""# Shell / Terminal 常用命令
ls -la
pwd
df -h
free -h
ping -c 4 8.8.8.8
top -b -n 1
"""
        else:
            sample1 = """# PowerShell 常用命令
Get-Process
Get-Service
Get-ChildItem
ipconfig
ping 8.8.8.8"""

        sample2 = """# Git 常用命令
git status
git add .
git commit -m "update"
git push
git pull"""

        sample3 = """# Python 命令
python --version
pip list
pip install requests
python -m pip install --upgrade pip"""

        with open(f'{self.commands_dir}/1_PowerShell.txt', 'w', encoding='utf-8') as f:
            f.write(sample1)
        with open(f'{self.commands_dir}/2_Git.txt', 'w', encoding='utf-8') as f:
            f.write(sample2)
        with open(f'{self.commands_dir}/3_Python.txt', 'w', encoding='utf-8') as f:
            f.write(sample3)

    def setup_ui(self):
        # ===== 设置全局默认字体（确保所有组件中文正常显示）=====
        # 修改 Tk 默认字体（所有 tk/ttk 组件均会继承此设置）
        try:
            default_font = tkfont.nametofont('TkDefaultFont')
            default_font.configure(family=get_font_ui(), size=10, weight='normal')
        except Exception:
            pass

        ui_font = (get_font_ui(), 10)
        style = ttk.Style()
        style.configure('.', font=ui_font)
        style.configure('TLabelframe.Label', font=ui_font)
        style.configure('TButton', font=ui_font)

        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 顶部：文件管理
        top_frame = ttk.Frame(main_frame)
        top_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(top_frame, text="最近文件:").pack(side=tk.LEFT)

        self.recent_combo = ttk.Combobox(top_frame, width=35, font=(get_font_ui(), 10), state='readonly')
        self.recent_combo.pack(side=tk.LEFT, padx=5)
        self.recent_combo.bind('<<ComboboxSelected>>', self.on_recent_file_select)
        
        ttk.Button(top_frame, text="删除", command=self.delete_selected_recent).pack(side=tk.LEFT, padx=2)

        self.recent_combo.bind('<Button-3>', self.on_recent_right_click)

        ttk.Button(top_frame, text="新建", command=self.new_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_frame, text="打开", command=self.open_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_frame, text="保存", command=self.save_current_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_frame, text="刷新", command=self.refresh_file_list).pack(side=tk.LEFT, padx=2)

        # 中间：命令文本区域
        text_frame = ttk.LabelFrame(main_frame, text="命令内容（用鼠标拖拽选择）", padding="5")
        text_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))

        self.text_widget = tk.Text(text_frame, font=(get_font_text(), 11), wrap=tk.NONE,
                                   undo=True, maxundo=-1)
        v_scroll = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.text_widget.yview)
        h_scroll = ttk.Scrollbar(text_frame, orient=tk.HORIZONTAL, command=self.text_widget.xview)
        self.text_widget.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.text_widget.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        v_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_scroll.grid(row=1, column=0, sticky=(tk.W, tk.E))

        # 修复 Linux 下 Tk Text 默认粘贴不覆盖选区的问题：
        # 绑定自定义粘贴处理，先删除选中内容再插入
        self.text_widget.bind('<<Paste>>', self._on_paste)
        self.text_widget.bind('<Control-v>', self._on_paste)
        self.text_widget.bind('<Control-V>', self._on_paste)

        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

        # 底部：窗口选择和发送
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.grid(row=2, column=0, columnspan=2, pady=(0, 10))

        window_frame = ttk.LabelFrame(bottom_frame, text="目标窗口", padding="5")
        window_frame.pack(side=tk.LEFT, padx=10)

        self.window_btn = ttk.Button(window_frame, text="选择目标窗口", command=self.select_target_window)
        self.window_btn.pack()

        self.window_status = ttk.Label(window_frame, text="未选择", foreground="red")
        self.window_status.pack(pady=(5, 0))

        send_frame = ttk.LabelFrame(bottom_frame, text="发送", padding="5")
        send_frame.pack(side=tk.LEFT, padx=10)

        style.configure('SendButton.TButton', font=(get_font_ui(), 10, 'normal'), foreground='black')

        ttk.Button(send_frame, text="发送选中内容", command=self.send_selected_text,
                   style='SendButton.TButton').pack()

        ttk.Button(send_frame, text="发送全部", command=self.send_all_text,
                   style='SendButton.TButton').pack(pady=(5, 0))

        # 状态栏
        self.status_var = tk.StringVar()
        self.status_var.set("就绪 - 选择命令文件，编辑内容，用鼠标选择后发送")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        status_bar.pack(fill=tk.X, in_=status_frame)

        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)

    def _on_paste(self, event=None):
        """自定义粘贴：若有选区先删除再插入，实现“覆盖选中内容”

        修复 Linux/X11 下 Tk Text 默认 <<Paste>> 不删除选区、
        导致粘贴内容出现在选区前/后而非覆盖的问题。
        """
        widget = event.widget if event is not None else self.text_widget
        try:
            clip = widget.clipboard_get()
        except Exception:
            return "break"  # 剪贴板为空或非文本，阻止默认行为

        # 删除当前选区（若有）
        try:
            if widget.tag_ranges(tk.SEL):
                widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
        except Exception:
            pass

        widget.insert(tk.INSERT, clip)
        widget.see(tk.INSERT)
        return "break"  # 阻止 Tk 默认粘贴绑定重复插入

    def load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.commands_dir = config.get('commands_dir', COMMANDS_DIR)
                    self.delay_after_focus = config.get('delay_after_focus', 0.3)
                    self.delay_between_keys = config.get('delay_between_keys', 0.005)
                    self.use_clipboard = config.get('use_clipboard', True)
                    self.recent_files = config.get('recent_files', [])
                    self.last_directory = config.get('last_directory', self.commands_dir)
        except Exception:
            pass

    def save_config(self, immediate=False):
        """保存配置，默认合并短时间内的多次调用"""
        if not immediate:
            if self._save_pending:
                return
            self._save_pending = True
            self.root.after(500, self._do_save_config)
        else:
            self._do_save_config()

    def _do_save_config(self):
        """实际执行配置写入"""
        self._save_pending = False
        try:
            config = {
                'commands_dir': self.commands_dir,
                'delay_after_focus': self.delay_after_focus,
                'delay_between_keys': self.delay_between_keys,
                'use_clipboard': self.use_clipboard,
                'recent_files': self.recent_files[:self.max_recent],
                'last_directory': self.last_directory
            }
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def add_to_recent(self, filepath):
        """添加到最近文件列表"""
        if filepath in self.recent_files:
            self.recent_files.remove(filepath)
        self.recent_files.insert(0, filepath)
        self.recent_files = self.recent_files[:self.max_recent]
        self.update_recent_files_display()
        self.save_config()

    def update_recent_files_display(self):
        """更新最近文件下拉列表"""
        display_list = []
        for f in self.recent_files:
            if os.path.exists(f):
                display_list.append(os.path.basename(f))
            else:
                if f in self.recent_files:
                    self.recent_files.remove(f)

        self.recent_combo['values'] = display_list
        if display_list:
            self.recent_combo.current(0)

    def on_recent_file_select(self, event):
        """选择最近文件"""
        idx = self.recent_combo.current()
        if 0 <= idx < len(self.recent_files):
            filepath = self.recent_files[idx]
            if os.path.exists(filepath):
                self.load_file_content(filepath)
            else:
                messagebox.showwarning('警告', '文件不存在，已从列表中移除')
                self.recent_files.remove(filepath)
                self.update_recent_files_display()
                self.save_config()

    def delete_selected_recent(self):
        """删除选中的最近文件记录"""
        idx = self.recent_combo.current()
        if 0 <= idx < len(self.recent_files):
            filepath = self.recent_files[idx]
            filename = os.path.basename(filepath)
            
            result = messagebox.askyesno('确认删除', f'确定要从最近文件列表中移除 "{filename}" 吗？')
            if result:
                self.recent_files.pop(idx)
                self.update_recent_files_display()
                self.save_config()
                self.status_var.set(f"已从最近文件列表移除: {filename}")

    def on_recent_right_click(self, event):
        """右键菜单处理"""
        idx = self.recent_combo.current()
        if 0 <= idx < len(self.recent_files):
            menu = tk.Menu(self.root, tearoff=0)
            menu.add_command(label="删除", command=self.delete_selected_recent)
            menu.post(event.x_root, event.y_root)

    def refresh_file_list(self):
        """刷新文件列表（仅在没有用户文件时扫描commands目录）"""
        if not self.recent_files:
            pattern = os.path.join(self.commands_dir, '*.txt')
            files = glob.glob(pattern)
            files.sort(key=os.path.getmtime, reverse=True)

            for f in files:
                if f not in self.recent_files:
                    self.recent_files.insert(0, f)

        self.recent_files = self.recent_files[:self.max_recent]
        self.update_recent_files_display()
        self.save_config()

    def load_file_content(self, filepath):
        """加载文件内容（禁用 undo 加速大文件加载）"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # 禁用 undo 避免逐字符记录历史导致卡顿
            was_undo = self.text_widget['undo']
            self.text_widget.configure(undo=False)
            self.text_widget.delete('1.0', tk.END)
            self.text_widget.insert('1.0', content)
            self.text_widget.edit_reset()          # 清空 undo/redo 栈
            self.text_widget.configure(undo=was_undo)

            commands_abs = os.path.abspath(self.commands_dir)
            file_abs = os.path.abspath(filepath)

            if file_abs.startswith(commands_abs):
                self.current_file = filepath
                self.current_file_origin = None
            else:
                self.current_file = filepath
                self.current_file_origin = filepath

            self.add_to_recent(filepath)

            filename = os.path.basename(filepath)
            self.status_var.set(f"已加载: {filename}")
        except Exception as e:
            messagebox.showerror('错误', f'加载文件失败: {str(e)}')

    def new_file(self):
        """新建命令文件"""
        initial_dir = self.last_directory if self.last_directory else self.commands_dir

        filepath = filedialog.asksaveasfilename(
            initialdir=initial_dir,
            defaultextension='.txt',
            filetypes=[('文本文件', '*.txt'), ('所有文件', '*.*')]
        )

        if filepath:
            self.last_directory = os.path.dirname(filepath)
            self.save_config()

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('')

            self.load_file_content(filepath)

    def open_file(self):
        """打开外部文件"""
        initial_dir = self.last_directory if self.last_directory else self.commands_dir

        filepath = filedialog.askopenfilename(
            initialdir=initial_dir,
            filetypes=[('文本文件', '*.txt'), ('所有文件', '*.*')]
        )

        if filepath:
            self.last_directory = os.path.dirname(filepath)
            self.save_config()

            try:
                self.load_file_content(filepath)
            except Exception as e:
                messagebox.showerror('错误', f'打开文件失败: {str(e)}')

    def save_current_file(self):
        """保存当前文件"""
        if not self.current_file:
            messagebox.showwarning('警告', '请先选择一个文件！')
            return

        try:
            content = self.text_widget.get('1.0', tk.END).rstrip()
            with open(self.current_file, 'w', encoding='utf-8') as f:
                f.write(content)

            filename = os.path.basename(self.current_file)
            self.status_var.set(f"已保存: {filename}")
            messagebox.showinfo('成功', f'文件已保存: {filename}')
        except Exception as e:
            messagebox.showerror('错误', f'保存失败: {str(e)}')

    # ============================================================
    # 窗口选择 (通过平台抽象层)
    # ============================================================

    def select_target_window(self):
        """选择目标窗口 (跨平台)"""
        self.status_var.set("请在目标窗口上点击来选择...")
        self.window_btn.config(state='disabled')
        self.selecting = True
        self.root.update()

        # 委托给平台窗口管理器
        root_widget_id = int(self.root.winfo_id())
        self.wm.start_selection(self, root_widget_id)

    def _finish_select_window(self, window_title):
        """完成窗口选择 (由窗口管理器回调)"""
        self.selecting = False
        self.wm.cancel_selection()
        self.root.config(cursor='')
        self.window_btn.config(state='normal')
        self.window_status.config(text=window_title[:30], foreground="green")
        self.status_var.set(f"已选择目标窗口: {window_title}")

        # 高亮窗口
        win_id = self.wm.get_window_id()
        if win_id is not None:
            self.wm.highlight_window(win_id, self.root)

    def _fail_select_window(self, error_msg):
        """窗口选择失败 (由窗口管理器回调)"""
        self.selecting = False
        self.wm.cancel_selection()
        self.root.config(cursor='')
        self.window_btn.config(state='normal')
        self.window_status.config(text="选择失败", foreground="red")
        self.status_var.set(f"选择失败: {error_msg}")

    # ============================================================
    # 命令发送
    # ============================================================

    def send_via_clipboard(self, text):
        """通过剪贴板发送"""
        import pyperclip

        original = ""
        try:
            original = pyperclip.paste()
        except Exception:
            pass

        try:
            pyperclip.copy(text)
            time.sleep(0.1)

            win_id = self.wm.get_window_id()
            if win_id is not None:
                self.wm.activate_window(win_id)
                time.sleep(0.2)

            pag = _get_pyautogui()
            pag.hotkey('ctrl', 'v')
            time.sleep(0.1)
            pag.press('enter')

            time.sleep(0.2)
            try:
                pyperclip.copy(original)
            except Exception:
                pass

            return True
        except Exception:
            return False

    def send_via_keyboard(self, text):
        """通过键盘模拟发送"""
        try:
            win_id = self.wm.get_window_id()
            if win_id is not None:
                self.wm.activate_window(win_id)

            pag = _get_pyautogui()
            pag.write(text, interval=self.delay_between_keys)
            pag.press('enter')

            return True
        except Exception:
            return False

    def get_selected_text(self):
        """获取选中的文本（兼容无选择的情况）"""
        try:
            selected = self.text_widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            return selected.strip() if selected else ""
        except Exception:
            return ""

    def get_selected_lines_text(self):
        """获取选中区域所在行的完整内容，如果没有选中则获取光标所在行"""
        try:
            start = self.text_widget.index(tk.SEL_FIRST)
            end = self.text_widget.index(tk.SEL_LAST)
            
            start_line = start.split('.')[0]
            end_line = end.split('.')[0]
            
            start_pos = f"{start_line}.0"
            end_pos = f"{end_line}.end"
            
            full_text = self.text_widget.get(start_pos, end_pos)
            return full_text.strip()
        except Exception:
            return ""

    def get_current_line_text(self):
        """获取光标所在行的完整内容"""
        try:
            cursor_pos = self.text_widget.index(tk.INSERT)
            line_num = cursor_pos.split('.')[0]
            line_text = self.text_widget.get(f"{line_num}.0", f"{line_num}.end")
            return line_text.strip()
        except Exception:
            return ""

    def send_selected_text(self):
        """发送选中区域所在行的完整内容，如果没有选中则发送光标所在行"""
        if self.wm.get_window_id() is None:
            messagebox.showwarning('警告', '请先选择目标窗口！')
            return

        text = self.get_selected_lines_text()
        
        if not text:
            text = self.get_current_line_text()

        if not text:
            messagebox.showwarning('警告', '没有可发送的内容！')
            return

        self.do_send(text)

    def send_all_text(self):
        """发送全部文本"""
        if self.wm.get_window_id() is None:
            messagebox.showwarning('警告', '请先选择目标窗口！')
            return

        text = self.text_widget.get('1.0', tk.END).strip()

        if not text:
            messagebox.showwarning('警告', '没有可发送的内容！')
            return

        self.do_send(text)

    def send_line(self, line):
        """发送单行命令，按平台选择最可靠的方式"""
        # Linux: 优先使用 xdotool 直接注入到目标窗口，
        # 避免 pyautogui 在 X11 下把回车传成字面 ^M
        if SYSTEM == 'Linux' and hasattr(self.wm, 'send_line'):
            if self.wm.send_line(line):
                return True

        # 其它平台或回退方案：剪贴板 / 键盘模拟
        success = False
        if self.use_clipboard:
            success = self.send_via_clipboard(line)
        if not success:
            success = self.send_via_keyboard(line)
        return success

    def do_send(self, text):
        """执行发送"""
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        if not lines:
            return

        self.status_var.set(f"正在发送 {len(lines)} 行命令...")
        self.root.update()

        self.wm.switch_to_english_input()

        success_count = 0
        failed_lines = []

        try:
            for line in lines:
                if line.startswith('#') or line.startswith('//'):
                    continue

                success = self.send_line(line)

                if success:
                    success_count += 1
                else:
                    failed_lines.append(line)

                time.sleep(0.3)
        finally:
            # 发送完毕后恢复用户原来的输入法（若曾切换）
            if hasattr(self.wm, 'restore_input_method'):
                self.wm.restore_input_method()

        if failed_lines:
            self.status_var.set(f"发送完成: {success_count}/{len(lines)} 成功")
            messagebox.showwarning('部分失败',
                                   f'成功: {success_count}/{len(lines)}\n失败:\n'
                                   + '\n'.join(failed_lines[:5]))
        else:
            self.status_var.set(f"发送成功: {success_count} 条命令")

    def on_closing(self):
        """关闭应用"""
        if self.current_file:
            try:
                content = self.text_widget.get('1.0', tk.END).rstrip()
                with open(self.current_file, 'w', encoding='utf-8') as f:
                    f.write(content)
            except Exception:
                pass

        self.save_config(immediate=True)
        self.wm.cleanup()
        self.root.destroy()


def create_app_icon(root):
    """设置应用图标：优先加载 PNG 文件，回退到 PPM 动态生成"""
    import sys, os
    
    # 1. 尝试从 PyInstaller 打包路径加载
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
        png_path = os.path.join(base, 'commandsender.png')
        if os.path.exists(png_path):
            try:
                img = tk.PhotoImage(file=png_path)
                root.iconphoto(True, img)
                return
            except Exception:
                pass
    
    # 2. 尝试从当前目录或标准路径加载
    local_paths = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'commandsender.png'),
        '/usr/share/icons/hicolor/48x48/apps/commandsender.png',
    ]
    for path in local_paths:
        if os.path.exists(path):
            try:
                img = tk.PhotoImage(file=path)
                root.iconphoto(True, img)
                return
            except Exception:
                pass
    
    # 3. 回退：动态生成 PPM 图标
    try:
        icon = _generate_ppm_icon()
        root.iconphoto(True, icon)
    except Exception:
        pass


def _generate_ppm_icon():
    """动态生成 48x48 PPM 图标（命令行终端风格）"""
    w, h, border, corner_r = 48, 48, 3, 4
    header = f"P6\n{w} {h}\n255\n".encode()
    corners = [(border, border), (w - 1 - border, border),
               (border, h - 1 - border), (w - 1 - border, h - 1 - border)]
    pixels = bytearray()
    for y in range(h):
        for x in range(w):
            at_corner = (x <= border or x >= w - 1 - border) and (y <= border or y >= h - 1 - border)
            on_border = x <= border or x >= w - 1 - border or y <= border or y >= h - 1 - border
            in_rounded = False
            if at_corner:
                for cx, cy in corners:
                    dx, dy = x - cx, y - cy
                    if dx * dx + dy * dy < corner_r * corner_r:
                        in_rounded = True
                        break
            if at_corner and not in_rounded:
                r, g, b = 0x00, 0x00, 0x00  # 透明通道（用黑色占位）
            elif on_border:
                r, g, b = 0x37, 0x6E, 0xA2  # 蓝色边框
            elif 12 <= x <= 36 and 10 <= y <= 38 and x >= 12 + abs(24 - y) * 0.55:
                r, g, b = 0x00, 0xCC, 0x88  # 绿色 ">"
            else:
                r, g, b = 0x1E, 0x1E, 0x1E  # 深色背景
            pixels.extend([r, g, b])
    return tk.PhotoImage(data=header + bytes(pixels))


if __name__ == "__main__":
    root = tk.Tk(className='CommandSender')
    app = CommandSenderApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)

    # 设置应用图标（优先文件，回退动态生成）
    create_app_icon(root)

    root.mainloop()
