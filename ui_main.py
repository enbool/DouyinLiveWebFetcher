#!/usr/bin/python
# coding:utf-8

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading
import os
import subprocess
import sys
from datetime import datetime
import json
import gzip
import time
import requests
import websocket
from liveMan import DouyinLiveWebFetcher
from protobuf.douyin import *
import io
from contextlib import redirect_stdout, redirect_stderr

class ModernStyle:
    """现代化UI样式配置"""
    # Windows 11 / macOS 风格配色
    BG_PRIMARY = "#F5F5F7"  # 主背景色 - 浅灰
    BG_SECONDARY = "#FFFFFF"  # 次要背景色 - 白色
    BG_ACCENT = "#007AFF"  # 强调色 - 蓝色
    BG_ACCENT_HOVER = "#0056CC"  # 强调色悬停
    BG_DANGER = "#FF6B6B"  # 危险色 - 柔和红色
    BG_SUCCESS = "#51CF66"  # 成功色 - 柔和绿色
    BG_NEUTRAL = "#6C757D"  # 中性色 - 灰色

    TEXT_PRIMARY = "#1D1D1F"  # 主文本色
    TEXT_SECONDARY = "#6E6E73"  # 次要文本色
    TEXT_LIGHT = "#FFFFFF"  # 浅色文本

    BORDER_COLOR = "#D1D1D6"  # 边框色
    SHADOW_COLOR = "#00000010"  # 阴影色

    # 控制台配色 (类似 VS Code Dark)
    CONSOLE_BG = "#1E1E1E"
    CONSOLE_FG = "#D4D4D4"
    CONSOLE_ACCENT = "#4FC3F7"

class LiveStreamUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("抖音直播间弹幕采集工具")
        self.root.geometry("1400x900")  # 增大窗口尺寸
        self.root.resizable(True, True)

        # 设置现代化样式
        self.setup_modern_style()

        # 直播间数据存储
        self.live_streams = {}
        self.live_fetchers = {}
        self.config_file = "live_config.json"

        # 创建data目录（如果不存在）
        self.data_dir = "data"
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

        # 当前选中的直播间ID
        self.selected_live_id = None

        self.setup_ui()
        self.load_config()

    def setup_modern_style(self):
        """设置现代化样式主题"""
        style = ttk.Style()

        # 设置主题
        style.theme_use('clam')

        # 配置主窗口
        self.root.configure(bg=ModernStyle.BG_PRIMARY)

        # 配置Frame样式
        style.configure('Modern.TFrame',
                       background=ModernStyle.BG_SECONDARY,
                       relief='flat',
                       borderwidth=1)

        style.configure('Card.TFrame',
                       background=ModernStyle.BG_SECONDARY,
                       relief='flat',
                       borderwidth=0)

        # 配置LabelFrame样式
        style.configure('Modern.TLabelframe',
                       background=ModernStyle.BG_SECONDARY,
                       relief='flat',
                       borderwidth=1,
                       lightcolor=ModernStyle.BORDER_COLOR,
                       darkcolor=ModernStyle.BORDER_COLOR)

        style.configure('Modern.TLabelframe.Label',
                       background=ModernStyle.BG_SECONDARY,
                       foreground=ModernStyle.TEXT_PRIMARY,
                       font=('Segoe UI', 11, 'bold'))

        # 配置按钮样式 - 使用更柔和的颜色
        style.configure('Modern.TButton',
                       background=ModernStyle.BG_ACCENT,
                       foreground=ModernStyle.TEXT_LIGHT,
                       font=('Segoe UI', 10),
                       padding=(20, 8),
                       relief='flat',
                       borderwidth=0)

        style.map('Modern.TButton',
                 background=[('active', ModernStyle.BG_ACCENT_HOVER),
                           ('pressed', ModernStyle.BG_ACCENT_HOVER)])

        # 柔和的危险按钮样式
        style.configure('Danger.TButton',
                       background=ModernStyle.BG_DANGER,
                       foreground=ModernStyle.TEXT_LIGHT,
                       font=('Segoe UI', 10),
                       padding=(20, 8),
                       relief='flat',
                       borderwidth=0)

        # 柔和的成功按钮样式
        style.configure('Success.TButton',
                       background=ModernStyle.BG_SUCCESS,
                       foreground=ModernStyle.TEXT_LIGHT,
                       font=('Segoe UI', 10),
                       padding=(20, 8),
                       relief='flat',
                       borderwidth=0)

        # 中性按钮样式
        style.configure('Neutral.TButton',
                       background=ModernStyle.BG_NEUTRAL,
                       foreground=ModernStyle.TEXT_LIGHT,
                       font=('Segoe UI', 10),
                       padding=(20, 8),
                       relief='flat',
                       borderwidth=0)

        # 圆形小按钮样式（用于帮助按钮）
        style.configure('Circle.TButton',
                       background=ModernStyle.TEXT_SECONDARY,
                       foreground=ModernStyle.TEXT_LIGHT,
                       font=('Segoe UI', 10, 'bold'),
                       padding=(0, 0),
                       relief='flat',
                       borderwidth=0,
                       width=3)

        style.map('Circle.TButton',
                 background=[('active', ModernStyle.BG_ACCENT),
                           ('pressed', ModernStyle.BG_ACCENT_HOVER)])

        # 配置Treeview样式
        style.configure('Modern.Treeview',
                       background=ModernStyle.BG_SECONDARY,
                       foreground=ModernStyle.TEXT_PRIMARY,
                       font=('Segoe UI', 10),
                       fieldbackground=ModernStyle.BG_SECONDARY,
                       borderwidth=0,
                       relief='flat')

        style.configure('Modern.Treeview.Heading',
                       background=ModernStyle.BG_PRIMARY,
                       foreground=ModernStyle.TEXT_PRIMARY,
                       font=('Segoe UI', 10, 'bold'),
                       relief='flat',
                       borderwidth=1)

        # 配置Entry样式
        style.configure('Modern.TEntry',
                       fieldbackground=ModernStyle.BG_SECONDARY,
                       foreground=ModernStyle.TEXT_PRIMARY,
                       font=('Segoe UI', 11),
                       borderwidth=2,
                       relief='flat',
                       insertcolor=ModernStyle.BG_ACCENT)

        # 配置Scrollbar样式 - 现代化滚动条
        style.configure('Modern.Vertical.TScrollbar',
                       background=ModernStyle.BG_PRIMARY,
                       troughcolor=ModernStyle.BG_PRIMARY,
                       arrowcolor=ModernStyle.TEXT_SECONDARY,
                       relief='flat',
                       borderwidth=0)

    def setup_ui(self):
        """设置UI界面"""
        # 主框架 - 使用更大的内边距
        main_frame = ttk.Frame(self.root, style='Card.TFrame', padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)

        # 上半部分框架：直播间列表和控制按钮
        top_frame = ttk.Frame(main_frame, style='Card.TFrame')
        top_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 15))
        top_frame.columnconfigure(0, weight=1)
        top_frame.rowconfigure(0, weight=1)

        # 直播间列表框架 - 现代化卡片样式
        list_frame = ttk.LabelFrame(top_frame, text="  直播间列表  ",
                                   style='Modern.TLabelframe', padding="15")
        list_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 15))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        # 创建TreeView容器框架
        tree_container = ttk.Frame(list_frame, style='Card.TFrame')
        tree_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_container.columnconfigure(0, weight=1)
        tree_container.rowconfigure(0, weight=1)

        # 创建Treeview
        columns = ("live_id", "username", "status", "excel_file")
        self.tree = ttk.Treeview(tree_container, columns=columns, show="headings",
                                height=14, style='Modern.Treeview')

        # 设置列标题
        self.tree.heading("live_id", text="直播间ID")
        self.tree.heading("username", text="主播信息")
        self.tree.heading("status", text="采集状态")
        self.tree.heading("excel_file", text="数据文件")

        # 设置列宽 - 更合理的分配
        self.tree.column("live_id", width=140, minwidth=120)
        self.tree.column("username", width=200, minwidth=150)
        self.tree.column("status", width=120, minwidth=100)
        self.tree.column("excel_file", width=250, minwidth=200)

        # 添加滚动条 - 与实时日志保持一致的样式
        tree_scrollbar = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scrollbar.set)

        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # 绑定选择事件
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)

        # 控制按钮框架 - 垂直布局，现代化间距
        control_frame = ttk.Frame(top_frame, style='Card.TFrame')
        control_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N), padx=(15, 0))

        # 按钮容器 - 添加背景卡片
        button_container = ttk.LabelFrame(control_frame, text="  操作面板  ",
                                         style='Modern.TLabelframe', padding="15")
        button_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N))

        # 控制按钮 - 使用更柔和的颜色
        ttk.Button(button_container, text="➕ 添加直播间",
                  command=self.show_add_dialog,
                  style='Modern.TButton').grid(row=0, column=0, pady=(0, 10), sticky=(tk.W, tk.E))

        ttk.Button(button_container, text="▶️ 开始采集",
                  command=self.start_collection,
                  style='Success.TButton').grid(row=1, column=0, pady=(0, 10), sticky=(tk.W, tk.E))

        ttk.Button(button_container, text="⏹️ 停止采集",
                  command=self.stop_collection,
                  style='Danger.TButton').grid(row=2, column=0, pady=(0, 10), sticky=(tk.W, tk.E))

        ttk.Button(button_container, text="🗑️删除直播间",
                  command=self.remove_live_stream,
                  style='Danger.TButton').grid(row=3, column=0, pady=(0, 10), sticky=(tk.W, tk.E))

        ttk.Button(button_container, text="🔄 刷新状态",
                  command=self.refresh_status,
                  style='Neutral.TButton').grid(row=4, column=0, pady=(0, 0), sticky=(tk.W, tk.E))

        button_container.columnconfigure(0, weight=1)

        # 下半部分：控制台日志框架 - 现代化设计
        console_frame = ttk.LabelFrame(main_frame, text="  实时日志  ",
                                      style='Modern.TLabelframe', padding="15")
        console_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        console_frame.columnconfigure(0, weight=1)
        console_frame.rowconfigure(0, weight=1)

        # 控制台文本框 - 现代化深色主题
        self.console_text = scrolledtext.ScrolledText(
            console_frame,
            height=16,
            wrap=tk.WORD,
            font=('Consolas', 10),
            bg=ModernStyle.CONSOLE_BG,
            fg=ModernStyle.CONSOLE_FG,
            insertbackground=ModernStyle.CONSOLE_ACCENT,
            selectbackground=ModernStyle.BG_ACCENT,
            selectforeground=ModernStyle.TEXT_LIGHT,
            relief='flat',
            borderwidth=0,
            padx=10,
            pady=10
        )
        self.console_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 状态栏和帮助按钮容器
        bottom_frame = ttk.Frame(main_frame, style='Card.TFrame')
        bottom_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        bottom_frame.columnconfigure(0, weight=1)

        # 状态栏 - 现代化设计
        self.status_label = ttk.Label(bottom_frame,
                                     text="🟢 就绪 | 请选择直播间查看实时日志",
                                     font=('Segoe UI', 9),
                                     foreground=ModernStyle.TEXT_SECONDARY,
                                     background=ModernStyle.BG_SECONDARY)
        self.status_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)

        # 帮助按钮 - 圆形小按钮
        help_btn = ttk.Button(bottom_frame, text="?", command=self.show_help_dialog,
                             style='Circle.TButton')
        help_btn.grid(row=0, column=1, sticky=tk.E, padx=5, pady=5)

        # 双击事件绑定
        self.tree.bind('<Double-1>', self.on_double_click)

    def show_help_dialog(self):
        """显示帮助对话框"""
        messagebox.showinfo("帮助",
                           "版本：v1.2\nbug修复、个性化定制请联系作者\n微信：enbool")

    def show_add_dialog(self):
        """显示添加直播间对话框 - 现代化设计"""
        dialog = tk.Toplevel(self.root)
        dialog.title("添加直播间")
        dialog.geometry("480x360")  # 修正窗口高度
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg=ModernStyle.BG_SECONDARY)

        # 居中显示
        x = self.root.winfo_rootx() + (self.root.winfo_width() - 480) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - 280) // 2
        dialog.geometry(f"+{x}+{y}")

        # 主容器
        main_container = ttk.Frame(dialog, style='Card.TFrame', padding="40")
        main_container.pack(fill=tk.BOTH, expand=True)

        # 图标区域
        icon_label = ttk.Label(main_container,
                              text="📺",
                              font=('Segoe UI', 32),
                              background=ModernStyle.BG_SECONDARY)
        icon_label.pack(pady=(0, 30))

        # 输入提示
        hint_label = ttk.Label(main_container,
                              text="请输入直播间网址：",
                              font=('Segoe UI', 12, 'bold'),
                              foreground=ModernStyle.TEXT_PRIMARY,
                              background=ModernStyle.BG_SECONDARY)
        hint_label.pack(pady=(0, 15))

        # 输入框
        live_url_var = tk.StringVar()
        entry = ttk.Entry(main_container, textvariable=live_url_var,
                         font=('Segoe UI', 11),
                         style='Modern.TEntry')
        entry.pack(fill=tk.X, ipady=12, pady=(0, 20))
        entry.focus()

        # 状态标签（用于显示验证信息）
        dialog_status_var = tk.StringVar()  # 使用局部变量而不是实例变量
        status_label = ttk.Label(main_container,
                                textvariable=dialog_status_var,
                                font=('Segoe UI', 9),
                                foreground=ModernStyle.TEXT_SECONDARY,
                                background=ModernStyle.BG_SECONDARY)
        status_label.pack(pady=(0, 20))

        # 按钮容器
        button_container = ttk.Frame(main_container, style='Card.TFrame')
        button_container.pack()

        def extract_live_id(url_or_id):
            """从直播间网址或ID中提取直播间ID"""
            import re

            # 如果输入的是纯数字，直接返回
            if url_or_id.isdigit():
                return url_or_id

            # 从URL中提取ID的正则表达式
            patterns = [
                r'live\.douyin\.com/(\d+)',  # https://live.douyin.com/986387176104
                r'webcast\.amemv\.com/webcast/reflow/(\d+)',  # 其他可能的格式
                r'douyin\.com/.*?(\d{10,})',  # 通用匹配长数字
            ]

            for pattern in patterns:
                match = re.search(pattern, url_or_id)
                if match:
                    return match.group(1)

            return None

        def validate_and_add():
            input_text = live_url_var.get().strip()

            # 基本验证
            if not input_text:
                dialog_status_var.set("❌ 请输入直播间网址或ID")
                return

            # 提取直播间ID
            live_id = extract_live_id(input_text)

            if not live_id:
                dialog_status_var.set("❌ 无法从输入内容中提取直播间ID")
                return

            # 数字验证
            if not live_id.isdigit():
                dialog_status_var.set("❌ 提取的直播间ID格式错误")
                return

            # 长度验证
            if len(live_id) < 6 or len(live_id) > 15:
                dialog_status_var.set("❌ 直播间ID长度应在6-15位之间")
                return

            # 重复检查
            if live_id in self.live_streams:
                dialog_status_var.set("❌ 该直播间已存在")
                return

            dialog_status_var.set(f"✅ 解析成功，直播间ID: {live_id}")
            # 先关闭对话框，然后添加直播间
            dialog.destroy()
            # 立即调用添加方法
            self.add_live_stream(live_id)

        def on_cancel():
            dialog.destroy()

        def on_entry_change(*args):
            """输入框内容变化时清空状态并尝试实时解析"""
            input_text = live_url_var.get().strip()
            if input_text:
                live_id = extract_live_id(input_text)
                if live_id and live_id.isdigit() and 6 <= len(live_id) <= 15:
                    dialog_status_var.set(f"🔍 检测到直播间ID: {live_id}")
                else:
                    dialog_status_var.set("🔍 正在解析...")
            else:
                dialog_status_var.set("")

        # 绑定输入变化事件
        live_url_var.trace('w', on_entry_change)

        # 取消按钮
        cancel_btn = ttk.Button(button_container, text="取消", command=on_cancel,
                               style='Neutral.TButton', width=12)
        cancel_btn.pack(side=tk.LEFT, padx=(0, 15))

        # 添加按钮
        add_btn = ttk.Button(button_container, text="添加直播间", command=validate_and_add,
                            style='Modern.TButton', width=15)
        add_btn.pack(side=tk.LEFT)

        # 绑定快捷键
        entry.bind('<Return>', lambda e: validate_and_add())
        dialog.bind('<Escape>', lambda e: on_cancel())

        # 窗口关闭事件
        dialog.protocol("WM_DELETE_WINDOW", on_cancel)

    def update_status(self, message, status_type="info"):
        """更新状态栏"""
        icons = {
            "info": "🔵",
            "success": "🟢",
            "warning": "🟡",
            "error": "🔴"
        }
        icon = icons.get(status_type, "🔵")
        self.status_label.configure(text=f"{icon} {message}")

    def log_to_console(self, message, live_id=None):
        """输出日志到控制台 - 增强的颜色支持"""
        # 如果指定了live_id，只有当它是当前选中的直播间时才显示
        if live_id and live_id != self.selected_live_id:
            return

        # 配置颜色标签
        self.console_text.tag_configure("chat", foreground="#4FC3F7")
        self.console_text.tag_configure("gift", foreground="#FF9800")
        self.console_text.tag_configure("like", foreground="#E91E63")
        self.console_text.tag_configure("follow", foreground="#4CAF50")
        self.console_text.tag_configure("system", foreground="#9C27B0")
        self.console_text.tag_configure("error", foreground="#F44336")
        self.console_text.tag_configure("time", foreground="#757575")

        # 时间戳
        current_time = datetime.now().strftime('%H:%M:%S')
        time_text = f"[{current_time}] "

        # 根据消息类型选择颜色
        tag = "system"
        if "聊天msg" in message:
            tag = "chat"
        elif "礼物msg" in message:
            tag = "gift"
        elif "点赞msg" in message:
            tag = "like"
        elif "关注msg" in message:
            tag = "follow"
        elif "异常" in message or "错误" in message:
            tag = "error"

        # 插入消息
        self.console_text.insert(tk.END, time_text, "time")
        self.console_text.insert(tk.END, message + "\n", tag)
        self.console_text.see(tk.END)

        # 限制日志行数
        lines = int(self.console_text.index('end-1c').split('.')[0])
        if lines > 1000:
            self.console_text.delete('1.0', '200.0')

    def load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.live_streams = json.load(f)

                # 更新Excel文件路径到data目录
                for live_id, info in self.live_streams.items():
                    info['excel_file'] = os.path.join("data", f"douyin_live_{live_id}.xlsx")

                self.refresh_tree()
                self.log_to_console(f"【加载】加载了 {len(self.live_streams)} 个直播间配置")
        except Exception as e:
            messagebox.showerror("错误", f"加载配置失败: {e}")
            self.log_to_console(f"【错误】加载配置失败: {e}")

    def save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.live_streams, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败: {e}")
            self.log_to_console(f"【错误】保存配置失败: {e}")

    def add_live_stream(self, live_id):
        """添加直播间"""
        live_id = str(live_id)
        if not live_id:
            messagebox.showwarning("警告", "请输入直播间ID")
            return

        if live_id in self.live_streams:
            messagebox.showinfo("提示", "该直播间已存在")
            return

        self.update_status(f"正在获取直播间 {live_id} 信息...", "info")
        self.log_to_console(f"【添加】正在获取直播间 {live_id} 信息...")

        def get_room_info():
            try:
                fetcher = DouyinLiveWebFetcher(live_id, ui_mode=True)
                room_status_info = fetcher.get_room_status()

                username = "未知主播"
                live_status = "未知状态"

                if room_status_info:
                    username = room_status_info.get('nickname', '未知主播')
                    room_status = room_status_info.get('room_status', 2)
                    live_status = "正在直播" if room_status == 0 else "已结束"

                self.live_streams[live_id] = {
                    "live_id": live_id,
                    "username": username,
                    "status": "未开始采集",
                    "live_status": live_status,
                    "excel_file": os.path.join("data", f"douyin_live_{live_id}.xlsx"),
                    "added_time": datetime.now().isoformat()
                }

                self.root.after(0, lambda: self.refresh_tree())
                self.root.after(0, lambda: self.save_config())
                self.root.after(0, lambda: self.update_status(f"成功添加直播间: {username}", "success"))
                self.root.after(0, lambda: self.log_to_console(f"【添加】成功添加直播间 {live_id} - {username}({live_status})"))

            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"添加直播间失败: {e}"))
                self.root.after(0, lambda: self.update_status("添加直播间失败", "error"))
                self.root.after(0, lambda: self.log_to_console(f"【错误】添加直播间失败: {e}"))

        threading.Thread(target=get_room_info, daemon=True).start()

    def remove_live_stream(self):
        """删除直播间"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请选择要删除的直播间")
            return

        item = self.tree.item(selected[0])
        live_id = str(item['values'][0])  # 确保live_id是字符串类型

        if messagebox.askyesno("确认", f"确定要删除直播间 {live_id} 吗？"):
            # 先停止采集
            if live_id in self.live_fetchers:
                self.live_fetchers[live_id].stop()
                del self.live_fetchers[live_id]
                self.log_to_console(f"【停止】停止直播间 {live_id} 的采集")

            # 删除记录
            if live_id in self.live_streams:
                del self.live_streams[live_id]

            self.refresh_tree()
            self.save_config()
            self.log_to_console(f"【删除】删除直播间 {live_id}")

    def start_collection(self):
        """开始采集"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请选择要开始采集的直播间")
            return

        item = self.tree.item(selected[0])
        live_id = str(item['values'][0])  # 确保live_id是字符串类型

        if live_id in self.live_fetchers:
            messagebox.showinfo("提示", "该直播间正在采集中")
            return

        self.log_to_console(f"【开始】检查直播间 {live_id} 的状态...")

        def start_fetcher():
            try:
                # 创建fetcher并检查直播状态
                def log_callback(message):
                    self.root.after(0, lambda: self.log_to_console(message, live_id))

                fetcher = CustomDouyinLiveWebFetcher(live_id, ui_mode=True, log_callback=log_callback)

                # 检查直播间状态
                room_status_info = fetcher.get_room_status()
                if room_status_info:
                    room_status = room_status_info.get('room_status', 2)
                    nickname = room_status_info.get('nickname', '未知主播')

                    if room_status != 0: # 0表示正在直播，其他状态表示已结束
                        self.root.after(0, lambda: self.log_to_console(f"【停止】直播间 {live_id} ({nickname}) 未在直播，无法开始采集"))
                        self.root.after(0, lambda: messagebox.showinfo("提示", f"直播间 {live_id} ({nickname}) 未在直播，无法开始采集"))
                        return
                    else:
                        self.root.after(0, lambda: self.log_to_console(f"【检查】直播间 {live_id} ({nickname}) 正在直播，开始采集..."))
                else:
                    self.root.after(0, lambda: self.log_to_console(f"【停止】无法获取直播间 {live_id} 状态，无法开始采集"))
                    self.root.after(0, lambda: messagebox.showerror("错误", f"无法获取直播间 {live_id} 状态"))
                    return

                # 添加到采集列表
                self.live_fetchers[live_id] = fetcher

                # 设置停止回调，当直播结束时自动清理
                fetcher.set_stop_callback(lambda: self.auto_stop_collection(live_id))

                # 更新状态
                if live_id in self.live_streams:  # 添加安全检查
                    self.live_streams[live_id]["status"] = "采集中"
                self.root.after(0, lambda: self.refresh_tree())

                # 开始采集
                fetcher.start()

            except Exception as e:
                # 采集结束或出错
                if live_id in self.live_fetchers:
                    del self.live_fetchers[live_id]
                if live_id in self.live_streams:  # 添加安全检查
                    self.live_streams[live_id]["status"] = "已停止"
                self.root.after(0, lambda: self.refresh_tree())
                self.root.after(0, lambda: self.log_to_console(f"【停止】直播间 {live_id} 采集已停止: {e}"))

        threading.Thread(target=start_fetcher, daemon=True).start()

    def auto_stop_collection(self, live_id):
        """自动停止采集（当直播结束时调用）"""
        def stop_task():
            if live_id in self.live_fetchers:
                try:
                    del self.live_fetchers[live_id]
                    if live_id in self.live_streams:
                        self.live_streams[live_id]["status"] = "已停止"
                    self.refresh_tree()
                    self.log_to_console(f"【自动停止】直播间 {live_id} 已结束，自动停止采集")
                except Exception as e:
                    self.log_to_console(f"【错误】自动停止采集失败: {e}")

        # 在主线程中执行停止操作
        self.root.after(0, stop_task)

    def stop_collection(self):
        """停止采集"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请选择要停止采集的直播间")
            return

        item = self.tree.item(selected[0])
        live_id = str(item['values'][0])  # 确保live_id是字符串类型

        if live_id not in self.live_fetchers:
            messagebox.showinfo("提示", "该直播间未在采集中")
            return

        try:
            self.live_fetchers[live_id].stop()
            del self.live_fetchers[live_id]

            if live_id in self.live_streams:  # 添加安全检查
                self.live_streams[live_id]["status"] = "已停止"
            self.refresh_tree()
            self.log_to_console(f"【停止】手动停止直播间 {live_id} 的采集")

        except Exception as e:
            messagebox.showerror("错误", f"停止采集失败: {e}")
            self.log_to_console(f"【错误】停止采集失败: {e}")

    def open_excel_folder(self):
        """打开Excel文件所在文件夹"""
        try:
            current_dir = os.getcwd()
            if sys.platform == "win32":
                os.startfile(current_dir)
            elif sys.platform == "darwin":
                subprocess.run(["open", current_dir])
            else:
                subprocess.run(["xdg-open", current_dir])
            self.log_to_console("已打开Excel文件夹")
        except Exception as e:
            messagebox.showerror("错误", f"打开文件夹失败: {e}")

    def refresh_status(self):
        """刷新状态"""
        self.refresh_tree()
        active_count = len(self.live_fetchers)
        total_count = len(self.live_streams)
        self.log_to_console(f"【刷新】总计 {total_count} 个直播间，{active_count} 个正在采集")

    def refresh_tree(self):
        """刷新树形列表"""
        # 清空现有项目
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 添加直播间
        for live_id, info in self.live_streams.items():
            collection_status = "🟢 采集中" if live_id in self.live_fetchers else "⚪ " + info.get("status", "未开始采集")
            live_status = info.get("live_status", "未知状态")

            # 状态图标
            status_icon = "🔴" if live_status == "已结束" else "🟢"
            username_display = f"{status_icon} {info.get('username', '未知')} ({live_status})"

            self.tree.insert("", "end", values=(
                live_id,
                username_display,
                collection_status,
                info.get("excel_file", os.path.join("data", f"douyin_live_{live_id}.xlsx"))
            ))

    def on_double_click(self, event):
        """双击事件"""
        selected = self.tree.selection()
        if not selected:
            return

        item = self.tree.item(selected[0])
        live_id = str(item['values'][0])  # 确保live_id是字符串类型
        excel_file = item['values'][3]

        # 确保Excel文件路径正确
        if not excel_file.startswith("data"):
            excel_file = os.path.join("data", f"douyin_live_{live_id}.xlsx")

        # 尝试打开Excel文件
        try:
            if os.path.exists(excel_file):
                if sys.platform == "win32":
                    os.startfile(excel_file)
                elif sys.platform == "darwin":
                    subprocess.run(["open", excel_file])
                else:
                    subprocess.run(["xdg-open", excel_file])
                self.log_to_console(f"【打开】打开Excel文件: {excel_file}")
            else:
                messagebox.showinfo("提示", f"Excel文件不存在: {excel_file}\n请先开始采集以生成Excel文件")
                self.log_to_console(f"【提示】Excel文件不存在: {excel_file}")
        except Exception as e:
            messagebox.showerror("错误", f"打开Excel文件失败: {e}")
            self.log_to_console(f"【错误】打开Excel文件失败: {e}")

    def on_closing(self):
        """关闭程序时的处理"""
        if self.live_fetchers:
            if messagebox.askyesno("确认", "还有正在采集的直播间，确定要退出吗？"):
                # 停止所有采集
                self.log_to_console("【退出】正在停止所有采集...")
                for live_id, fetcher in self.live_fetchers.items():
                    try:
                        fetcher.stop()
                        self.log_to_console(f"【停止】停止直播间 {live_id} 的采集")
                    except:
                        pass
                self.save_config()
                self.root.destroy()
        else:
            self.save_config()
            self.root.destroy()

    def run(self):
        """运行界面"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.log_to_console("【启动】抖音直播间弹幕采集工具已启动")
        self.log_to_console("【提示】请先选择一个直播间，控制台将只显示选中直播间的日志")
        self.update_status("应用程序已启动，请添加直播间开始使用", "success")
        self.root.mainloop()

    def on_tree_select(self, event):
        """树形列表选择事件"""
        selected = self.tree.selection()
        if selected:
            item = self.tree.item(selected[0])
            new_selected_id = str(item['values'][0])

            # 如果选中的直播间发生变化，清空控制台并显示提示
            if self.selected_live_id != new_selected_id:
                self.selected_live_id = new_selected_id
                self.console_text.delete('1.0', tk.END)
                self.log_to_console(f"【选择】已切换到直播间: {self.selected_live_id}")
                self.update_status(f"已选择直播间: {self.selected_live_id}", "info")

                # 如果选中的直播间正在采集，显示当前状态
                if self.selected_live_id in self.live_fetchers:
                    self.log_to_console(f"【状态】直播间 {self.selected_live_id} 正在采集中")
                    self.update_status(f"直播间 {self.selected_live_id} 正在采集中", "success")
                else:
                    self.log_to_console(f"【状态】直播间 {self.selected_live_id} 未开始采集")

class CustomDouyinLiveWebFetcher(DouyinLiveWebFetcher):
    """自定义的DouyinLiveWebFetcher，支持日志回调"""

    def __init__(self, live_id, ui_mode=False, log_callback=None):
        self.log_callback = log_callback
        self.stop_callback = None
        self._running = False
        super().__init__(live_id, ui_mode)

    def set_stop_callback(self, callback):
        """设置停止回调函数"""
        self.stop_callback = callback

    def log(self, message):
        """输出日志"""
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)

    def start(self):
        """启动采集"""
        self._running = True
        try:
            self.log(f"【系统】开始连接直播间 {self.live_id}")
            super().start()
        except Exception as e:
            self.log(f"【异常】启动失败: {e}")
            self._running = False
            if self.stop_callback:
                self.stop_callback()
            raise

    def stop(self):
        """停止采集"""
        self._running = False
        self.log(f"【系统】正在停止直播间 {self.live_id} 的采集")
        super().stop()

    def _connectWebSocket(self):
        """重写WebSocket连接方法，增加错误处理"""
        try:
            self.log(f"【系统】正在获取直播间 {self.live_id} 的连接信息...")

            # 检查ttwid
            if not self.ttwid or self.ttwid == "default_ttwid":
                self.log(f"【警告】ttwid获取失败，使用默认值")

            # 检查room_id
            if not self.room_id:
                self.log(f"【异常】无法获取room_id")
                raise Exception("无法获取room_id")

            self.log(f"【系统】room_id: {self.room_id}")

            # 调用父类方法
            super()._connectWebSocket()

        except Exception as e:
            self.log(f"【异常】WebSocket连接失败: {e}")
            self._running = False
            if self.stop_callback:
                self.stop_callback()
            raise

    def _wsOnOpen(self, ws):
        """连接建立成功"""
        self.log("【√】WebSocket连接成功，开始接收数据")
        threading.Thread(target=self._sendHeartbeat, daemon=True).start()

    def _wsOnError(self, ws, error):
        self.log(f"【异常】WebSocket错误: {error}")
        self._running = False
        if self.stop_callback:
            self.stop_callback()

    def _wsOnClose(self, ws, *args):
        self.log("【!】WebSocket连接已关闭")
        self._running = False
        # 连接关闭时自动保存
        self.save_excel()
        if self.stop_callback:
            self.stop_callback()

    def _sendHeartbeat(self):
        """发送心跳包"""
        while self._running:
            try:
                if hasattr(self, 'ws') and self.ws:
                    heartbeat = PushFrame(payload_type='hb').SerializeToString()
                    self.ws.send(heartbeat, websocket.ABNF.OPCODE_PING)
                    self.log("【√】发送心跳包")
                else:
                    break
            except Exception as e:
                self.log(f"【异常】心跳包发送失败: {e}")
                break
            else:
                time.sleep(5)

    def get_room_status(self):
        """
        获取直播间开播状态:
        room_status: 2 直播已结束
        room_status: 0 直播进行中
        """
        try:
            self.log(f"【系统】正在检查直播间 {self.live_id} 状态...")

            url = ('https://live.douyin.com/webcast/room/web/enter/?aid=6383'
                   '&app_name=douyin_web&live_id=1&device_platform=web&language=zh-CN&enter_from=web_live'
                   '&cookie_enabled=true&screen_width=1536&screen_height=864&browser_language=zh-CN&browser_platform=Win32'
                   '&browser_name=Edge&browser_version=133.0.0.0'
                   f'&web_rid={self.live_id}'
                   f'&room_id_str={self.room_id}'
                   '&enter_source=&is_need_double_stream=false&insert_task_id=&live_reason='
                   '&msToken=&a_bogus=')
            resp = requests.get(url, headers={
                'User-Agent': self.user_agent,
                'Cookie': f'ttwid={self.ttwid};'
            }, timeout=10)

            data = resp.json().get('data')
            if data:
                room_status = data.get('room_status')
                user = data.get('user')
                if user:
                    user_id = user.get('id_str')
                    nickname = user.get('nickname')
                    status_text = ['正在直播', '已结束'][bool(room_status)]
                    self.log(f"【房间状态】{nickname}[{user_id}]直播间：{status_text}")

                    # 返回详细信息供UI使用
                    return {
                        'room_status': room_status,
                        'user_id': user_id,
                        'nickname': nickname,
                        'status_text': status_text
                    }
                else:
                    self.log("【异常】响应中缺少用户信息")
            else:
                self.log("【异常】API响应中缺少数据")
        except Exception as e:
            self.log(f"【异常】获取房间状态失败: {e}")
        return None

if __name__ == "__main__":
    app = LiveStreamUI()
    app.run()
