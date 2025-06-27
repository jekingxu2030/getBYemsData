import asyncio
import json
import websockets
from PyQt5.QtCore import QThread, pyqtSignal


class WebSocketWorker(QThread):
    message_signal = pyqtSignal(dict)  # 传输数据消息
    log_signal = pyqtSignal(str)  # 输出日志

    def __init__(self, token):
        super().__init__()
        self.is_running = True
        self.websocket = None
        self.token = token
        self.need_refresh = False

    def run(self):
        asyncio.run(self.connect_websocket())

    async def connect_websocket(self):
        if not self.token:
            self.log_signal.emit("Token为空，使用默认值")
            self.token = "your-default-token-here"

        uri = f"ws://ems.hy-power.net:8888/E6F7D5412A20?{self.token}"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Origin": "http://ems.hy-power.net:8114",
        }

        while self.is_running:
            try:
                async with websockets.connect(uri, extra_headers=headers) as websocket:
                    self.websocket = websocket
                    self.log_signal.emit("WebSocket连接成功")
                    # self.connect_btn.setEnabled(False)
                    # self.disconnect_btn.setEnabled(True)
                    # self.refresh_btn.setEnabled(True)
                    await websocket.send(json.dumps({"func": "menu"}))
                    self.log_signal.emit("已发送menu请求")

                    while self.is_running:
                        if self.need_refresh:
                            self.need_refresh = False
                            await websocket.send(json.dumps({"func": "menu"}))
                            self.log_signal.emit("刷新menu请求")

                        msg = await websocket.recv()
                        if isinstance(msg, str):
                            try:
                                data = json.loads(msg)
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

    def stop(self):
        self.is_running = False
        self.websocket = None

    def request_refresh(self):
        self.need_refresh = True

    def send_cmd(self, cmd_id, ref_fid, ref_rid, value):
        if not self.websocket:
            self.log_signal.emit("WebSocket未连接，命令未发送")
            return

        message = {
            "func": "cmd",
            "id": cmd_id,
            "refFid": ref_fid,
            "refRid": ref_rid,
            "value": value,
        }
        asyncio.run(self.websocket.send(json.dumps(message)))
