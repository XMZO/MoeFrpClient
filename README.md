# 萌！FRP 高级客户端 (Moe! FRP Client)

这是一个功能丰富、注重安全与用户体验的FRP（Fast Reverse Proxy）解决方案。它由一个轻量级的 **Flask** 后端服务器和一个功能强大的 **PySide6** 图形化桌面客户端组成，旨在为用户提供便捷、可同步、可分享的内网穿透服务管理。

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0-black.svg)](https://flask.palletsprojects.com/)
[![PySide6](https://img.shields.io/badge/PySide6-6.9-brightgreen.svg)](https://www.qt.io/qt-for-python)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## ✨ 核心特性

*   **☁️ 云端同步与配置管理**:
    *   用户配置（节点、代理规则）可安全地存储在云端服务器。
    *   支持多份独立配置文件的创建與管理。
    *   支持游客模式，可在未登录状态下进行本地临时配置。

*   **🤝 强大的分享与订阅系统**:
    *   用户可将自己的配置创建为分享链接。
    *   支持**完整模式**（订阅者使用固定配置）和**模板模式**（订阅者可自定义部分参数，如本地端口）。
    *   分享者可以随时管理或撤销自己的分享。

*   **🔐 注重安全的设计**:
    *   **邀请码注册**: 控制用户来源，只有通过邀请码才能注册账户。
    *   **增强登录验证**: 采用**挑战-应答(Challenge-Response)**机制，将`版本密钥`+`核心组件哈希`+`客户端版本`+`挑战码`四者结合进行多重绑定，确保只有官方特定版本的客户端才能登录。
    *   **抗暴力破解**: 客户端登录/注册时会触发一个**安全加固延时**对话框，它在后台线程中运行高成本的Argon2哈希运算，有效减缓自动化攻击。
    *   **强密码哈希**: 服务端使用 **Argon2** 算法安全存储用户密码。
    *   **本地凭证加密**: 客户端使用系统原生密钥环(`keyring`)结合**机器唯一GUID**进行加密，将“记住密码”信息安全地绑定到当前设备。
    *   **服务端速率限制**: 使用 Flask-Limiter 对关键API进行速率限制，防止滥用。

*   **👑 管理员权限**:
    *   内置 `admin` 角色，特定API（如为用户重置密码）需要管理员权限才能调用，确保了高级操作的安全性。

*   **🖥️ 丰富的图形化客户端**:
    *   使用 PySide6 (Qt for Python) 构建，界面美观，操作直观。
    *   **FRP核心隔离**: 通过独立的子进程运行FRP核心(`MoeFrpClient.mfc`)，与主GUI进程完全隔离，保证稳定性。
    *   支持节点和代理规则的可视化增删改查。
    *   **趣味图片浏览器**:
        *   从多个API源**加权随机**获取图片。
        *   支持 **GIF 动图**播放。
        *   内置功能完善的查看器，支持**鼠标拖动**、**滚轮缩放**和**右键保存**。


*   **🔧 便捷的服务端管理**:
    *   提供一个功能强大的命令行管理工具 (`generate_invite_code.py`)。
    *   支持交互式菜单和命令行参数两种模式，方便管理用户、邀请码和（通过管理员登录）重置密码。

##  项目结构

```
frp_end/
├── client/                      # 客户端目录
│   ├── api/                     # 模块化的API客户端库
│   │   ├── __init__.py          # 组装ApiClient, 暴露各模块接口
│   │   ├── auth.py              # 处理用户认证、注册、会话
│   │   ├── base.py              # 封装底层requests请求, 处理错误
│   │   ├── config.py            # 处理云端配置的同步、获取
│   │   └── share.py             # 处理分享与订阅相关API
│   ├── app.ico                  # 通用应用图标
│   ├── windows.ico              # PySide6主窗口图标
│   ├── config.py                # 客户端静态配置 (服务器URL, 版本号, 图片源等)
│   ├── Dialogs.py               # 所有对话框UI (登录, 编辑, 图片查看器等)
│   ├── frpc_runner.py           # 独立子进程，用于运行frpc核心服务
│   ├── ImageLabel.py            # 自定义图片显示控件(支持模糊背景)
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
    *   本地加密: **Cryptography**, **Keyring**, **机器GUID**
    *   配置文件格式: **TOML**
    *   HTTP通信: **Requests**
    *   核心加载: **ctypes**

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

## 👑 管理员设置 (重要)

系统中的某些高级功能（如代替用户重置密码）需要**管理员(admin)**权限。`admin`角色不会自动分配，需要数据库管理员**手动设置**，这是为了保证最高权限的安全性。

请按以下步骤设置您的第一个管理员账户：

1.  **注册一个普通账户**:
    首先，使用客户端的注册功能，注册一个您打算用作管理员的账户（例如，昵称 `myadmin`）。

2.  **定位数据库**:
    找到服务端目录下的 `users.db` 文件。

3.  **提升权限**:
    使用任何SQLite数据库工具 (如 [DB Browser for SQLite](https://sqlitebrowser.org/)) 打开 `users.db` 文件。然后执行以下SQL命令：

    ```sql
    UPDATE users SET role = 'admin' WHERE nickname = '你的管理员昵称';
    ```
    例如，要将用户 `myadmin` 提升为管理员，命令为:
    ```sql
    UPDATE users SET role = 'admin' WHERE nickname = 'myadmin';
    ```
    保存更改后，该用户即拥有管理员权限。

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
*   **5. 重置用户密码**: 为指定用户生成一个一次性的密码重置令牌。**此操作需要您输入管理员账户的密码**。
*   **6. 退出**

**命令行模式:**

*   **生成邀请码**: `python generate_invite_code.py -g 5` (生成5个)
*   **查看状态**: `python generate_invite_code.py -s`
*   **删除用户**: `python generate_invite_code.py -du <nickname>`
*   **删除邀请码**: `python generate_invite_code.py -dc <invitation_code>`
*   **重置密码 (需要管理员权限)**: `python generate_invite_code.py -rp <nickname>`

### 客户端使用流程

1.  **注册与登录**:
    *   首次使用，向管理员索要一个**邀请码**进行注册。
    *   使用注册的昵称和密码登录。可以选择“记住密码”以便安全地在本地保存凭证。
    *   管理员账户和普通用户账户使用相同的登录入口。

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
