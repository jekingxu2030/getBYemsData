import asyncio
import json
import websockets
from PyQt5.QtCore import QThread, pyqtSignal
import time

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
                    max_queue=1024,
                ) as websocket:

                    self.websocket = websocket
                    self.log_signal.emit("WebSocket连接成功")
                    # self.connect_btn.setEnabled(False)
                    # self.disconnect_btn.setEnabled(True)
                    # self.refresh_btn.setEnabled(True)
                    # 发送menu请求
                    await websocket.send(json.dumps({"func": "menu"}))
                    self.log_signal.emit("已发送menu请求")

                    # 当is_running为True时，循环接收WebSocket消息
                    while self.is_running:
                        # 如果需要刷新，则发送menu请求
                        if self.need_refresh:
                            self.need_refresh = False
                            await websocket.send(json.dumps({"func": "menu"}))
                            self.log_signal.emit("刷新menu请求")

                        # 接收WebSocket消息
                        msg = await websocket.recv()
                        self.log_signal.emit(
                            f"收到原始消息: {msg[:100]}..."
                        )  # 只显示前200个字符
                        # 打印接收到的完整JSON数据
                        print("Received JSON data:")
                        print(json.dumps(json.loads(msg), indent=4, ensure_ascii=False))
                        # 如果消息是字符串类型，则解析JSON
                        if isinstance(msg, str):
                            try:
                                data = json.loads(msg)
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
