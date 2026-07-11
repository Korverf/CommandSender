# -*- coding: utf-8 -*-
"""
平台抽象层 - 窗口管理器
为 Windows 和 Linux (Ubuntu 22.04) 提供统一的窗口操作接口
"""
import platform
import subprocess
import time
import tkinter as tk

SYSTEM = platform.system()


class BaseWindowManager:
    """窗口管理器基类，定义统一接口"""

    def start_selection(self, app, root_widget_id: int):
        """开始窗口选择流程，完成后通过 app._finish_select_window(title) 或 app._fail_select_window(err) 回调"""
        raise NotImplementedError

    def cancel_selection(self):
        """取消当前进行中的窗口选择"""
        raise NotImplementedError

    def highlight_window(self, window_id, root):
        """高亮显示窗口边框，返回高亮窗口对象"""
        raise NotImplementedError

    def close_highlight(self):
        """关闭高亮窗口"""
        raise NotImplementedError

    def activate_window(self, window_id) -> bool:
        """激活目标窗口，返回是否成功"""
        raise NotImplementedError

    def get_window_id(self):
        """返回当前选中的窗口ID"""
        raise NotImplementedError

    def cleanup(self):
        """资源清理"""
        pass


# ============================================================
# Windows 实现 (基于 ctypes + user32.dll)
# ============================================================

class WindowsWindowManager(BaseWindowManager):
    def __init__(self):
        import ctypes
        from ctypes import wintypes
        self.ctypes = ctypes
        self.wintypes = wintypes
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32

        self.target_hwnd = None
        self._highlight_win = None
        self._cursor_timer = None
        self._root = None

        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
        self._POINT = POINT

    def get_window_id(self):
        return self.target_hwnd

    def start_selection(self, app, root_widget_id: int):
        """Windows 窗口选择：使用系统级十字光标 + 鼠标轮询"""
        self._app = app
        self._root_widget_id = root_widget_id
        self._set_system_cursor(True)
        self._check_mouse_for_selection(app)

    def _set_system_cursor(self, show_cross):
        try:
            if show_cross:
                cursor = self.user32.LoadCursorW(0, 32515)  # IDC_CROSS
                self.user32.SetCursor(cursor)
                self.user32.SetCapture(self._root_widget_id)
                app = self._app
                app.root.config(cursor='cross')
                app.root.update()
                self._cursor_timer = app.root.after(50, lambda: self._update_cursor(True))
            else:
                if self._cursor_timer:
                    app = self._app
                    if app:
                        app.root.after_cancel(self._cursor_timer)
                    self._cursor_timer = None
                self.user32.ReleaseCapture()
                self.user32.SetCursor(0)
                if self._app:
                    self._app.root.config(cursor='')
        except Exception:
            pass

    def _update_cursor(self, show_cross):
        if self._cursor_timer is None:
            return
        try:
            cursor = self.user32.LoadCursorW(0, 32515)
            self.user32.SetCursor(cursor)
            if self._app:
                self._cursor_timer = self._app.root.after(50, lambda: self._update_cursor(True))
        except Exception:
            pass

    def _check_mouse_for_selection(self, app):
        """定时检查鼠标按键状态"""
        if not hasattr(app, 'selecting') or not app.selecting:
            return

        state = self.user32.GetAsyncKeyState(0x01)  # VK_LBUTTON

        if state & 0x8000:
            try:
                pt = self._POINT()
                self.user32.GetCursorPos(self.ctypes.byref(pt))
                hwnd = self.user32.WindowFromPoint(pt)

                if hwnd == self._root_widget_id:
                    app.root.after(100, lambda: self._check_mouse_for_selection(app))
                    return

                # 获取顶层窗口
                while True:
                    parent = self.user32.GetParent(hwnd)
                    if parent == 0:
                        break
                    hwnd = parent

                length = self.user32.GetWindowTextLengthW(hwnd)
                buff = self.ctypes.create_unicode_buffer(length + 1)
                self.user32.GetWindowTextW(hwnd, buff, length + 1)
                window_title = buff.value if buff.value else "Unknown Window"

                self.target_hwnd = hwnd
                app.target_window = window_title
                app._finish_select_window(window_title)
                return
            except Exception as e:
                app._fail_select_window(str(e))
                return

        # 继续轮询，最多30秒
        if hasattr(app, 'selecting') and app.selecting:
            app.root.after(50, lambda: self._check_mouse_for_selection(app))

    def cancel_selection(self):
        self._set_system_cursor(False)
        self._cursor_timer = None

    def highlight_window(self, window_id, root):
        try:
            rect = self.wintypes.RECT()
            self.user32.GetWindowRect(window_id, self.ctypes.byref(rect))

            self._highlight_win = tk.Toplevel(root)
            self._highlight_win.overrideredirect(True)
            self._highlight_win.geometry(
                f"{rect.right - rect.left}x{rect.bottom - rect.top}+{rect.left}+{rect.top}"
            )
            self._highlight_win.attributes('-alpha', 0.3)
            self._highlight_win.attributes('-topmost', True)

            frame = tk.Frame(self._highlight_win, bg='red')
            frame.pack(fill=tk.BOTH, expand=True)

            root.after(500, self.close_highlight)
        except Exception:
            pass

    def close_highlight(self):
        try:
            if self._highlight_win:
                self._highlight_win.destroy()
                self._highlight_win = None
        except Exception:
            pass

    def activate_window(self, window_id) -> bool:
        try:
            if self.user32.IsIconic(window_id):
                self.user32.ShowWindow(window_id, 9)
            self.user32.SetForegroundWindow(window_id)
            self.user32.SetFocus(window_id)
            return True
        except Exception:
            return False

    def switch_to_english_input(self):
        """切换到英文输入法（Windows）"""
        try:
            import ctypes
            user32 = ctypes.windll.user32
            
            hwnd = user32.GetForegroundWindow()
            thread_id = user32.GetWindowThreadProcessId(hwnd, 0)
            
            hkl = user32.GetKeyboardLayout(thread_id)
            lang_id = hkl & 0xFFFF
            
            if lang_id != 0x0409:
                user32.PostMessageW(hwnd, 0x0050, 0, 0x04090409)
            
            time.sleep(0.1)
            return True
        except Exception:
            return False

    def cleanup(self):
        self.cancel_selection()
        self.close_highlight()


# ============================================================
# Linux / Ubuntu 22.04 实现 (基于 xdotool)
# ============================================================

class LinuxWindowManager(BaseWindowManager):
    """Linux 窗口管理器，基于 xdotool"""

    def __init__(self):
        self.target_win_id = None
        self._highlight_win = None
        self._selection_proc = None

    def get_window_id(self):
        return self.target_win_id

    def _check_xdotool(self) -> bool:
        """检查 xdotool 是否可用"""
        try:
            subprocess.run(['which', 'xdotool'], capture_output=True, timeout=3)
            return True
        except Exception:
            return False

    def _run_xdotool(self, args, timeout=5):
        """执行 xdotool 命令"""
        try:
            result = subprocess.run(
                ['xdotool'] + args,
                capture_output=True, text=True, timeout=timeout
            )
            return result.stdout.strip(), result.returncode == 0
        except Exception as e:
            return str(e), False

    def start_selection(self, app, root_widget_id: int):
        """
        Linux 窗口选择：使用 xdotool selectwindow
        启动子进程执行 xdotool selectwindow，定时轮询结果
        """
        self._app = app
        self._root_widget_id = root_widget_id

        if not self._check_xdotool():
            app.root.after(0, lambda: app._fail_select_window(
                "xdotool 未安装，请执行: sudo apt install xdotool"
            ))
            return

        # 启动 xdotool selectwindow 子进程
        try:
            self._selection_proc = subprocess.Popen(
                ['xdotool', 'selectwindow'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        except Exception as e:
            app.root.after(0, lambda: app._fail_select_window(str(e)))
            return

        # 定时轮询
        app.root.after(200, lambda: self._poll_selection(app))

    def _poll_selection(self, app):
        """轮询 xdotool selectwindow 子进程结果"""
        if not hasattr(app, 'selecting') or not app.selecting:
            self.cancel_selection()
            return

        if self._selection_proc is None:
            return

        # 检查子进程是否完成
        retcode = self._selection_proc.poll()
        if retcode is None:
            # 仍在运行，继续轮询
            app.root.after(200, lambda: self._poll_selection(app))
            return

        if retcode == 0:
            # 成功获取窗口ID
            win_id = self._selection_proc.stdout.read().strip()
            self._selection_proc = None

            if not win_id:
                app.root.after(0, lambda: app._fail_select_window("未获取到窗口ID"))
                return

            try:
                self.target_win_id = int(win_id)
            except ValueError:
                app.root.after(0, lambda: app._fail_select_window(f"无效的窗口ID: {win_id}"))
                return

            # 获取窗口标题
            title, ok = self._run_xdotool(['getwindowname', str(self.target_win_id)])
            if not ok:
                title = f"Window {self.target_win_id}"

            app.target_window = title
            app.root.after(0, lambda: app._finish_select_window(title))
        else:
            # 选择被取消或出错
            err = self._selection_proc.stderr.read().strip() if self._selection_proc.stderr else ""
            self._selection_proc = None
            if err:
                app.root.after(0, lambda: app._fail_select_window(f"xdotool 错误: {err}"))
            else:
                app.root.after(0, lambda: app._fail_select_window("窗口选择已取消"))

    def cancel_selection(self):
        if self._selection_proc and self._selection_proc.poll() is None:
            self._selection_proc.terminate()
            try:
                self._selection_proc.wait(timeout=2)
            except Exception:
                self._selection_proc.kill()
        self._selection_proc = None

    def highlight_window(self, window_id, root):
        """高亮显示窗口边框（Linux）"""
        try:
            wid = str(window_id)
            geo, ok = self._run_xdotool(['getwindowgeometry', '--shell', wid])

            if not ok:
                return

            # 解析 geometry 输出
            x = y = w = h = 0
            for line in geo.split('\n'):
                line = line.strip()
                if line.startswith('X='):
                    x = int(line.split('=')[1])
                elif line.startswith('Y='):
                    y = int(line.split('=')[1])
                elif line.startswith('WIDTH='):
                    w = int(line.split('=')[1])
                elif line.startswith('HEIGHT='):
                    h = int(line.split('=')[1])

            if w <= 0 or h <= 0:
                return

            self._highlight_win = tk.Toplevel(root)
            self._highlight_win.overrideredirect(True)
            self._highlight_win.geometry(f"{w}x{h}+{x}+{y}")
            self._highlight_win.attributes('-alpha', 0.3)
            self._highlight_win.attributes('-topmost', True)

            frame = tk.Frame(self._highlight_win, bg='red')
            frame.pack(fill=tk.BOTH, expand=True)

            root.after(500, self.close_highlight)
        except Exception:
            pass

    def close_highlight(self):
        try:
            if self._highlight_win:
                self._highlight_win.destroy()
                self._highlight_win = None
        except Exception:
            pass

    def activate_window(self, window_id) -> bool:
        """激活目标窗口（Linux）"""
        try:
            wid = str(window_id)
            # 使用 windowactivate 激活窗口
            _, ok = self._run_xdotool(['windowactivate', '--sync', wid], timeout=3)
            if not ok:
                return False
            time.sleep(0.2)
            return True
        except Exception:
            return False

    def switch_to_english_input(self):
        """切换到英文输入法（Linux）"""
        try:
            _, ok = self._run_xdotool(['key', 'ctrl+space'], timeout=2)
            if not ok:
                _, ok = self._run_xdotool(['key', 'shift'], timeout=2)
            time.sleep(0.1)
            return True
        except Exception:
            return False

    def cleanup(self):
        self.cancel_selection()
        self.close_highlight()


# ============================================================
# 工厂函数
# ============================================================

def create_window_manager():
    """根据当前平台创建对应的窗口管理器"""
    if SYSTEM == 'Windows':
        return WindowsWindowManager()
    elif SYSTEM == 'Linux':
        return LinuxWindowManager()
    else:
        raise RuntimeError(f"不支持的平台: {SYSTEM}")
