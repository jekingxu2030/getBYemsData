


# # =============================

# from PyQt5.QtWidgets import (
#     QMainWindow,
#     QWidget,
#     QVBoxLayout,
#     QHBoxLayout,
#     QPushButton,
#     QLabel,
#     QTextEdit,
#     QTreeWidget,
#     QTreeWidgetItem,
#     QListWidget,
#     QListWidgetItem,
#     QLineEdit,
#     QSizePolicy,
#     QGraphicsDropShadowEffect,
# )
# from PyQt5.QtGui import QColor, QIcon, QFont, QIntValidator
# from PyQt5.QtCore import Qt, QTimer
# from emsContronl import ChargeDischargeController
# from connection import WebSocketWorker
# from data_processing import (
#     update_device_tree,
#     get_item_level,
#     get_rtv_ids_for_item,
#     update_data_list_by_ids,
# )
# from datetime import datetime


# class WebSocketClient(QMainWindow):
#     def __init__(self):
#         super().__init__()
#         self.ws_worker = None
#         self.device_info = {}
#         self.latest_rtv_data = {}

#         self.controller = ChargeDischargeController(log_callback=self.log)

#         self.update_timer = QTimer()
#         self.update_timer.timeout.connect(self.update_display)
#         self.update_timer.start(3000)

#         self.setWindowIcon(QIcon("./img/ems.png"))
#         self.initUI()

#     def initUI(self):
#         self.setWindowTitle("BY-EMS Monitoring System V1.0")
#         self.setGeometry(100, 100, 1600, 900)
#         self.setStyleSheet("QMainWindow { background-color: #f0f0f0; padding: 5px; }")
#         self.setGraphicsEffect(
#             QGraphicsDropShadowEffect(blurRadius=2, xOffset=2, yOffset=2)
#         )

#         central_widget = QWidget()
#         self.setCentralWidget(central_widget)
#         main_layout = QHBoxLayout(central_widget)
#         main_layout.setContentsMargins(0, 0, 0, 0)

#         # 左侧控件布局
#         left_panel = QWidget()
#         left_layout = QVBoxLayout(left_panel)
#         left_panel.setMaximumWidth(700)

#         self.device_tree = QTreeWidget()
#         self.device_tree.setHeaderLabels(["设备列表"])
#         self.device_tree.setStyleSheet("QTreeWidget { font-size: 14px; }")
#         left_layout.addWidget(self.device_tree)

#         self.token_input = QLineEdit()
#         self.token_input.setPlaceholderText("请输入 WebSocket Token")
#         left_layout.addWidget(self.token_input)

#         self.charging_time_input_start = QLineEdit()
#         self.charging_time_input_end = QLineEdit()
#         self.discharging_time_input_start = QLineEdit()
#         self.discharging_time_input_end = QLineEdit()
#         self.charging_soc_input = QLineEdit()
#         self.discharging_soc_input = QLineEdit()

#         for box in [
#             self.charging_time_input_start,
#             self.charging_time_input_end,
#             self.discharging_time_input_start,
#             self.discharging_time_input_end,
#         ]:
#             box.setValidator(QIntValidator(0, 23))
#             left_layout.addWidget(box)

#         for box in [self.charging_soc_input, self.discharging_soc_input]:
#             box.setValidator(QIntValidator(0, 100))
#             left_layout.addWidget(box)

#         self.log_text = QTextEdit()
#         self.log_text.setReadOnly(True)
#         left_layout.addWidget(self.log_text)

#         self.connect_btn = QPushButton("连接WebSocket")
#         self.disconnect_btn = QPushButton("断开连接")
#         self.refresh_btn = QPushButton("刷新数据")

#         self.connect_btn.clicked.connect(self.start_websocket)
#         self.disconnect_btn.clicked.connect(self.stop_websocket)
#         self.refresh_btn.clicked.connect(self.refresh_data)

#         button_layout = QHBoxLayout()
#         button_layout.addWidget(self.connect_btn)
#         button_layout.addWidget(self.disconnect_btn)
#         button_layout.addWidget(self.refresh_btn)
#         left_layout.addLayout(button_layout)

#         main_layout.addWidget(left_panel)

#         # 右侧数据显示
#         self.data_list = QListWidget()
#         self.data_list.setStyleSheet("QListWidget { font-size: 14px; }")
#         main_layout.addWidget(self.data_list)

#     def log(self, message):
#         current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#         self.log_text.append(f"{current_time} - {message}")

#     def start_websocket(self):
#         token = self.token_input.text()
#         self.ws_worker = WebSocketWorker(token)
#         self.ws_worker.message_signal.connect(self.handle_message)
#         self.ws_worker.log_signal.connect(self.log)
#         self.ws_worker.start()
#         self.disconnect_btn.setEnabled(True)
#         self.refresh_btn.setEnabled(True)
#         self.update_timer.start(1000)

#     def stop_websocket(self):
#         self.update_timer.stop()
#         if self.ws_worker:
#             self.ws_worker.stop()
#             self.ws_worker = None
#         self.connect_btn.setEnabled(True)
#         self.disconnect_btn.setEnabled(False)
#         self.refresh_btn.setEnabled(False)
#         self.log("WebSocket连接已断开")

#     def handle_message(self, data):
#         func_type = data.get("func")
#         if func_type == "menu":
#             self.device_info = update_device_tree(self.device_tree, data, self.log)
#         elif func_type == "rtv":
#             for item in data.get("data", []):
#                 self.latest_rtv_data[str(item.get("id"))] = item.get("value", "N/A")
#             current_item = self.device_tree.currentItem()
#             if current_item:
#                 level = get_item_level(current_item)
#                 rtv_ids = get_rtv_ids_for_item(
#                     current_item, level, self.device_tree, self.log
#                 )
#                 update_data_list_by_ids(
#                     self.data_list,
#                     rtv_ids,
#                     self.device_info,
#                     self.latest_rtv_data,
#                     self.log,
#                 )

#     def update_display(self):
#         try:
#             current_item = self.device_tree.currentItem()
#             if current_item:
#                 level = get_item_level(current_item)
#                 rtv_ids = get_rtv_ids_for_item(
#                     current_item, level, self.device_tree, self.log
#                 )
#                 update_data_list_by_ids(
#                     self.data_list,
#                     rtv_ids,
#                     self.device_info,
#                     self.latest_rtv_data,
#                     self.log,
#                 )

#             soc = float(self.latest_rtv_data.get("412001056", 0))
#             runModel = self.latest_rtv_data.get("412001051", 0)
#             charging_start = int(self.charging_time_input_start.text())
#             charging_end = int(self.charging_time_input_end.text())
#             discharging_start = int(self.discharging_time_input_start.text())
#             discharging_end = int(self.discharging_time_input_end.text())
#             soc_upper = float(self.charging_soc_input.text())
#             soc_lower = float(self.discharging_soc_input.text())

#             self.controller.monitor_charge_discharge(
#                 soc,
#                 charging_start,
#                 charging_end,
#                 discharging_start,
#                 discharging_end,
#                 soc_upper,
#                 soc_lower,
#                 runModel,
#             )
#         except Exception:
#             pass

#     def refresh_data(self):
#         self.log("手动刷新数据...")
#         if self.ws_worker and self.ws_worker.websocket:
#             self.latest_rtv_data.clear()
#             self.device_info.clear()
#             self.stop_websocket()
#             self.start_websocket()
#             self.log("已重新建立WebSocket连接")

#     def closeEvent(self, event):
#         self.stop_websocket()
#         event.accept()



# # ===================================
# from PyQt5.QtWidgets import (
#     QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
#     QTextEdit, QTreeWidget, QTreeWidgetItem, QListWidget, QListWidgetItem,
#     QLineEdit, QSizePolicy, QGraphicsDropShadowEffect
# )
# from PyQt5.QtGui import QColor, QIcon, QFont, QIntValidator
# from PyQt5.QtCore import Qt, QTimer
# from emsContronl import ChargeDischargeController
# from connection import WebSocketWorker
# from data_processing import (
#     update_device_tree,
#     get_item_level,
#     get_rtv_ids_for_item,
#     update_data_list_by_ids
# )
# from datetime import datetime


# class WebSocketClient(QMainWindow):
#     def __init__(self):
#         super().__init__()
#         self.ws_worker = None
#         self.device_info = {}
#         self.latest_rtv_data = {}

#         self.controller = ChargeDischargeController(log_callback=self.log)

#         self.update_timer = QTimer()
#         self.update_timer.timeout.connect(self.update_display)
#         self.update_timer.start(3000)

#         self.setWindowIcon(QIcon("./img/ems.png"))
#         self.initUI()

#     def initUI(self):
#         self.setWindowTitle('BY-EMS Monitoring System V1.0')
#         self.setGeometry(100, 100, 1600, 900)
#         self.setStyleSheet("QMainWindow { background-color: #f0f0f0; padding: 5px; }")
#         self.setGraphicsEffect(QGraphicsDropShadowEffect(blurRadius=2, xOffset=2, yOffset=2))

#         central_widget = QWidget()
#         self.setCentralWidget(central_widget)
#         main_layout = QHBoxLayout(central_widget)
#         main_layout.setContentsMargins(0, 0, 0, 0)

#         # 左侧控件布局
#         left_panel = QWidget()
#         left_layout = QVBoxLayout(left_panel)
#         left_panel.setMaximumWidth(700)

#         self.device_tree = QTreeWidget()
#         self.device_tree.setHeaderLabels(['设备列表'])
#         self.device_tree.setStyleSheet("QTreeWidget { font-size: 14px; }")
#         left_layout.addWidget(self.device_tree)

#         # 中部监控设置区域
#         settings_panel = QWidget()
#         settings_layout = QVBoxLayout(settings_panel)
#         settings_panel.setStyleSheet("background-color: #f0f0f0; border: 1px solid rgba(128, 128, 128, 0.1); padding: 10px;")

#         def styled_input(label_text, input_field):
#             label = QLabel(label_text)
#             label.setStyleSheet("color: #2196F3; font-weight: bold;")
#             input_field.setFixedWidth(450)
#             input_field.setStyleSheet("QLineEdit { background-color:rgba(255, 255, 255, 0.9); border: 1px solid #ccc; border-radius: 3px; padding: 3px; color: #2196F3; }")
#             row = QHBoxLayout()
#             row.addWidget(label)
#             row.addWidget(input_field)
#             row_widget = QWidget()
#             row_widget.setLayout(row)
#             return row_widget

#         self.token_input = QLineEdit()
#         self.token_input.setText("请输入最新token值")
#         settings_layout.addWidget(styled_input("WebSocket Token:", self.token_input))

#         self.charging_time_input_start = QLineEdit()
#         self.charging_time_input_end = QLineEdit()
#         self.discharging_time_input_start = QLineEdit()
#         self.discharging_time_input_end = QLineEdit()
#         self.charging_soc_input = QLineEdit()
#         self.discharging_soc_input = QLineEdit()

#         for box in [self.charging_time_input_start, self.charging_time_input_end,
#                     self.discharging_time_input_start, self.discharging_time_input_end]:
#             box.setValidator(QIntValidator(0, 23))

#         for box in [self.charging_soc_input, self.discharging_soc_input]:
#             box.setValidator(QIntValidator(0, 100))

#         settings_layout.addWidget(styled_input("充电时间(HH):", self.charging_time_input_start))
#         settings_layout.addWidget(styled_input("充电结束时间(HH):", self.charging_time_input_end))
#         settings_layout.addWidget(styled_input("放电时间(HH):", self.discharging_time_input_start))
#         settings_layout.addWidget(styled_input("放电结束时间(HH):", self.discharging_time_input_end))
#         settings_layout.addWidget(styled_input("充电SOC上限(%):", self.charging_soc_input))
#         settings_layout.addWidget(styled_input("放电SOC下限(%):", self.discharging_soc_input))

#         left_layout.addWidget(settings_panel)

#         self.log_text = QTextEdit()
#         self.log_text.setReadOnly(True)
#         self.log_text.setStyleSheet("QTextEdit { background-color: #f0f0f0; font-size: 12px; color: #333; border: 1px solid rgba(128, 128, 128, 0.1); border-radius: 5px; }")
#         left_layout.addWidget(self.log_text)

#         self.connect_btn = QPushButton("连接WebSocket")
#         self.disconnect_btn = QPushButton("断开连接")
#         self.refresh_btn = QPushButton("刷新数据")

#         self.connect_btn.clicked.connect(self.start_websocket)
#         self.disconnect_btn.clicked.connect(self.stop_websocket)
#         self.refresh_btn.clicked.connect(self.refresh_data)

#         self.connect_btn.setStyleSheet("""
#             QPushButton {
#                 background-color: #4CAF50;
#                 color: white;
#                 padding: 10px;
#                 border: none;
#                 border-radius: 5px;
#             }
#             QPushButton:hover { background-color: #45a049; }
#         """)
#         self.disconnect_btn.setStyleSheet("""
#             QPushButton {
#                 background-color: #f44336;
#                 color: white;
#                 padding: 10px;
#                 border: none;
#                 border-radius: 5px;
#             }
#             QPushButton:hover { background-color: #e53935; }
#         """)
#         self.refresh_btn.setStyleSheet("""
#             QPushButton {
#                 background-color: #2196F3;
#                 color: white;
#                 padding: 10px;
#                 border: none;
#                 border-radius: 5px;
#             }
#             QPushButton:hover { background-color: #1976D2; }
#         """)

#         button_layout = QHBoxLayout()
#         button_layout.addWidget(self.connect_btn)
#         button_layout.addWidget(self.disconnect_btn)
#         button_layout.addWidget(self.refresh_btn)
#         left_layout.addLayout(button_layout)

#         main_layout.addWidget(left_panel)

#         # 右侧数据显示
#         self.data_list = QListWidget()
#         self.data_list.setStyleSheet("QListWidget { font-size: 14px; background-color: #f0f0f0; border-radius: 5px; }")
#         main_layout.addWidget(self.data_list)

#     def log(self, message):
#         current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
#         self.log_text.append(f"{current_time} - {message}")

#     def start_websocket(self):
#         token = self.token_input.text()
#         self.ws_worker = WebSocketWorker(token)
#         self.ws_worker.message_signal.connect(self.handle_message)
#         self.ws_worker.log_signal.connect(self.log)
#         self.ws_worker.start()
#         self.connect_btn.setEnabled(False)
#         self.disconnect_btn.setEnabled(True)
#         self.refresh_btn.setEnabled(True)
#         self.update_timer.start(1000)

#     def stop_websocket(self):
#         self.update_timer.stop()
#         if self.ws_worker:
#             self.ws_worker.stop()
#             self.ws_worker = None
#         self.connect_btn.setEnabled(True)
#         self.disconnect_btn.setEnabled(False)
#         self.refresh_btn.setEnabled(False)
#         self.log("WebSocket连接已断开")

#     def handle_message(self, data):
#         func_type = data.get('func')
#         if func_type == "menu":
#             self.device_info = update_device_tree(self.device_tree, data, self.log)
#         elif func_type == "rtv":
#             for item in data.get("data", []):
#                 self.latest_rtv_data[str(item.get("id"))] = item.get("value", "N/A")
#             current_item = self.device_tree.currentItem()
#             if current_item:
#                 level = get_item_level(current_item)
#                 rtv_ids = get_rtv_ids_for_item(current_item, level, self.device_tree, self.log)
#                 update_data_list_by_ids(self.data_list, rtv_ids, self.device_info, self.latest_rtv_data, self.log)

#     def update_display(self):
#         try:
#             current_item = self.device_tree.currentItem()
#             if current_item:
#                 level = get_item_level(current_item)
#                 rtv_ids = get_rtv_ids_for_item(current_item, level, self.device_tree, self.log)
#                 update_data_list_by_ids(self.data_list, rtv_ids, self.device_info, self.latest_rtv_data, self.log)

#             soc = float(self.latest_rtv_data.get('412001056', 0))
#             runModel = self.latest_rtv_data.get('412001051', 0)
#             charging_start = int(self.charging_time_input_start.text())
#             charging_end = int(self.charging_time_input_end.text())
#             discharging_start = int(self.discharging_time_input_start.text())
#             discharging_end = int(self.discharging_time_input_end.text())
#             soc_upper = float(self.charging_soc_input.text())
#             soc_lower = float(self.discharging_soc_input.text())

#             self.controller.monitor_charge_discharge(
#                 soc, charging_start, charging_end,
#                 discharging_start, discharging_end,
#                 soc_upper, soc_lower, runModel
#             )
#         except Exception:
#             pass

#     def refresh_data(self):
#         self.log("手动刷新数据...")
#         if self.ws_worker and self.ws_worker.websocket:
#             self.latest_rtv_data.clear()
#             self.device_info.clear()
#             self.stop_websocket()
#             self.start_websocket()
#             self.log("已重新建立WebSocket连接")

#     def closeEvent(self, event):
#         self.stop_websocket()
#         event.accept()


# ========================================第三版
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QTreeWidget, QTreeWidgetItem, QListWidget, QListWidgetItem,
    QLineEdit, QSizePolicy, QGraphicsDropShadowEffect
)
from PyQt5.QtGui import QColor, QIcon, QFont, QIntValidator
from PyQt5.QtCore import Qt, QTimer
from emsContronl import ChargeDischargeController
from connection import WebSocketWorker
from data_processing import (
    update_device_tree,
    get_item_level,
    get_rtv_ids_for_item,
    update_data_list_by_ids
)
from datetime import datetime


class WebSocketClient(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ws_worker = None
        self.device_info = {}
        self.latest_rtv_data = {}

        self.controller = ChargeDischargeController(log_callback=self.log)

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(3000)

        self.setWindowIcon(QIcon("./img/ems.png"))
        self.initUI()

    def initUI(self):
        self.setWindowTitle('BY-EMS Monitoring System V1.0')
        self.setGeometry(100, 100, 1600, 900)
        self.setStyleSheet("QMainWindow { background-color: #f0f0f0; padding: 5px; }")
        self.setGraphicsEffect(QGraphicsDropShadowEffect(blurRadius=2, xOffset=2, yOffset=2))

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 左侧控件布局
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setMaximumWidth(700)

        self.device_tree = QTreeWidget()
        self.device_tree.setHeaderLabels(['设备列表'])
        self.device_tree.setStyleSheet("QTreeWidget { font-size: 14px; }")
        left_layout.addWidget(self.device_tree)

        # 中部监控设置区域
        settings_panel = QWidget()
        settings_layout = QVBoxLayout(settings_panel)
        settings_panel.setStyleSheet("background-color: #f0f0f0; border: 1px solid rgba(128, 128, 128, 0.1); padding: 10px;")

        def styled_input(label_text, input_field):
            label = QLabel(label_text)
            label.setStyleSheet("color: #2196F3; font-weight: bold;")
            input_field.setFixedWidth(150)
            input_field.setStyleSheet("QLineEdit { background-color:rgba(255, 255, 255, 0.9); border: 1px solid #ccc; border-radius: 3px; padding: 3px; color: #2196F3; }")
            row = QHBoxLayout()
            row.addWidget(label)
            row.addWidget(input_field)
            row_widget = QWidget()
            row_widget.setLayout(row)
            return row_widget

        self.token_input = QLineEdit()
        self.token_input.setText("请输入最新token值")
        token_layout = QHBoxLayout()
        token_label = QLabel("WebSocket Token:")
        token_label.setStyleSheet("color: #2196F3; font-weight: bold;")
        token_layout.addWidget(token_label)
        token_layout.addWidget(self.token_input)
        token_widget = QWidget()
        token_widget.setLayout(token_layout)
        settings_layout.addWidget(token_widget)

        self.charging_time_input_start = QLineEdit()
        self.charging_time_input_end = QLineEdit()
        self.discharging_time_input_start = QLineEdit()
        self.discharging_time_input_end = QLineEdit()
        self.charging_soc_input = QLineEdit()
        self.discharging_soc_input = QLineEdit()

        for box in [self.charging_time_input_start, self.charging_time_input_end,
                    self.discharging_time_input_start, self.discharging_time_input_end]:
            box.setValidator(QIntValidator(0, 23))

        for box in [self.charging_soc_input, self.discharging_soc_input]:
            box.setValidator(QIntValidator(0, 100))

        def double_input_row(label1, input1, label2, input2):
            row = QHBoxLayout()
            label1.setStyleSheet("color: #2196F3; font-weight: bold;")
            label2.setStyleSheet("color: #2196F3; font-weight: bold;")
            input1.setFixedWidth(100)
            input2.setFixedWidth(100)
            input1.setStyleSheet("QLineEdit { background-color:rgba(255, 255, 255, 0.9); border: 1px solid #ccc; border-radius: 3px; padding: 3px; color: #2196F3; }")
            input2.setStyleSheet("QLineEdit { background-color:rgba(255, 255, 255, 0.9); border: 1px solid #ccc; border-radius: 3px; padding: 3px; color: #2196F3; }")
            row.addWidget(label1)
            row.addWidget(input1)
            row.addSpacing(30)
            row.addWidget(label2)
            row.addWidget(input2)
            row_widget = QWidget()
            row_widget.setLayout(row)
            return row_widget

        settings_layout.addWidget(double_input_row(QLabel("充电开始时间(HH):"), self.charging_time_input_start,
                                                  QLabel("充电结束时间(HH):"), self.charging_time_input_end))
        settings_layout.addWidget(double_input_row(QLabel("放电开始时间(HH):"), self.discharging_time_input_start,
                                                  QLabel("放电结束时间(HH):"), self.discharging_time_input_end))
        settings_layout.addWidget(double_input_row(QLabel("充电SOC上限(%):"), self.charging_soc_input,
                                                  QLabel("放电SOC下限(%):"), self.discharging_soc_input))

        left_layout.addWidget(settings_panel)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("QTextEdit { background-color: #f0f0f0; font-size: 12px; color: #333; border: 1px solid rgba(128, 128, 128, 0.1); border-radius: 5px; }")
        left_layout.addWidget(self.log_text)

        self.connect_btn = QPushButton("连接WebSocket")
        self.disconnect_btn = QPushButton("断开连接")
        self.refresh_btn = QPushButton("刷新数据")

        self.connect_btn.clicked.connect(self.start_websocket)
        self.disconnect_btn.clicked.connect(self.stop_websocket)
        self.refresh_btn.clicked.connect(self.refresh_data)

        self.connect_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #45a049; }
        """)
        self.disconnect_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 10px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #e53935; }
        """)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 10px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #1976D2; }
        """)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.connect_btn)
        button_layout.addWidget(self.disconnect_btn)
        button_layout.addWidget(self.refresh_btn)
        left_layout.addLayout(button_layout)

        main_layout.addWidget(left_panel)

        # 右侧数据显示
        self.data_list = QListWidget()
        self.data_list.setStyleSheet("QListWidget { font-size: 14px; background-color: #f0f0f0; border-radius: 5px; }")
        main_layout.addWidget(self.data_list)

    def log(self, message):
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.log_text.append(f"{current_time} - {message}")

    def start_websocket(self):
        token = self.token_input.text()
        self.ws_worker = WebSocketWorker(token)
        self.ws_worker.message_signal.connect(self.handle_message)
        self.ws_worker.log_signal.connect(self.log)
        self.ws_worker.start()
        self.connect_btn.setEnabled(False)
        self.disconnect_btn.setEnabled(True)
        # self.refresh_btn.setEnabled(True)
        self.update_timer.start(1000)

    def stop_websocket(self):
        self.update_timer.stop()
        if self.ws_worker:
            self.ws_worker.stop()
            self.ws_worker = None
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.log("WebSocket连接已断开")

    def handle_message(self, data):
        func_type = data.get('func')
        if func_type == "menu":
            self.device_info = update_device_tree(self.device_tree, data, self.log)
        elif func_type == "rtv":
            for item in data.get("data", []):
                self.latest_rtv_data[str(item.get("id"))] = item.get("value", "N/A")
            current_item = self.device_tree.currentItem()
            if current_item:
                level = get_item_level(current_item)
                rtv_ids = get_rtv_ids_for_item(current_item, level, self.device_tree, self.log)
                update_data_list_by_ids(self.data_list, rtv_ids, self.device_info, self.latest_rtv_data, self.log)

    def update_display(self):
        try:
            current_item = self.device_tree.currentItem()
            if current_item:
                level = get_item_level(current_item)
                rtv_ids = get_rtv_ids_for_item(current_item, level, self.device_tree, self.log)
                update_data_list_by_ids(self.data_list, rtv_ids, self.device_info, self.latest_rtv_data, self.log)

            soc = float(self.latest_rtv_data.get('412001056', 0))
            runModel = self.latest_rtv_data.get('412001051', 0)
            charging_start = int(self.charging_time_input_start.text())
            charging_end = int(self.charging_time_input_end.text())
            discharging_start = int(self.discharging_time_input_start.text())
            discharging_end = int(self.discharging_time_input_end.text())
            soc_upper = float(self.charging_soc_input.text())
            soc_lower = float(self.discharging_soc_input.text())

            self.controller.monitor_charge_discharge(
                soc, charging_start, charging_end,
                discharging_start, discharging_end,
                soc_upper, soc_lower, runModel
            )
        except Exception:
            pass

    def refresh_data(self):
        self.log("手动刷新数据...")
        if self.ws_worker and self.ws_worker.websocket:
            self.latest_rtv_data.clear()
            self.device_info.clear()
            self.stop_websocket()
            self.start_websocket()
            self.log("已重新建立WebSocket连接")

    def closeEvent(self, event):
        self.stop_websocket()
        event.accept()
