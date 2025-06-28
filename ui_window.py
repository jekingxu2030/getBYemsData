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
from data_processing import DataProcessor


class WebSocketClient(QMainWindow):
    """
    EMS监控系统界面模块
    包含主窗口类、界面组件初始化、事件处理等UI相关功能
    """

    def __init__(self):
        # 初始化父类
        super().__init__()
        # 初始化ws_worker
        self.ws_worker = None
        # 初始化device_info
        self.device_info = {}
        self.latest_rtv_data = {}

        # 初始化ChargeDischargeController，并传入log_callback参数
        self.controller = ChargeDischargeController(log_callback=self.log)

        # 初始化QTimer，并连接timeout信号到update_display槽函数
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        # 启动定时器，每隔3秒触发一次timeout信号
        self.update_timer.start(3000)

        # 数据处理模块消息传递 - 只保留这一处初始化
        self.data_processor = DataProcessor()
        self.data_processor.db_log_signal.connect(self.log)

        self.setWindowIcon(QIcon("./img/ems.png"))
        self.initUI()

    def initUI(self):
        """初始化界面布局和控件"""
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
        self.device_tree.setStyleSheet("QTreeWidget { font-size: 12px; }")
        self.device_tree.setStyleSheet(
            "QLineEdit { background-color:rgba(255, 255, 255, 0.9); border: 1px solid #ccc; border-radius: 3px; padding: 3px; color: #2196F3; }"
        )
        left_layout.addWidget(self.device_tree)

        # 中部监控设置区域
        settings_panel = QWidget()
        settings_layout = QVBoxLayout(settings_panel)
        settings_panel.setStyleSheet("background-color: #f0f0f0; border: 1px solid rgba(128, 128, 128, 0.1); padding: 10px;")

        # 定义一个函数，用于创建一个带有标签和输入框的行
        def styled_input(label_text, input_field):
            # 创建一个标签
            label = QLabel(label_text)
            # 设置标签的样式
            label.setStyleSheet("color: #2196F3; font-weight: bold;")
            # 设置输入框的宽度
            input_field.setFixedWidth(150)
            # 设置输入框的样式
            input_field.setStyleSheet("QLineEdit { background-color:rgba(255, 255, 255, 0.9); border: 1px solid #ccc; border-radius: 3px; padding: 3px; color: #2196F3; }")
            # 创建一个水平布局
            row = QHBoxLayout()
            # 将标签和输入框添加到水平布局中
            row.addWidget(label)
            row.addWidget(input_field)
            # 创建一个QWidget，并将水平布局设置为它的布局
            row_widget = QWidget()
            row_widget.setLayout(row)
            # 返回QWidget
            return row_widget

        self.token_input = QLineEdit()
        self.token_input.setText(
            "3d22c9d902d186e73c45998bd25c591a4d92ec0eb50951acc7878171a92ac09295d3540652fdcf0f44b828d9475e81bca5677687f2d9421d06632bd6cee25c81de3fa112ee3100ef84230ccf7b3824f3"
            # "63f0efd89ab8b6ab850b71ea5ec30c9b89af7999fee2592ca5a30ca2f098f684ac720bef95d7b7332b7031be375548da233dfc0e1b07187101b3cf38d658ba99d25d20b07e60fb5a7ea90b9c52cb5faa"
        )
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

        # 定义一个函数，用于创建一个包含两个标签和两个输入框的行
        def double_input_row(label1, input1, label2, input2):
            # 创建一个水平布局
            row = QHBoxLayout()
            # 设置第一个标签的样式
            label1.setStyleSheet("color: #2196F3; font-weight: bold;")
            # 设置第二个标签的样式
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

        # 初始化数据处理模块
        # self.data_processor = DataProcessor()
        # self.data_processor.db_log_signal.connect(self.log)

    def log(self, message):
        """
        日志记录方法
        参数：
        - message: 要记录的日志信息
        """
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.log_text.append(f"{current_time} - {message}")

    def start_websocket(self):
        # 获取输入框中的token
        token = self.token_input.text()
        # 创建WebSocketWorker对象，传入token
        self.ws_worker = WebSocketWorker(token)
        # 将WebSocketWorker对象的message_signal信号连接到handle_message槽函数
        self.ws_worker.message_signal.connect(self.handle_message)
        # 将WebSocketWorker对象的log_signal信号连接到log槽函数
        self.ws_worker.log_signal.connect(self.log)
        # 启动WebSocketWorker对象
        self.ws_worker.start()
        # 禁用连接按钮
        self.connect_btn.setEnabled(False)
        self.disconnect_btn.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        self.update_timer.start(1000)
        self.log("WebSocket已开始连接")
        self.log("数据更新已开启")

    def stop_websocket(self):
        # 停止更新定时器
        self.update_timer.stop()
        # 如果ws_worker存在，则停止ws_worker，并将ws_worker置为None
        if self.ws_worker:
            self.ws_worker.stop()
            self.ws_worker = None
        # 设置连接按钮为可用状态
        self.connect_btn.setEnabled(True)
        # 设置断开连接按钮为不可用状态
        self.disconnect_btn.setEnabled(False)
        # 设置刷新按钮为不可用状态
        self.refresh_btn.setEnabled(False)
        self.log("WebSocket连接已断开")

    def handle_message(self, data):
        # 获取消息中的函数类型
        func_type = data.get('func')
        # 如果函数类型为menu
        if func_type == "menu":
            # 更新设备树
            self.device_info = update_device_tree(self.device_tree, data, self.log)
        # 如果函数类型为rtv
        elif func_type == "rtv":
            # 遍历消息中的数据
            for item in data.get("data", []):
                self.latest_rtv_data[str(item.get("id"))] = item.get("value", "N/A")
            current_item = self.device_tree.currentItem()
            if current_item:
                level = get_item_level(current_item)
                rtv_ids = get_rtv_ids_for_item(current_item, level, self.device_tree, self.log)
                update_data_list_by_ids(self.data_list, rtv_ids, self.device_info, self.latest_rtv_data, self.log)

    def update_display(self):
        # 尝试更新显示
        try:
            # 获取当前选中的设备
            current_item = self.device_tree.currentItem()
            # 如果有选中的设备
            if current_item:
                # 获取设备等级
                level = get_item_level(current_item)
                # 获取设备的RTV ID
                rtv_ids = get_rtv_ids_for_item(current_item, level, self.device_tree, self.log)
                # 根据RTV ID更新数据列表
                update_data_list_by_ids(self.data_list, rtv_ids, self.device_info, self.latest_rtv_data, self.log)

            # 获取SOC值
            soc = float(self.latest_rtv_data.get('412001056', 0))
            # 获取运行模式
            runModel = self.latest_rtv_data.get('412001051', 0)
            # 获取充电开始时间
            charging_start = int(self.charging_time_input_start.text())
            # 获取充电结束时间
            charging_end = int(self.charging_time_input_end.text())
            # 获取放电开始时间
            discharging_start = int(self.discharging_time_input_start.text())
            # 获取放电结束时间
            discharging_end = int(self.discharging_time_input_end.text())
            # 获取充电SOC上限
            soc_upper = float(self.charging_soc_input.text())
            # 获取放电SOC下限
            soc_lower = float(self.discharging_soc_input.text())

            # 调用控制器进行充电放电监控
            self.controller.monitor_charge_discharge(
                soc, charging_start, charging_end,
                discharging_start, discharging_end,
                soc_upper, soc_lower, runModel
            )
        except Exception:
            # 如果发生异常，则忽略
            pass

    def refresh_data(self):
        # 手动刷新数据
        self.log("手动刷新数据...")
        # 如果ws_worker存在且websocket存在
        if self.ws_worker and self.ws_worker.websocket:
            # 清空latest_rtv_data
            # 清空device_info
            self.latest_rtv_data.clear()
            self.device_info.clear()
            # 停止websocket
            # self.stop_websocket()
            # self.start_websocket()
            self.ws_worker.request_refresh()
            self.log("已重新刷新WebSocket请求")

    # 重写closeEvent方法，当窗口关闭时调用
    def closeEvent(self, event):
        # 停止websocket连接
        self.stop_websocket()
        # 接受关闭事件
        event.accept()
        # 关闭窗口
        self.close()
