# 萌！FRP 高级客户端 (Moe! FRP Client)

这是一个功能丰富、注重安全与用户体验的FRP（Fast Reverse Proxy）解决方案。它由一个轻量级的 **Flask** 后端服务器和一个功能强大的 **PySide6** 图形化桌面客户端组成，旨在为用户提供便捷、可同步、可分享的内网穿透服务管理。

部分代码使用 Gemini-2.5-pro 编写

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0-black.svg)](https://flask.palletsprojects.com/)
[![PySide6](https://img.shields.io/badge/PySide6-6.9-brightgreen.svg)](https://www.qt.io/qt-for-python)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## ✨ 核心特性

*   **☁️ 云端同步与配置管理**:
    *   用户配置（节点、代理规则）可安全地存储在云端服务器。
    *   支持多份独立配置文件的创建与管理。
    *   支持游客模式，可在未登录状态下进行本地临时配置。

*   **🤝 强大的分享与订阅系统**:
    *   用户可将自己的配置创建为分享链接。
    *   支持**完整模式**（订阅者使用固定配置）和**模板模式**（订阅者可自定义部分参数，如本地端口）。
    *   分享者可以随时管理或撤销自己的分享。

*   **🔐 注重安全的设计**:
    *   **邀请码注册**: 控制用户来源，只有通过邀请码才能注册账户。
    *   **增强登录**: 采用 **挑战-应答(Challenge-Response)** 机制验证客户端身份，结合客户端版本和核心组件哈希进行多重校验。
    *   **强密码哈希**: 使用 **Argon2** 算法安全存储用户密码。
    *   **本地加密**: 客户端使用系统密钥环(`keyring`)和设备指纹安全地存储“记住密码”信息。

*   **🖥️ 丰富的图形化客户端**:
    *   使用 PySide6 (Qt for Python) 构建，界面美观，操作直观。
    *   内置FRP核心，通过独立的子进程运行，与主GUI进程隔离。
    *   支持节点和代理规则的可视化增删改查。
    *   集成趣味性的**图片浏览器**，可从多个API源获取并展示图片，增添使用乐趣。

*   **🔧 便捷的服务端管理**:
    *   提供一个功能强大的命令行管理工具 (`generate_invite_code.py`)。
    *   支持交互式菜单和命令行参数两种模式，方便管理用户、邀请码和重置密码。

##  项目结构

```
frp_end/
├── client/                      # 客户端目录
│   ├── api/
│   │   └── __init__.py          # API客户端模块封装
│   ├── app.ico                  # 应用图标
│   ├── config.py                # 客户端静态配置 (服务器URL, 版本号等)
│   ├── Dialogs.py               # 所有对话框UI (登录, 编辑, 分享等)
│   ├── frpc_runner.py           # 独立子进程，用于运行frpc核心服务
│   ├── ImageLabel.py            # 自定义图片显示控件
│   ├── main.py                  # 客户端主程序入口
│   ├── MoeFrpClient.mfc         # (需自行提供) FRP核心动态链接库
│   ├── requirements.txt         # 客户端Python依赖
│   ├── security.py              # 加密管理器 (本地凭证安全存储)
│   ├── threads.py               # 后台线程 (Ping, 日志读取, 图片获取等)
│   └── utils.py                 # 工具函数 (资源路径, 哈希计算等)
│
└── server/                      # 服务端目录
    ├── generate_invite_code.py  # 服务端管理脚本 (核心)
    ├── requirements.txt         # 服务端Python依赖
    ├── server.py                # Flask后端服务器主程序
    ├── users.db                 # (自动生成) SQLite数据库文件
    └── server.log               # (自动生成) 服务器日志
```

## 🛠️ 技术栈

*   **后端 (Server)**:
    *   框架: **Flask**
    *   数据库: **SQLite**
    *   密码哈希: **Argon2**
    *   速率限制: **Flask-Limiter**

*   **前端 (Client)**:
    *   GUI框架: **PySide6 (Qt6)**
    *   本地加密: **Cryptography**, **Keyring**
    *   配置文件格式: **TOML**
    *   HTTP通信: **Requests**

## 🚀 安装与部署

### 1. 服务端 (Server)

服务端负责用户认证和配置存储。

```bash
# 1. 进入服务端目录
cd frp_end/server

# 2. (推荐) 创建并激活Python虚拟环境
python -m venv venv
source venv/bin/activate  # on Windows: venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 运行服务器
# 首次运行会自动创建 users.db 数据库文件
python server.py
# 服务器将默认在 http://127.0.0.1:5000 运行
```

### 2. 客户端 (Client)

客户端是用户与之交互的图形化界面程序。

```bash
# 1. 进入客户端目录
cd frp_end/client

# 2. (推荐) 创建并激活Python虚拟环境
python -m venv venv
source venv/bin/activate # on Windows: venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. (重要!) 放置核心组件
# 将你的frpc核心动态链接库文件命名为 `MoeFrpClient.mfc` 并放置在此目录下。
# 如果没有此文件，客户端将无法启动连接。

# 5. 运行客户端
python main.py
```

## 📖 使用指南

### 服务端管理 (`generate_invite_code.py`)

这是管理后台的核心工具，支持交互模式和命令行参数模式。

**交互模式 (推荐):**

```bash
cd frp_end/server
python generate_invite_code.py
```

启动后将看到菜单：
*   **1. 查看邀请码状态**: 显示所有邀请码（未使用/已使用）和使用者信息。
*   **2. 生成邀请码**: 创建一个新的或多个邀请码。
*   **3. 删除邀请码**: 删除指定的邀请码或所有未使用的邀请码。
*   **4. 删除用户**: 删除指定的用户及其所有数据。
*   **5. 重置用户密码**: 为指定用户生成一个一次性的密码重置令牌。
*   **6. 退出**

**命令行模式:**

*   **生成邀请码**: `python generate_invite_code.py -g 5` (生成5个)
*   **查看状态**: `python generate_invite_code.py -s`
*   **删除用户**: `python generate_invite_code.py -du <nickname>`
*   **删除邀请码**: `python generate_invite_code.py -dc <invitation_code>`
*   **重置密码**: `python generate_invite_code.py -rp <nickname>`

### 客户端使用流程

1.  **注册与登录**:
    *   首次使用，向管理员索要一个**邀请码**进行注册。
    *   使用注册的昵称和密码登录。可以选择“记住密码”以便安全地在本地保存凭证。

2.  **配置管理**:
    *   **游客模式**: 未登录时使用，配置仅存在于本地，关闭程序后可能会丢失。
    *   **云端配置**: 登录后，可以创建、删除、编辑自己的云端配置文件。所有更改都可以通过点击“保存到云端”按钮进行同步。

3.  **节点与代理**:
    *   在选定的配置中，可以添加、编辑、删除**服务器节点**（你的frps服务器信息）。
    *   可以添加、编辑、删除**代理规则**（如 `tcp`, `http` 等）。

4.  **订阅分享**:
    *   点击“添加订阅”，输入他人分享的ID，即可订阅。
    *   如果订阅的是**模板分享**，你可以在客户端自定义本地端口等信息。
    *   如果订阅的是**完整分享**，你将使用分享者预设的完整配置。

5.  **启动连接**:
    *   在“控制与日志”区域，从下拉框中选择要运行的**激活节点**。
    *   点击“启动连接”按钮。连接日志将实时显示在下方的文本框中。

---

希望这份文档能帮助您更好地理解和使用这个项目！
