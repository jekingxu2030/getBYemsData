# # test_store.py
# """
# 简单测试脚本：
# 1. 导入 MySQLStorage
# 2. 组织两条示例数据
# 3. 调用 store_data() 写入数据库
# 4. 打印返回结果
# """
# from datetime import datetime
# from mysql_storage import MySQLStorage  # ← 如果你的模块文件名不同，改这里


# def main():
#     # ① 构造测试数据
#     sample_data = {
#         "1001": {
#             "value": 23.5,
#             "unit": "℃",
#             "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#         },
#         "1002": {
#             "value": 45.2,
#             "unit": "%",
#             "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#         },
#     }

#     # ② 创建（或复用）数据库连接
#     storage = MySQLStorage()  # 你的单例保证不会重复连接

#     # ③ 写库并反馈
#     if storage.store_data(sample_data):
#         print("✅ 数据写入成功")
#     else:
#         print("❌ 数据写入失败")

#     # ④ 关闭连接（可选）
#     storage.close()


# if __name__ == "__main__":
#     main()


# ============================================
# test_store.py
from datetime import datetime
from mysql_storage import MySQLStorage


# ① 先确保表存在
def ensure_table(storage):
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


def main():
    storage = MySQLStorage()
    ensure_table(storage)  # ← 只在首次运行时真正建表

    sample_data = {
        "1001": {
            "value": 23.5,
            "unit": "℃",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "1002": {
            "value": 45.2,
            "unit": "%",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
    }

    ok = storage.store_data(sample_data)
    print("✅ 数据写入成功" if ok else "❌ 数据写入失败")
    storage.close()


if __name__ == "__main__":
    main()
