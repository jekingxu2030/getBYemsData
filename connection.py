


# ======================================
# connection.py  — WebSocket 后台通信线程（修正版）
# --------------------------------------
# * 自动重连
# * 收到完整 JSON → 打印 / 保存文件 / 入库
# * 保留 UI 日志信号，方便窗口显示
# * 解决 "asyncio.run() cannot be called from a running event loop" 问题
# --------------------------------------

import asyncio
import json
import websockets
from PyQt5.QtCore import QThread, pyqtSignal
import os
from datetime import datetime

# from mysql_storage import MySQLStorage
from data_insert import save_realtime_data  # 调用数据存入方法模块


class WebSocketWorker(QThread):
    """后台 WebSocket 通信线程
    - 使用 QThread 封装 asyncio 事件循环
    - 收/发消息、自动重连、落库、写文件
    - 通过信号与主线程（UI）交互
    """

    message_signal = pyqtSignal(dict)  # 传递业务数据
    log_signal = pyqtSignal(str)  # 传递日志字符串

    def __init__(self, token: str):
        super().__init__()
        self.is_running = True
        self.websocket = None
        self.token = token or "your-default-token-here"
        self.need_refresh = False
        self.loop = None
        self.rtv_interval = 5  # 默认间隔5秒
        self.rtv_timer = None

    # ------------------------------------------------------------------
    # QThread 入口
    # ------------------------------------------------------------------
    def run(self):
        """在线程中启动独立事件循环"""
        asyncio.run(self.connect_websocket())

    # ------------------------------------------------------------------
    # 建立并维护 WebSocket 连接
    # ------------------------------------------------------------------
    async def connect_websocket(self):
        """主协程：负责连接 + 消息循环 + 重连"""
        self.loop = asyncio.get_running_loop()  # 记录当前事件循环
        uri = f"ws://ems.hy-power.net:8888/E6F7D5412A20?{self.token}"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Origin": "http://ems.hy-power.net:8114",
        }

        while self.is_running:
            try:
                async with websockets.connect(
                    uri,
                    extra_headers=headers,
                    ping_interval=60,
                    ping_timeout=30,
                    close_timeout=5,
                    max_queue=1024,
                ) as ws:
                    self.websocket = ws
                    self.log_signal.emit("[WS] 连接成功")

                    # 首次请求 menu主动发送
                    await ws.send(json.dumps({"func": "menu"}))
                    self.log_signal.emit("[WS] 已发送 menu 请求")

                    async for msg in ws:  # 自动合并分片
                        self.log_signal.emit(f"[WS] 收到 {len(msg)} 字节")
                        if isinstance(msg, str) and msg:
                            await self._handle_message(msg)

            except Exception as e:
                self.log_signal.emit(f"[WS] 异常: {e}，3秒后重连")
                await asyncio.sleep(3)

    # ------------------------------------------------------------------
    # 处理每一条文本消息
    # ------------------------------------------------------------------
    async def _handle_message(self, msg: str):
        """保存 → 解析 → 入库 → UI → 如需再订阅"""
        # 1) 保存原始 JSON 到文件
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs("ws_json_dump", exist_ok=True)
        file_path = os.path.join("ws_json_dump", f"ws_msg_{ts}.json")
        # with open(file_path, "w", encoding="utf-8") as f:
        # f.write(msg)
        # self.log_signal.emit(f"[文件] JSON 已保存: {file_path}")

        # 2) 解析 JSON
        try:
            data = json.loads(msg)
        except json.JSONDecodeError as err:
            self.log_signal.emit(f"[WS] JSON 解析失败: {err}")
            return

        # print("len(str(data)) =", len(str(data)))                       # dict 转字符串后的长度
        raw = json.dumps(data, ensure_ascii=False)                      # 不缩进
        print("len(json.dumps) =", len(raw))                            # 序列化后长度
        # print("尾 200 字:", raw[-200:])                                 # 看最后 200 个字符

        # 3) 写入数据库（使用统一封装函数，直接传 dict）
        ok = save_realtime_data(data)
        self.log_signal.emit("[存库] 写库" + ("成功" if ok else "失败"))

        # 4) 广播给 UI
        self.message_signal.emit(data)

        func = data.get("func")
        if func == "menu":
              # -------- menu 逻辑：取 rtv‑id，订阅实时值 --------
              rtv_ids = [
                  r["id"]
                  for devs in data.get("data", {}).values()
                  for dev in devs
                  for r in dev.get("rtvList", [])
              ]
              sub_cmd = {"func": "rtv", "ids": rtv_ids, "period": 5}
              await self.websocket.send(json.dumps(sub_cmd))

              dev_cnt = sum(len(devs) for devs in data["data"].values())
              self.log_signal.emit(
                  f"[WS] 收到menu订阅：设备 {dev_cnt} 个，字段 {len(rtv_ids)} 项 → 已发送 rtv 订阅"
              )

没有        elif func == "rtv":
            # -------- rtv 逻辑：这里只做提示，数据已在上层处理 --------
            rtv_list = data.get("data", [])           # 默认空列表
            field_cnt = len(rtv_list)
            print(f"[DEBUG] RTV数据: {rtv_list}")  # 打印rtv数据
            self.log_signal.emit(f"[WS] 收到 rtv订阅数据包，字段数 {field_cnt}")

        else:
              # -------- 其它消息类型 --------
              self.log_signal.emit(f"[WS] 收到 {func} 消息")
              self.log_signal.emit(f"[WS] 刷新数据")  
              
    # ------------------------------------------------------------------
    # 控制接口
    # ------------------------------------------------------------------
    def stop(self):
        """外部调用，安全停止线程"""
        self.is_running = False
        self.websocket = None

    def request_refresh(self):
        """外部调用，触发下次循环发送 menu"""
        self.need_refresh = True

    def send_cmd(self, cmd_id, ref_fid, ref_rid, value):
        """在主线程调用：向设备下发命令"""
        if not self.websocket or not self.loop:
            self.log_signal.emit("[WS] WebSocket未连接，命令未发送")
            return

        async def _do_send():
            message = {
                "func": "cmd",
                "id": cmd_id,
                "refFid": ref_fid,
                "refRid": ref_rid,
                "value": value,
            }
            await self.websocket.send(json.dumps(message))

        # 在线程安全的方式提交协程到事件循环
        asyncio.run_coroutine_threadsafe(_do_send(), self.loop)

    def _start_rtv_timer(self, rtv_ids):
        """启动定时请求rtv的定时器"""
        if self.rtv_timer:
            self.rtv_timer.cancel()
        
        async def _send_rtv_request():
            if self.websocket:
                await self.websocket.send(json.dumps({
                    "func": "rtv", 
                    "ids": rtv_ids,
                    "period": self.rtv_interval
                }))
        
        self.rtv_timer = self.loop.call_later(
            self.rtv_interval, 
            lambda: asyncio.create_task(_send_rtv_request())
        )
