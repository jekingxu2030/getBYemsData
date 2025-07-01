"""
data_insert.py
==============

数据写入 MySQL 的统一入口：
    from data_insert import save_realtime_data
    save_realtime_data(rtv_data)
"""

from datetime import datetime
from typing import Dict, Any
import json
from mysql_storage import MySQLStorage


def _ensure_table(storage: MySQLStorage) -> None:
    """若表不存在则自动创建"""
    ddl = """
    CREATE TABLE IF NOT EXISTS ems_realtime_data (
        data_id   VARCHAR(64) NOT NULL,
        value     JSON        NOT NULL,
        timestamp DATETIME    NOT NULL,
        PRIMARY KEY (data_id, timestamp)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    with storage.connection.cursor() as cur:
        cur.execute(ddl)
    storage.connection.commit()

storage = MySQLStorage() #保持数据库连接一直存在

def save_realtime_data(data: Dict[str, Any]) -> bool:
    """
    对外暴露的写库函数。返回 True/False 代表写入成功与否。
    """
    # print("insert收到完整JSON ↓")
    # print(json.dumps(data, indent=2, ensure_ascii=False))
    # print("len(str(data)) =", len(str(data)))                       # dict 转字符串后的长度
    raw = json.dumps(data, ensure_ascii=False)                      # 不缩进
    # print("len(json.dumps) =", len(raw))                            # 序列化后长度
    print("尾 200 字:", raw[-200:])    
    if not data:
        return False

    
    _ensure_table(storage)  # 保证表存在
    ok=1
    # ok = storage.store_data(data)
    # storage.close()  # 这里也可以不关，让上层决定
    return ok


# --- 简单自测 ---
if __name__ == "__main__":
    demo = {
        "1001": {"value": 23.5, "unit": "℃"},
        "1002": {"value": 45.2, "unit": "%"},
    }
    print("写入结果:", save_realtime_data(demo))
