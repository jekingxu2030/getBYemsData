

# ===========================================
# mysql_storage.py
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any
import configparser
import os

import pymysql
from pymysql.cursors import DictCursor
from PyQt5.QtCore import QObject, pyqtSignal

# 导入荷兰时间同步器
from time_sync import netherlands_time


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
        config_file: str = "config.ini",
        charset: str = "utf8mb4",
        reconnect_retry: int = 3,  # ping 失败后的自动重连次数
    ):
        if MySQLStorage._is_init:  # 保证只初始化一次
            return
        super().__init__()

        # 先初始化logger，避免在_load_config中使用未初始化的logger
        self._init_logger()
        
        # 从配置文件读取数据库配置
        self.config = self._load_config(config_file)
        
        # 基本连接参数
        self.host = self.config.get("host", "localhost")
        self.port = int(self.config.get("port", 3306))
        self.user = self.config.get("user", "getBYemsData")
        self.password = self.config.get("password", "getBYemsData")
        self.db = self.config.get("db", "getBYemsData")
        self.charset = charset
        self._reconnect_retry = reconnect_retry
        self.connection = None

        self.connect()
        MySQLStorage._is_init = True

    def _init_logger(self):
        """初始化日志记录器"""
        self.logger = logging.getLogger("EMS_MySQL")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            )
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
            self.logger.propagate = False

    def _load_config(self, config_file: str) -> Dict[str, str]:
        """从配置文件加载数据库配置"""
        config = configparser.ConfigParser()
        config_path = os.path.join(os.path.dirname(__file__), config_file)
        
        # 默认配置
        default_config = {
            "host": "localhost",
            "port": "3306",
            "user": "getBYemsData",
            "password": "getBYemsData",
            "db": "getBYemsData"
        }
        
        try:
            if os.path.exists(config_path):
                config.read(config_path, encoding='utf-8')
                
                # 从database section读取配置
                if 'database' in config:
                    db_config = dict(config['database'])
                    # 清理引号和逗号
                    for key, value in db_config.items():
                        db_config[key] = value.strip('"\'').rstrip(',')
                    
                    # 合并默认配置
                    default_config.update(db_config)
                    self.logger.info(f"成功从 {config_file} 加载数据库配置")
                else:
                    self.logger.warning(f"配置文件 {config_file} 中未找到 [database] 部分，使用默认配置")
            else:
                self.logger.warning(f"配置文件 {config_file} 不存在，使用默认配置")
                
        except Exception as e:
            # 使用print作为备选，因为此时logger可能有问题
            print(f"读取配置文件失败: {e}，使用默认配置")
            
        return default_config

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
            msg = f"MySQL 数据库连接成功 - 服务器: {self.host}:{self.port}, 数据库: {self.db}, 用户: {self.user}"
            self.logger.info(msg)
            self.log_signal.emit(msg)
            print(msg)  # 同时输出到控制台
        except Exception as e:
            msg = f"MySQL 数据库连接失败 - 服务器: {self.host}:{self.port}, 数据库: {self.db}, 用户: {self.user}, 错误: {e}"
            self.logger.error(msg)
            self.log_signal.emit(msg)
            print(msg)  # 同时输出到控制台
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

    # ---------- 存储数据 ----------
    def store_data(self, data: Dict[str, Any]) -> bool:

        if not self.is_connected():
            self.logger.error("数据库未连接，无法存储数据")
            return False

        try:
            with self.connection.cursor() as cursor:
                sql = (
                    "INSERT INTO ems_realtime_data "
                    "(data_id, value, timestamp, netherlands_timestamp) "
                    "VALUES (%(id)s, %(value)s, %(timestamp)s, %(netherlands_timestamp)s)"
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
                    # 获取荷兰时间
                    netherlands_now = netherlands_time.get_netherlands_time()
                    netherlands_timestamp_str = netherlands_now.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    item = {
                        "id": k,
                        "value": json.dumps(v, ensure_ascii=False),
                        "timestamp": timestamp_str,
                        "netherlands_timestamp": netherlands_timestamp_str,
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

    # ---------- 关闭 ----------
    def close(self) -> None:
        if self.connection:
            self.connection.close()
            self.connection = None
            MySQLStorage._is_init = False
            msg = "MySQL 数据库连接已关闭"
            self.logger.info(msg)
            self.log_signal.emit(msg)
