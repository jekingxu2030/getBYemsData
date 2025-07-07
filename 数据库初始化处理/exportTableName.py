import pymysql

conn = pymysql.connect(
    host="localhost",
    port=3306,
    user="getBYemsData",
    password="getBYemsData",
    db="getbyemsdata",
    charset="utf8mb4",
)

try:
    with conn.cursor() as cursor:
        cursor.execute("SHOW COLUMNS FROM device_data_summary")
        columns = [row[0] for row in cursor.fetchall()]
        print(columns)  # ✅ 控制台输出字段列表
        # 保存为本地文件：
        with open("field_order.txt", "w", encoding="utf-8") as f:
            for col in columns:
                f.write(col + "\n")
finally:
    conn.close()
