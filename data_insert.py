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
    # host="localhost",
    port=3306,
    # user="getBYemsData",
    # password="getBYemsData",
    # db="getBYemsData",
)

FIELD_ORDER_FILE = os.path.join(
    os.path.dirname(__file__), "数据库初始化处理", "field_order.txt"
)


# 加载字段顺序列表
def load_field_order() -> list:
    if not os.path.exists(FIELD_ORDER_FILE):
        logger.error(f"[字段顺序] 文件不存在: {FIELD_ORDER_FILE}")
        raise FileNotFoundError(FIELD_ORDER_FILE)
    with open(FIELD_ORDER_FILE, encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    logger.debug(f"[字段顺序] 加载字段 {len(lines)} 个")
    
    # 更新缓存管理器的期望字段数
    data_cache_manager.update_expected_count(len(lines))
    logger.debug(f"[缓存管理] 更新期望字段数为: {len(lines)}")
    
    return lines


async def save_realtime_data(
    rtv_data: list, timestamp: datetime, interval_seconds: int = 0
) -> bool:
    global _last_insert_time, _last_write_complete_time

    logger.debug(
        f"[入口] save_realtime_data 被调用，时间间隔限制: {interval_seconds}秒"
    )

    if not isinstance(rtv_data, list) or not rtv_data:
        logger.warning("[数据校验] 传入数据为空或格式不正确，写入终止")
        return False

    # 检查时间间隔
    if _last_insert_time:
        elapsed = (timestamp - _last_insert_time).total_seconds()
        remaining = interval_seconds - elapsed
        if remaining > 0:
            logger.info(f"[时间限制]间隔不足，跳过此次写入，还剩 {remaining:.1f} 秒")
            return "skipped"

    # 智能缓存合并逻辑
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
        
        await asyncio.get_event_loop().run_in_executor(
            None, _sync_save_data, data_dict, timestamp
        )
        
        # 写入成功后清空缓存
        data_cache_manager.clear_cache()
        _last_insert_time = timestamp
        
        # 记录写库完成时间并计算间隔
        current_time = datetime.now()
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


def _sync_save_data(data: Dict[str, Any], timestamp: datetime) -> None:
    # logger.debug("[数据库] 校验连接状态")
    # print("[DEBUD] [数据库] 校验连接状态")
    if not storage.is_connected():
        logger.warning("[数据库] 连接断开，尝试重新连接")
        # print("[DEBUD] [数据库] 连接断开，尝试重新连接")
        storage.connect()
        logger.info("[数据库] 重新连接成功")
        # print("[DEBUD] [数据库] 重新连接成功")

    field_order = load_field_order()
    if len(field_order) < 2:
        logger.error("[字段顺序] 字段顺序列表过短，终止写入")
        # print("[DEBUD] [字段顺序] 字段顺序列表过短，终止写入")
        raise RuntimeError("字段顺序太短，写入中止")

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
                
                
            logger.debug(f"[SQL构造] SQL语句: {sql[:5]}")
            # print(f"[SQL构造] SQL语句: {sql}")
            logger.debug(
                f"[SQL构造] 参数示例: {row_values[:10]} ... 共 {len(row_values)} 个字段"
            )
            # print(
            #     f"[SQL构造] 参数示例: {row_values[:10]} ... 共 {len(row_values)} 个字段"
            # )

            cur.execute(sql, row_values)
            storage.connection.commit()
            logger.info(f"[数据库] 成功插入 1 条宽表数据，字段数: {len(row_values)}")
            # print(f"\n[数据库] 成功插入 1 条宽表数据，字段数: {len(row_values)}")

    except Exception as e:
        storage.connection.rollback()
        logger.error(f"[数据库] 插入失败: {e}", exc_info=True)
        # print(f"[数据库] 插入失败: {e}")
        raise
