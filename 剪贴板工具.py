import tkinter as tk
from tkinter import ttk, messagebox
import keyboard
import pyperclip
import json
import os
from datetime import datetime
import screeninfo

class MultiClipboard:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("多重剪切板工具")
        self.root.geometry("400x500")
        self.root.resizable(True, True)
        
        # 设置窗口置顶
        self.root.attributes('-topmost', True)
        
        # 存储剪切板历史
        self.clipboard_history = []
        self.max_history = 20
        
        # 配置文件路径
        self.config_file = "clipboard_history.json"
        
        # 窗口位置相关
        self.window_width = 400
        self.window_height = 500
        self.margin = 10  # 窗口与屏幕边缘的边距
        
        # 加载历史记录
        self.load_history()
        
        # 创建UI
        self.create_widgets()
        
        # 注册全局热键
        self.register_hotkey()
        
        # 注册数字快捷键
        self.register_number_hotkeys()
        
        # 初始隐藏窗口
        self.root.withdraw()
        
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 绑定窗口移动事件，记录窗口位置
        self.root.bind('<Configure>', self.on_window_configure)
        
        # 打印使用方法
        self.print_usage()
        
    def get_screen_info(self):
        """获取所有显示器信息"""
        try:
            screens = screeninfo.get_monitors()
            return screens
        except:
            # 如果screeninfo不可用，使用默认单屏信息
            return None
            
    def get_mouse_position(self):
        """获取鼠标当前位置"""
        try:
            # 使用pyautogui获取鼠标位置，如果没有则使用tkinter的winfo_pointerxy
            import pyautogui
            return pyautogui.position()
        except:
            # 降级方案：使用tkinter获取鼠标位置
            x = self.root.winfo_pointerx()
            y = self.root.winfo_pointery()
            return type('Point', (), {'x': x, 'y': y})()
            
    def get_monitor_at_position(self, x, y):
        """获取鼠标位置所在的显示器"""
        screens = self.get_screen_info()
        if screens:
            for screen in screens:
                if (screen.x <= x <= screen.x + screen.width and 
                    screen.y <= y <= screen.y + screen.height):
                    return screen
            # 如果没找到，返回第一个显示器
            return screens[0]
        return None
        
    def calculate_window_position(self):
        """计算窗口应该显示的位置"""
        mouse_pos = self.get_mouse_position()
        screen = self.get_monitor_at_position(mouse_pos.x, mouse_pos.y)
        
        if screen:
            # 计算窗口位置（在鼠标位置附近显示）
            x = mouse_pos.x + 10  # 鼠标右下方偏移
            y = mouse_pos.y + 10
            
            # 获取屏幕边界
            screen_left = screen.x
            screen_right = screen.x + screen.width
            screen_top = screen.y
            screen_bottom = screen.y + screen.height
            
            # 调整水平位置
            if x + self.window_width > screen_right - self.margin:
                # 如果右侧放不下，放在鼠标左侧
                x = mouse_pos.x - self.window_width - 10
                
            if x < screen_left + self.margin:
                # 如果左侧放不下，从左侧开始
                x = screen_left + self.margin
                
            # 调整垂直位置
            if y + self.window_height > screen_bottom - self.margin:
                # 如果底部放不下，放在鼠标上方
                y = mouse_pos.y - self.window_height - 10
                
            if y < screen_top + self.margin:
                # 如果顶部放不下，从顶部开始
                y = screen_top + self.margin
                
            # 确保窗口完全在屏幕内
            if x + self.window_width > screen_right - self.margin:
                x = screen_right - self.window_width - self.margin
            if y + self.window_height > screen_bottom - self.margin:
                y = screen_bottom - self.window_height - self.margin
                
            return int(x), int(y)
        else:
            # 如果无法获取显示器信息，使用默认位置
            return 100, 100
            
    def on_window_configure(self, event=None):
        """窗口配置变化时记录位置"""
        if self.root.state() != 'withdrawn':
            # 记录窗口位置以便下次显示
            self.last_window_x = self.root.winfo_x()
            self.last_window_y = self.root.winfo_y()
            
    def toggle_window(self):
        if self.root.state() == 'withdrawn':
            # 计算窗口位置
            x, y = self.calculate_window_position()
            self.root.geometry(f"{self.window_width}x{self.window_height}+{x}+{y}")
            
            # 显示窗口
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
            
            # 将焦点设置到列表
            self.history_listbox.focus_set()
            # 更新列表内容
            self.update_listbox()
        else:
            self.hide_window()
            
    def print_usage(self):
        """在控制台打印使用方法"""
        print("=" * 60)
        print("多重剪切板工具已启动")
        print("=" * 60)
        print("快捷键说明:")
        print("  Win+C          - 显示/隐藏多重剪切板窗口")
        print("  Ctrl+1~9       - 直接粘贴第1-9条历史记录")
        print("  Ctrl+0         - 直接粘贴第10条历史记录")
        print("  Ctrl+V         - 粘贴当前选中的内容（在窗口内）")
        print("  Enter          - 在窗口内粘贴选中内容")
        print("  ← → 方向键     - 在窗口内选择不同记录")
        print("  鼠标左键单击   - 粘贴选中的记录并隐藏窗口")
        print("  鼠标右键单击   - 显示编辑/删除菜单")
        print("=" * 60)
        print(f"当前已保存 {len(self.clipboard_history)} 条剪切板记录")
        print("提示: 使用数字快捷键时窗口会自动隐藏")
        
        # 显示双屏支持信息
        screens = self.get_screen_info()
        if screens:
            print(f"检测到 {len(screens)} 个显示器，支持多屏智能定位")
        print("=" * 60)
        
    def create_widgets(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="多重剪切板", font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 10))
        
        # 提示标签
        hint_label = ttk.Label(main_frame, text="快捷键: Ctrl+1-9,0 快速粘贴 | Win+C 显示/隐藏", 
                              font=("Arial", 9))
        hint_label.pack(pady=(0, 10))
        
        # 搜索框
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(search_frame, text="搜索:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        self.search_entry.bind('<KeyRelease>', self.filter_history)
        
        # 历史记录列表
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.history_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, font=("Arial", 10))
        self.history_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        # 单击绑定
        self.history_listbox.bind('<ButtonRelease-1>', self.on_single_click)
        self.history_listbox.bind('<Return>', self.paste_selected)
        # 右键菜单绑定
        self.history_listbox.bind('<Button-3>', self.show_context_menu)
        
        scrollbar.config(command=self.history_listbox.yview)
        
        # 创建右键菜单
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="编辑", command=self.edit_selected)
        self.context_menu.add_command(label="删除", command=self.delete_selected)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="复制到剪切板", command=self.copy_to_clipboard)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="粘贴选中", command=self.paste_selected).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="清空历史", command=self.clear_history).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="隐藏窗口", command=self.hide_window).pack(side=tk.RIGHT)
        
        # 快捷键提示
        shortcut_frame = ttk.Frame(main_frame)
        shortcut_frame.pack(fill=tk.X, pady=(5, 0))
        
        shortcuts = ["Ctrl+1", "Ctrl+2", "Ctrl+3", "Ctrl+4", "Ctrl+5", 
                    "Ctrl+6", "Ctrl+7", "Ctrl+8", "Ctrl+9", "Ctrl+0"]
        
        for i, shortcut in enumerate(shortcuts):
            if i < 10:
                shortcut_label = ttk.Label(shortcut_frame, text=f"{shortcut}", font=("Arial", 8))
                shortcut_label.pack(side=tk.LEFT, padx=2)
        
        # 状态栏
        self.status_var = tk.StringVar()
        self.status_var.set(f"共 {len(self.clipboard_history)} 条记录")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, pady=(10, 0))
        
        # 更新列表显示
        self.update_listbox()
        
    def get_time_display(self, timestamp):
        """获取时间显示格式（月日时分）"""
        try:
            # 尝试解析时间戳
            dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            return dt.strftime("%m-%d %H:%M")
        except:
            # 如果解析失败，返回原字符串
            return timestamp
        
    def show_context_menu(self, event):
        """显示右键菜单"""
        # 获取点击位置的项目索引
        index = self.history_listbox.nearest(event.y)
        if index >= 0:
            # 设置选中项
            self.history_listbox.selection_clear(0, tk.END)
            self.history_listbox.selection_set(index)
            # 显示右键菜单
            self.context_menu.post(event.x_root, event.y_root)
        
    def register_hotkey(self):
        # 注册Win+C热键
        try:
            keyboard.add_hotkey('win+c', self.toggle_window)
        except Exception as e:
            messagebox.showerror("错误", f"无法注册热键: {e}")
            
    def register_number_hotkeys(self):
        """注册Ctrl+数字键的快捷键"""
        try:
            # 注册 Ctrl+1 到 Ctrl+9
            for i in range(1, 10):
                keyboard.add_hotkey(f'ctrl+{i}', self.paste_by_number, args=(i-1,))
            # 注册 Ctrl+0
            keyboard.add_hotkey('ctrl+0', self.paste_by_number, args=(9,))
        except Exception as e:
            messagebox.showerror("错误", f"无法注册数字快捷键: {e}")
            
    def paste_by_number(self, index):
        """根据数字快捷键粘贴对应位置的内容"""
        # 获取当前实际历史记录（考虑搜索筛选）
        search_term = self.search_var.get().lower()
        if search_term:
            filtered_items = [item for item in self.clipboard_history 
                             if search_term in item['content'].lower()]
            if index < len(filtered_items):
                content = filtered_items[index]['content']
                # 复制到剪切板
                pyperclip.copy(content)
                # 执行粘贴
                self.perform_paste_without_hide()
                # 打印提示
                print(f"已粘贴第{index+1}条记录")
        else:
            if index < len(self.clipboard_history):
                content = self.clipboard_history[index]['content']
                # 复制到剪切板
                pyperclip.copy(content)
                # 执行粘贴
                self.perform_paste_without_hide()
                # 打印提示
                print(f"已粘贴第{index+1}条记录")
                
    def perform_paste_without_hide(self):
        """执行粘贴操作但不隐藏窗口"""
        try:
            # 模拟Ctrl+V粘贴
            keyboard.send('ctrl+v')
        except Exception as e:
            print(f"粘贴操作失败: {e}")
            
    def hide_window(self):
        self.root.withdraw()
        
    def update_listbox(self):
        self.history_listbox.delete(0, tk.END)
        for i, item in enumerate(self.clipboard_history):
            # 截断长文本以便显示
            display_text = item['content']
            if len(display_text) > 50:
                display_text = display_text[:47] + "..."
            timestamp = self.get_time_display(item['timestamp'])
            # 添加编号以便用户知道快捷键
            number = i + 1
            if number == 10:
                number = 0
            self.history_listbox.insert(tk.END, f"{number}. {timestamp} - {display_text}")
            
        self.status_var.set(f"共 {len(self.clipboard_history)} 条记录")
        
    def filter_history(self, event=None):
        search_term = self.search_var.get().lower()
        self.history_listbox.delete(0, tk.END)
        
        filtered_items = [item for item in self.clipboard_history 
                         if search_term in item['content'].lower()]
        
        for i, item in enumerate(filtered_items):
            display_text = item['content']
            if len(display_text) > 50:
                display_text = display_text[:47] + "..."
            timestamp = self.get_time_display(item['timestamp'])
            number = i + 1
            if number == 10:
                number = 0
            self.history_listbox.insert(tk.END, f"{number}. {timestamp} - {display_text}")
            
        self.status_var.set(f"共 {len(filtered_items)} 条记录 (筛选自 {len(self.clipboard_history)} 条)")
    
    def get_actual_index(self, listbox_index):
        """根据列表框索引获取实际数据索引"""
        search_term = self.search_var.get().lower()
        if search_term:
            # 有搜索条件时，获取筛选后的列表
            filtered_items = [item for item in self.clipboard_history 
                             if search_term in item['content'].lower()]
            if listbox_index < len(filtered_items):
                # 返回实际数据中的索引
                actual_item = filtered_items[listbox_index]
                return self.clipboard_history.index(actual_item)
            else:
                return None
        else:
            # 没有搜索条件时，直接返回列表框索引
            return listbox_index if listbox_index < len(self.clipboard_history) else None
        
    def on_single_click(self, event=None):
        """单击事件处理"""
        # 获取点击位置
        index = self.history_listbox.nearest(event.y)
        if index >= 0:
            # 设置选中项
            self.history_listbox.selection_clear(0, tk.END)
            self.history_listbox.selection_set(index)
            # 立即执行粘贴操作
            self.paste_selected()
        
    def paste_selected(self, event=None):
        """粘贴选中的内容并隐藏窗口"""
        selection = self.history_listbox.curselection()
        if selection:
            index = selection[0]
            actual_index = self.get_actual_index(index)
            
            if actual_index is not None and actual_index < len(self.clipboard_history):
                content = self.clipboard_history[actual_index]['content']
                # 将内容复制到系统剪切板
                pyperclip.copy(content)
                
                # 先隐藏窗口，让焦点回到之前的应用
                self.hide_window()
                
                # 短暂延迟后执行粘贴操作
                self.root.after(100, self.perform_paste)
            
    def perform_paste(self):
        """执行实际的粘贴操作"""
        try:
            # 模拟Ctrl+V粘贴
            keyboard.send('ctrl+v')
        except Exception as e:
            # 如果模拟粘贴失败，至少内容已经在剪切板中
            # 用户仍然可以手动按Ctrl+V粘贴
            print(f"粘贴操作失败: {e}")
            
    def copy_to_clipboard(self):
        """复制选中内容到剪切板（不粘贴）"""
        selection = self.history_listbox.curselection()
        if selection:
            index = selection[0]
            actual_index = self.get_actual_index(index)
            
            if actual_index is not None and actual_index < len(self.clipboard_history):
                content = self.clipboard_history[actual_index]['content']
                pyperclip.copy(content)
                # 显示提示
                self.status_var.set("已复制到剪切板")
                # 几秒后恢复状态显示
                self.root.after(2000, self.update_status)
                
    def update_status(self):
        """更新状态栏"""
        self.status_var.set(f"共 {len(self.clipboard_history)} 条记录")
            
    def edit_selected(self):
        """编辑选中的项目"""
        selection = self.history_listbox.curselection()
        if selection:
            index = selection[0]
            actual_index = self.get_actual_index(index)
            
            if actual_index is not None:
                self.edit_item(actual_index)
                
    def edit_item(self, index):
        # 创建编辑窗口
        edit_window = tk.Toplevel(self.root)
        edit_window.title("编辑内容")
        edit_window.geometry("400x300")
        edit_window.resizable(True, True)
        edit_window.attributes('-topmost', True)
        
        # 内容文本框
        content_text = tk.Text(edit_window, wrap=tk.WORD)
        content_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        content_text.insert(tk.END, self.clipboard_history[index]['content'])
        
        # 按钮框架
        button_frame = ttk.Frame(edit_window)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def save_changes():
            new_content = content_text.get(1.0, tk.END).strip()
            if new_content:
                self.clipboard_history[index]['content'] = new_content
                self.clipboard_history[index]['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.update_listbox()
                self.save_history()
                edit_window.destroy()
            else:
                messagebox.showwarning("警告", "内容不能为空")
                
        ttk.Button(button_frame, text="保存", command=save_changes).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="取消", command=edit_window.destroy).pack(side=tk.LEFT)
        
    def delete_selected(self):
        """删除选中的项目"""
        selection = self.history_listbox.curselection()
        if selection:
            index = selection[0]
            actual_index = self.get_actual_index(index)
            
            if actual_index is not None:
                # 获取要删除的内容预览
                content_preview = self.clipboard_history[actual_index]['content']
                if len(content_preview) > 50:
                    content_preview = content_preview[:47] + "..."
                
                # 确认删除
                if messagebox.askyesno("确认删除", f"确定要删除这条记录吗？\n\n{content_preview}"):
                    self.clipboard_history.pop(actual_index)
                    self.update_listbox()
                    self.save_history()
            
    def clear_history(self):
        if messagebox.askyesno("确认", "确定要清空所有历史记录吗？"):
            self.clipboard_history.clear()
            self.update_listbox()
            self.save_history()
            
    def save_history(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.clipboard_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("错误", f"保存历史记录失败: {e}")
            
    def load_history(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.clipboard_history = json.load(f)
            except Exception as e:
                messagebox.showerror("错误", f"加载历史记录失败: {e}")
                
    def add_to_history(self, content):
        # 检查是否已存在相同内容
        for item in self.clipboard_history:
            if item['content'] == content:
                # 更新现有项的时间戳
                item['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                # 移动到列表顶部
                self.clipboard_history.remove(item)
                self.clipboard_history.insert(0, item)
                return
                
        # 添加新项
        new_item = {
            'content': content,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.clipboard_history.insert(0, new_item)
        
        # 限制历史记录数量
        if len(self.clipboard_history) > self.max_history:
            self.clipboard_history = self.clipboard_history[:self.max_history]
            
        self.save_history()
        
    def monitor_clipboard(self):
        # 监控剪切板变化
        try:
            current_content = pyperclip.paste()
            if hasattr(self, 'last_clipboard_content'):
                if current_content != self.last_clipboard_content and current_content.strip():
                    self.add_to_history(current_content)
                    if self.root.state() != 'withdrawn':
                        self.update_listbox()
            self.last_clipboard_content = current_content
        except:
            pass
            
        # 每500ms检查一次剪切板
        self.root.after(500, self.monitor_clipboard)
        
    def on_closing(self):
        # 保存历史记录并退出
        self.save_history()
        self.root.destroy()
        
    def run(self):
        # 开始监控剪切板
        self.root.after(500, self.monitor_clipboard)
        self.root.mainloop()

if __name__ == "__main__":
    # 尝试安装screeninfo（如果未安装）
    try:
        import screeninfo
    except ImportError:
        import subprocess
        import sys
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "screeninfo"])
            import screeninfo
        except:
            print("警告: 无法安装screeninfo，将使用基本屏幕支持")
            pass
    
    app = MultiClipboard()
    app.run()
