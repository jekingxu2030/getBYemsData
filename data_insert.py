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
    return lines


async def save_realtime_data(
    rtv_data: list, timestamp: datetime, interval_seconds: int = 30
) -> bool:
    global _last_insert_time

    logger.debug(
        # f"[入口] save_realtime_data 被调用，时间间隔限制: {interval_seconds}秒"
    )
    # print(f"\n[入口] save_realtime_data 被调用，时间间隔限制: {interval_seconds}秒")

    if not isinstance(rtv_data, list) or not rtv_data:
        logger.warning("[数据校验] 传入数据为空或格式不正确，写入终止")
        # print("[数据校验] 传入数据为空或格式不正确，写入终止")
        return False

    # if _last_insert_time and (timestamp - _last_insert_time) < timedelta(
    #     seconds=interval_seconds
    # ):
    #     logger.info("[时间限制] 间隔不足，跳过此次写入,还剩{}秒")
        # print("[DEBUD] [时间限制] 写入间隔不足，跳过此次写入")
    if _last_insert_time:
        elapsed = (timestamp - _last_insert_time).total_seconds()
        remaining = interval_seconds - elapsed
        if remaining > 0:
            logger.info(f"[时间限制]间隔不足，跳过此次写入，还剩 {remaining:.1f} 秒")
            return "skipped"

        # return "skipped"

    try:
        data_dict = {
            item["id"]: item["value"]
            for item in rtv_data
            if "id" in item and "value" in item
        }
        await asyncio.get_event_loop().run_in_executor(
            None, _sync_save_data, data_dict, timestamp
        )
        _last_insert_time = timestamp
        logger.info("[完成] 数据写入成功")
        # print("[DEBUD] [完成] 数据写入成功")
        return True
    except Exception as e:
        logger.error(f"[异常] 数据写入失败: {e}", exc_info=True)
        # print(f"\n[异常] 数据写入失败: {e}")
        return False


def _sync_save_data(data: Dict[str, Any], timestamp: datetime) -> None:
    logger.debug("[数据库] 校验连接状态")
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
