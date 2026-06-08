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

# 配置文件
CONFIG_FILE = 'app_config.json'
COMMANDS_DIR = 'commands'

# 应用标题
APP_TITLE = '命令行发送工具 v2.0'
if SYSTEM == 'Windows':
    APP_TITLE = 'Windows 命令发送工具 v2.0'
elif SYSTEM == 'Linux':
    APP_TITLE = 'Linux 命令发送工具 v2.0 (Ubuntu 22.04)'


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

        # 创建命令目录
        if not os.path.exists(self.commands_dir):
            os.makedirs(self.commands_dir)
            self.create_sample_files()

        self.load_config()
        self.setup_ui()
        self.refresh_file_list()
        self.update_recent_files_display()

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
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 顶部：文件管理
        top_frame = ttk.Frame(main_frame)
        top_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(top_frame, text="最近文件:").pack(side=tk.LEFT)

        self.recent_combo = ttk.Combobox(top_frame, width=35, font=('Arial', 10), state='readonly')
        self.recent_combo.pack(side=tk.LEFT, padx=5)
        self.recent_combo.bind('<<ComboboxSelected>>', self.on_recent_file_select)

        ttk.Button(top_frame, text="新建", command=self.new_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_frame, text="打开", command=self.open_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_frame, text="保存", command=self.save_current_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_frame, text="刷新", command=self.refresh_file_list).pack(side=tk.LEFT, padx=2)

        # 中间：命令文本区域
        text_frame = ttk.LabelFrame(main_frame, text="命令内容（用鼠标拖拽选择）", padding="5")
        text_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))

        self.text_widget = tk.Text(text_frame, font=("Consolas", 11), wrap=tk.NONE,
                                   undo=True, maxundo=-1)
        v_scroll = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.text_widget.yview)
        h_scroll = ttk.Scrollbar(text_frame, orient=tk.HORIZONTAL, command=self.text_widget.xview)
        self.text_widget.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.text_widget.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        v_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_scroll.grid(row=1, column=0, sticky=(tk.W, tk.E))

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

        style = ttk.Style()
        style.configure('SendButton.TButton', font=('Arial', 10, 'bold'), foreground='black')

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

    def save_config(self):
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

    def refresh_file_list(self):
        """刷新文件列表（扫描commands目录）"""
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
        """加载文件内容"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            self.text_widget.delete('1.0', tk.END)
            self.text_widget.insert('1.0', content)

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
        """获取选中的文本"""
        try:
            selected = self.text_widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            return selected.strip() if selected else ""
        except Exception:
            return ""

    def send_selected_text(self):
        """发送选中的文本"""
        if self.wm.get_window_id() is None:
            messagebox.showwarning('警告', '请先选择目标窗口！')
            return

        text = self.get_selected_text()

        if not text:
            messagebox.showwarning('警告', '请先用鼠标选择要发送的文本！')
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

    def do_send(self, text):
        """执行发送"""
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        if not lines:
            return

        self.status_var.set(f"正在发送 {len(lines)} 行命令...")
        self.root.update()

        success_count = 0
        failed_lines = []

        for line in lines:
            if line.startswith('#') or line.startswith('//'):
                continue

            success = False
            if self.use_clipboard:
                success = self.send_via_clipboard(line)

            if not success:
                success = self.send_via_keyboard(line)

            if success:
                success_count += 1
            else:
                failed_lines.append(line)

            time.sleep(0.3)

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

        self.save_config()
        self.wm.cleanup()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = CommandSenderApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
