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
        # 初始化函数，传入token和间隔时间
        super().__init__()  # 调用父类的初始化函数
        self.is_running = True  # 设置运行状态为True
        self.websocket = None  # 初始化websocket为None
        self.token = token or "your-default-token-here"  # 设置token，如果没有传入token，则使用默认token
        self.need_refresh = False  # 设置需要刷新为False
        self.loop = None  # 初始化loop为None
        self.rtv_interval = interval_seconds  # 使用传入的间隔时间
        self.rtv_timer = None  # 初始化rtv_timer为None
        self.res_counts=0  # 初始化res_counts为0
        self.last_message_time = time.time()  # 记录最后收到消息的时间
        self.timeout_threshold = 60  # 超时阈值(秒)  订阅超时没返回记一次超时

        # 智能重订阅相关变量
        self.rtv_timeout_count = 0  # RTV订阅超时计数器
        self.max_rtv_timeout = 3  # 最大超时次数
        self.rtv_ids_cache = []  # 缓存RTV ID列表用于重订阅
        self.last_rtv_subscribe_time = 0  # 最后发送RTV订阅的时间

        # 连接状态标志
        self.is_connected = False  # WebSocket连接成功标志，初始为False

    # ------------------------------------------------------------------
    # QThread 入口
    # ------------------------------------------------------------------
    def run(self):
        """在线程中启动独立事件循环"""
        asyncio.run(self.connect_websocket())

    # ------------------------------------------------------------------
    # 建立并维护 WebSocket 连接
    async def connect_websocket(self):
        """主协程：负责连接 + 消息循环 + 重连"""
        self.loop = asyncio.get_running_loop()  # 记录当前事件循环
        # uri = f"ws://ems.hy-power.net:8888/E6F7D5412A20?{self.token}"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Origin": "http://ems.hy-power.net:8114",
        }
        print(f"[WS] 连接所用Token: {self.token}")
        while self.is_running and not self.is_connected:  # 同时检查运行状态和连接状态
            # 每次循环重新构建uri，确保使用最新的token
            uri = f"ws://ems.hy-power.net:8888/E6F7D5412A20?{self.token}"
            try:
                async with websockets.connect(
                    uri,
                    extra_headers=headers,
                    ping_interval=60,
                    ping_timeout=55,
                    close_timeout=5,
                    open_timeout=5,
                    timeout=60,
                    max_size=2**23,  # 8MiB
                    max_queue=1024,
                ) as ws:
                    self.websocket = ws
                    self.is_connected = True  # 设置连接成功标志
                    self.log_signal.emit("[WS] 连接成功")

                    # 首次请求 menu主动发送
                    await ws.send(json.dumps({"func": "menu"}))
                    print(f"\n[DEBUG] 已发送 menu 请求: {json.dumps({'func': 'menu'})}")
                    self.log_signal.emit("[WS] 已发送 menu 请求")

                    async for msg in ws:  # 自动合并分片
                        self.log_signal.emit(f"[WS] 收到 {len(msg)} 字节")
                        if isinstance(msg, str) and msg:
                            await self._handle_message(msg)

                    # # 在消息循环中添加超时检测 ---开始---
                    # current_time = time.time()
                    # if self.last_rtv_subscribe_time > 0:  # 已发送过RTV订阅
                    #     if current_time - self.last_rtv_subscribe_time > self.rtv_interval:
                    #         self.rtv_timeout_count += 1
                    #         self.log_signal.emit(f"[WS] RTV订阅超时 {self.rtv_timeout_count}/{self.max_rtv_timeout}")

                    #         # 超时3次后重发订阅
                    #         if self.rtv_timeout_count >= self.max_rtv_timeout and self.rtv_ids_cache:
                    #             self.log_signal.emit("[WS] 连续超时3次，重新发送RTV订阅...")
                    #             try:
                    #                 resub_cmd = {"func": "rtv", "ids": self.rtv_ids_cache, "period": self.rtv_interval}
                    #                 print(f"\n[DEBUG] 首次订阅参数配置指令: {json.dumps(resub_cmd)}")
                    #                 await self.websocket.send(json.dumps(resub_cmd))
                    #                 self.log_signal.emit("[WS] RTV重订阅已发送")
                    #                 self.last_rtv_subscribe_time = time.time()
                    #                 self.rtv_timeout_count = 0
                    #             except Exception as e:
                    #                 self.log_signal.emit(f"[WS] 重订阅失败: {e}")

                    #         # 更新最后订阅时间，避免重复计数
                    #         self.last_rtv_subscribe_time = current_time
                    # # 超时检测逻辑 ---结束---

            except Exception as e:
                self.is_connected = False  # 连接失败，复位连接标志
                self.log_signal.emit(f"[WS] 异常: {e}，6秒后重连")
                await asyncio.sleep(6)  # 等待6秒后重连

        # 检查是否超时
        current_time = time.time()
        if current_time - self.last_message_time > self.timeout_threshold:
            self.log_signal.emit(f"[WS] 警告: 超过{self.timeout_threshold}秒未收到数据，可能连接异常")

    # ------------------------------------------------------------------
    # 处理每一条文本消息
    async def _handle_message(self, msg: str):
        """保存 → 解析 → 入库 → UI → 如需再订阅"""
        # 重置超时计时器
        self.last_message_time = time.time()

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
            # print(f"\n收到-{type(data)}类数据")
            print(f"\n[DEBUG]收到订阅数据: {json.dumps(data, ensure_ascii=False)[:70]}")
            self.log_signal.emit(f"收到订阅数据: {json.dumps(data, ensure_ascii=False)[:60]}")
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
                # print("收到menu数据")
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

                # 缓存RTV ID列表用于重订阅
                self.rtv_ids_cache = rtv_ids

                # 修复：正确处理rtv_ids为空的逻辑
                if not rtv_ids:
                    print("rtv_ids为空，不订阅")
                else:
                    # 首次发送订阅
                    sub_cmd = {"func": "rtv", "ids": rtv_ids, "period": self.rtv_interval}
                    sub_cmd_Debug = {"func": "rtv", "ids": len(rtv_ids), "period": 0}
                    await self.websocket.send(json.dumps(sub_cmd))
                    print(f"\n[DEBUG]首次RTV订阅已发送: {json.dumps(sub_cmd_Debug)}")
                    self.log_signal.emit(f"[WS]已发送首次rtv订阅，频率: {self.rtv_interval}秒")

                    # 记录最后订阅时间，重置超时计数器RTV订阅数据示例
                    self.last_rtv_subscribe_time = time.time()
                    self.rtv_timeout_count = 0

                    # 注释掉原有的定时重发机制
                    # self._start_rtv_timer(rtv_ids)
                    time.sleep(1)

            elif func == "rtv":
                # 收到RTV数据，重置超时计数器
                self.rtv_timeout_count = 0
                self.last_rtv_subscribe_time = time.time()

                # 修改为完整获取data内容
                rtvJsonStr = json.dumps(data, ensure_ascii=False)
                # print(f"\nRTV数据josnStr: {rtvJsonStr[:70]}")
                rtvData = data.get("data", [])

                # print(f"RTV数据: {json.dumps(rtvData[:30], ensure_ascii=False)}")
                field_cnt = len(rtvData)
                self.log_signal.emit(f"[WS] 收到 rtv订阅数据包，字段数 {field_cnt}")

                # 添加调试日志确认rtv请求已发送
                print(f"\n[DEBUG] RTV订阅数据长度: {len(rtvData)},字段数量：{field_cnt}")
                print(
                    f"[DEBUG] RTV订阅到数据: {json.dumps(rtvData[:3], ensure_ascii=False) if rtvData else '无数据'}"
                )

                # 3) 写入数据库（使用统一封装函数，直接传 dict）
                # print(f"\n[DEBUG] rtvData完整内容: {rtvData[:2]}")
                startTime = time.time()

                ok =await save_realtime_data(   #调用写库函数
                    rtvData, datetime.now(), self.rtv_interval
                )  # 数据库模块
                if ok == "skipped":
                    self.log_signal.emit("[存库] 跳过: 时间间隔不足")
                else:
                    self.log_signal.emit("[存库] 写库" + ("成功" if ok else "失败"))
                    endTime=time.time()
                    useTime=endTime-startTime
                    print(f"[DEBUG]写库耗时：{useTime}")

                # 保存rtv数据到文件
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                log_dir = os.path.join(os.path.dirname(__file__), "dataLog")
                os.makedirs(log_dir, exist_ok=True)
                log_file = os.path.join(log_dir, f"rtv_update_{timestamp}.json")
                # with open(log_file, "w", encoding="utf-8") as f:   //写出rtv数据到本地文件暂时注释
                #     json.dump(rtvData, f, ensure_ascii=False, indent=2)
                # print(f"\n[DEBUG] RTV数据已保存到: {log_file}")

            else:
                # -------- 其它消息类型 --------
                self.log_signal.emit(f"[WS] 收到其他 {func} 消息")
            # self.log_signal.emit(f"[WS] 刷新数据")

            # ===== 独立的超时检测逻辑 - 开始 =====
            # 此逻辑放在所有消息类型处理之后，确保无论收到什么消息都会执行超时检测
            current_time = time.time()
            if self.last_rtv_subscribe_time > 0:  # 已发送过RTV订阅
                if current_time - self.last_rtv_subscribe_time > self.rtv_interval:
                    self.rtv_timeout_count += 1
                    self.log_signal.emit(f"[WS] RTV订阅超时 {self.rtv_timeout_count}/{self.max_rtv_timeout}")

                    # 超时3次后重发订阅
                    if self.rtv_timeout_count >= self.max_rtv_timeout and self.rtv_ids_cache:
                        self.log_signal.emit("[WS] 连续超时3次，重新发送RTV订阅...")
                        try:
                            resub_cmd = {"func": "rtv", "ids": self.rtv_ids_cache, "period": 0} #订阅间隔默认都按正常访问是的0
                            print(f"\n[DEBUG] 重订阅参数配置指令: {json.dumps(resub_cmd)}")
                            await self.websocket.send(json.dumps(resub_cmd))
                            self.log_signal.emit("[WS] RTV重订阅已发送")
                            self.last_rtv_subscribe_time = time.time()
                            self.rtv_timeout_count = 0
                        except Exception as e:
                            self.log_signal.emit(f"[WS] 重订阅失败: {e}")
            # ===== 独立的超时检测逻辑 - 结束 =====

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
        """启动定时请求rtv的定时器 - 已废弃，使用智能重订阅机制"""
        """
        原有的定时重发机制已注释掉
        现在使用基于超时检测的智能重订阅机制
        
        if self.rtv_timer:
            self.rtv_timer.cancel()

        async def _send_rtv_request():
            if self.websocket:
                try:
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
        """
        pass  # 方法已废弃，保留空实现
