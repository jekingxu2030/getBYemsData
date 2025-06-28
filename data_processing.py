from PyQt5.QtWidgets import QTreeWidgetItem, QListWidgetItem
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtCore import Qt
from PyQt5.QtCore import pyqtSignal, QObject

# import logging
# from datetime import datetime
from mysql_storage import MySQLStorage  # Absolute import

"""
数据处理工具模块
================

本模块提供与EMS系统数据展示相关的各种处理功能，包括：
1. 设备树结构更新与维护
2. 实时数据解析与展示
3. 数据项层级关系处理

主要功能：
- update_device_tree: 构建设备树形结构
- get_item_level: 获取树形项层级
- get_rtv_ids_for_item: 提取实时数据ID
- update_data_list_by_ids: 按ID更新数据列表

依赖：
- PyQt5.QtWidgets
- PyQt5.QtGui
- PyQt5.QtCore
"""


# 新增数据处理模块信号
class DataProcessor(QObject):
    # 新增数据处理模块信号
    db_log_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()  # Ensure parent class initialized
        self.storage = MySQLStorage()
        self.storage.log_signal.connect(self._forward_db_log)

    def _forward_db_log(self, msg):
        # self.db_log_signal.emit(f"[存储模块] {msg}")
        self.db_log_signal.emit(f"[DB] {msg}")


def update_device_tree(tree_widget, data, log):
    """
    更新设备树控件

    功能：
    - 根据传入的菜单数据构建完整的设备树结构
    - 生成设备信息映射表用于后续数据查询

    参数：
    - tree_widget: QTreeWidget 设备树控件对象
    - data: dict 菜单数据，格式为：
        {
            "data": {
                "设备类型1": [设备1信息, 设备2信息...],
                "设备类型2": [...]
            }
        }
    - log: function 日志记录回调函数

    返回值：
    - dict: 设备信息映射表，结构为：
        {
            "数据项ID": {
                "name": "中文名称",
                "eng_name": "英文名称",
                "device_type": "设备类型",
                "device_name": "设备名称",
                "table_name": "表名"
            }
        }
    """
    tree_widget.clear()
    device_info = {}
    menu_data = data.get("data", {})

    for device_type, devices in menu_data.items():
        type_item = QTreeWidgetItem([device_type])
        tree_widget.addTopLevelItem(type_item)

        for device in devices:
            device_id = str(device["rtvList"][0]["id"]) if device.get("rtvList") else ""
            device_item = QTreeWidgetItem([f"{device_id} - {device.get('chnName')}"])
            device_item.setData(0, Qt.UserRole, device)

            for rtv_item in device.get("rtvList", []):
                item_id = str(rtv_item["id"])
                rtv_node = QTreeWidgetItem(
                    [f"{item_id} - {rtv_item.get('fieldChnName')}"]
                )
                device_item.addChild(rtv_node)

                device_info[item_id] = {
                    "name": rtv_item.get("fieldChnName", ""),
                    "eng_name": rtv_item.get("fieldEngName", ""),
                    "device_type": device_type,
                    "device_name": device.get("chnName", ""),
                    "table_name": device.get("tableName", ""),
                }

            type_item.addChild(device_item)
        type_item.setExpanded(True)

    log("设备树更新完成")
    return device_info


def get_item_level(item):
    """
    获取树形项的层级深度

    参数：
    - item: QTreeWidgetItem 树形项对象

    返回值：
    - int: 层级深度(0表示顶级项，1表示二级项，以此类推)
    """
    level = 0
    while item.parent():
        item = item.parent()
        level += 1
    return level


def get_rtv_ids_for_item(item, level, tree_widget, log):
    """
    根据树形项获取关联的实时数据ID列表

    参数：
    - item: QTreeWidgetItem 当前选中的树形项
    - level: int 当前项的层级(来自get_item_level)
    - tree_widget: QTreeWidget 树形控件对象
    - log: function 日志记录回调函数

    返回值：
    - list: 实时数据ID列表

    处理逻辑：
    - 层级0(顶级项): 获取该项下所有子设备的所有数据项ID
    - 层级1(设备项): 获取该设备下所有数据项ID
    - 层级2(数据项): 直接获取该项ID
    """
    ids = []
    try:
        if level == 0:
            for i in range(item.childCount()):
                dev_item = item.child(i)
                for j in range(dev_item.childCount()):
                    rtv_item = dev_item.child(j)
                    item_id = rtv_item.text(0).split(" - ")[0]
                    ids.append(int(item_id))
        elif level == 1:
            for i in range(item.childCount()):
                rtv_item = item.child(i)
                item_id = rtv_item.text(0).split(" - ")[0]
                ids.append(int(item_id))
        elif level == 2:
            item_id = item.text(0).split(" - ")[0]
            ids.append(int(item_id))
        log(f"提取了 {len(ids)} 个数据ID")
    except Exception as e:
        log(f"提取ID失败: {e}")
    return ids


def update_data_list_by_ids(data_list, rtv_ids, device_info, rtv_data, log):
    """
    根据ID列表更新数据显示列表

    参数：
    - data_list: QListWidget 数据展示列表控件
    - rtv_ids: list 实时数据ID列表
    - device_info: dict 设备信息映射表(来自update_device_tree)
    - rtv_data: dict 实时数据值，格式为{"ID": "值"}
    - log: function 日志记录回调函数

    功能：
    - 按设备类型分组显示数据
    - 为不同类型数据设置不同背景色
    - 格式化显示数据项ID、名称和当前值
    """
    data_list.clear()
    grouped = {"d_bms": [], "d_pcs": [], "d_grid": [], "d_air_condition": []}
    colors = {
        "d_bms": QColor(230, 230, 255),
        "d_pcs": QColor(255, 230, 230),
        "d_grid": QColor(255, 255, 230),
        "d_air_condition": QColor(230, 255, 230),
    }

    for item_id in rtv_ids:
        str_id = str(item_id)
        info = device_info.get(str_id)
        value = rtv_data.get(str_id, "N/A")
        if not info:
            continue
        dtype = info.get("device_type")
        if dtype in grouped:
            grouped[dtype].append((str_id, info, value))

    for dtype, items in grouped.items():
        if items:
            title = QListWidgetItem(f"==={dtype}===")
            title.setBackground(colors[dtype])
            data_list.addItem(title)

            for item_id, info, value in items:
                text = f"ID: {item_id:<12}  {info['name']:<30}  {value:<45}"
                entry = QListWidgetItem(text)
                entry.setFont(QFont("Courier New"))
                entry.setBackground(colors[dtype])
                data_list.addItem(entry)

    log(f"数据显示完成，共 {data_list.count()} 项")
