

# if __name__ == "__main__":
#     insert_air_condition(JSON_FILE)
import json
import logging
from pathlib import Path
from mysql.connector import connect, Error


# 构建文件路径
# JSON_FILE = Path(__file__).parent / "ws_json_dump" / "ACD.json"  #--空调导入
# JSON_FILE = Path(__file__).parent / "ws_json_dump" / "PCS.json"    #--PCS导入
# JSON_FILE = Path(__file__).parent / "ws_json_dump" / "BMS.json"    #--BMS导入
JSON_FILE = Path(__file__).parent / "ws_json_dump" / "Meter.json"    #--电表导入


def load_json_file(json_path: Path):
    # 判断路径是否存在
    if not json_path.exists():
        print(f"❌ 文件不存在: {json_path}")
        return None
    if not json_path.is_file():
        print(f"❌ 路径不是文件: {json_path}")
        return None

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            print(f"✅ JSON 文件加载成功，共有键：{len(data)}")
            return data
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解码失败: {e}")
    except Exception as e:
        print(f"❌ 加载文件时出错: {e}")

    return None


# 调用方法
if __name__ == "__main__":
    data = load_json_file(JSON_FILE)
    if data is not None:
        print("👍 JSON 已成功导入并解析！")
    else:
        print("⚠️ JSON 导入失败")


# ========= 基本配置 =========
DB_CONFIG = dict(
    host="127.0.0.1",
    user="getBYemsData",
    password="getBYemsData",
    database="getBYemsData",
    charset="utf8mb4",
)

# TABLE = "device_air_condition"
# TABLE = "device_pcs"
# TABLE = "device_bms"
TABLE = "device_meter"
TOP_KEYS = [
    "dispIdx",
    "chnName",
    "engName",
    "tableId",
    "tableName",
    "tableChnName",
    "tableEngName",
]

# ========= 日志 =========
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
)
log = logging.getLogger(__name__)


# ========= 主处理 =========
def import_acd(json_path: Path):
    if not json_path.exists():
        log.error(f"JSON 文件不存在：{json_path}")
        return

    data = json.loads(json_path.read_text(encoding="utf-8"))
    # records = data.get("d_air_condition", [])
    # records = data.get("d_pcs", [])
    # records = data.get("d_bms", [])
    records = data.get("d_grid", [])

    try:
        conn = connect(**DB_CONFIG)
        cur = conn.cursor()
        log.info("✅ 已连接数据库")
    except Error as e:
        log.error(f"❌ 无法连接数据库：{e}")
        return

    processed = 0
    try:
        for dev in records:
            device_id = dev["id"]
            log.info(f"→ 处理设备 #{device_id}")

            # 1) 确保行存在
            cur.execute(
                f"INSERT IGNORE INTO {TABLE}(device_id) VALUES(%s)", (device_id,)
            )

            # 2) 一次性更新第一层字段
            set_frag = ", ".join(f"`{k}`=%s" for k in TOP_KEYS if k in dev)
            set_values = [dev[k] for k in TOP_KEYS if k in dev]
            if set_frag:
                cur.execute(
                    f"UPDATE {TABLE} SET {set_frag} WHERE device_id=%s",
                    (*set_values, device_id),
                )

            for item in dev.get("rtvList", []):
                col_name = f"`{item['id']}`"  # 结果形如 `413001051`
                json_val = json.dumps(item, ensure_ascii=False)

                # 打印值的长度信息（字符长度 + 字节长度）
                print(f"[调试] 列 {col_name} 的 JSON 长度：{len(json_val)} 字符，{len(json_val.encode('utf-8'))} 字节")
                print(f"[调试] JSON 内容示例：{json_val[:300]}...")  # 截取前100字符看看

                # 触发错误前的插入尝试
                cur.execute(
                  f"UPDATE {TABLE} SET {col_name}=%s WHERE device_id=%s",
                  (json_val, device_id),
              )

            processed += 1

        conn.commit()
        log.info(f"🏁 完成，已处理 {processed} 台设备。")
    except Exception as e:
        conn.rollback()
        log.error(f"❌ 出错已回滚：{e}")
        raise
    finally:
        cur.close()
        conn.close()
        log.info("🔌 数据库连接已关闭")


# ========= CLI =========
if __name__ == "__main__":
    import_acd(JSON_FILE)
