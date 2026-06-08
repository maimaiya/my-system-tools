'''
由deepseek v4多次迭代，仅支持win系统，测试win10
'''
import sys
import tkinter as tk
from tkinter import ttk
import pyautogui
import keyboard
from PIL import Image, ImageTk, ImageDraw
import threading
import time
import math
import ctypes
import win32gui
import win32ui
import win32con
from ctypes import wintypes

class ScreenMagnifier:
    def __init__(self):
        # 默认设置
        self.zoom_level = 2.5
        self.zoom_step = 0.25
        self.min_zoom = 1.0
        self.max_zoom = 10.0
        
        # 放大镜窗口大小（宽×高）
        self.lens_width = 600
        self.lens_height = 200
        
        # 偏移量（窗口相对于鼠标的偏移）
        self.offset_x = 15.0
        self.offset_y = 25.0
        
        # 状态变量
        self.is_active = False
        self.is_window_locked = False  # 窗口是否锁定（固定位置）
        self.locked_window_x = 0  # 锁定时窗口的X坐标
        self.locked_window_y = 0  # 锁定时窗口的Y坐标
        
        # 快捷键
        self.toggle_key = 'z'
        self.lock_key = 'x'
        
        # 多屏信息
        self.monitors = []
        self.update_monitors_info()
        
        # 创建窗口
        self.window = None
        self.setup_window()
        
        # 注册快捷键
        self.setup_hotkeys()
        
        print(f"屏幕放大镜已启动")
        print(f"放大镜窗口大小: {self.lens_width}×{self.lens_height}")
        print(f"检测到 {len(self.monitors)} 个显示器")
        for i, mon in enumerate(self.monitors):
            print(f"  显示器 {i+1}: {mon['width']}x{mon['height']} 位置: ({mon['left']}, {mon['top']})")
        print(f"\n提示: 按 Z 开启/关闭放大镜")
        print(f"      按 X 锁定/解锁窗口位置（锁定时窗口固定，内容仍跟随鼠标）")
        print(f"      鼠标滚轮调整放大倍数")
        print(f"      鼠标拖拽窗口可以移动位置")
    
    def update_monitors_info(self):
        """使用 Windows API 获取多显示器信息"""
        try:
            monitors = []
            
            class MONITORINFOEX(ctypes.Structure):
                _fields_ = [
                    ("cbSize", ctypes.c_ulong),
                    ("rcMonitor", wintypes.RECT),
                    ("rcWork", wintypes.RECT),
                    ("dwFlags", ctypes.c_ulong),
                    ("szDevice", ctypes.c_wchar * 32)
                ]
            
            def monitor_enum_proc(hmonitor, hdc, rect, lparam):
                monitor_info = MONITORINFOEX()
                monitor_info.cbSize = ctypes.sizeof(MONITORINFOEX)
                if ctypes.windll.user32.GetMonitorInfoW(hmonitor, ctypes.byref(monitor_info)):
                    monitor = {
                        'left': monitor_info.rcMonitor.left,
                        'top': monitor_info.rcMonitor.top,
                        'right': monitor_info.rcMonitor.right,
                        'bottom': monitor_info.rcMonitor.bottom,
                        'width': monitor_info.rcMonitor.right - monitor_info.rcMonitor.left,
                        'height': monitor_info.rcMonitor.bottom - monitor_info.rcMonitor.top,
                        'name': monitor_info.szDevice
                    }
                    monitors.append(monitor)
                return True
            
            MonitorEnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_ulong, ctypes.c_ulong, ctypes.POINTER(wintypes.RECT), ctypes.c_ulong)
            callback = MonitorEnumProc(monitor_enum_proc)
            ctypes.windll.user32.EnumDisplayMonitors(None, None, callback, 0)
            
            if monitors:
                monitors.sort(key=lambda m: (m['left'], m['top']))
                self.monitors = monitors
            else:
                screen_width = ctypes.windll.user32.GetSystemMetrics(0)
                screen_height = ctypes.windll.user32.GetSystemMetrics(1)
                self.monitors = [{'left': 0, 'top': 0, 'width': screen_width, 'height': screen_height}]
        except Exception as e:
            print(f"获取显示器信息失败: {e}")
            screen_width = ctypes.windll.user32.GetSystemMetrics(0)
            screen_height = ctypes.windll.user32.GetSystemMetrics(1)
            self.monitors = [{'left': 0, 'top': 0, 'width': screen_width, 'height': screen_height}]
    
    def get_monitor_at_position(self, x, y):
        """获取坐标所在的显示器"""
        for i, mon in enumerate(self.monitors):
            if (mon['left'] <= x < mon['left'] + mon['width'] and
                mon['top'] <= y < mon['top'] + mon['height']):
                return i, mon
        return 0, self.monitors[0]
    
    def capture_screen_area_direct(self, center_x, center_y):
        """直接使用 Windows API 截图"""
        try:
            # 计算截图区域
            half_width = self.lens_width / (2 * self.zoom_level)
            half_height = self.lens_height / (2 * self.zoom_level)
            
            left = int(center_x - half_width)
            top = int(center_y - half_height)
            right = int(center_x + half_width)
            bottom = int(center_y + half_height)
            
            monitor_id, monitor = self.get_monitor_at_position(center_x, center_y)
            
            # 边界限制
            left = max(monitor['left'], left)
            top = max(monitor['top'], top)
            right = min(monitor['left'] + monitor['width'], right)
            bottom = min(monitor['top'] + monitor['height'], bottom)
            
            if right <= left or bottom <= top:
                return None
            
            width = right - left
            height = bottom - top
            
            # 截屏
            hwnd_desktop = win32gui.GetDesktopWindow()
            desktop_dc = win32gui.GetWindowDC(hwnd_desktop)
            img_dc = win32ui.CreateDCFromHandle(desktop_dc)
            mem_dc = img_dc.CreateCompatibleDC()
            
            screenshot = win32ui.CreateBitmap()
            screenshot.CreateCompatibleBitmap(img_dc, width, height)
            mem_dc.SelectObject(screenshot)
            
            mem_dc.BitBlt((0, 0), (width, height), img_dc, (left, top), win32con.SRCCOPY)
            
            bmpinfo = screenshot.GetInfo()
            bmpstr = screenshot.GetBitmapBits(True)
            img = Image.frombuffer(
                'RGB',
                (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                bmpstr, 'raw', 'BGRX', 0, 1
            )
            
            win32gui.DeleteObject(screenshot.GetHandle())
            mem_dc.DeleteDC()
            img_dc.DeleteDC()
            win32gui.ReleaseDC(hwnd_desktop, desktop_dc)
            
            return img
            
        except Exception as e:
            return None
    
    def setup_window(self):
        """创建放大镜窗口"""
        self.window = tk.Tk()
        self.window.title("屏幕放大镜")
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        self.window.geometry(f"{self.lens_width}x{self.lens_height}")
        self.window.attributes('-alpha', 0.95)
        
        self.canvas = tk.Canvas(self.window, width=self.lens_width, 
                               height=self.lens_height, highlightthickness=0,
                               cursor="hand2", bg='black')
        self.canvas.pack()
        
        # 绑定事件
        self.canvas.bind('<Button-2>', self.reset_zoom)
        self.canvas.bind('<Button-3>', self.toggle_lock)
        self.canvas.bind('<MouseWheel>', self.on_mousewheel)
        
        # 拖动窗口功能（用于手动调整窗口位置）
        self.canvas.bind('<Button-1>', self.start_move)
        self.canvas.bind('<B1-Motion>', self.on_move)
        
        self.window.bind('<KeyPress-x>', self.toggle_lock)
        self.window.bind('<KeyPress-X>', self.toggle_lock)
        self.window.bind('<KeyPress-z>', lambda e: self.toggle_magnifier())
        self.window.bind('<KeyPress-Z>', lambda e: self.toggle_magnifier())
        
        self.window.withdraw()
        
        # 拖动相关变量
        self.drag_start_x = 0
        self.drag_start_y = 0
    
    def start_move(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y
    
    def on_move(self, event):
        x = self.window.winfo_x() + (event.x - self.drag_start_x)
        y = self.window.winfo_y() + (event.y - self.drag_start_y)
        self.window.geometry(f"+{x}+{y}")
        
        # 如果窗口在锁定状态下被手动移动，更新锁定位置
        if self.is_window_locked:
            self.locked_window_x = x
            self.locked_window_y = y
    
    def setup_hotkeys(self):
        """注册全局快捷键"""
        try:
            keyboard.add_hotkey(self.toggle_key, self.toggle_magnifier, suppress=True)
            keyboard.add_hotkey(self.lock_key, self.toggle_lock, suppress=True)
            print("全局快捷键已注册")
        except Exception as e:
            print(f"注册快捷键失败: {e}")
            print("请以管理员权限运行程序")
    
    def toggle_magnifier(self):
        if self.is_active:
            self.deactivate()
        else:
            self.activate()
    
    def toggle_lock(self, event=None):
        if not self.is_active:
            return
        
        self.is_window_locked = not self.is_window_locked
        
        if self.is_window_locked:
            # 锁定时，保存当前窗口位置
            self.locked_window_x = self.window.winfo_x()
            self.locked_window_y = self.window.winfo_y()
            print(f"🔒 窗口已锁定 - 窗口固定在位置 ({self.locked_window_x}, {self.locked_window_y})")
            print(f"   内容将继续跟随鼠标移动")
        else:
            print(f"🔓 窗口已解锁 - 窗口将跟随鼠标移动")
            # 解锁后立即更新窗口位置到当前鼠标位置
            mouse_x, mouse_y = pyautogui.position()
            self.update_window_position(mouse_x, mouse_y)
    
    def activate(self):
        self.is_active = True
        self.is_window_locked = False
        
        # 获取当前鼠标位置并设置窗口位置
        mouse_x, mouse_y = pyautogui.position()
        self.update_window_position(mouse_x, mouse_y)
        
        self.window.deiconify()
        self.window.lift()
        self.window.focus_set()
        
        print(f"✅ 放大镜已激活 | 放大倍数: {self.zoom_level:.1f}x | 窗口: {self.lens_width}×{self.lens_height}")
        print(f"   模式: 窗口跟随鼠标 (按 X 锁定窗口位置)")
        
        # 启动更新循环
        self.update_loop()
    
    def update_window_position(self, mouse_x, mouse_y):
        """更新窗口位置（相对于鼠标位置）"""
        if self.is_window_locked:
            # 窗口锁定模式：不移动窗口
            return
        
        window_x = mouse_x + self.offset_x
        window_y = mouse_y + self.offset_y
        
        monitor_id, monitor = self.get_monitor_at_position(mouse_x, mouse_y)
        
        # 边界检测
        max_x = monitor['left'] + monitor['width'] - self.lens_width
        max_y = monitor['top'] + monitor['height'] - self.lens_height
        
        window_x = max(monitor['left'], min(window_x, max_x))
        window_y = max(monitor['top'], min(window_y, max_y))
        
        self.window.geometry(f"+{int(window_x)}+{int(window_y)}")
    
    def deactivate(self):
        self.is_active = False
        self.window.withdraw()
        print(f"❌ 放大镜已关闭")
    
    def reset_zoom(self, event=None):
        self.zoom_level = 2.0
        print(f"🔄 重置倍数: {self.zoom_level:.1f}x")
    
    def on_mousewheel(self, event):
        if not self.is_active:
            return
        if event.delta > 0:
            self.zoom_level = min(self.zoom_level + self.zoom_step, self.max_zoom)
            print(f"🔍 放大: {self.zoom_level:.1f}x")
        else:
            self.zoom_level = max(self.zoom_level - self.zoom_step, self.min_zoom)
            print(f"🔍 缩小: {self.zoom_level:.1f}x")
    
    def add_crosshair(self, img):
        """在图像中心添加十字准星"""
        if img is None:
            return img
        draw = ImageDraw.Draw(img)
        cx = img.width // 2
        cy = img.height // 2
        
        crosshair_size = min(img.width, img.height) // 12
        
        draw.line([(cx - crosshair_size, cy), (cx + crosshair_size, cy)], fill='red', width=2)
        draw.line([(cx, cy - crosshair_size), (cx, cy + crosshair_size)], fill='red', width=2)
        
        ring_size = min(img.width, img.height) // 20
        draw.ellipse([(cx - ring_size, cy - ring_size), (cx + ring_size, cy + ring_size)], outline='red', width=2)
        draw.ellipse([(cx - 2, cy - 2), (cx + 2, cy + 2)], fill='red')
        
        return img
    
    def update_magnifier(self):
        """更新放大镜内容"""
        if not self.is_active:
            return
        
        try:
            # 获取当前鼠标位置（始终用于内容）
            mouse_x, mouse_y = pyautogui.position()
            
            # 根据窗口锁定状态决定是否移动窗口
            if not self.is_window_locked:
                # 窗口未锁定：窗口跟随鼠标移动
                self.update_window_position(mouse_x, mouse_y)
            
            # 内容始终跟随鼠标（不管窗口是否锁定）
            screenshot = self.capture_screen_area_direct(mouse_x, mouse_y)
            
            if screenshot is None:
                self.canvas.delete("all")
                self.canvas.create_text(self.lens_width//2, self.lens_height//2,
                                       text="截图失败", fill="red",
                                       font=("Arial", 12), anchor="center")
                return
            
            # 放大图像
            magnified = screenshot.resize((self.lens_width, self.lens_height), 
                                         Image.Resampling.LANCZOS)
            magnified = self.add_crosshair(magnified)
            
            # 显示图像
            self.photo = ImageTk.PhotoImage(magnified)
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor='nw', image=self.photo)
            
            # 显示状态信息
            status_y = 15
            if self.is_window_locked:
                # 窗口锁定状态
                self.canvas.create_text(self.lens_width - 10, status_y, 
                                       text="🔒 窗口已锁定", font=("Arial", 12),
                                       fill="orange", anchor="ne")
                self.canvas.create_text(self.lens_width - 10, status_y + 20,
                                       text="内容跟随鼠标", font=("Arial", 9), 
                                       fill="yellow", anchor="ne")
            else:
                # 窗口跟随状态
                self.canvas.create_text(self.lens_width - 10, status_y,
                                       text="🔍 窗口跟随", font=("Arial", 12),
                                       fill="green", anchor="ne")
            
            # 显示放大倍数
            self.canvas.create_text(10, status_y,
                                   text=f"{self.zoom_level:.1f}x",
                                   font=("Arial", 12), fill="white", anchor="nw")
            
            # 显示鼠标坐标
            self.canvas.create_text(10, status_y + 20,
                                   text=f"🖱️ ({mouse_x}, {mouse_y})",
                                   font=("Arial", 9), fill="white", anchor="nw")
            
            # 显示窗口位置提示
            if self.is_window_locked:
                self.canvas.create_text(10, self.lens_height - 10,
                                       text="💡 鼠标拖拽可移动窗口",
                                       font=("Arial", 8), fill="gray", anchor="sw")
            
        except Exception as e:
            pass
    
    def update_loop(self):
        """持续更新循环"""
        if self.is_active:
            self.update_magnifier()
            # 60fps 更新频率
            self.window.after(16, self.update_loop)
    
    def run(self):
        try:
            self.window.mainloop()
        except KeyboardInterrupt:
            print("\n程序已退出")
        finally:
            keyboard.unhook_all()

def main():
    try:
        import pyautogui
        import keyboard
        from PIL import Image, ImageTk
        import win32gui
        import win32ui
        import win32con
    except ImportError as e:
        print("请安装依赖: pip install pyautogui keyboard Pillow pywin32")
        sys.exit(1)
    
    if sys.platform == 'win32':
        import ctypes
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except:
            pass
        
        if not ctypes.windll.shell32.IsUserAnAdmin():
            print("⚠️  建议以管理员权限运行，否则快捷键可能不生效")
    
    magnifier = ScreenMagnifier()
    magnifier.run()

if __name__ == "__main__":
    main()
