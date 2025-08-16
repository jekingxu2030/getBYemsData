# time_sync.py
import configparser
import os
import logging
from datetime import datetime, timedelta
import requests

# 初始化日志器
logger = logging.getLogger("EMS_TimeSync")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

class NetherlandsTimeSync:
    """荷兰时间同步器 - 优先使用配置文件偏移值，API作为备选"""
    
    def __init__(self):
        # 读取配置文件
        config = configparser.ConfigParser()
        config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config.read_file(f)
        except Exception as e:
            logger.error(f"[配置文件] 读取失败: {e}")
            config = None

        self.time_offset = None  # 偏移量（秒）
        self.use_api = config.getboolean('time', 'enable_api_time_sync', fallback=False) if config else False
        self.offset_hours = config.getfloat('time', 'netherlands_offset_hours', fallback=-6.0) if config else -6.0
        
    def sync_time_once(self) -> bool:
        """同步时间 - 优先使用配置文件，API作为备选"""
        try:
            if not self.use_api:
                # 使用配置文件中的固定偏移值
                self.time_offset = self.offset_hours * 3600  # 转换为秒
                logger.info(f"[时间同步] 使用配置文件偏移值: {self.offset_hours}小时 ({self.time_offset/3600:.1f}小时)")
                return True
                
            # API方式（保留作为备选）
            logger.info("[时间同步] 尝试API获取荷兰时间...")
            response = requests.get("https://worldtimeapi.org/api/timezone/Europe/Amsterdam", timeout=5)
            response.raise_for_status()
            
            data = response.json()
            netherlands_datetime_str = data["datetime"]
            netherlands_dt = datetime.fromisoformat(netherlands_datetime_str)
            netherlands_naive = netherlands_dt.replace(tzinfo=None)
            
            local_now = datetime.now()
            self.time_offset = (netherlands_naive - local_now).total_seconds()
            
            logger.info(f"[时间同步] API获取成功，偏移量: {self.time_offset/3600:.1f}小时")
            return True
            
        except Exception as e:
            # API失败时使用配置文件偏移值
            logger.warning(f"[时间同步] API失败，使用配置文件偏移值: {e}")
            self.time_offset = self.offset_hours * 3600
            logger.info(f"[时间同步] 使用配置文件偏移值: {self.offset_hours}小时")
            return False
    
    def get_netherlands_time(self) -> datetime:
        """获取当前荷兰时间"""
        if self.time_offset is None:
            self.sync_time_once()
        
        # 基于配置文件的偏移量计算荷兰时间
        local_now = datetime.now()
        netherlands_now = local_now + timedelta(seconds=self.time_offset or 0)
        
        # 添加调试打印，验证时间计算
        print(f"[时间调试] 本地时间: {local_now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"[时间调试] 偏移值: {self.time_offset/3600:.1f}小时")
        print(f"[时间调试] 荷兰时间: {netherlands_now.strftime('%Y-%m-%d %H:%M:%S')}")
        
        return netherlands_now

# 创建荷兰时间同步器实例
netherlands_time = NetherlandsTimeSync()

# 启动时同步时间
netherlands_time.sync_time_once()