# import json
# import mysql.connector
# from pathlib import Path
# import logging

# # ---------- 配置 ----------
# DB = dict(
#     host="127.0.0.1",
#     user="getBYemsData",
#     password="getBYemsData",
#     database="getBYemsData",
#     charset="utf8mb4",
# )

# JSON_DIR = Path(__file__).parent / "ws_json_dump"  # 4 个菜单 JSON 均放这里
# FILE_MAP = {  # 文件名 → 对应 device 表
#     "ACD.json": "device_air_condition",
#     "BMS.json": "device_bms",
#     "METER.json": "device_meter",
#     "PCS.json": "device_pcs",
# }

# logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
# log = logging.getLogger(__name__)


# def load_id_dict():
#     rows = []
#     for fname, tbl in FILE_MAP.items():
#         fpath = JSON_DIR / fname
#         if not fpath.exists():
#             log.warning(f"缺少 {fname}，跳过")
#             continue

#         data = json.loads(fpath.read_text(encoding="utf-8"))
#         # 菜单包顶层键与表名基本同名，这里取第一层列表
#         key = next(k for k in data.keys() if k.startswith("d_"))
#         for dev in data[key]:  # 每台设备
#             for item in dev.get("rtvList", []):
#                 rows.append(
#                     (
#                         item["id"],
#                         tbl,
#                         item.get("fieldName"),
#                         item.get("fieldChnName"),
#                         item.get("fieldEngName"),
#                         item.get("valueType"),
#                         item.get("dispType"),
#                     )
#                 )
#     return rows


# def insert_rows(rows):
#     conn = mysql.connector.connect(**DB)
#     cur = conn.cursor()
#     sql = """INSERT INTO id_list
#              (field_id, device_tbl, field_name, field_chn_name, field_eng_name, value_type, disp_type)
#              VALUES (%s,%s,%s,%s,%s,%s,%s)
#              ON DUPLICATE KEY UPDATE
#                field_name=VALUES(field_name),
#                field_chn_name=VALUES(field_chn_name),
#                field_eng_name=VALUES(field_eng_name),
#                value_type=VALUES(value_type),
#                disp_type=VALUES(disp_type)"""
#     cur.executemany(sql, rows)
#     conn.commit()
#     log.info(f"已写入 / 更新 {cur.rowcount} 条字典记录")
#     cur.close()
#     conn.close()


# if __name__ == "__main__":
#     all_rows = load_id_dict()
#     if all_rows:
#         insert_rows(all_rows)
#     else:
#         log.error("未找到任何菜单 JSON，未执行写入")


# ----------------------------------第二版
import json
import mysql.connector
from pathlib import Path
import logging

# ---------- 配置 ----------
DB = dict(
    host="127.0.0.1",
    user="getBYemsData",
    password="getBYemsData",
    database="getBYemsData",
    charset="utf8mb4",
)

JSON_DIR = Path(__file__).parent / "ws_json_dump"
FILE_MAP = {
    "ACD.json": "device_air_condition",
    "BMS.json": "device_bms",
    "METER.json": "device_meter",
    "PCS.json": "device_pcs",
}

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


# ---------- 1. 解析所有 JSON ----------
def iter_items():
    """
    逐条产出 (device_tbl, item_dict)；
    item_dict 就是 JSON 中的字段对象。
    """
    for fname, dev_tbl in FILE_MAP.items():
        fpath = JSON_DIR / fname
        if not fpath.exists():
            log.warning(f"缺少 {fname}，跳过")
            continue

        data = json.loads(fpath.read_text(encoding="utf-8"))
        # 菜单包顶层 key 形如 d_grid / d_acd ...
        key = next(k for k in data.keys() if k.startswith("d_"))
        for dev in data[key]:
            for item in dev.get("rtvList", []):
                yield dev_tbl, item


# ---------- 2. 动态生成 INSERT ----------
def gen_sql_and_rows():
    """
    根据 id_dict 表的列，拼接 INSERT ... ON DUPLICATE KEY UPDATE
    保证脚本与表结构同步；若表增列，脚本无需改。
    """
    conn = mysql.connector.connect(**DB)
    cur = conn.cursor()

    cur.execute("SHOW COLUMNS FROM id_list")  # 若表名不同请改
    cols = [row[0] for row in cur.fetchall()]

    # 生成 (%s, %s, ...)，同时构造 ON DUPLICATE KEY UPDATE
    placeholders = ",".join(["%s"] * len(cols))
    updates = ",".join([f"{c}=VALUES({c})" for c in cols if c != "field_id"])
    sql = (
        f"INSERT INTO id_list ({','.join(cols)}) VALUES ({placeholders}) "
        f"ON DUPLICATE KEY UPDATE {updates}"
    )

    rows = []
    for dev_tbl, item in iter_items():
        row = []
        for col in cols:
            if col == "device_tbl":
                row.append(dev_tbl)
            elif col == "field_id":
                row.append(item.get("id"))
            else:
                # JSON 键名与列名一致或下划线 ↔ 驼峰差异
                json_key = col
                if col in (
                    "table_id",
                    "row_id",
                    "his_period",
                    "his_idx",
                    "disp_type",
                    "value_type",
                    "ref_xid",
                ):
                    # 列名是蛇形 JSON 是驼峰
                    parts = col.split("_")
                    json_key = parts[0] + "".join(p.title() for p in parts[1:])

                row.append(item.get(json_key))
        rows.append(tuple(row))

    cur.executemany(sql, rows)
    conn.commit()
    log.info(f"已写入 / 更新 {cur.rowcount} 条记录")
    cur.close()
    conn.close()


if __name__ == "__main__":
    gen_sql_and_rows()
