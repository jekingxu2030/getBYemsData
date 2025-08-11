# BY-EMS能源管理系统监控工具

## 项目概述

本项目是一个基于PyQt5的EMS（能源管理系统）实时监控工具，用于监控和管理储能系统的运行状态。系统通过WebSocket协议实时获取EMS数据，提供图形化界面展示，并支持充放电自动控制策略。

## 系统架构

### 整体架构图
```
┌─────────────────────────────────────────────────────────────┐
│                    BY-EMS Monitor System                    │
├─────────────────────────────────────────────────────────────┤
│  UI层 (PyQt5)    │  业务逻辑层    │  数据处理层    │ 存储层 │
│  ui_window.py    │  emsContronl.py│  data_processing│ MySQL │
│  ├─设备树展示     │  ├─充放电控制  │  ├─数据解析    │       │
│  ├─实时监控面板   │  ├─策略判断    │  ├─数据分类    │       │
│  └─日志输出      │  └─命令发送    │  └─实时更新    │       │
├─────────────────────────────────────────────────────────────┤
│              WebSocket通信层 (connection.py)                 │
├─────────────────────────────────────────────────────────────┤
│                    EMS服务器 (WebSocket)                     │
└─────────────────────────────────────────────────────────────┘
```

## 核心模块详解

### 1. 入口模块 - main.py
- **功能**: 程序入口，启动PyQt5应用
- **主要职责**:
  - 创建QApplication实例
  - 初始化主窗口(WebSocketClient)
  - 启动事件循环

### 2. UI界面模块 - ui_window.py
- **类**: `WebSocketClient(QMainWindow)`
- **核心功能**:
  - **界面布局**: 三栏式设计（左-设备树，中-控制面板，右-数据展示）
  - **设备树**: 动态展示EMS系统所有设备（BMS、PCS、空调、电表等）
  - **控制面板**: 提供充放电时间设置、SOC阈值配置
  - **实时监控**: 3秒定时刷新显示最新数据
  - **日志系统**: 实时输出系统运行状态和错误信息
  - **Token管理**: 每小时自动更新WebSocket连接token

- **关键组件**:
  - `device_tree`: QTreeWidget - 层级化设备展示
  - `controller`: ChargeDischargeController - 充放电控制器
  - `data_processor`: DataProcessor - 数据处理器
  - `update_timer`: QTimer - 3秒定时刷新
  - `token_timer`: QTimer - 1小时更新token

### 3. WebSocket通信模块 - connection.py
- **类**: `WebSocketWorker(QThread)`
- **核心功能**:
  - **异步通信**: 基于asyncio和websockets库实现
  - **自动重连**: 连接断开后3秒自动重试
  - **心跳检测**: 30秒无数据视为连接异常
  - **消息处理**: 自动解析JSON格式数据
  - **数据订阅**: 支持menu和rtv两种数据订阅
  - **文件存储**: 原始数据自动保存到ws_json_dump目录

- **通信协议**:
  - 连接地址: `ws://ems.hy-power.net:8888/E6F7D5412A20`
  - 消息格式: JSON格式，包含func字段区分消息类型
  - 订阅类型: menu（设备列表）、rtv（实时数据）

### 4. 充放电控制模块 - emsContronl.py
- **类**: `ChargeDischargeController`
- **核心功能**:
  - **策略判断**: 基于时间窗口和SOC值的智能控制
  - **状态管理**: 跟踪当前充放电状态(is_charging/is_discharging)
  - **命令发送**: 通过WebSocket发送控制命令到EMS
  - **日志记录**: 详细记录每次决策和操作

- **控制逻辑**:
  ```
  充电时间段内：
  ├─ SOC ≥ 上限 → 停止充电
  └─ SOC < 上限且未充电 → 启动充电
  
  放电时间段内：
  ├─ SOC ≤ 下限 → 停止放电  
  └─ SOC > 下限且未放电 → 启动放电
  ```

### 5. 数据处理模块 - data_processing.py
- **类**: `DataProcessor(QObject)`
- **核心功能**:
  - **设备树构建**: 根据menu数据动态创建设备层级结构
  - **数据分类**: 按设备类型(BMS/PCS/电表/空调)分组处理
  - **ID提取**: 自动提取和管理所有数据点ID
  - **实时更新**: 支持按设备或数据点维度更新显示

- **数据组织**:
  - 设备类型 → 设备实例 → 数据点列表
  - 支持三级层级：设备类型/设备/数据点

### 6. 数据存储模块 - mysql_storage.py
- **类**: `MySQLStorage(QObject)`
- **设计模式**: 单例模式确保全局唯一连接
- **核心功能**:
  - **连接管理**: 自动重连和连接池管理
  - **数据存储**: 实时数据批量插入
  - **表结构维护**: 自动创建和管理数据表
  - **错误处理**: 连接失败自动重试3次

- **数据库配置**:
  - 主机: 18.185.184.251 (或localhost)
  - 数据库: getbyemsdata
  - 用户: getbyemsdata
  - 端口: 3306

### 7. 数据插入模块 - data_insert.py
- **功能**: 实时数据存储调度器
- **核心特性**:
  - **时间控制**: 支持最小时间间隔限制(默认30秒)
  - **批量插入**: 使用executemany提高性能
  - **字段映射**: 基于field_order.txt定义的顺序存储
  - **异步存储**: 使用asyncio避免阻塞主线程

## 数据流分析

### 1. 下行数据流（EMS→系统）
```
EMS服务器 → WebSocket → connection.py → data_processing.py → ui_window.py → 界面展示
                                      ↓
                               data_insert.py → MySQL数据库
```

### 2. 上行控制流（系统→EMS）
```
ui_window.py → emsContronl.py → connection.py → EMS服务器 → 设备控制
```

### 3. 数据格式
- **Menu数据**: 设备层级结构，包含设备类型、设备、数据点三层
- **RTV数据**: 实时数据，格式为{id: value}键值对
- **字段定义**: 基于field_order.txt的162个字段顺序

## 文件组织结构

```
getBYemsData/
├── main.py                 # 程序入口
├── ui_window.py            # 主界面
├── connection.py           # WebSocket通信
├── emsContronl.py          # 充放电控制
├── data_processing.py      # 数据处理
├── data_insert.py          # 数据插入
├── mysql_storage.py        # MySQL存储
├── config.ini             # 配置文件
├── requirements.txt        # 依赖列表
├── 样板数据.json           # 数据格式示例
├── dataLog/               # 日志文件目录
├── ws_json_dump/          # WebSocket原始数据
├── 数据库初始化处理/        # 数据库工具脚本
│   ├── field_order.txt    # 字段顺序定义
│   ├── exportTableName.py # 表名导出
│   └── fristInsertRtvData.py # 初始数据插入
└── 原版/                  # 旧版本备份
```

## 运行流程

### 1. 启动流程
1. 用户运行`python main.py`
2. 创建PyQt5应用和主窗口
3. 初始化UI界面和各个模块
4. 自动加载WebSocket token
5. 启动定时器开始监控

### 2. 数据获取流程
1. WebSocketWorker连接EMS服务器
2. 发送menu请求获取设备列表
3. 解析设备列表提取所有RTV ID
4. 订阅rtv实时数据
5. 每5秒接收一次实时数据包

### 3. 控制流程
1. 用户在界面设置充放电时间和SOC阈值
2. 系统每3秒检查一次当前策略
3. 根据当前时间和SOC值判断是否动作
4. 通过WebSocket发送控制命令
5. 更新系统状态和日志

## 配置说明

## 配置说明

### 1. 环境要求
- Python 3.8+
- MySQL 5.7+
- Chrome浏览器（用于验证码识别）
- Windows/Linux/macOS操作系统

### 2. 安装依赖
```bash
# 进入项目目录
cd getBYemsData

# 激活虚拟环境
.\venv\Scripts\activate  # Windows
```

---

## 🔍 WebSocket数据交互分析结论

### 实际观测数据模式
基于浏览器实际抓包分析，发现以下关键数据交互模式：

#### 1. 心跳机制
- **PING/PONG模式**：客户端发送PING，服务器返回PONG
- **响应格式**：`00000000: 504f4e47 PONG`（十六进制ASCII）
- **作用**：维持WebSocket连接活跃，检测连接状态

#### 2. 时区查询
- **请求格式**：`{func: "timezone"}`
- **响应格式**：`{func: "timezone", data: "-7"}`
- **用途**：获取服务器时区偏移（-7小时，即UTC-7）

#### 3. RTV订阅参数优化
**浏览器实际使用参数**：
- `period=0`：在浏览器中观察到使用，但实际测试发现推送不连续
- **建议调整**：基于实际观测，可能需要设置具体数值而非0

#### 4. 数据推送频率分析
- **PONG响应**：持续稳定，证明连接正常
- **RTV数据**：当前观测中未看到连续推送，可能需要调整订阅参数

### 关键发现
1. **心跳正常**：PING/PONG机制工作稳定
2. **时区功能**：单次请求响应模式正常
3. **RTV推送**：需要进一步优化订阅参数
4. **连接稳定性**：WebSocket层连接正常

### 后续优化建议
- **RTV period值**：建议测试 `period=5` 或 `period=10` 以获得更稳定推送
- **超时检测**：基于PONG响应调整心跳超时时间
- **数据验证**：增加RTV数据到达的监控和验证机制
source venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt
```

### 3. 数据库配置
```sql
-- 创建数据库
CREATE DATABASE getbyemsdata CHARACTER SET utf8mb4;

-- 创建用户并授权
CREATE USER 'getbyemsdata'@'%' IDENTIFIED BY 'getbyemsdata';
GRANT ALL PRIVILEGES ON getbyemsdata.* TO 'getbyemsdata'@'%';
FLUSH PRIVILEGES;
```

### 4. 配置文件(config.ini)
```ini
[websocket]
url = ws://ems.hy-power.net:8888/E6F7D5412A20?your-token-here

[database]
host = 18.185.184.251
user = getbyemsdata
password = getbyemsdata
dbname = getbyemsdata

[settings]
timeout = 30
```

## 使用说明

### 1. 启动程序
```bash
python main.py
```

### 2. 界面操作
1. **设备监控**: 左侧树形结构查看所有设备状态
2. **参数设置**: 中间面板设置充放电时间和SOC阈值
3. **实时数据**: 右侧列表显示最新数据值
4. **日志查看**: 底部文本框显示系统运行日志

### 3. 控制策略设置
- **充电时间**: 设置开始和结束时间（24小时制）
- **放电时间**: 设置开始和结束时间（24小时制）
- **SOC上限**: 充电停止阈值（百分比）
- **SOC下限**: 放电停止阈值（百分比）

## 故障排除

### 1. 连接问题
- **症状**: WebSocket连接失败
- **解决**: 检查网络连接和token有效性

### 2. 数据库问题
- **症状**: 数据无法存储
- **解决**: 检查MySQL服务状态和连接配置

### 3. 界面卡顿
- **症状**: 界面响应缓慢
- **解决**: 降低数据刷新频率或优化数据库查询

## 扩展开发

### 1. 添加新设备类型
1. 在data_processing.py中添加设备类型处理
2. 更新field_order.txt添加新字段
3. 在数据库中创建对应表结构

### 2. 增加控制策略
1. 在emsContronl.py中添加新的控制方法
2. 在ui_window.py中添加对应的UI控件
3. 更新配置参数存储

### 3. 数据可视化
1. 集成matplotlib或pyqtgraph进行图表展示
2. 添加历史数据查询功能
3. 支持数据导出到Excel/CSV

## 版本历史

- **v1.0**: 基础版本，支持实时监控和自动控制
- **原版**: 初始版本，仅支持数据获取和展示
- **当前**: 重构版本，模块化设计和数据库支持

## 技术支持

- **项目地址**: [待补充]
- **问题反馈**: [待补充]
- **文档更新**: [待补充]

---

*本文档最后更新：2025年1月*
