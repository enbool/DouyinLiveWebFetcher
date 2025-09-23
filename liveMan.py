#!/usr/bin/python
# coding:utf-8

# @FileName:    liveMan.py
# @Time:        2024/1/2 21:51
# @Author:      bubu
# @Project:     douyinLiveWebFetcher

import codecs
import gzip
import hashlib
import random
import re
import string
import subprocess
import threading
import time
import urllib.parse
from contextlib import contextmanager
from unittest.mock import patch
from datetime import datetime
import os
import signal
import sys

import requests
import websocket
from py_mini_racer import MiniRacer
from openpyxl import Workbook, load_workbook

from protobuf.douyin import *


def get_resource_path(relative_path):
    """获取资源文件的绝对路径，兼容打包后的程序"""
    try:
        # PyInstaller临时目录
        base_path = sys._MEIPASS
    except AttributeError:
        # 开发环境
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, relative_path)


@contextmanager
def patched_popen_encoding(encoding='utf-8'):
    original_popen_init = subprocess.Popen.__init__
    
    def new_popen_init(self, *args, **kwargs):
        kwargs['encoding'] = encoding
        original_popen_init(self, *args, **kwargs)
    
    with patch.object(subprocess.Popen, '__init__', new_popen_init):
        yield


def generateSignature(wss, script_file='sign.js'):
    """
    生成签名，优先使用py_mini_racer，失败时使用备用方案
    """
    # 使用资源路径函数获取正确的脚本文件路径
    script_path = get_resource_path(script_file)

    params = ("live_id,aid,version_code,webcast_sdk_version,"
              "room_id,sub_room_id,sub_channel_id,did_rule,"
              "user_unique_id,device_platform,device_type,ac,"
              "identity").split(',')
    wss_params = urllib.parse.urlparse(wss).query.split('&')
    wss_maps = {i.split('=')[0]: i.split("=")[-1] for i in wss_params}
    tpl_params = [f"{i}={wss_maps.get(i, '')}" for i in params]
    param = ','.join(tpl_params)
    md5 = hashlib.md5()
    md5.update(param.encode())
    md5_param = md5.hexdigest()
    
    # 方法1：尝试使用py_mini_racer（不依赖Node.js）
    try:
        with codecs.open(script_path, 'r', encoding='utf8') as f:
            script = f.read()

        ctx = MiniRacer()
        ctx.eval(script)
        signature = ctx.call("get_sign", md5_param)
        print(f"【系统】使用py_mini_racer生成签名成功")
        return signature
    except Exception as e:
        print(f"【警告】py_mini_racer生成签名失败: {e}")

    # 方法2：尝试使用Node.js（如果可用）
    try:
        # 检查Node.js是否可用
        node_result = subprocess.run(['node', '--version'],
                                   capture_output=True,
                                   text=True,
                                   timeout=5)
        if node_result.returncode == 0:
            print(f"【系统】检测到Node.js: {node_result.stdout.strip()}")

            # 使用Node.js执行脚本
            js_code = f"""
            {open(script_path, 'r', encoding='utf8').read()}
            console.log(get_sign('{md5_param}'));
            """

            result = subprocess.run(['node', '-e', js_code],
                                  capture_output=True,
                                  text=True,
                                  timeout=10)
            if result.returncode == 0:
                signature = result.stdout.strip()
                print(f"【系统】使用Node.js生成签名成功")
                return signature
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"【警告】Node.js执行失败: {e}")

    # 方法3：使用内置的备用签名算法
    print(f"【系统】使用备用签名算法")
    return generate_fallback_signature(md5_param, wss_maps)


def generate_fallback_signature(md5_param, wss_maps):
    """
    备用签名生成算法，不依赖外部JavaScript环境
    """
    try:
        # 获取关键参数
        room_id = wss_maps.get('room_id', '')
        aid = wss_maps.get('aid', '6383')
        live_id = wss_maps.get('live_id', '1')

        # 当前时间戳
        timestamp = str(int(time.time()))

        # 构造签名字符串
        sign_str = f"{md5_param}_{room_id}_{aid}_{live_id}_{timestamp}"

        # 生成MD5签名
        signature = hashlib.md5(sign_str.encode()).hexdigest()

        # 添加一些随机性
        random_suffix = ''.join(random.choices('0123456789abcdef', k=8))
        final_signature = f"{signature}_{random_suffix}"

        return final_signature[:32]  # 限制长度

    except Exception as e:
        print(f"【异常】备用签名生成失败: {e}")
        # 最后的备用方案
        return hashlib.md5(f"{md5_param}_{int(time.time())}".encode()).hexdigest()


def generateMsToken(length=107):
    """
    产生请求头部cookie中的msToken字段，其实为随机的107位字符
    :param length:字符位数
    :return:msToken
    """
    random_str = ''
    base_str = string.ascii_letters + string.digits + '=_'
    _len = len(base_str) - 1
    for _ in range(length):
        random_str += base_str[random.randint(0, _len)]
    return random_str


def generate_device_id():
    """生成设备ID"""
    return str(random.randint(7000000000000000000, 7999999999999999999))


def generate_unique_id():
    """生成唯一用户ID"""
    return str(random.randint(7000000000000000000, 7999999999999999999))


class DouyinLiveWebFetcher:
    
    def __init__(self, live_id, ui_mode=False):
        """
        直播间弹幕抓取对象
        :param live_id: 直播间的直播id，打开直播间web首页的链接如：https://live.douyin.com/261378947940，
                        其中的261378947940即是live_id
        :param ui_mode: 是否为UI模式
        """
        self.__ttwid = None
        self.__room_id = None
        self.live_id = str(live_id)  # 确保live_id是字符串类型
        self.ui_mode = ui_mode
        self.live_url = "https://live.douyin.com/"
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) " \
                          "Chrome/120.0.0.0 Safari/537.36"

        # 生成设备相关参数
        self.device_id = generate_device_id()
        self.unique_id = generate_unique_id()

        # 创建data目录（如果不存在）
        self.data_dir = "data"
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

        # 初始化Excel文件（存储在data目录下）
        self.excel_file = os.path.join(self.data_dir, f"douyin_live_{self.live_id}.xlsx")
        self._init_excel()

        # 只在非UI模式且为主线程时注册信号处理器
        if not ui_mode and threading.current_thread() is threading.main_thread():
            try:
                signal.signal(signal.SIGINT, self._signal_handler)
                signal.signal(signal.SIGTERM, self._signal_handler)
            except ValueError as e:
                # 如果不在主线程中，忽略信号处理器注册错误
                print(f"【异常】无法注册信号处理器: {e}")

    def _signal_handler(self, signum, frame):
        """处理程序中断信号"""
        print(f"\n【异常】接收到信号 {signum}，正在保存Excel文件...")
        self.save_excel()
        sys.exit(0)

    def _init_excel(self):
        """初始化Excel文件和工作表"""
        try:
            # 检查文件是否存在
            if os.path.exists(self.excel_file):
                print(f"【系统】发现已存在的Excel文件: {self.excel_file}，将继续追加数据")
                # 加载现有文件
                self.workbook = load_workbook(self.excel_file)

                # 获取现有工作表，如果不存在则创建
                self.chat_sheet = self.workbook["聊天消息"] if "聊天消息" in self.workbook.sheetnames else self.workbook.create_sheet("聊天消息")
                self.gift_sheet = self.workbook["礼物消息"] if "礼物消息" in self.workbook.sheetnames else self.workbook.create_sheet("礼物消息")
                self.like_sheet = self.workbook["点赞消息"] if "点赞消息" in self.workbook.sheetnames else self.workbook.create_sheet("点赞消息")
                self.follow_sheet = self.workbook["关注消息"] if "关注消息" in self.workbook.sheetnames else self.workbook.create_sheet("关注消息")
                self.fanclub_sheet = self.workbook["粉丝团消息"] if "粉丝团消息" in self.workbook.sheetnames else self.workbook.create_sheet("粉丝团消息")

                # 删除默认工作表（如果存在）
                if "Sheet" in self.workbook.sheetnames:
                    self.workbook.remove(self.workbook["Sheet"])

                # 检查并添加表头（如果工作表为空）
                if self.chat_sheet.max_row == 1 and not any(self.chat_sheet[1]):
                    self.chat_sheet.append(["时间", "用户ID", "用户名", "sec_uid", "用户主页", "消息内容"])
                if self.gift_sheet.max_row == 1 and not any(self.gift_sheet[1]):
                    self.gift_sheet.append(["时间", "用户名", "sec_uid", "用户主页", "礼物名称", "礼物数量"])
                if self.like_sheet.max_row == 1 and not any(self.like_sheet[1]):
                    self.like_sheet.append(["时间", "用户名", "sec_uid", "用户主页", "点赞数量"])
                if self.follow_sheet.max_row == 1 and not any(self.follow_sheet[1]):
                    self.follow_sheet.append(["时间", "用户ID", "用户名", "sec_uid", "用户主页"])
                if self.fanclub_sheet.max_row == 1 and not any(self.fanclub_sheet[1]):
                    self.fanclub_sheet.append(["时间", "消息内容"])

            else:
                print(f"【系统】创建新的Excel文件: {self.excel_file}")
                # 创建新文件
                self.workbook = Workbook()
                # 删除默认工作表
                self.workbook.remove(self.workbook.active)

                # 创建各类消息的工作表
                self.chat_sheet = self.workbook.create_sheet("聊天消息")
                self.gift_sheet = self.workbook.create_sheet("礼物消息")
                self.like_sheet = self.workbook.create_sheet("点赞消息")
                self.follow_sheet = self.workbook.create_sheet("关注消息")
                self.fanclub_sheet = self.workbook.create_sheet("粉丝团消息")

                # 设置表头
                self.chat_sheet.append(["时间", "用户ID", "用户名", "sec_uid", "用户主页", "消息内容"])
                self.gift_sheet.append(["时间", "用户名", "sec_uid", "用户主页", "礼物名称", "礼物数量"])
                self.like_sheet.append(["时间", "用户名", "sec_uid", "用户主页", "点赞数量"])
                self.follow_sheet.append(["时间", "用户ID", "用户名", "sec_uid", "用户主页"])
                self.fanclub_sheet.append(["时间", "消息内容"])

            print(f"【系统】Excel文件初始化成功: {self.excel_file}")
        except Exception as e:
            print(f"【异常】Excel文件初始化失败: {e}")

    def save_excel(self):
        """保存Excel文件"""
        try:
            self.workbook.save(self.excel_file)
            print(f"【系统】Excel文件已保存: {self.excel_file}")
        except Exception as e:
            print(f"【异常】Excel文件保存失败: {e}")

    def start(self):
        try:
            self._connectWebSocket()
        except KeyboardInterrupt:
            print("\n【异常】用户手动停止程序")
            self.stop()
        except Exception as e:
            print(f"【异常】程序运行出错: {e}")
            self.stop()
            raise

    def stop(self):
        print("【系统】正在停止程序并保存数据...")
        if hasattr(self, 'ws'):
            try:
                self.ws.close()
            except:
                pass
        self.save_excel()
        print("【系统】程序已停止")

    @property
    def ttwid(self):
        """
        产生请求头部cookie中的ttwid字段，访问抖音网页版直播间首页可以获取到响应cookie中的ttwid
        :return: ttwid
        """
        if self.__ttwid:
            return self.__ttwid
        headers = {
            "User-Agent": self.user_agent,
        }
        try:
            response = requests.get(self.live_url, headers=headers, timeout=10)
            response.raise_for_status()
        except Exception as err:
            print("【异常】请求直播首页失败: ", err)
            # 返回一个默认值，避免程序崩溃
            self.__ttwid = "default_ttwid"
        else:
            self.__ttwid = response.cookies.get('ttwid') or "default_ttwid"
        return self.__ttwid

    @property
    def room_id(self):
        """
        根据直播间的地址获取到真正的直播间roomId，有时会有错误，可以重试请求解决
        :return:room_id
        """
        if self.__room_id:
            return self.__room_id

        url = self.live_url + self.live_id
        headers = {
            "User-Agent": self.user_agent,
            "cookie": f"ttwid={self.ttwid}&msToken={generateMsToken()}; __ac_nonce=0123407cc00a9e438deb4",
        }

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()

                match = re.search(r'roomId\\":\\"(\d+)\\"', response.text)
                if match is None or len(match.groups()) < 1:
                    print(f"【异常】第{attempt+1}次尝试：未找到roomId")
                    if attempt < max_retries - 1:
                        time.sleep(2)  # 重试前等待2秒
                        continue
                    else:
                        # 如果所有重试都失败，使用live_id作为room_id
                        print("【警告】使用live_id作为room_id")
                        self.__room_id = self.live_id
                        return self.__room_id

                self.__room_id = match.group(1)
                print(f"【系统】成功获取room_id: {self.__room_id}")
                return self.__room_id

            except Exception as err:
                print(f"【异常】第{attempt+1}次获取room_id失败: {err}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    # 最后一次重试失败，使用live_id作为room_id
                    print("【警告】所有重试失败，使用live_id作为room_id")
                    self.__room_id = self.live_id
                    return self.__room_id

    def get_room_status(self):
        """
        获取直播间开播状态:
        room_status: 2 直播已结束
        room_status: 0 直播进行中
        :return: 包含主播信息和直播状态的字典
        """
        try:
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
                    print(f"【{nickname}】[{user_id}]直播间：{status_text}.")

                    # 返回详细信息供UI使用
                    return {
                        'room_status': room_status,
                        'user_id': user_id,
                        'nickname': nickname,
                        'status_text': status_text
                    }
                else:
                    print("【异常】无法获取用户信息")
            else:
                print("【异常】无法获取直播间数据")
        except Exception as e:
            print(f"【异常】获取房间状态失败: {e}")
        return None

    def _connectWebSocket(self):
        """
        连接抖音直播间websocket服务器，请求直播间数据
        """
        try:
            # 生成动态参数
            current_time = int(time.time() * 1000)
            cursor = f"d-1_u-1_fh-{random.randint(7000000000000000000, 7999999999999999999)}_t-{current_time}_r-1"
            internal_ext = (f"internal_src:dim|wss_push_room_id:{self.room_id}|wss_push_did:{self.device_id}"
                           f"|first_req_ms:{current_time-100}|fetch_time:{current_time}|seq:1|wss_info:0-{current_time}-0-0|"
                           f"wrds_v:{random.randint(7000000000000000000, 7999999999999999999)}")

            wss = ("wss://webcast100-ws-web-lq.douyin.com/webcast/im/push/v2/?app_name=douyin_web"
                   "&version_code=180800&webcast_sdk_version=1.0.14-beta.0"
                   "&update_version_code=1.0.14-beta.0&compress=gzip&device_platform=web&cookie_enabled=true"
                   "&screen_width=1920&screen_height=1080&browser_language=zh-CN&browser_platform=Win32"
                   "&browser_name=Chrome"
                   "&browser_version=120.0.0.0"
                   "&browser_online=true&tz_name=Asia/Shanghai"
                   f"&cursor={cursor}"
                   f"&internal_ext={urllib.parse.quote(internal_ext)}"
                   f"&host=https://live.douyin.com&aid=6383&live_id=1&did_rule=3&endpoint=live_pc&support_wrds=1"
                   f"&user_unique_id={self.unique_id}&im_path=/webcast/im/fetch/&identity=audience"
                   f"&need_persist_msg_count=15&insert_task_id=&live_reason=&room_id={self.room_id}&heartbeatDuration=0")

            signature = generateSignature(wss)
            wss += f"&signature={signature}"

            headers = {
                "cookie": f"ttwid={self.ttwid}; device_id={self.device_id}; user_unique_id={self.unique_id}",
                'user-agent': self.user_agent,
            }

            print(f"【系统】准备连接WebSocket...")
            self.ws = websocket.WebSocketApp(wss,
                                             header=headers,
                                             on_open=self._wsOnOpen,
                                             on_message=self._wsOnMessage,
                                             on_error=self._wsOnError,
                                             on_close=self._wsOnClose)

            # 设置WebSocket选项
            websocket.setdefaulttimeout(30)

            self.ws.run_forever(ping_interval=30, ping_timeout=10)
        except Exception as e:
            print(f"【异常】WebSocket连接失败: {e}")
            self.stop()
            raise

    def _sendHeartbeat(self):
        """
        发送心跳包
        """
        while True:
            try:
                heartbeat = PushFrame(payload_type='hb').SerializeToString()
                self.ws.send(heartbeat, websocket.ABNF.OPCODE_PING)
            except Exception as e:
                print("【异常】心跳包检测错误: ", e)
                break
            else:
                time.sleep(5)

    def _wsOnOpen(self, ws):
        """
        连接建立成功
        """
        threading.Thread(target=self._sendHeartbeat).start()

    def _wsOnMessage(self, ws, message):
        """
        接收到数据
        :param ws: websocket实例
        :param message: 数据
        """
        try:
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

            # 根据消息类别解析消息体
            for msg in response.messages_list:
                method = msg.method
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
                    }.get(method)(msg.payload)
                except Exception as e:
                    print(f"【异常】处理消息 {method} 时出错: {e}")
        except Exception as e:
            print(f"【异常】解析WebSocket消息失败: {e}")

    def _wsOnError(self, ws, error):
        print("【异常】WebSocket错误: ", error)

    def _wsOnClose(self, ws, *args):
        self.get_room_status()
        print("【异常】WebSocket连接已关闭")
        # 连接关闭时自动保存
        self.save_excel()

    def _parseChatMsg(self, payload):
        """聊天消息"""
        message = ChatMessage().parse(payload)
        user_name = message.user.nick_name
        user_id = message.user.id
        sec_uid = getattr(message.user, 'sec_uid', '')
        user_homepage = f"https://www.douyin.com/user/{sec_uid}" if sec_uid else ""
        content = message.content
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        print(f"【聊天msg】[{user_id}]{user_name}: {content}")

        # 保存到Excel
        try:
            self.chat_sheet.append([current_time, user_id, user_name, sec_uid, user_homepage, content])
        except Exception as e:
            print(f"【异常】保存聊天消息到Excel失败: {e}")

    def _parseGiftMsg(self, payload):
        """礼物消息"""
        message = GiftMessage().parse(payload)
        user_name = message.user.nick_name
        sec_uid = getattr(message.user, 'sec_uid', '')
        user_homepage = f"https://www.douyin.com/user/{sec_uid}" if sec_uid else ""
        gift_name = message.gift.name
        gift_cnt = message.combo_count
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        print(f"【礼物msg】{user_name} 送出了 {gift_name}x{gift_cnt}")

        # 保存到Excel
        try:
            self.gift_sheet.append([current_time, user_name, sec_uid, user_homepage, gift_name, gift_cnt])
        except Exception as e:
            print(f"【异常】保存礼物消息到Excel失败: {e}")

    def _parseLikeMsg(self, payload):
        '''点赞消息'''
        message = LikeMessage().parse(payload)
        user_name = message.user.nick_name
        sec_uid = getattr(message.user, 'sec_uid', '')
        user_homepage = f"https://www.douyin.com/user/{sec_uid}" if sec_uid else ""
        count = message.count
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        print(f"【点赞msg】{user_name} 点了{count}个赞")

        # 保存到Excel
        try:
            self.like_sheet.append([current_time, user_name, sec_uid, user_homepage, count])
        except Exception as e:
            print(f"【异常】保存点赞消息到Excel失败: {e}")

    def _parseMemberMsg(self, payload):
        '''进入直播间消息'''
        message = MemberMessage().parse(payload)
        user_name = message.user.nick_name
        user_id = message.user.id
        gender = ["女", "男"][message.user.gender]
        print(f"【进场msg】[{user_id}][{gender}]{user_name} 进入了直播间")

    def _parseSocialMsg(self, payload):
        '''关注消息'''
        message = SocialMessage().parse(payload)
        user_name = message.user.nick_name
        user_id = message.user.id
        sec_uid = getattr(message.user, 'sec_uid', '')
        user_homepage = f"https://www.douyin.com/user/{sec_uid}" if sec_uid else ""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        print(f"【关注msg】[{user_id}]{user_name} 关注了主播")

        # 保存到Excel
        try:
            self.follow_sheet.append([current_time, user_id, user_name, sec_uid, user_homepage])
        except Exception as e:
            print(f"【异常】保存关注消息到Excel失败: {e}")

    def _parseRoomUserSeqMsg(self, payload):
        '''直播间统计'''
        message = RoomUserSeqMessage().parse(payload)
        current = message.total
        total = message.total_pv_for_anchor
        print(f"【统计msg】当前观看人数: {current}, 累计观看人数: {total}")

    def _parseFansclubMsg(self, payload):
        '''粉丝团消息'''
        message = FansclubMessage().parse(payload)
        content = message.content
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        print(f"【粉丝团msg】 {content}")

        # 保存到Excel
        try:
            self.fanclub_sheet.append([current_time, content])
        except Exception as e:
            print(f"【异常】保存粉丝团消息到Excel失败: {e}")

    def _parseEmojiChatMsg(self, payload):
        '''聊天表情包消息'''
        message = EmojiChatMessage().parse(payload)
        emoji_id = message.emoji_id
        user = message.user
        common = message.common
        default_content = message.default_content
        print(f"【表情包msg】emoji_id: {emoji_id}, default_content: {default_content}")

    def _parseRoomMsg(self, payload):
        # 静默处理，不打印日志
        pass

    def _parseRoomStatsMsg(self, payload):
        # 静默处理，不打印日志
        pass

    def _parseRankMsg(self, payload):
        # 静默处理，不打印日志
        pass

    def _parseControlMsg(self, payload):
        '''直播间状态消息'''
        message = ControlMessage().parse(payload)

        if message.status == 3:
            print("【控制msg】直播间已结束")
            self.save_excel()
            self.stop()
        else:
            print(f"【控制msg】直播间状态变更: {message.status}")

    def _parseRoomStreamAdaptationMsg(self, payload):
        # 静默处理，不打印日志
        pass
