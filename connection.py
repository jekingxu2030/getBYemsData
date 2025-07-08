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
# 保存RTV数据到JSON文件
# import os
import time
# from mysql_storage import MySQLStorage
from data_insert import save_realtime_data  # 调用数据库存入方法模块
import gc


class WebSocketWorker(QThread):
    """后台 WebSocket 通信线程
    - 使用 QThread 封装 asyncio 事件循环
    - 收/发消息、自动重连、落库、写文件
    - 通过信号与主线程（UI）交互
    """

    message_signal = pyqtSignal(dict)  # 传递业务数据
    log_signal = pyqtSignal(str)  # 传递日志字符串

    def __init__(self, token: str, interval_seconds: int = 10):
        super().__init__()
        self.is_running = True
        self.websocket = None
        self.token = token or "your-default-token-here"
        self.need_refresh = False
        self.loop = None
        self.rtv_interval = interval_seconds  # 使用传入的间隔时间
        self.rtv_timer = None
        self.res_counts=0

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
                    print(f"\n[DEBUG] 已发送 menu 请求: {json.dumps({'func': 'menu'})}")
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
            print(f"\n收到-{type(data)}类数据")
            print(f"\n[DEBUG]收到订阅数据: {json.dumps(data, ensure_ascii=False)[:50]}")
            self.log_signal.emit(f"收到订阅数据: {json.dumps(data, ensure_ascii=False)[:50]}")
        except json.JSONDecodeError as err:
            self.log_signal.emit(f"[WS] JSON 解析失败: {err}")
            return
            
        try:
            # print("len(str(data)) =", len(str(data)))                       # dict 转字符串后的长度
            raw = json.dumps(data, ensure_ascii=False)                      # 转json字符串  任意字符
            print("len(json.dumps) =", len(raw))          
            # 序列化后长度
            print("前50 字:", raw[:50])                                 # 看最后 200 个字符

            # 4) 广播给 UI #不管是啥数据，ui层自己分类，本模块也自己分类，用于获取和更新id清单
            self.message_signal.emit(data)

            func = data.get("func")
            if func == "menu":
                print("收到menu数据")
                # -------- menu 逻辑：取 rtv‑id，订阅实时值 遍历获取全部数据id--------

                rtv_ids = []
                for dev_list in data.get("data", {}).values():
                    for dev in dev_list:
                        for rtv in dev.get("rtvList", []):
                            rtv_id = rtv.get("id")
                            if isinstance(rtv_id, int):  # ✅ 只保留数字类型 ID
                                rtv_ids.append(rtv_id)

                print(f"\n[DEBUG] 获取到的menu_rtv_ids: {rtv_ids[:3]}")

                dev_cnt = sum(len(devs) for devs in data["data"].values())
                self.log_signal.emit(
                      f"[WS] 收到menu订阅：设备 {dev_cnt} 个，字段 {len(rtv_ids)} 项 → 已发送 rtv 订阅"
                  )
                print(f"\n 收到menu订阅：设备 {dev_cnt} 个，字段 {len(rtv_ids)} 项")
                sub_cmd = {"func": "rtv", "ids": rtv_ids, "period": 5}
                await self.websocket.send(json.dumps(sub_cmd))
                print(f"\n[DEBUG]RTV已订阅: {json.dumps(sub_cmd)[:50]}")
                self.log_signal.emit(f"[WS]已发送 rtv 订阅")
                self._start_rtv_timer(rtv_ids)
                time.sleep(1)  

            elif func == "rtv":
                # print("收到RTV数据")
                # 修改为完整获取data内容

                rtvJsonStr = json.dumps(data, ensure_ascii=False)
                # print(f"\nRTV数据josnStr: {rtvJsonStr[:70]}")
                rtvData = data.get("data", [])

                # print(f"RTV数据: {json.dumps(rtvData[:30], ensure_ascii=False)}")
                field_cnt = len(rtvData)
                # self.log_signal.emit(f"[WS] 收到 rtv订阅数据包")
                self.log_signal.emit(f"[WS] 收到 rtv订阅数据包，字段数 {field_cnt}")

                # 添加调试日志确认rtv请求已发送
                print(f"\n[DEBUG] RTV订阅数据长度: {len(rtvData)},字段数量：{field_cnt}")
                print(
                    f"[DEBUG] RTV订阅数据示例: {json.dumps(rtvData[:3], ensure_ascii=False) if rtvData else '无数据'}"
                )

                # 3) 写入数据库（使用统一封装函数，直接传 dict）
                # print(f"\n[DEBUG] rtvData完整内容: {rtvData[:2]}")
                startTime = time.time()
                
                ok =await save_realtime_data(
                    rtvData, datetime.now(), self.rtv_interval
                )  # 数据库模块
                if ok == "skipped":
                    self.log_signal.emit("[存库] 跳过: 时间间隔不足")
                else:
                    self.log_signal.emit("[存库] 写库" + ("成功" if ok else "失败"))
                endTime=time.time()
                useTime=endTime-startTime
                print(f"[DEBUG]写入数据库耗时：{useTime}")
                # 保存rtv数据到文件
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                log_dir = os.path.join(os.path.dirname(__file__), "dataLog")
                os.makedirs(log_dir, exist_ok=True)
                log_file = os.path.join(log_dir, f"rtv_update_{timestamp}.json")
                # with open(log_file, "w", encoding="utf-8") as f:
                #     json.dump(rtvData, f, ensure_ascii=False, indent=2)
                # print(f"\n[DEBUG] RTV数据已保存到: {log_file}")

            else:
                # -------- 其它消息类型 --------
                self.log_signal.emit(f"[WS] 收到其他 {func} 消息")
            # self.log_signal.emit(f"[WS] 刷新数据")
            
            if self.res_counts > 10000:
               gc.collect()
               self.res_counts=0
            else:
               self.res_counts+=1
                     
        except Exception as e:
            self.log_signal.emit(f"[WS] 消息处理失败: {e}")
            print(e)
        
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
                try:
                    # print(f"\n[DEBUG] 准备发送RTV请求: {json.dumps({'func': 'rtv', 'ids': rtv_ids[:5], 'period': self.rtv_interval})}")
                    await self.websocket.send(json.dumps({
                        "func": "rtv", 
                        "ids": rtv_ids,
                        "period": self.rtv_interval/2
                    }))
                    print(f"\n[DEBUG] 定时RTV请求已发送: {json.dumps({'func': 'rtv', 'ids': rtv_ids[:5], 'period': self.rtv_interval/2})}")
                except Exception as e:
                    print(f"\n[ERROR] 发送RTV请求失败: {e}")
                finally:
                    self._start_rtv_timer(rtv_ids)  # 重新启动定时器

        self.rtv_timer = self.loop.call_later(
            self.rtv_interval, 
            lambda: asyncio.create_task(_send_rtv_request())
        )
