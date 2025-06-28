

# ===========================================
# mysql_storage.py
import json
import logging
from datetime import datetime
from typing import Dict, Any

import pymysql
from pymysql.cursors import DictCursor
from PyQt5.QtCore import QObject, pyqtSignal


class MySQLStorage(QObject):
    """
    MySQL 数据库存储模块（线程内单例）

    用法示例：
        from mysql_storage import MySQLStorage
        storage = MySQLStorage()
        storage.store_data({...})
        storage.close()
    """

    log_signal = pyqtSignal(str)

    # ---------- 单例实现 ----------
    _instance = None
    _is_init = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # ---------- 初始化 ----------
    def __init__(
        self,
        host: str = "localhost",
        port: int = 3306,
        user: str = "getBYemsData",
        password: str = "getBYemsData",
        db: str = "getBYemsData",
        charset: str = "utf8mb4",
        reconnect_retry: int = 3,  # ping 失败后的自动重连次数
    ):
        if MySQLStorage._is_init:  # 保证只初始化一次
            return
        super().__init__()

        # 基本连接参数
        self.host = host
        self.port = int(port)
        self.user = user
        self.password = password
        self.db = db
        self.charset = charset
        self._reconnect_retry = reconnect_retry
        self.connection = None

        # 配置 logger（仅一次）
        self.logger = logging.getLogger("EMS_MySQL")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            )
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
            self.logger.propagate = False

        self.connect()
        MySQLStorage._is_init = True

    # ---------- 连接 ----------
    def connect(self) -> None:
        if self.connection:  # 已连接则跳过
            return
        try:
            self.connection = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                db=self.db,
                charset=self.charset,
                cursorclass=DictCursor,
            )
            msg = "MySQL 数据库连接成功"
            self.logger.info(msg)
            self.log_signal.emit(msg)
        except Exception as e:
            msg = f"MySQL 数据库连接失败: {e}"
            self.logger.error(msg)
            self.log_signal.emit(msg)
            self.connection = None

    # ---------- 连接检查 ----------
    def is_connected(self) -> bool:
        if not self.connection:
            return False
        try:
            self.connection.ping(reconnect=True)
            return True
        except Exception:
            # 自动重连
            for _ in range(self._reconnect_retry):
                self.connect()
                if self.connection:
                    return True
            return False

  
    #         return False
    def store_data(self, data: Dict[str, Any]) -> bool:

        if not self.is_connected():
            self.logger.error("数据库未连接，无法存储数据")
            return False

        try:
            with self.connection.cursor() as cursor:
                sql = (
                    "INSERT INTO ems_realtime_data "
                    "(data_id, value, timestamp) "
                    "VALUES (%(id)s, %(value)s, %(timestamp)s)"
                )
                batch = []
                for k, v in data.items():
                    ts = v.get("timestamp")
                    if isinstance(ts, str):
                        timestamp_str = ts
                    else:
                        timestamp_str = (ts or datetime.now()).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                    item = {
                        "id": k,
                        "value": json.dumps(v, ensure_ascii=False),
                        "timestamp": timestamp_str,
                    }
                    batch.append(item)

                cursor.executemany(sql, batch)
            self.connection.commit()
            msg = f"成功存储 {len(batch)} 条数据"
            self.logger.info(msg)
            self.log_signal.emit(msg)
            return True

        except Exception as e:
            self.connection.rollback()
            msg = f"数据存储失败: {e}"
            self.logger.error(msg)
            self.log_signal.emit(msg)
            return False

    # ---------- 刷新 ----------

    # ---------- 关闭 ----------
    def close(self) -> None:
        if self.connection:
            self.connection.close()
            self.connection = None
            MySQLStorage._is_init = False
            msg = "MySQL 数据库连接已关闭"
            self.logger.info(msg)
            self.log_signal.emit(msg)
