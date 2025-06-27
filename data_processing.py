from PyQt5.QtWidgets import QTreeWidgetItem, QListWidgetItem
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtCore import Qt


# 数据处理工具模块
# 包含设备树更新、实时数据处理、数据解析等工具函数

def update_device_tree(tree_widget, data, log):
    """
    更新设备树控件
    参数：
    - tree_widget: QTreeWidget 设备树控件
    - data: dict 菜单数据
    - log: function 日志记录函数
    返回值：dict 设备信息映射表
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
    level = 0
    while item.parent():
        item = item.parent()
        level += 1
    return level


def get_rtv_ids_for_item(item, level, tree_widget, log):
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
