from re import S
import sys
import json
import asyncio
import websockets
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QPushButton, QLabel, QTextEdit, 
                           QTreeWidget, QTreeWidgetItem, QListWidget, QListWidgetItem,
                           QHeaderView, QGraphicsDropShadowEffect, QLineEdit, QSizePolicy)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QColor, QIcon, QFont,QIntValidator, QDoubleValidator
# import traceback
from emsContronl import ChargeDischargeController  # 导入监控控制器

# EMS监控系统客户端主窗口类
class WebSocketClient(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ws_worker = None  # WebSocket工作线程实例
        self.device_info = {}  # 设备ID和名称的映射关系
        self.latest_rtv_data = {}  # 存储最新的rtv数据

        self.log_text = QTextEdit(self)
        self.log_text.setReadOnly(True)  # 设置为只读
        # 添加定时器，每秒更新一次显示
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(3000)  # 1000毫秒 = 1秒

        # 设置窗口图标
        icon_path = "./img/ems.png"  # 图标文件路径
        try:
            self.setWindowIcon(QIcon(icon_path))
        except Exception as e:
            self.log(f"设置窗口图标失败: {str(e)}")

        self.initUI()  # 初始化UI

        self.controller = ChargeDischargeController(log_callback=self.log)  # 创建监控控制器实例

        self.device_tree.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # 禁止横向滚动条

        # self.setup_input_validations()  # 设置输入验证

        # self.connect_btn.setEnabled(False)
        # self.disconnect_btn.setEnabled(False)
        # self.refresh_btn.setEnabled(False)
        # self.disconnect_btn.setStyleSheet(" color: darkgray;")  # 禁用状态样式
        # self.refresh_btn.setStyleSheet("color: darkgray;")  # 禁用状态样式

    # 初始化UI
    def initUI(self):
        self.setWindowTitle('BY-EMS Monitoring System V1.0')  # 设置窗口标题
        self.setGeometry(100, 100, 1600, 900)  # 设置窗口大小

        # 添加窗口边框样式的设置 rgba(255, 255, 255, 0.8)
        self.setStyleSheet("QMainWindow { border: 0px solid red; border-radius: 0px; background-color: #f0f0f0; padding: 5px;}")  # 设置边框样式
        self.setGraphicsEffect(QGraphicsDropShadowEffect(blurRadius=2, xOffset=2, yOffset=2))  # 添加阴影效果

        # === 创建中心部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)  # 设置左、上、右、下边距为10像素

        # === 创建左侧面板gin
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 2, 5, 5)
        left_panel.setMaximumWidth(700)
        # 设置左侧面板背景颜色
        left_panel.setStyleSheet("""
            QWidget { background-color: #f0f0f0;  border-radius: 5px;}
        """)  # 设置为浅灰色背景

        # 添加标签
        top_left_label = QLabel('设备列表', self)  # 创建标签
        top_left_label.setStyleSheet("""
             font-size: 14px;
             font-weight: bold;
             color: #2196F3;
             margin: 0px;
             padding: 10px;
         """)  # 设置标签样式

        # left_layout.addWidget(top_left_label)  # 将标签添加到布局中

        # 设置数据菜单栏
        self.device_tree = QTreeWidget(self)  # 设备树控件
        self.device_tree.setHeaderLabels(['设备列表'])  # 设备树标题
        self.device_tree.setMaximumWidth(700)
        self.device_tree.setMinimumHeight(int(self.height() * 0.15))  # 设置监控设置栏高度为15%
        self.device_tree.setStyleSheet("""
            QTreeWidget {
                 background-color: rgba(255, 255, 255, 0);
                font-size: 14px;
                border: 1px solid rgba(128, 128, 128, 0.1);
                border-radius: 5px;
                color: #2196F3;
                
            }
            QHeaderView::section {
                color: #2196F3;  /* 设置标题文本颜色 */
                font-weight: bold;  /* 设置标题文本加粗 */
                border: 0px solid red;         
                padding-left:20px ;
                padding-top:30px ;
               
            }
        """)
        left_layout.addWidget(self.device_tree)  # 添加数据菜单栏        

        # === 创建监控设置栏
        monitoring_settings_panel = QWidget()
        monitoring_settings_layout = QVBoxLayout(monitoring_settings_panel)
        monitoring_settings_layout.setContentsMargins(10, 10, 10, 10)  # 设置内容边距为0像素
        monitoring_settings_panel.setStyleSheet("""
         QWidget { 
           background-color: #f0f0f0;
            padding: 10px;
           
             }   
         """)
        # 添加左上角标题
        top_left_label = QLabel('监控设置', self)
        top_left_label.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #2196F3;
            margin: 0px;
            padding: 10px;
              padding-top:20px ;
              border:0px
        """)  # 设置左上角标题样式
        # top_left_label.setGeometry(2, 2, 100, 30)  # 设置绝对位置和大小
        monitoring_settings_layout.addWidget(top_left_label)  # 添加左上角标题

        # == 添加Token输入框
        token_label = QLabel('WebSocket Token:', self)
        token_widget = QWidget(self)  # 创建一个新的QWidget来包含token布局
        token_layout = QHBoxLayout(token_widget)
        token_widget.setStyleSheet("background-color: #f0f0f0; border:0px")  # 设置背景色
        self.token_input = QLineEdit(self)
        self.token_input.setFixedWidth(450)  # 设置宽度
        self.token_input.setStyleSheet("""
            QLineEdit {
               background-color:rgba(255, 255, 255, 0.9);   
                text-align: center;
                border: 1px solid #f0f0f0;
                border-radius: 1px;
                color:#2196F3;
                padding: 2px;
                font-size: 12px;
            }
        """)
        # 设置默认token值
        self.token_input.setText("请输入最新token值")

        token_layout.addWidget(token_label)
        token_layout.addWidget(self.token_input)
        token_layout.setAlignment(Qt.AlignLeft)  # 设置对齐方式为左对齐

        token_widget.setLayout(token_layout)  # 设置布局
        monitoring_settings_layout.addWidget(token_widget)  # 将新QWidget添加到监控设置栏

        # 设置token标签宽度
        token_label.setFixedWidth(120)  # 设置固定宽度
        token_label.setStyleSheet(f"color: #2196F3;width: 100px;")

        # == 添加充电时间输入框
        charging_time_label = QLabel('充电时间(HH):', self)
        charging_time_widget = QWidget(self)  # 创建一个新的QWidget来包含充电时间标题布局
        charging_time_layout = QHBoxLayout(charging_time_widget)
        charging_time_widget.setStyleSheet("background-color: #f0f0f0; border:0px")  # 设置背景色
        self.charging_time_input_start = QLineEdit(self)
        self.charging_time_input_end = QLineEdit(self)
        self.charging_time_input_start.setFixedWidth(200)  # 设置宽度为100px
        self.charging_time_input_end.setFixedWidth(200)  # 设置宽度为100px
        self.charging_time_input_start.setStyleSheet("""
            QLineEdit {
               background-color:rgba(255, 255, 255, 0.9);   
                text-align: center;
                border: 1px solid #f0f0f0;
                border-radius: 1px;
                color:#2196F3;
                padding: 2px;
                font-size: 12px;
                 
            }
        """)
        self.charging_time_input_end.setStyleSheet("""
            QLineEdit {
                background-color:rgba(255, 255, 255, 0.9);   
                text-align: center;
                border: 1px solid #f0f0f0;
                border-radius: 1px;
                color:#2196F3;
                padding: 2px;
                font-size: 12px;
            }
        """)

        charging_time_layout.addWidget(charging_time_label)
        charging_time_layout.addWidget(self.charging_time_input_start)
        charging_time_layout.addWidget(self.charging_time_input_end)
        charging_time_layout.setAlignment(Qt.AlignLeft)  # 设置对齐方式为左对齐

        charging_time_widget = QWidget(self)  # 创建一个新的QWidget来包含充电时间布局
        charging_time_widget.setLayout(charging_time_layout)  # 设置布局
        charging_time_widget.setStyleSheet("""
            QWidget { background-color: #f0f0f0; border:0px}
        """)  # 设置样式
        monitoring_settings_layout.addWidget(charging_time_widget)  # 将新QWidget添加到监控设置栏
        # 在添加控件的布局中
        charging_time_layout.setAlignment(Qt.AlignLeft)  # 设置对齐方式为左对齐   

        # == 添加放电时间输入框
        discharging_time_label = QLabel('放电时间(HH):', self)
        discharging_time_widget = QWidget(self)  # 创建一个新的QWidget来包含放电时间布局
        discharging_time_layout = QHBoxLayout(discharging_time_widget)  # 创建水平布局并将其设置为discharging_time_widget的布局
        # discharging_time_widget.setAutoFillBackground(True)  # 确保背景填充整个widget
        self.discharging_time_input_start = QLineEdit(self)
        self.discharging_time_input_end = QLineEdit(self)

        self.discharging_time_input_start.setFixedWidth(200)  # 设置宽度为100px
        self.discharging_time_input_end.setFixedWidth(200)  # 设置宽度为100px
        discharging_time_layout.addWidget(discharging_time_label)
        discharging_time_label.setStyleSheet("""
              border:0px;
        """)
        discharging_time_widget.setStyleSheet("background-color: #f0f0f0; border: 0px;")  # 设置背景色和边框
        # discharging_time_layout.setSpacing(0)  # 设置布局间距为0
        discharging_time_layout.addWidget(self.discharging_time_input_start)
        discharging_time_layout.addWidget(self.discharging_time_input_end)
        discharging_time_layout.setAlignment(Qt.AlignLeft)  # 设置对齐方式为左对齐
        discharging_time_widget.setStyleSheet("background-color: #f0f0f0; border:0px;")  # 设置背景色
        self.discharging_time_input_start.setStyleSheet("""
            QLineEdit {
                 background-color:rgba(255, 255, 255, 0.9);   
                text-align: center;
                border: 0px  ;
                border-radius: 1px;
                color:#2196F3;
                padding: 2px;
                font-size: 12px;
            }
        """)
        self.discharging_time_input_end.setStyleSheet("""
            QLineEdit {
                 background-color:rgba(255, 255, 255, 0.9);   
                text-align: center;
                border: 0px solid #f0f0f0;
                border-radius: 1px;
                color:#2196F3;
                padding: 2px;
                font-size: 12px;
            }
        """)
        discharging_time_layout.setAlignment(Qt.AlignLeft)  # 设置对齐方式为左对齐
        monitoring_settings_layout.addWidget(discharging_time_widget)  # 将新QWidget添加到监控设置栏

        # == 添加充电SOC上限输入框
        charging_soc_label = QLabel('充电SOC上限(%):', self)
        charging_soc_layout = QHBoxLayout()  # 创建水平布局
        self.charging_soc_input = QLineEdit(self)
        self.charging_soc_input.setFixedWidth(450)  # 设置宽度为120+120+10
        charging_soc_layout.addWidget(charging_soc_label)
        charging_soc_layout.addWidget(self.charging_soc_input)
        charging_soc_layout.setAlignment(Qt.AlignLeft)  # 设置对齐方式为左对齐
        self.charging_soc_input.setStyleSheet("""
            QLineEdit {
                 background-color:rgba(255, 255, 255, 0.9);   
                text-align: center;
                border: 1px solid #f0f0f0;
                border-radius: 1px;
                color:#2196F3;
                padding: 2px;
                font-size: 12px;
            }
        """)
        charging_soc_widget = QWidget(self)  # 创建一个新的QWidget来包含充电SOC布局
        charging_soc_widget.setLayout(charging_soc_layout)  # 设置布局
        charging_soc_widget.setStyleSheet("""
            QWidget { background-color: #f0f0f0;border:0px }
        """)  # 设置样式
        monitoring_settings_layout.addWidget(charging_soc_widget)  # 将新QWidget添加到监控设置栏
        charging_soc_layout.setAlignment(Qt.AlignLeft)  # 设置对齐方式为左对齐

        # == 添加放电SOC下限输入框
        discharging_soc_label = QLabel('放电SOC下限(%):', self)
        discharging_soc_layout = QHBoxLayout()  # 创建水平布局
        self.discharging_soc_input = QLineEdit(self)
        self.discharging_soc_input.setFixedWidth(450)  # 设置宽度为100px
        discharging_soc_layout.addWidget(discharging_soc_label)
        discharging_soc_layout.addWidget(self.discharging_soc_input)
        discharging_soc_layout.setAlignment(Qt.AlignLeft)  # 设置对齐方式为左对齐
        self.discharging_soc_input.setStyleSheet("""
            QLineEdit {
                 background-color:rgba(255, 255, 255, 0.9);     
                text-align: center;
                border: 1px solid #f0f0f0;
                border-radius: 1px;
                color:#2196F3;
                padding: 2px;
                font-size: 12px;
                border:0px
            }
        """)
        discharging_soc_widget = QWidget(self)  # 创建一个新的QWidget来包含放电SOC布局
        discharging_soc_widget.setLayout(discharging_soc_layout)  # 设置布局
        discharging_soc_widget.setStyleSheet("""
            QWidget { background-color: #f0f0f0; border:0px}
        """)  # 设置样式
        monitoring_settings_layout.addWidget(discharging_soc_widget)  # 将新QWidget添加到监控设置栏

        # 设置监控栏样式
        monitoring_settings_panel.setMinimumHeight(int(self.height() * 0.3))  # 设置监控设置栏高度为30%
        monitoring_settings_panel.setStyleSheet("""
            QWidget { background-color: #f0f0f0;   border: 1px solid rgba(128, 128, 128, 0.1);}
        """)  # 设置监控设置栏背景颜色
        left_layout.addWidget(monitoring_settings_panel)  # 添加监控设置栏

        # 设置输入框的对齐方式
        self.charging_time_input_start.setAlignment(Qt.AlignCenter)
        self.charging_time_input_end.setAlignment(Qt.AlignCenter)
        self.discharging_time_input_start.setAlignment(Qt.AlignCenter)
        self.discharging_time_input_end.setAlignment(Qt.AlignCenter)
        self.charging_soc_input.setAlignment(Qt.AlignCenter)
        self.discharging_soc_input.setAlignment(Qt.AlignCenter)

        # 设置文本颜色
        label_color = "#2196F3"  # 您可以根据需要更改颜色
        charging_time_label.setStyleSheet(f"color: {label_color};width: 100px;  ")
        discharging_time_label.setStyleSheet(f"color: {label_color};width: 100px;  ")
        charging_soc_label.setStyleSheet(f"color: {label_color};width: 100px;  ")
        discharging_soc_label.setStyleSheet(f"color: {label_color};width: 100px;  ")   

        # 设置监控标题标签宽度 #
        charging_time_label.setFixedWidth(120)  # 设置固定宽度
        discharging_time_label.setFixedWidth(120)  # 设置固定宽度
        charging_soc_label.setFixedWidth(120)  # 设置固定宽度
        discharging_soc_label.setFixedWidth(120)  # 设置固定宽度

        # 设置输入框宽度
        self.charging_time_input_start.setFixedWidth(100)  # 设置固定宽度
        self.charging_time_input_end.setFixedWidth(100)  # 设置固定宽度
        self.discharging_time_input_start.setFixedWidth(100)  # 设置固定宽度
        self.discharging_time_input_end.setFixedWidth(100)  # 设置固定宽度
        self.charging_soc_input.setFixedWidth(200)  # 设置固定宽度
        self.discharging_soc_input.setFixedWidth(200)  # 设置固定宽度  

        # 假设你有六个输入框
        self.charging_soc_input.setValidator(QIntValidator(0, 100))  # 整数范围 0-100
        self.charging_time_input_start.setValidator(QIntValidator(0, 23))  # 小时范围 0-23
        self.charging_time_input_end.setValidator(QIntValidator(0, 23))  # 小时范围 0-23
        self.discharging_time_input_start.setValidator(QIntValidator(0, 23))  # 小时范围 0-23
        self.discharging_time_input_end.setValidator(QIntValidator(0, 23))  # 小时范围 0-23
        self.discharging_soc_input.setValidator(QIntValidator(0, 100))  # 整数范围 0-100        

        # ===== 创建日志显示区
        self.log_text = QTextEdit(self)  # 日志显示控件
        self.log_text.setReadOnly(True)  # 日志显示区只读
        self.log_text.setMaximumHeight(int(self.height() * 0.5))  # 设置日志显示区高度为40%
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #f0f0f0;
                font-size: 12px;
                color: #333333;
                border: 1px solid rgba(128, 128, 128, 0.1);
                border-radius: 5px;
            }
            QTextEdit::item:hover {
                 background-color: #ffffff;
            }
        """)  # 设置日志显示区背景颜色
        left_layout.addWidget(self.log_text)  # 添加日志显示区

        # 创建控制按钮
        button_layout = QHBoxLayout()  # 创建水平布局放置按钮

        self.connect_btn = QPushButton('连接WebSocket', self)
        self.connect_btn.clicked.connect(self.start_websocket)

        self.disconnect_btn = QPushButton('断开连接', self)
        self.disconnect_btn.clicked.connect(self.stop_websocket)
        self.disconnect_btn.setEnabled(False)

        self.refresh_btn = QPushButton('刷新数据', self)  # 添加刷新按钮
        self.refresh_btn.clicked.connect(self.refresh_data)
        self.refresh_btn.setEnabled(False)  # 初始时禁用

        # 设置按钮样式
        self.connect_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;  /* 绿色 */
                color: white;  /* 字体颜色 */
                padding: 10px;  /* 内边距 */
                border: none;  /* 无边框 */
                border-radius: 5px;  /* 圆角 */
            }
            QPushButton:hover {
                background-color: #45a049;  /* 悬停时的背景色 */
            }
        """)

        self.disconnect_btn.setStyleSheet("""
           
            QPushButton {
                background-color: #f44336;  /* 红色 */
                color: white;  /* 字体颜色 */
                padding: 10px;  /* 内边距 */
                border: none;  /* 无边框 */
                border-radius: 5px;  /* 圆角 */
            }
            QPushButton:hover {        
                background-color: #e53935;  /* 悬停时的背景色 */
            }
        """)

        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;  /* 蓝色 */
                color: white;  /* 字体颜色 */
                padding: 10px;  /* 内边距 */
                border: none;  /* 无边框 */
                border-radius: 5px;  /* 圆角 */
            }
            QPushButton:hover {
                background-color: #1976D2;  /* 悬停时的背景色 */
            }
        """)

        button_layout.addWidget(self.connect_btn)
        button_layout.addWidget(self.disconnect_btn)
        button_layout.addWidget(self.refresh_btn)

        left_layout.addLayout(button_layout)  # 使用布局替代单独添加按钮
        # 设置输入框的大小策略
        self.charging_time_input_start.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.charging_time_input_end.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.discharging_time_input_start.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.discharging_time_input_end.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.charging_soc_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.discharging_soc_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # 创建右侧数据显示列表
        self.data_list = QListWidget(self)  # 数据显示列表控件
        self.data_list.setStyleSheet("QListWidget { font-size: 14px; }")  # 设置列表样式
        self.data_list.setContentsMargins(5, 2, 5, 5)  # 设置无边距
        # self.data_list.setGeometry(800, 0, 400, 900)  # 设置位置和大小
        # 设置右侧数据详细显示框样式
        self.data_list.setStyleSheet("""
            QListWidget {
                
                border: 0px solid gray;
                background-color: #f0f0f0;
                font-size: 14px;
                color: #333333;
                border-radius: 5px;
                padding: 5px;
                border: 1px solid rgba(128, 128, 128, 0.1);
                padding-bottom: 15px;
            }
            QListWidget::item {
                padding: 1px;
                margin: 1px;
                
            }
            QListWidget::item:selected {
                background-color: #d0e0f0;
            }
            QListWidget::item:hover {
                 
            }
        """)

        # 添加面板到主布局
        main_layout.addWidget(left_panel)
        main_layout.addWidget(self.data_list)

    # 日志记录函数
    def log(self, message):
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # 获取当前时间
        # self.log_text.append(f"{current_time} - {message}")  # 记录日志
        self.log_text.append(f"{message}")  # 记录日志

    # 启动WebSocket工作线程
    def start_websocket(self):
        try:
            self.connect_btn.setEnabled(False)
            # self.connect_btn.setStyleSheet(" color: darkgray;")  # 禁用状态样式
            self.refresh_btn.setEnabled(False)
            # self.connect_btn.setEnabled(False)
            # self.disconnect_btn.setEnabled(True)
            # self.refresh_btn.setEnabled(True)  # 连接后启用刷新按钮
            self.log("正在连接WebSocket...")

            # 获取token输入框的值
            token = self.token_input.text()
            if not token:
                self.log("警告：Token输入框为空，将使用默认token")

            # 启动WebSocket工作线程
            self.ws_worker = WebSocketWorker()
            self.ws_worker.set_token(token)  # 设置token
            self.ws_worker.message_signal.connect(self.handle_message)
            self.ws_worker.log_signal.connect(self.log)
            self.ws_worker.start()

            self.disconnect_btn.setEnabled(True)
            self.refresh_btn.setEnabled(True)  # 连接后启用刷新按钮

            self.update_timer.start(1000)  # 启动定时器

        except Exception as e:
            self.log(f"启动WebSocket连接失败: {str(e)}")
            self.connect_btn.setEnabled(True)
            # self.disconnect_btn.setEnabled(False)
            # self.refresh_btn.setEnabled(False)
            # self.disconnect_btn.setStyleSheet(" color: darkgray;")  # 禁用状态样式
            # self.refresh_btn.setStyleSheet("color: darkgray;")  # 禁用状态样式

    # 停止WebSocket工作线程
    def stop_websocket(self):
        self.update_timer.stop()  # 停止定时器
        if self.ws_worker:
            self.ws_worker.stop()
            self.ws_worker = None

        self.connect_btn.setEnabled(True)
        # self.connect_btn.setStyleSheet(" color: white;")  # 禁用状态样式
        self.disconnect_btn.setEnabled(False)
        # self.disconnect_btn.setStyleSheet(" color:darkgray;")  # 禁用状态样式
        self.refresh_btn.setEnabled(False)  # 断开连接时禁用刷新按钮
        # self.refresh_btn.setStyleSheet(" color:darkgray;")  # 禁用状态样式
        self.log("WebSocket连接已断开")

    # 处理WebSocket工作线程消息
    def handle_message(self, data):
        try:
            func_type = data.get('func')
            self.log(f"收到消息类型: {func_type}")

            if func_type == "menu":
                menu_data = data.get("data", {})
                self.log(f"处理menu数据，包含设备类型: {list(menu_data.keys())}")
                self.update_device_tree(menu_data)

                # 存储设备ID和名称的映射关系
                self.device_info = {}
                for device_type, devices in menu_data.items():
                    for device in devices:
                        for rtv_item in device.get("rtvList", []):
                            item_id = str(rtv_item["id"])
                            self.device_info[item_id] = {
                                "name": rtv_item.get("fieldChnName", ""),
                                "eng_name": rtv_item.get("fieldEngName", ""),
                                "device_type": device_type,
                                "device_name": device.get("chnName", ""),
                                "table_name": device.get("tableName", "")
                            }
                self.log(f"设备信息映射表已更新，共 {len(self.device_info)} 个设备点位")

            elif func_type == "rtv":
                rtv_data = data.get("data", [])
                self.log(f"收到rtv数据，数量: {len(rtv_data)}")

                # 更新数据缓存
                for item in rtv_data:
                    item_id = str(item.get("id"))
                    value = item.get("value", "N/A")
                    self.latest_rtv_data[item_id] = value
                    # self.log(f"更新数据缓存: ID={item_id}, 值={value}")

                self.log(f"更新 {len(rtv_data)} 个数据缓存")   
                # 如果当前有选中的项，更新显示
                current_item = self.device_tree.currentItem()
                if current_item:
                    level = self.get_item_level(current_item)
                    rtv_ids = self.get_rtv_ids_for_item(current_item, level)
                    self.update_data_list_by_ids(rtv_ids)

        except Exception as e:
            self.log(f"处理消息出错: {str(e)}")

    # 更新设备树
    def update_device_tree(self, menu_data):
        try:
            self.device_tree.clear()  # 清空设备树

            for device_type, devices in menu_data.items():
                type_item = QTreeWidgetItem([device_type])  # 设备类型项
                self.device_tree.addTopLevelItem(type_item)  # 添加设备类型项到设备树

                for device in devices:
                    # 获取第一个rtv_item的ID作为设备ID
                    device_id = ""
                    if device.get("rtvList"):
                        device_id = str(device["rtvList"][0]["id"])

                    device_item = QTreeWidgetItem([
                        # f"{device.get('chnName')} ({device.get('engName')})"
                        f"{device_id} - {device.get('chnName')}"
                    ])  # 设备项
                    device_item.setData(0, Qt.UserRole, device)  # 设备项数据

                    # 添加子节点显示设备的详细信息
                    for rtv_item in device.get("rtvList", []):
                        rtv_item_node = QTreeWidgetItem([
                            # f"{rtv_item.get('fieldChnName')} ({rtv_item.get('fieldEngName')})"
                            f"{rtv_item['id']} - {rtv_item.get('fieldChnName')}"
                        ])  # 设备详细信息项
                        device_item.addChild(rtv_item_node)  # 添加设备详细信息项到设备项

                    type_item.addChild(device_item)  # 添加设备项到设备类型项

                type_item.setExpanded(True)  # 设备类型项展开

            self.log("设备树更新完成")  # 记录日志

        except Exception as e:
            self.log(f"更新设备树出错: {str(e)}")  # 记录日志

    # 更新数据列表
    def update_data_list(self, rtv_data):
        try:
            self.log(f"开始更新数据列表，数据数量: {len(rtv_data)}")

            # 清空列表
            self.data_list.clear()

            # 按设备类型对数据进行分组
            grouped_data = {
                "d_bms": [],
                "d_pcs": [],
                "d_grid": [],
                "d_air_condition": []
            }

            # 将数据分组
            for item in rtv_data:
                try:
                    item_id = str(item.get("id"))
                    value = item.get("value", "")

                    # 获取设备信息
                    device_info = self.device_info.get(item_id)
                    if not device_info:
                        self.log(f"未找到设备信息: ID={item_id}")
                        continue

                    device_type = device_info.get("device_type")
                    if device_type in grouped_data:
                        grouped_data[device_type].append((item_id, device_info, value))

                except Exception as row_error:
                    self.log(f"处理数据项出错: {str(row_error)}")
                    continue

            # 按设备类型顺序显示数据
            color_map = {
                "d_bms": QColor(230, 230, 255),           # 浅蓝色 - BMS电池
                "d_pcs": QColor(255, 230, 230),           # 浅红色 - PCS
                "d_grid": QColor(255, 255, 230),          # 浅黄色 - 电网
                "d_air_condition": QColor(230, 255, 230)  # 浅绿色 - 空调
            }

            # 按顺序添加各组数据
            for device_type, items in grouped_data.items():
                if items:  # 如果该类型有数据
                    # 添加设备类型标题
                    title_item = QListWidgetItem(f"*{device_type}*")
                    title_item.setBackground(color_map[device_type])
                    self.data_list.addItem(title_item)

                    # 添加该类型的所有数据项
                    for item_id, device_info, value in items:
                        display_text = f"ID: {item_id:<12}  {device_info['name']:<30}  {value:<45}"
                        list_item = QListWidgetItem(display_text)

                        # 设置等宽字体以便对齐
                        font = QFont("Courier New")  # 使用等宽字体
                        list_item.setFont(font)

                        # 设置背景色
                        list_item.setBackground(color_map[device_type])

                        # 添加到列表
                        self.data_list.addItem(list_item)

            self.log(f"数据列表更新完成，当前列表项数: {self.data_list.count()}")

            # 修改设备类型标题的格式
            title_item = QListWidgetItem(f"*{device_type}*")
            title_item.setBackground(color_map[device_type])
            self.data_list.addItem(title_item)

        except Exception as e:
            self.log(f"更新数据列表出错: {str(e)}")

    # 设备树项点击事件
    def on_tree_item_clicked(self, item, column):
        try:
            # 获取点击项的层级
            level = self.get_item_level(item)
            self.log(f"点击项层级: {level}")

            # 获取需要显示的数据ID列表
            rtv_ids = self.get_rtv_ids_for_item(item, level)
            if not rtv_ids:
                return

            # 过滤并显示数据
            self.update_data_list_by_ids(rtv_ids)

        except Exception as e:
            self.log(f"处理点击事件出错: {str(e)}")

    # 获取树节点的层级
    def get_item_level(self, item):
        """获取树节点的层级（0-顶级分组，1-设备，2-数据项）"""
        level = 0
        parent = item.parent()
        while parent:
            level += 1
            parent = parent.parent()
        return level

    # 根据点击项和层级获取需显示的数据ID列表
    def get_rtv_ids_for_item(self, item, level):
        """根据点击项和层级获取需显示的数据ID列表"""
        rtv_ids = []

        try:
            if level == 0:  # 顶级分组
                # 获取该分组下所有数据项ID
                device_type = item.text(0)
                for i in range(item.childCount()):
                    device_item = item.child(i)
                    for j in range(device_item.childCount()):
                        rtv_item = device_item.child(j)
                        item_text = rtv_item.text(0)
                        item_id = item_text.split(" - ")[0]  # 从显示文本中提取ID
                        rtv_ids.append(int(item_id))

            elif level == 1:  # 设备项
                # 获取该设备下所有数据项ID
                for i in range(item.childCount()):
                    rtv_item = item.child(i)
                    item_text = rtv_item.text(0)
                    item_id = item_text.split(" - ")[0]  # 从显示文本中提取ID
                    rtv_ids.append(int(item_id))

            else:  # 数据项
                # 获取单个数据项ID
                item_text = item.text(0)
                item_id = item_text.split(" - ")[0]  # 从显示文本中提取ID
                rtv_ids.append(int(item_id))

            self.log(f"获取到 {len(rtv_ids)} 个数据项ID")
            return rtv_ids

        except Exception as e:
            self.log(f"获取数据ID出错: {str(e)}")
            return []

    # 根据ID列表更新右侧数据显示
    def update_data_list_by_ids(self, rtv_ids):
        """根据ID列表更新右侧数据显示"""
        try:
            # 清空列表
            self.data_list.clear()

            # 按设备类型对数据进行分组
            grouped_data = {
                "d_bms": [],
                "d_pcs": [],
                "d_grid": [],
                "d_air_condition": []
            }

            # 将数据分组
            for item_id in rtv_ids:
                str_id = str(item_id)
                device_info = self.device_info.get(str_id)
                if not device_info:
                    continue

                # 从最近一次的rtv数据中获取值
                value = self.get_latest_value(str_id)
                device_type = device_info.get("device_type")

                if device_type in grouped_data:
                    grouped_data[device_type].append((str_id, device_info, value))

            # 输出缓存池数据数量
            self.log(f"获取数据值个数:{len(rtv_ids)}")

            # 显示分组数据
            color_map = {
                "d_bms": QColor(230, 230, 255),           # 浅蓝色 - BMS电池
                "d_pcs": QColor(255, 230, 230),           # 浅红色 - PCS
                "d_grid": QColor(255, 255, 230),          # 浅黄色 - 电网
                "d_air_condition": QColor(230, 255, 230)  # 浅绿色 - 空调
            }

            for device_type, items in grouped_data.items():
                if items:
                    # 添加设备类型标题
                    title_item = QListWidgetItem(f"==={device_type}===")
                    title_item.setBackground(color_map[device_type])
                    self.data_list.addItem(title_item)

                    # 添加数据项
                    for item_id, device_info, value in items:
                        display_text = f"ID: {item_id:<12}  {device_info['name']:<30}  {value:<45}"
                        list_item = QListWidgetItem(display_text)
                        list_item.setFont(QFont("Courier New"))
                        list_item.setBackground(color_map[device_type])
                        self.data_list.addItem(list_item)

        except Exception as e:
            self.log(f"更新数据列表出错: {str(e)}")

    # 获取最新一次的数据值
    def get_latest_value(self, item_id):
        """获取最新一次的数据值"""
        try:
            # 从缓存中获取最新数据
            value = self.latest_rtv_data.get(item_id, "N/A")
            # self.log(f"获取数据值: ID={item_id}, 值={value}")
            return value
        except Exception as e:
            self.log(f"获取数据值出错: {str(e)}")
            return "Error"

    # 关闭事件
    def closeEvent(self, event):
        self.stop_websocket()  # 停止WebSocket工作线程
        event.accept()  # 接受关闭事件

    # 手动刷新数据
    def refresh_data(self):
        """手动刷新数据"""
        try:
            self.log("手动刷新数据...")
            if self.ws_worker and self.ws_worker.websocket:
                # 清空现有数据
                self.latest_rtv_data.clear()
                self.device_info.clear()
                # 重新连接
                self.stop_websocket()
                self.start_websocket()
                self.log("已发送刷新请求")
        except Exception as e:
            self.log(f"刷新数据出错: {str(e)}")

    # 定时更新显示
    def update_display(self):
        # from emsContronl import ChargeDischargeController  # 延迟导入

        """定时更新显示"""
        try:
            # 如果有选中的项，更新其显示
            current_item = self.device_tree.currentItem()
            if current_item:
                level = self.get_item_level(current_item)
                rtv_ids = self.get_rtv_ids_for_item(current_item, level)
                if rtv_ids:
                    self.update_data_list_by_ids(rtv_ids)

            # 获取并转换变量
            soc = float(self.latest_rtv_data.get('412001056', 0))  # SOC，默认值为0
            runModel = (self.latest_rtv_data.get('412001051', 0))  # PCS运行模式 默认值为0
            charging_start_time = int(self.charging_time_input_start.text())  # 充电开始时间
            charging_end_time = int(self.charging_time_input_end.text())  # 充电结束时间
            discharging_start_time = int(self.discharging_time_input_start.text())  # 放电开始时间
            discharging_end_time = int(self.discharging_time_input_end.text())  # 放电结束时间
            soc_upper_limit = float(self.charging_soc_input.text())  # SOC上限
            soc_lower_limit = float(self.discharging_soc_input.text())  # SOC下限            

            # 调用监控控制器的方法
            self.controller.monitor_charge_discharge(soc, charging_start_time, charging_end_time, discharging_start_time, discharging_end_time, soc_upper_limit, soc_lower_limit,runModel)
        except Exception as e:
            pass  # 静默处理定时器的错误，避免日志刷屏

    # 连接按钮点击
    def on_connect_button_clicked(self):
        if not self.validate_inputs():
            self.log("请填写所有输入框！")
            return  # 如果输入不完整，返回而不发起连接

        # 如果所有输入框都填写了，继续执行连接逻辑
    #   self.log("正在连接WebSocket...")
    #   self.ws_worker = WebSocketWorker()
    #   self.ws_worker.message_signal.connect(self.handle_message)
    # 其他连接逻辑...

    # 启动WebSocket工作线程

    def validate_inputs(self):
        # 检查六个输入框是否都有输入
        if (self.charging_soc_input.text() == "" or   
          self.charging_time_input_start.text() == "" or   
          self.charging_time_input_end.text() == "" or
          self.discharging_time_input_start.text() == "" or
          self.discharging_time_input_end.text() == "" or
          self.discharging_soc_input.text() == ""):
            return False
        return True

    # 更新连接按钮状态
    def update_connect_button_state(self):
        if self.validate_inputs():
            self.connect_btn.setEnabled(True)  # 启用连接按钮
        #   self.connect_btn.setStyleSheet("background-color: #4CAF50;")  # 禁用状态样式
        #   self.connect_btn.setEnabled(False)
        else:
            self.connect_btn.setEnabled(False)  # 禁用连接按钮
        #   self.connect_btn.setStyleSheet(" background-color: #45a049;")  # 禁用状态样式

    # 设置输入验证
    def setup_input_validations(self):
        self.charging_soc_input.textChanged.connect(self.update_connect_button_state)
        self.charging_time_input_start.textChanged.connect(self.update_connect_button_state)
        self.charging_time_input_end.textChanged.connect(self.update_connect_button_state)
        self.discharging_time_input_start.textChanged.connect(self.update_connect_button_state)
        self.discharging_time_input_end.textChanged.connect(self.update_connect_button_state)
        self.discharging_soc_input.textChanged.connect(self.update_connect_button_state)      

# WebSocket工作线程类
class WebSocketWorker(QThread):
    message_signal = pyqtSignal(dict)  # 消息信号
    log_signal = pyqtSignal(str)  # 日志信号
    refresh_signal = pyqtSignal()  # 添加刷新信号

    def __init__(self):
        # 调用父类的构造函数
        super().__init__()
        # 设置程序运行状态为True
        self.is_running = True
        self.websocket = None
        self.need_refresh = False  # 添加刷新标志
        # 初始化WebSocket连接为None
        self.websocket = None
        # 设置是否需要刷新为False
        self.need_refresh = False
        # 初始化token
        self.token = None
        
    def set_token(self, token):
        """设置WebSocket连接使用的token"""
        self.token = token

    async def connect_websocket(self):
        # 使用从UI获取的token
        if not self.token:
            self.log_signal.emit("未设置token，使用默认token")
            self.token = "a7b403de831ad791006d86e86ecd67ae9df47ba05146fd407080b85a78f430882a1286f19d2d9fbee41ad81fce7e13dc24d75c2a3db4eb445b7f552a0f4bdba656486d824b90533603b7a92ee9130396"
        
        uri='ws://ems.hy-power.net:8888/E6F7D5412A20?'+self.token
        print("uri:",uri)
        headers = {
          
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Origin": "http://ems.hy-power.net:8114",
        }

        while self.is_running:  # 添加外层循环实现重连
            try:
                async with websockets.connect(uri, extra_headers=headers) as websocket:
                    self.websocket = websocket
                    self.log_signal.emit("WebSocket连接已建立")
                    # self.disconnect_btn.setEnabled(True)
                    # self.refresh_btn.setEnabled(Ture)
                    # self.disconnect_btn.setStyleSheet(" color: red;")  # 禁用状态样式
                    # self.refresh_btn.setStyleSheet("color: primary;")  # 禁用状态样式
                    # 发送初始menu订阅
                    menu_subscribe = {"func": "menu"}
                    await websocket.send(json.dumps(menu_subscribe))
                    self.log_signal.emit("已发送menu订阅请求")
                    
                    while self.is_running:
                        try:
                            # 检查是否需要刷新
                            if self.need_refresh:
                                self.need_refresh = False
                                # 重新发送menu订阅
                                menu_subscribe = {"func": "menu"}
                                await websocket.send(json.dumps(menu_subscribe))
                                self.log_signal.emit("已重新发送menu订阅请求")
                            
                            message = await websocket.recv()
                            self.log_signal.emit(f"收到原始消息: {message[:100]}...")  # 只显示前200个字符
                            
                            if isinstance(message, str):
                                data = json.loads(message)
                                self.message_signal.emit(data)
                                
                                # 如果收到menu数据，自动发送rtv订阅
                                if data.get("func") == "menu":
                                    # 从menu数据中提取所有ID
                                    rtv_ids = []
                                    menu_data = data.get("data", {})
                                    for device_type, devices in menu_data.items():
                                        for device in devices:
                                            for rtv_item in device.get("rtvList", []):
                                                rtv_ids.append(rtv_item["id"])
                                    
                                    # 发送rtv订阅消息
                                    rtv_subscribe = {
                                        "func": "rtv",
                                        "ids": rtv_ids,
                                        "period": 5
                                    }
                                    await websocket.send(json.dumps(rtv_subscribe))
                                    self.log_signal.emit(f"已发送rtv订阅请求，订阅 {len(rtv_ids)} 个ID")
                                
                        except websockets.exceptions.ConnectionClosed:
                            self.log_signal.emit("WebSocket连接已关闭，准备重连...")
                            break  # 跳出内层循环，外层循环会重新连接
                        except json.JSONDecodeError as e:
                            self.log_signal.emit(f"JSON解析错误: {str(e)}")
                        except Exception as e:
                            self.log_signal.emit(f"接收数据错误: {str(e)}")
                            
            except Exception as e:
                self.log_signal.emit(f"WebSocket连接错误: {str(e)}，3秒后重试...")
                # self.disconnect_btn.setEnabled(False)
                # self.refresh_btn.setEnabled(False)
                # self.disconnect_btn.setStyleSheet(" color: darkgray;")  # 禁用状态样式
                # self.refresh_btn.setStyleSheet("color: darkgray;")  # 禁用状态样式
                await asyncio.sleep(3)  # 等待3秒后重试

    # 定义run方法
    def run(self):
        # 使用asyncio.run方法运行connect_websocket方法
        asyncio.run(self.connect_websocket())
     
    def send_cmd_subscription(self, cmd_id, ref_fid, ref_rid, value):
        # 构建要发送的消息
        message = {
            "func": "cmd",
            "id": cmd_id,
            "refFid": ref_fid,
            "refRid": ref_rid,
            "value": value
        }

        # 将消息转换为 JSON 字符串
        message_json = json.dumps(message)
        
        # 发送消息
        self.send_message(message_json)  # 使用 send_message 方法发送
        print(f"发送CMD消息: {message_json}")  # 记录发送的消息



    def stop(self):
        """停止工作线程"""
        # self.stop_websocket()  # 停止WebSocket工作线程
        self.is_running = False
        self.websocket = None  # 直接清空 websocket 实例
        # self.disconnect_btn.setEnabled(False)
        # self.refresh_btn.setEnabled(False)
        # self.disconnect_btn.setStyleSheet(" color: darkgray;")  # 禁用状态样式
        # self.refresh_btn.setStyleSheet("color: darkgray;")  # 禁用状态样式
        
    def request_refresh(self):
        """请求刷新数据"""
        self.need_refresh = True

# 主函数
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = WebSocketClient()
    ex.show()
    sys.exit(app.exec_())
