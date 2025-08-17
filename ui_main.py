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

class LiveStreamUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("抖音直播间弹幕采集工具")
        self.root.geometry("1200x800")
        self.root.resizable(True, True)

        # 直播间数据存储
        self.live_streams = {}
        self.live_fetchers = {}
        self.config_file = "live_config.json"

        # 当前选中的直播间ID
        self.selected_live_id = None

        self.setup_ui()
        self.load_config()

    def setup_ui(self):
        """设置UI界面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)

        # 标题
        title_label = ttk.Label(main_frame, text="抖音直播间弹幕采集工具", font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))

        # 上半部分框架：直播间列表和控制按钮
        top_frame = ttk.Frame(main_frame)
        top_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        top_frame.columnconfigure(0, weight=1)
        top_frame.rowconfigure(0, weight=1)

        # 直播间列表框架
        list_frame = ttk.LabelFrame(top_frame, text="直播间列表", padding="10")
        list_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        # 创建Treeview
        columns = ("live_id", "username", "status", "excel_file")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=12)

        # 设置列标题
        self.tree.heading("live_id", text="直播间ID")
        self.tree.heading("username", text="主播用户名")
        self.tree.heading("status", text="采集状态")
        self.tree.heading("excel_file", text="Excel文件")

        # 设置列宽
        self.tree.column("live_id", width=120)
        self.tree.column("username", width=150)
        self.tree.column("status", width=100)
        self.tree.column("excel_file", width=200)

        # 添加滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # 绑定选择事件
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)

        # 控制按钮框架
        control_frame = ttk.Frame(top_frame)
        control_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N), padx=(10, 0))

        # 控制按钮
        ttk.Button(control_frame, text="添加直播间", command=self.show_add_dialog).grid(row=0, column=0, pady=5, sticky=(tk.W, tk.E))
        ttk.Button(control_frame, text="开始采集", command=self.start_collection).grid(row=1, column=0, pady=5, sticky=(tk.W, tk.E))
        ttk.Button(control_frame, text="停止采集", command=self.stop_collection).grid(row=2, column=0, pady=5, sticky=(tk.W, tk.E))
        ttk.Button(control_frame, text="删除直播间", command=self.remove_live_stream).grid(row=3, column=0, pady=5, sticky=(tk.W, tk.E))
        ttk.Button(control_frame, text="刷新状态", command=self.refresh_status).grid(row=4, column=0, pady=5, sticky=(tk.W, tk.E))

        control_frame.columnconfigure(0, weight=1)

        # 下半部分：控制台日志框架
        console_frame = ttk.LabelFrame(main_frame, text="控制台日志", padding="10")
        console_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        console_frame.columnconfigure(0, weight=1)
        console_frame.rowconfigure(0, weight=1)

        # 控制台文本框
        self.console_text = scrolledtext.ScrolledText(
            console_frame,
            height=15,
            wrap=tk.WORD,
            font=('Consolas', 9),
            bg='black',
            fg='lightgreen'
        )
        self.console_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 状态栏
        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))

        # 双击事件绑定
        self.tree.bind('<Double-1>', self.on_double_click)

    def show_add_dialog(self):
        """显示添加直播间对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("添加直播间")
        dialog.geometry("300x150")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        # 居中显示
        dialog.geometry("+%d+%d" % (
            self.root.winfo_rootx() + 50,
            self.root.winfo_rooty() + 50
        ))

        # 对话框内容
        ttk.Label(dialog, text="请输入直播间ID:", font=('Arial', 12)).pack(pady=20)

        live_id_var = tk.StringVar()
        entry = ttk.Entry(dialog, textvariable=live_id_var, width=25, font=('Arial', 11))
        entry.pack(pady=10)
        entry.focus()

        # 按钮框架
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=20)

        def on_add():
            live_id = live_id_var.get().strip()
            if live_id:
                dialog.destroy()
                self.add_live_stream(live_id)
            else:
                messagebox.showwarning("警告", "请输入直播间ID")

        def on_cancel():
            dialog.destroy()

        ttk.Button(btn_frame, text="添加", command=on_add).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=on_cancel).pack(side=tk.LEFT, padx=5)

        # 绑定回车键
        entry.bind('<Return>', lambda e: on_add())
        dialog.bind('<Escape>', lambda e: on_cancel())

    def on_tree_select(self, event):
        """树形列表选择事件"""
        selected = self.tree.selection()
        if selected:
            item = self.tree.item(selected[0])
            self.selected_live_id = str(item['values'][0])
            self.log_to_console(f"【选择】选中直播间: {self.selected_live_id}")

    def log_to_console(self, message):
        """输出日志到控制台"""
        current_time = datetime.now().strftime('%H:%M:%S')
        log_message = f"[{current_time}] {message}\n"

        self.console_text.insert(tk.END, log_message)
        self.console_text.see(tk.END)

        # 限制日志行数，避免内存占用过多
        lines = int(self.console_text.index('end-1c').split('.')[0])
        if lines > 1000:
            self.console_text.delete('1.0', '200.0')

    def load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.live_streams = json.load(f)
                self.refresh_tree()
                self.status_var.set(f"已加载 {len(self.live_streams)} 个直播间")
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
        live_id = str(live_id)  # 确保live_id是字符串类型
        if not live_id:
            messagebox.showwarning("警告", "请输入直播间ID")
            return

        if live_id in self.live_streams:
            messagebox.showinfo("提示", "该直播间已存在")
            return

        # 获取直播间信息
        self.status_var.set(f"正在获取直播间 {live_id} 信息...")
        self.log_to_console(f"【添加】正在获取直播间 {live_id} 信息...")

        def get_room_info():
            try:
                fetcher = DouyinLiveWebFetcher(live_id, ui_mode=True)
                fetcher.get_room_status()

                # 添加到列表
                self.live_streams[live_id] = {
                    "live_id": live_id,
                    "username": "获取中...",
                    "status": "未开始",
                    "excel_file": f"douyin_live_{live_id}.xlsx",
                    "added_time": datetime.now().isoformat()
                }

                self.root.after(0, lambda: self.refresh_tree())
                self.root.after(0, lambda: self.save_config())
                self.root.after(0, lambda: self.status_var.set(f"已添加直播间 {live_id}"))
                self.root.after(0, lambda: self.log_to_console(f"【添加】成功添加直播间 {live_id}"))

            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"添加直播间失败: {e}"))
                self.root.after(0, lambda: self.status_var.set("就绪"))
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
            self.status_var.set(f"已删除直播间 {live_id}")
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

        self.log_to_console(f"【开始】启动直播间 {live_id} 的采集")

        def start_fetcher():
            try:
                # 创建自定义的DouyinLiveWebFetcher，重定向输出到控制台
                fetcher = CustomDouyinLiveWebFetcher(live_id, ui_mode=True, log_callback=self.log_to_console)
                self.live_fetchers[live_id] = fetcher

                # 更新状态
                if live_id in self.live_streams:  # 添加安全检查
                    self.live_streams[live_id]["status"] = "采集中"
                self.root.after(0, lambda: self.refresh_tree())
                self.root.after(0, lambda: self.status_var.set(f"开始采集直播间 {live_id}"))

                # 开始采集
                fetcher.start()

            except Exception as e:
                # 采集结束或出错
                if live_id in self.live_fetchers:
                    del self.live_fetchers[live_id]
                if live_id in self.live_streams:  # 添加安全检查
                    self.live_streams[live_id]["status"] = "已停止"
                self.root.after(0, lambda: self.refresh_tree())
                self.root.after(0, lambda: self.status_var.set(f"直播间 {live_id} 采集已停止"))
                self.root.after(0, lambda: self.log_to_console(f"【停止】直播间 {live_id} 采集已停止: {e}"))

        threading.Thread(target=start_fetcher, daemon=True).start()

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
            self.status_var.set(f"已停止采集直播间 {live_id}")
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
            self.status_var.set("已打开Excel文件夹")
        except Exception as e:
            messagebox.showerror("错误", f"打开文件夹失败: {e}")

    def refresh_status(self):
        """刷新状态"""
        self.refresh_tree()
        active_count = len(self.live_fetchers)
        total_count = len(self.live_streams)
        self.status_var.set(f"总计 {total_count} 个直播间，{active_count} 个正在采集")
        self.log_to_console(f"【刷新】总计 {total_count} 个直播间，{active_count} 个正在采集")

    def refresh_tree(self):
        """刷新树形列表"""
        # 清空现有项目
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 添加直播间
        for live_id, info in self.live_streams.items():
            status = "采集中" if live_id in self.live_fetchers else info.get("status", "未开始")
            self.tree.insert("", "end", values=(
                live_id,
                info.get("username", "未知"),
                status,
                info.get("excel_file", f"douyin_live_{live_id}.xlsx")
            ))

    def on_double_click(self, event):
        """双击事件"""
        selected = self.tree.selection()
        if not selected:
            return

        item = self.tree.item(selected[0])
        live_id = str(item['values'][0])  # 确保live_id是字符串类型
        excel_file = item['values'][3]

        # 尝试打开Excel文件
        try:
            if os.path.exists(excel_file):
                if sys.platform == "win32":
                    os.startfile(excel_file)
                elif sys.platform == "darwin":
                    subprocess.run(["open", excel_file])
                else:
                    subprocess.run(["xdg-open", excel_file])
                self.status_var.set(f"已打开 {excel_file}")
                self.log_to_console(f"【打开】打开Excel文件: {excel_file}")
            else:
                messagebox.showinfo("提示", f"Excel文件不存在: {excel_file}")
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
        self.root.mainloop()


class CustomDouyinLiveWebFetcher(DouyinLiveWebFetcher):
    """自定义的DouyinLiveWebFetcher，支持日志回调"""

    def __init__(self, live_id, ui_mode=False, log_callback=None):
        self.log_callback = log_callback
        super().__init__(live_id, ui_mode)

    def log(self, message):
        """输出日志"""
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)

    # 重写所有需要输出日志的方法
    def _parseChatMsg(self, payload):
        """聊天消息"""
        message = ChatMessage().parse(payload)
        user_name = message.user.nick_name
        user_id = message.user.id
        sec_uid = getattr(message.user, 'sec_uid', '')
        user_homepage = f"https://www.douyin.com/user/{sec_uid}" if sec_uid else ""
        content = message.content
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        self.log(f"【聊天msg】[{user_id}]{user_name}: {content}")

        # 保存到Excel
        try:
            self.chat_sheet.append([current_time, user_id, user_name, sec_uid, user_homepage, content])
        except Exception as e:
            self.log(f"【X】保存聊天消息到Excel失败: {e}")

    def _parseGiftMsg(self, payload):
        """礼物消息"""
        message = GiftMessage().parse(payload)
        user_name = message.user.nick_name
        sec_uid = getattr(message.user, 'sec_uid', '')
        user_homepage = f"https://www.douyin.com/user/{sec_uid}" if sec_uid else ""
        gift_name = message.gift.name
        gift_cnt = message.combo_count
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        self.log(f"【礼物msg】{user_name} 送出了 {gift_name}x{gift_cnt}")

        # 保存到Excel
        try:
            self.gift_sheet.append([current_time, user_name, sec_uid, user_homepage, gift_name, gift_cnt])
        except Exception as e:
            self.log(f"【X】保存礼物消息到Excel失败: {e}")

    def _parseLikeMsg(self, payload):
        '''点赞消息'''
        message = LikeMessage().parse(payload)
        user_name = message.user.nick_name
        sec_uid = getattr(message.user, 'sec_uid', '')
        user_homepage = f"https://www.douyin.com/user/{sec_uid}" if sec_uid else ""
        count = message.count
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        self.log(f"【点赞msg】{user_name} 点了{count}个赞")

        # 保存到Excel
        try:
            self.like_sheet.append([current_time, user_name, sec_uid, user_homepage, count])
        except Exception as e:
            self.log(f"【X】保存点赞消息到Excel失败: {e}")

    def _parseMemberMsg(self, payload):
        '''进入直播间消息'''
        message = MemberMessage().parse(payload)
        user_name = message.user.nick_name
        user_id = message.user.id
        gender = ["女", "男"][message.user.gender]
        self.log(f"【进场msg】[{user_id}][{gender}]{user_name} 进入了直播间")

    def _parseSocialMsg(self, payload):
        '''关注消息'''
        message = SocialMessage().parse(payload)
        user_name = message.user.nick_name
        user_id = message.user.id
        sec_uid = getattr(message.user, 'sec_uid', '')
        user_homepage = f"https://www.douyin.com/user/{sec_uid}" if sec_uid else ""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        self.log(f"【关注msg】[{user_id}]{user_name} 关注了主播")

        # 保存到Excel
        try:
            self.follow_sheet.append([current_time, user_id, user_name, sec_uid, user_homepage])
        except Exception as e:
            self.log(f"【X】保存关注消息到Excel失败: {e}")

    def _parseRoomUserSeqMsg(self, payload):
        '''直播间统计'''
        message = RoomUserSeqMessage().parse(payload)
        current = message.total
        total = message.total_pv_for_anchor
        self.log(f"【统计msg】当前观看人数: {current}, 累计观看人数: {total}")

    def _parseFansclubMsg(self, payload):
        '''粉丝团消息'''
        message = FansclubMessage().parse(payload)
        content = message.content
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        self.log(f"【粉丝团msg】 {content}")

        # 保存到Excel
        try:
            self.fanclub_sheet.append([current_time, content])
        except Exception as e:
            self.log(f"【X】保存粉丝团消息到Excel失败: {e}")

    def _parseEmojiChatMsg(self, payload):
        '''聊天表情包消息'''
        message = EmojiChatMessage().parse(payload)
        emoji_id = message.emoji_id
        user = message.user.nick_name if message.user else "未知用户"
        default_content = message.default_content
        self.log(f"【表情包msg】{user} 发送了表情包: {default_content} (ID:{emoji_id})")

    def _parseRoomMsg(self, payload):
        message = RoomMessage().parse(payload)
        common = message.common
        room_id = common.room_id
        self.log(f"【直播间msg】直播间id:{room_id}")

    def _parseRoomStatsMsg(self, payload):
        message = RoomStatsMessage().parse(payload)
        display_long = message.display_long
        self.log(f"【直播间统计msg】{display_long}")

    def _parseRankMsg(self, payload):
        message = RoomRankMessage().parse(payload)
        ranks_list = message.ranks_list
        self.log(f"【直播间排行榜msg】{ranks_list}")

    def _parseControlMsg(self, payload):
        '''直播间状态消息'''
        message = ControlMessage().parse(payload)

        if message.status == 3:
            self.log("【控制msg】直播间已结束")
            self.save_excel()
            self.stop()
        else:
            self.log(f"【控制msg】直播间状态变更: {message.status}")

    def _parseRoomStreamAdaptationMsg(self, payload):
        message = RoomStreamAdaptationMessage().parse(payload)
        adaptationType = message.adaptation_type
        self.log(f"【流配置msg】直播间adaptation: {adaptationType}")

    def _wsOnOpen(self, ws):
        """连接建立成功"""
        self.log("【√】WebSocket连接成功")
        threading.Thread(target=self._sendHeartbeat).start()

    def _wsOnMessage(self, ws, message):
        """
        接收到数据
        :param ws: websocket实例
        :param message: 数据
        """

        # 根据proto结构体解析对象
        package = PushFrame().parse(message)
        response = Response().parse(gzip.decompress(package.payload))

        # 返回直播间服务器链接存活确认消息，便于持续获取数据
        if response.need_ack:
            ack = PushFrame(log_id=package.log_id,
                            payload_type='ack',
                            payload=response.internal_ext.encode('utf-8')
                            ).SerializeToString()
            ws.send(ack, websocket.ABNF.OPCODE_BINARY)
            self.log("【√】发送ACK确认消息")

        # 记录收到的消息数量
        msg_count = len(response.messages_list)
        if msg_count > 0:
            self.log(f"【收到】接收到 {msg_count} 条消息")

        # 根据消息类别解析消息体
        for msg in response.messages_list:
            method = msg.method
            # 记录收到的消息类型
            self.log(f"【消息类型】{method}")

            try:
                {
                    'WebcastChatMessage': self._parseChatMsg,  # 聊天消息
                    'WebcastGiftMessage': self._parseGiftMsg,  # 礼物消息
                    'WebcastLikeMessage': self._parseLikeMsg,  # 点赞消息
                    'WebcastMemberMessage': self._parseMemberMsg,  # 进入直播间消息
                    'WebcastSocialMessage': self._parseSocialMsg,  # 关注消息
                    'WebcastRoomUserSeqMessage': self._parseRoomUserSeqMsg,  # 直播间统计
                    'WebcastFansclubMessage': self._parseFansclubMsg,  # 粉丝团消息
                    'WebcastControlMessage': self._parseControlMsg,  # 直播间状态消息
                    'WebcastEmojiChatMessage': self._parseEmojiChatMsg,  # 聊天表情包消息
                    'WebcastRoomStatsMessage': self._parseRoomStatsMsg,  # 直播间统计信息
                    'WebcastRoomMessage': self._parseRoomMsg,  # 直播间信息
                    'WebcastRoomRankMessage': self._parseRankMsg,  # 直播间排行榜信息
                    'WebcastRoomStreamAdaptationMessage': self._parseRoomStreamAdaptationMsg,  # 直播间流配置
                }.get(method, lambda x: self.log(f"【未处理消息】{method}"))(msg.payload)
            except Exception as e:
                self.log(f"【X】处理消息 {method} 时出错: {e}")

    def _wsOnError(self, ws, error):
        self.log(f"【X】WebSocket错误: {error}")

    def _wsOnClose(self, ws, *args):
        self.log("【!】WebSocket连接已关闭")
        self.get_room_status()
        # 连接关闭时自动保存
        self.save_excel()

    def _sendHeartbeat(self):
        """发送心跳包"""
        while True:
            try:
                heartbeat = PushFrame(payload_type='hb').SerializeToString()
                self.ws.send(heartbeat, websocket.ABNF.OPCODE_PING)
                self.log("【√】发送心跳包")
            except Exception as e:
                self.log(f"【X】心跳包检测错误: {e}")
                break
            else:
                time.sleep(5)

    def get_room_status(self):
        """
        获取直播间开播状态:
        room_status: 2 直播已结束
        room_status: 0 直播进行中
        """
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
        })
        data = resp.json().get('data')
        if data:
            room_status = data.get('room_status')
            user = data.get('user')
            user_id = user.get('id_str')
            nickname = user.get('nickname')
            status_text = ['正在直播', '已结束'][bool(room_status)]
            self.log(f"【房间状态】{nickname}[{user_id}]直播间：{status_text}")

if __name__ == "__main__":
    app = LiveStreamUI()
    app.run()
