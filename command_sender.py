import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pyautogui
import time
import json
import os
import sys
import ctypes
from ctypes import wintypes
import glob

# 配置文件
CONFIG_FILE = 'app_config.json'
COMMANDS_DIR = 'commands'

# Windows API
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

class CommandSenderApp:
    def __init__(self, root):
        self.root = root
        self.root.title('Windows 命令发送工具 v1.0')
        self.root.geometry('900x650')
        self.root.minsize(700, 500)
        
        # 配置
        self.commands_dir = COMMANDS_DIR
        self.target_hwnd = None
        self.target_window = None
        self.current_file = None  # 当前文件完整路径
        self.current_file_origin = None  # 原始文件路径（外部文件用）
        self.recent_files = []  # 最近打开的文件
        self.max_recent = 10    # 最多显示10个
        self.last_directory = ''  # 上次打开的目录
        
        # 默认配置
        self.delay_after_focus = 0.3
        self.delay_between_keys = 0.005
        self.use_clipboard = True
        
        # 创建命令目录
        if not os.path.exists(self.commands_dir):
            os.makedirs(self.commands_dir)
            # 创建示例文件
            self.create_sample_files()
        
        self.load_config()
        self.setup_ui()
        self.refresh_file_list()
        self.update_recent_files_display()
        
    def create_sample_files(self):
        """创建示例文件"""
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
        
        # 最近文件下拉列表
        self.recent_combo = ttk.Combobox(top_frame, width=35, font=('Arial', 10), state='readonly')
        self.recent_combo.pack(side=tk.LEFT, padx=5)
        self.recent_combo.bind('<<ComboboxSelected>>', self.on_recent_file_select)
        
        ttk.Button(top_frame, text="新建", command=self.new_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_frame, text="打开", command=self.open_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_frame, text="保存", command=self.save_current_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_frame, text="刷新", command=self.refresh_file_list).pack(side=tk.LEFT, padx=2)
        
        # 中间：命令文本区域（支持鼠标选择）
        text_frame = ttk.LabelFrame(main_frame, text="命令内容（用鼠标拖拽选择）", padding="5")
        text_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # 创建带滚动条的文本框
        self.text_widget = tk.Text(text_frame, font=("Consolas", 11), wrap=tk.NONE, 
                                   undo=True, maxundo=-1)
        v_scroll = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.text_widget.yview)
        h_scroll = ttk.Scrollbar(text_frame, orient=tk.HORIZONTAL, command=self.text_widget.xview)
        self.text_widget.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        # 布局
        self.text_widget.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        v_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_scroll.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        
        # 底部：窗口选择和发送
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.grid(row=2, column=0, columnspan=2, pady=(0, 10))
        
        # 窗口选择
        window_frame = ttk.LabelFrame(bottom_frame, text="目标窗口", padding="5")
        window_frame.pack(side=tk.LEFT, padx=10)
        
        self.window_btn = ttk.Button(window_frame, text="选择目标窗口", command=self.select_target_window)
        self.window_btn.pack()
        
        self.window_status = ttk.Label(window_frame, text="未选择", foreground="red")
        self.window_status.pack(pady=(5, 0))
        
        # 发送按钮
        send_frame = ttk.LabelFrame(bottom_frame, text="发送", padding="5")
        send_frame.pack(side=tk.LEFT, padx=10)
        
        # 使用黑色文字的按钮样式
        style = ttk.Style()
        style.configure('SendButton.TButton', font=('Arial', 10, 'bold'), foreground='black')
        
        ttk.Button(send_frame, text="🚀 发送选中内容", command=self.send_selected_text, 
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
        
        # 配置样式（按钮文字颜色）
        style = ttk.Style()
        style.configure('SendButton.TButton', font=('Arial', 10, 'bold'), foreground='black')
        
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
        except:
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
        except:
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
                # 移除不存在的文件
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
                self.add_to_recent(filepath)  # 会自动移除
    
    def refresh_file_list(self):
        """刷新文件列表（扫描commands目录）"""
        # 扫描命令目录，更新recent_files
        pattern = os.path.join(self.commands_dir, '*.txt')
        files = glob.glob(pattern)
        files.sort(key=os.path.getmtime, reverse=True)  # 按修改时间排序
        
        # 将新文件添加到最近文件
        for f in files:
            if f not in self.recent_files:
                self.recent_files.insert(0, f)
        
        self.recent_files = self.recent_files[:self.max_recent]
        self.update_recent_files_display()
        self.save_config()
    
    def on_file_select(self, event):
        """文件选择事件（保留兼容性）"""
        # 现在主要通过recent_combo选择
        pass
    
    def load_file_content(self, filepath):
        """加载文件内容"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.text_widget.delete('1.0', tk.END)
            self.text_widget.insert('1.0', content)
            
            # 判断是否是外部文件（不在commands目录）
            commands_abs = os.path.abspath(self.commands_dir)
            file_abs = os.path.abspath(filepath)
            
            if file_abs.startswith(commands_abs):
                # 在commands目录内
                self.current_file = filepath
                self.current_file_origin = None
            else:
                # 外部文件，记录原始路径
                self.current_file = filepath
                self.current_file_origin = filepath
            
            # 添加到最近文件
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
            # 记住上次目录
            self.last_directory = os.path.dirname(filepath)
            self.save_config()
            
            # 创建空文件
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('')
            
            self.load_file_content(filepath)
    
    def open_file(self):
        """打开外部文件"""
        # 使用上次打开的目录
        initial_dir = self.last_directory if self.last_directory else self.commands_dir
        
        filepath = filedialog.askopenfilename(
            initialdir=initial_dir,
            filetypes=[('文本文件', '*.txt'), ('所有文件', '*.*')]
        )
        
        if filepath:
            # 记住上次打开的目录
            self.last_directory = os.path.dirname(filepath)
            self.save_config()
            
            # 直接加载原文件，不复制到commands目录
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
            self.status_var.set(f"✓ 已保存: {filename}")
            messagebox.showinfo('成功', f'文件已保存: {filename}')
        except Exception as e:
            messagebox.showerror('错误', f'保存失败: {str(e)}')
    
    def select_target_window(self):
        """选择目标窗口"""
        self.status_var.set("请点击目标窗口来选择...")
        self.window_btn.config(state='disabled')
        self.root.update()
        
        # 使用Windows API设置系统级十字光标
        self._set_system_cursor(True)
        
        self.selecting = True
        
        # 启动定时器检测鼠标状态
        self._check_mouse_for_selection()
    
    def _set_system_cursor(self, show_cross):
        """设置系统级光标"""
        try:
            if show_cross:
                # 加载十字光标
                cursor = user32.LoadCursorW(0, 32515)  # IDC_CROSS
                user32.SetCursor(cursor)
                # 设置捕获，这样光标会在整个系统范围内保持
                user32.SetCapture(int(self.root.winfo_id()))
                # 强制设置光标
                self.root.config(cursor='cross')
                self.root.update()
                # 使用定时器持续设置光标
                self._cursor_timer = self.root.after(50, lambda: self._update_cursor(True))
            else:
                if hasattr(self, '_cursor_timer'):
                    self.root.after_cancel(self._cursor_timer)
                user32.ReleaseCapture()
                user32.SetCursor(0)
                self.root.config(cursor='')
        except:
            pass
    
    def _update_cursor(self, show_cross):
        """持续更新光标"""
        if hasattr(self, 'selecting') and self.selecting and show_cross:
            try:
                cursor = user32.LoadCursorW(0, 32515)
                user32.SetCursor(cursor)
                self._cursor_timer = self.root.after(50, lambda: self._update_cursor(True))
            except:
                pass
    
    def _check_mouse_for_selection(self):
        """定时检查鼠标按键状态"""
        if not hasattr(self, 'selecting') or not self.selecting:
            return
        
        # 检查鼠标左键是否被按下
        state = user32.GetAsyncKeyState(0x01)  # VK_LBUTTON
        
        if state & 0x8000:  # 鼠标按下
            # 鼠标按下，获取当前位置的窗口
            try:
                class POINT(ctypes.Structure):
                    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
                
                pt = POINT()
                user32.GetCursorPos(ctypes.byref(pt))
                
                hwnd = user32.WindowFromPoint(pt)
                
                # 排除工具窗口本身
                if hwnd == int(self.root.winfo_id()):
                    # 等一下再试
                    self.root.after(100, self._check_mouse_for_selection)
                    return
                
                # 获取顶层窗口
                while True:
                    parent = user32.GetParent(hwnd)
                    if parent == 0:
                        break
                    hwnd = parent
                
                # 获取窗口标题
                length = user32.GetWindowTextLengthW(hwnd)
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                window_title = buff.value if buff.value else "Unknown Window"
                
                self.target_hwnd = hwnd
                self.target_window = window_title
                
                # 高亮显示窗口
                self.highlight_window(hwnd)
                
                # 完成选择
                self._finish_select_window(window_title)
                
                return
                
            except Exception as e:
                self._fail_select_window(str(e))
                return
        
        # 继续检测，最多30秒
        if hasattr(self, 'selecting') and self.selecting:
            self.root.after(50, self._check_mouse_for_selection)
    
    def _finish_select_window(self, window_title):
        """完成窗口选择"""
        self.selecting = False
        self._set_system_cursor(False)
        self.root.config(cursor='')
        self.window_btn.config(state='normal')
        self.window_status.config(text=window_title[:30], foreground="green")
        self.status_var.set(f"✓ 已选择目标窗口: {window_title}")
    
    def _fail_select_window(self, error_msg):
        """窗口选择失败"""
        self.selecting = False
        self._set_system_cursor(False)
        self.root.config(cursor='')
        self.window_btn.config(state='normal')
        self.window_status.config(text="选择失败", foreground="red")
        self.status_var.set(f"✗ 选择失败: {error_msg}")
    
    def highlight_window(self, hwnd):
        """高亮显示窗口边框"""
        try:
            # 获取窗口位置
            rect = ctypes.wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            
            # 创建高亮窗口
            self.highlight_win = tk.Toplevel(self.root)
            self.highlight_win.overrideredirect(True)
            self.highlight_win.geometry(f"{rect.right - rect.left}x{rect.bottom - rect.top}+{rect.left}+{rect.top}")
            self.highlight_win.attributes('-alpha', 0.3)
            self.highlight_win.attributes('-topmost', True)
            
            # 红色边框
            frame = tk.Frame(self.highlight_win, bg='red', cursor='cross')
            frame.pack(fill=tk.BOTH, expand=True)
            
            # 0.5秒后自动关闭
            self.root.after(500, self.close_highlight)
            
        except Exception as e:
            pass
    
    def close_highlight(self):
        """关闭高亮窗口"""
        try:
            if hasattr(self, 'highlight_win'):
                self.highlight_win.destroy()
        except:
            pass
    
    def activate_window(self, hwnd):
        """激活目标窗口"""
        try:
            if user32.IsIconic(hwnd):
                user32.ShowWindow(hwnd, 9)
            
            user32.SetForegroundWindow(hwnd)
            user32.SetFocus(hwnd)
            
            time.sleep(self.delay_after_focus)
            return True
        except:
            return False
    
    def send_via_clipboard(self, text):
        """通过剪贴板发送"""
        import pyperclip
        
        original = ""
        try:
            original = pyperclip.paste()
        except:
            pass
        
        try:
            pyperclip.copy(text)
            time.sleep(0.1)
            
            if self.target_hwnd:
                self.activate_window(self.target_hwnd)
                time.sleep(0.2)
            
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.1)
            pyautogui.press('enter')
            
            time.sleep(0.2)
            try:
                pyperclip.copy(original)
            except:
                pass
            
            return True
        except:
            return False
    
    def send_via_keyboard(self, text):
        """通过键盘发送"""
        try:
            if self.target_hwnd:
                self.activate_window(self.target_hwnd)
            
            pyautogui.write(text, interval=self.delay_between_keys)
            pyautogui.press('enter')
            
            return True
        except:
            return False
    
    def get_selected_text(self):
        """获取选中的文本"""
        try:
            # 获取文本控件的选中内容
            selected = self.text_widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            return selected.strip() if selected else ""
        except:
            return ""
    
    def send_selected_text(self):
        """发送选中的文本"""
        if not self.target_hwnd:
            messagebox.showwarning('警告', '请先选择目标窗口！')
            return
        
        # 获取选中内容
        text = self.get_selected_text()
        
        if not text:
            messagebox.showwarning('警告', '请先用鼠标选择要发送的文本！')
            return
        
        self.do_send(text)
    
    def send_all_text(self):
        """发送全部文本"""
        if not self.target_hwnd:
            messagebox.showwarning('警告', '请先选择目标窗口！')
            return
        
        # 获取全部内容
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
        
        # 不最小化窗口，保持可见
        
        success_count = 0
        failed_lines = []
        
        for i, line in enumerate(lines):
            # 跳过注释行
            if line.startswith('#') or line.startswith('//'):
                continue
            
            # 发送命令
            success = False
            if self.use_clipboard:
                success = self.send_via_clipboard(line)
            
            if not success:
                success = self.send_via_keyboard(line)
            
            if success:
                success_count += 1
            else:
                failed_lines.append(line)
            
            # 等待下一条命令
            time.sleep(0.3)
        
        if failed_lines:
            self.status_var.set(f"✓ 发送完成: {success_count}/{len(lines)} 成功")
            messagebox.showwarning('部分失败', f'成功: {success_count}/{len(lines)}\n失败:\n' + '\n'.join(failed_lines[:5]))
        else:
            self.status_var.set(f"✓ 发送成功: {success_count} 条命令")
    
    def on_closing(self):
        # 保存当前文件
        if self.current_file:
            try:
                content = self.text_widget.get('1.0', tk.END).rstrip()
                with open(self.current_file, 'w', encoding='utf-8') as f:
                    f.write(content)
            except:
                pass
        
        self.save_config()
        self.root.destroy()

if __name__ == "__main__":
    pyautogui.FAILSAFE = True
    
    root = tk.Tk()
    app = CommandSenderApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
