import asyncio
import json
import websockets
from PyQt5.QtCore import QThread, pyqtSignal
import time

from mysql_storage import MySQLStorage  # Absolute import

import os
from datetime import datetime
import json

from data_insert import save_realtime_data  # <‑‑ 只需这一行 import

# WebSocket连接管理模块
# 负责建立和维护与EMS服务器的WebSocket连接，处理数据收发


class WebSocketWorker(QThread):
    """
    WebSocket通信工作线程
    功能：
    - 使用QThread实现后台WebSocket通信
    - 处理连接建立、消息收发、断线重连
    - 通过信号机制与主线程交互
    属性：
    - message_signal: 数据消息信号
    - log_signal: 日志信号
    - token: 认证令牌
    """

    message_signal = pyqtSignal(dict)  # 传输数据消息
    log_signal = pyqtSignal(str)  # 输出日志

    def __init__(self, token):
        """初始化工作线程"""
        super().__init__()
        self.is_running = True  # 线程运行标志
        self.websocket = None  # WebSocket连接对象
        self.token = token  # 认证令牌
        self.need_refresh = False  # 刷新标志

    def run(self):
        # 运行connect_websocket方法
        asyncio.run(self.connect_websocket())

    async def connect_websocket(self):
        # 如果token为空，则使用默认值
        if not self.token:
            self.log_signal.emit("Token为空，使用默认值")
            self.token = "your-default-token-here"

        # 构造WebSocket连接的URI
        uri = f"ws://ems.hy-power.net:8888/E6F7D5412A20?{self.token}"
        # 设置WebSocket连接的头部信息
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Origin": "http://ems.hy-power.net:8114",
        }

        last_ping = time.time()
        # 当is_running为True时，循环连接WebSocket
        while self.is_running:

            try:
                # 使用async with语句连接WebSocket

                async with websockets.connect(
                    uri,
                    extra_headers=headers,
                    ping_interval=60,
                    ping_timeout=30,
                    close_timeout=5,
                    # max_queue=1024,
                    max_queue=None,  # ← 队列无限制
                    max_size=None,  # ← 关闭 1 MB 消息大小上限
                ) as websocket:

                    self.websocket = websocket
                    self.log_signal.emit("WebSocket连接成功")
                    # self.connect_btn.setEnabled(False)
                    # self.disconnect_btn.setEnabled(True)
                    # self.refresh_btn.setEnabled(True)
                    # 发送menu请求
                    await websocket.send(json.dumps({"func": "menu"}))
                    self.log_signal.emit("已发送menu请求1")

                    # 当is_running为True时，循环接收WebSocket消息
                    while self.is_running:
                        # 如果需要刷新，则发送menu请求
                        if self.need_refresh:
                            self.need_refresh = False
                            # await websocket.send(json.dumps({"func": "menu"}))
                            # self.log_signal.emit("刷新menu请求2")

                        # 接收WebSocket消息
                        msg = await websocket.recv()
                        self.log_signal.emit(
                            f"收到原始消息: {msg[:100]}..."
                        )  # 只显示前200个字符
                        # 打印接收到的完整JSON数据
                        # print("Received JSON data:")
                        # print(json.dumps(json.loads(msg), indent=4, ensure_ascii=False))
                        # 如果消息是字符串类型，则解析JSON
                        if isinstance(msg, str):
                            if msg:
                                try:
                                    # print("即将写入的数据 ↓")
                                    print(
                                        # "\n即将写入的数据 ->", msg
                                    )  # 直接 str() 转成字符串
                                    # 或者
                                    print(
                                    json.dumps(msg, indent=2, ensure_ascii=False)
                                    )  # 漂亮格式化
                                    ok = save_realtime_data(msg)  # <‑‑ 调用统一入口
                                    ok=1
                                    if ok:
                                        self.log_signal.emit(f"{len(msg)} 条数据存储到 MySQL")
                                        print(f"{len(msg)} 条数据存储到 MySQL")
                                    else:
                                        self.log_signal.emit("据存储到MySQL失败")
                                        print("据存储到MySQL失败")
                                except Exception as e:
                                    print(f"数据存储异常: {e}")
                                    self.log_signal.emit(f"数据存储异常: {e}")

                                try:
                                    data = json.loads(msg)
                               
                                    # data = json.loads(msg)  # ← 你已成功解析得到的 dict

                                    # -------- ① 终端 / 日志输出（完整） --------
                                    pretty = json.dumps(data, ensure_ascii=False, indent=2)
                                    print("▼ 收到完整 JSON 数据包：")
                                    print(pretty)

                                    # 如果想用你的 log() 而不是 print：
                                    # log(pretty)

                                    # -------- ② 同步写入文件 --------
                                    # 生成形如 20250628_142530.json 的文件名
                                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                                    fname = f"ws_msg_{ts}.json"

                                    # 建议放到专门的 logs 文件夹
                                    os.makedirs("ws_json_dump", exist_ok=True)
                                    file_path = os.path.join("ws_json_dump", fname)

                                    with open(file_path, "w", encoding="utf-8") as f:
                                        f.write(pretty)

                                    print(f"已保存到 {file_path}")
                                    # log(f"已保存到 {file_path}")

                                except json.JSONDecodeError as err:          
                                               
                                    # 发送消息信号
                                    self.message_signal.emit(data)

                                    if data.get("func") == "menu":
                                        rtv_ids = []
                                        for devs in data.get("data", {}).values():
                                            for dev in devs:
                                                for rtv in dev.get("rtvList", []):
                                                    rtv_ids.append(rtv["id"])

                                        rtv_sub = {
                                            "func": "rtv",
                                            "ids": rtv_ids,
                                            "period": 5,
                                        }
                                        await websocket.send(json.dumps(rtv_sub))
                                        self.log_signal.emit(
                                            f"已订阅rtv，{len(rtv_ids)}个ID"
                                        )

                                except json.JSONDecodeError:
                                    self.log_signal.emit("JSON解析失败")

            except Exception as e:
                self.log_signal.emit(f"WebSocket连接失败: {e}，3秒后重试")
                await asyncio.sleep(3)

    # 停止函数
    def stop(self):
        # 将is_running属性设置为False
        self.is_running = False
        # 将websocket属性设置为None
        self.websocket = None

    def request_refresh(self):
        # 请求刷新
        self.need_refresh = True

    def send_cmd(self, cmd_id, ref_fid, ref_rid, value):
        # 检查WebSocket是否连接
        if not self.websocket:
            # 如果未连接，则发出日志信号，命令未发送
            self.log_signal.emit("WebSocket未连接，命令未发送")
            return

        # 构造消息
        message = {
            "func": "cmd",
            "id": cmd_id,
            "refFid": ref_fid,
            "refRid": ref_rid,
            "value": value,
        }
        # 使用asyncio.run发送消息
        asyncio.run(self.websocket.send(json.dumps(message)))
