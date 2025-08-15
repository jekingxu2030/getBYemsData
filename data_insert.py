#     except Exception as e:
#         storage.connection.rollback()
#         logger.error(f"[数据库] 插入失败: {e}", exc_info=True)
#         print(f"[数据库] 插入失败: {e}")
#         raise


# --------------------4.0------------------
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import os
from mysql_storage import MySQLStorage

# 初始化日志器
logger = logging.getLogger("EMS_DataInsert")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False


# 全局上次插入时间
_last_insert_time: Optional[datetime] = None
# 全局上次写库完成时间
_last_write_complete_time: Optional[datetime] = None

# 智能缓存合并机制
class DataCacheManager:
    """管理RTV数据缓存和合并的智能缓存类"""
    
    def __init__(self):
        self.cache = {}  # 缓存数据 {rtv_id: value}
        self.cache_threshold = 0.8  # 80%订阅量触发写库（根据需求调整）
        self.total_expected = 159  # 期望的总字段数（从field_order获取）
        self.cache_hits = 0  # 缓存命中统计
        
    def update_expected_count(self, expected_count: int):
        """更新期望的总字段数"""
        self.total_expected = max(expected_count, 1)
        
    def add_data(self, rtv_data: list) -> int:
        """添加新数据到缓存，返回缓存中的数据量"""
        for item in rtv_data:
            if "id" in item and "value" in item:
                self.cache[item["id"]] = item["value"]
        return len(self.cache)
        
    def should_write_to_db(self) -> bool:
        """判断是否达到写库阈值"""
        cache_ratio = len(self.cache) / self.total_expected
        return cache_ratio >= self.cache_threshold
        
    def get_merged_data(self) -> list:
        """获取合并后的完整数据格式"""
        return [{"id": k, "value": v} for k, v in self.cache.items()]
        
    def clear_cache(self):
        """清空缓存（写库后调用）"""
        self.cache.clear()
        
    def get_cache_info(self) -> dict:
        """获取缓存状态信息"""
        return {
            "cached_items": len(self.cache),
            "expected_total": self.total_expected,
            "cache_ratio": f"{len(self.cache)/self.total_expected*100:.1f}%",
            "cache_hits": self.cache_hits
        }

# 创建缓存管理器实例
data_cache_manager = DataCacheManager()

# 连接数据库
storage = MySQLStorage(
    host="18.185.184.251",
    user="getbyemsdata",
    password="getbyemsdata",
    db="getbyemsdata",
    port=3306,
    
    # 本地数据库账户名不一样
    # host="localhost",
    # user="getBYemsData",
    # password="getBYemsData",
    # db="getBYemsData",
)

FIELD_ORDER_FILE = os.path.join(
    os.path.dirname(__file__), "数据库初始化处理", "field_order.txt"
)


# 加载字段顺序列表
# 新增：启动时加载字段顺序，缓存为全局变量
# 修改原有的load_field_order函数，增加缓存机制

# 全局字段顺序缓存
_global_field_order = None
_global_field_order_loaded = False

def load_field_order_once() -> list:
    """启动时只加载一次字段顺序，并缓存"""
    global _global_field_order, _global_field_order_loaded
    
    if _global_field_order_loaded and _global_field_order is not None:
        return _global_field_order
    
    if not os.path.exists(FIELD_ORDER_FILE):
        logger.error(f"[字段顺序] 文件不存在: {FIELD_ORDER_FILE}")
        raise FileNotFoundError(FIELD_ORDER_FILE)
    
    with open(FIELD_ORDER_FILE, encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    
    # 缓存字段顺序
    _global_field_order = lines
    _global_field_order_loaded = True
    
    # 更新缓存管理器的期望字段数
    data_cache_manager.update_expected_count(len(lines))
    
    logger.info(f"[字段顺序] 启动时加载字段 {len(lines)} 个，已缓存")
    return _global_field_order

# 启动时加载字段顺序
try:
    _global_field_order = load_field_order_once()
    logger.info(f"[初始化] 字段顺序已加载并缓存: {len(_global_field_order)} 个字段")
except Exception as e:
    logger.error(f"[初始化] 加载字段顺序失败: {e}")
    _global_field_order = []

# 修改原有的load_field_order函数，使用缓存版本
# 保留原函数用于向后兼容
def load_field_order() -> list:
    """兼容原有调用，实际使用缓存版本"""
    if _global_field_order is None:
        return load_field_order_once()
    return _global_field_order
    logger.debug(f"[字段顺序] 加载字段 {len(lines)} 个")
    
    # 更新缓存管理器的期望字段数
    data_cache_manager.update_expected_count(len(lines))
    logger.debug(f"[缓存管理] 更新期望字段数为: {len(lines)}")
    
    return lines


# 修改save_realtime_data函数，使用荷兰时间
# 原函数中使用的timestamp参数改为可选，默认使用荷兰时间

async def save_realtime_data(
    rtv_data: list, timestamp: datetime = None, interval_seconds: int = 0
) -> bool:
    global _last_insert_time, _last_write_complete_time

    # 使用荷兰时间作为默认时间
    if timestamp is None:
        timestamp = netherlands_time.get_netherlands_time()
    
    logger.debug(
        f"[入口] save_realtime_data 被调用，使用荷兰时间: {timestamp}, 时间间隔限制: {interval_seconds}秒"
    )

    if not isinstance(rtv_data, list) or not rtv_data:
        logger.warning("[数据校验] 传入数据为空或格式不正确，写入终止")
        return False

    # 检查时间间隔 - 使用荷兰时间
    if _last_insert_time:
        elapsed = (timestamp - _last_insert_time).total_seconds()
        remaining = interval_seconds - elapsed
        if remaining > 0:
            logger.info(f"[时间限制]间隔不足，跳过此次写入，还剩 {remaining:.1f} 秒")
            return "skipped"

    # 智能缓存合并逻辑（保持不变）
    try:
        # 添加新数据到缓存
        cached_count = data_cache_manager.add_data(rtv_data)
        cache_info = data_cache_manager.get_cache_info()
        
        logger.debug(f"[缓存管理] 当前缓存状态: {cache_info}")
        
        # 检查是否达到写库阈值（80%）
        if not data_cache_manager.should_write_to_db():
            cache_ratio = cached_count / data_cache_manager.total_expected
            logger.info(
                f"[缓存管理] 数据量不足({cached_count}/{data_cache_manager.total_expected}) "
                f"({cache_ratio:.1%}) - 阈值80%，已缓存等待下次合并"
            )
            data_cache_manager.cache_hits += 1
            return "cached"
        
        # 达到阈值，合并数据并写入数据库
        merged_data = data_cache_manager.get_merged_data()
        logger.info(
            f"[缓存管理] 达到写库阈值，合并 {len(merged_data)} 条数据写入数据库"
        )
        
        data_dict = {
            item["id"]: item["value"]
            for item in merged_data
            if "id" in item and "value" in item
        }
        
        # 使用荷兰时间写入数据库
        await asyncio.get_event_loop().run_in_executor(
            None, _sync_save_data, data_dict, timestamp
        )
        
        # 写入成功后清空缓存
        data_cache_manager.clear_cache()
        _last_insert_time = timestamp
        
        # 记录写库完成时间并计算间隔
        current_time = netherlands_time.get_netherlands_time()  # 使用荷兰时间
        if _last_write_complete_time:
            time_interval = (current_time - _last_write_complete_time).total_seconds()
            logger.info(f"[完成] 数据写入成功，上次写库间隔: {time_interval:.1f}秒")
        else:
            logger.info("[完成] 数据写入成功（首次写库）")
        
        _last_write_complete_time = current_time
        return True
        
    except Exception as e:
        logger.error(f"[异常] 数据写入失败: {e}", exc_info=True)
        return False


# 修改_sync_save_data函数，使用缓存的字段顺序
# 原函数中每次都调用load_field_order()，现在改为使用缓存

def _sync_save_data(data: Dict[str, Any], timestamp: datetime) -> None:
    # logger.debug("[数据库] 校验连接状态")
    # print("[DEBUD] [数据库] 校验连接状态")
    if not storage.is_connected():
        logger.warning("[数据库] 连接断开，尝试重新连接")
        # print("[DEBUD] [数据库] 连接断开，尝试重新连接")
        storage.connect()
        logger.info("[数据库] 重新连接成功")
        # print("[DEBUD] [数据库] 重新连接成功")

    # 使用缓存的字段顺序，避免重复文件读取
    field_order = _global_field_order
    if not field_order:
        logger.error("[字段顺序] 字段顺序未加载或为空，终止写入")
        return
    
    if len(field_order) < 2:
        logger.error("[字段顺序] 字段顺序列表过短，终止写入")
        # print("[DEBUD] [字段顺序] 字段顺序列表过短，终止写入")
        return

    # 使用荷兰时间格式化时间字符串
    record_time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        with storage.connection.cursor() as cur:
            columns =  load_field_order()[1:]  # 跳过前1个，保留record_time及之后

            placeholders = ", ".join(["%s"] * len(columns))
            sql = f"INSERT INTO device_data_summary ({', '.join([f'`{col}`' for col in columns])}) VALUES ({placeholders})"
 
            row_values = []
            for col in columns:
                if col == "record_time":
                    value = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                elif col == "productType":
                    value = "215户外柜"
                elif col == "projectName":
                    value = "BY-P01"
                else:
                    value = data.get(col, None)
                row_values.append(value)
            
            # === 简化的数据包信息打印 ===
            print(f"\n[数据写入] 荷兰时间: {timestamp.strftime('%Y-%m-%d %H:%M:%S')} | 字段数: {len(row_values)}")
            # =========================
                
            logger.debug(f"[SQL构造] SQL语句: {sql[:5]}")
            logger.debug(
                f"[SQL构造] 参数示例: {row_values[:10]} ... 共 {len(row_values)} 个字段"
            )

            cur.execute(sql, row_values)
            storage.connection.commit()
            logger.info(f"[数据库] 成功插入 1 条宽表数据，字段数: {len(row_values)}")

    except Exception as e:
        storage.connection.rollback()
        logger.error(f"[数据库] 插入失败: {e}", exc_info=True)
        raise


# --------------------4.0------------------
import configparser
import os

# 在文件开头添加配置读取
config = configparser.ConfigParser()
config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
# 使用with语句确保文件正确关闭
with open(config_path, 'r', encoding='utf-8') as f:
    config.read_file(f)

# 修正：荷兰时间同步模块 - 使用配置文件偏移值
class NetherlandsTimeSync:
    """荷兰时间同步器 - 优先使用配置文件偏移值，API作为备选"""
    
    def __init__(self):
        self.time_offset = None  # 偏移量（秒）
        self.use_api = config.getboolean('time', 'enable_api_time_sync', fallback=False)
        self.offset_hours = config.getfloat('time', 'netherlands_offset_hours', fallback=-6.0)
        
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
