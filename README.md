# 萌！FRP 高级版全栈项目 (Moe-FRP-Advanced-Project)

![Banner](https://img.shields.io/badge/%E8%90%8C%EF%BC%81FRP-%E5%85%A8%E6%A0%88%E9%A1%B9%E7%9B%AE-ff69b4?style=for-the-badge&logo=python&logoColor=white)
![版本](https://img.shields.io/badge/版本-v1.0.3c-blue?style=for-the-badge)
![技术栈](https://img.shields.io/badge/技术栈-PySide6%20%7C%20Flask%20%7C%20SQLite-green?style=for-the-badge)
![许可](https://img.shields.io/badge/许可-MIT-lightgrey?style=for-the-badge)

这是一个功能强大的 FRP (Fast Reverse Proxy) 图形化客户端与配套服务端的全栈解决方案。项目不仅提供了传统 frpc 的所有功能，还集成了账户系统、配置云同步、配置分享与订阅、在线节点管理等高级特性。

## ✨ 项目亮点

*   **全功能图形界面**：基于 PySide6 构建，提供直观的节点和代理规则管理，无需手动编辑 TOML 文件。
*   **云端同步**：将您的配置安全地保存在云端，在任何设备上登录即可恢复所有设置。
*   **配置分享与订阅系统**：支持“模板分享”和“完整分享”两种模式，满足不同场景需求。
*   **多重安全机制**：客户端与服务端通过版本密钥、核心组件哈希、动态挑战码等多重校验；用户密码使用 Argon2id 安全存储；本地“记住密码”凭证通过系统密钥环和本机唯一ID加密。
*   **动态图片背景**：集成多个图片API，定时刷新萌图，提升使用愉悦感。
*   **独立后台管理工具**：提供一个强大的命令行工具，用于生成邀请码、管理用户和重置密码。

## 📂 项目结构

本项目包含两个核心部分，分别位于不同的子目录中：

```
frp_end/
├── client/          # 客户端（图形界面程序）的所有源代码
├── server/          # 服务端（API 后端）的所有源代码
└── README.md        # 您正在阅读的这份主说明文档
```

---

## 🛠️ (一) 服务端 / Server

`server` 目录包含了项目的后端 API 服务和管理工具。

### 1. 环境与依赖

*   Python 3.8+
*   依赖库见 `server/requirements.txt`

### 2. 部署步骤

1.  **进入服务端目录**
    ```bash
    cd server
    ```

2.  **创建并激活虚拟环境 (推荐)**
    ```bash
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # macOS / Linux
    source venv/bin/activate
    ```

3.  **安装依赖**
    ```bash
    pip install -r requirements.txt
    ```

4.  **初始化数据库**
    首次运行 `server.py` 会自动创建 `users.db` 数据库文件。

5.  **创建管理员账户**
    服务端本身不提供注册管理员的接口。您需要通过客户端注册一个普通用户后，手动修改数据库：
    ```bash
    # (确保在 server 目录下执行)
    sqlite3 users.db
    
    # 假设你已注册用户'myadmin'，将其角色提升为管理员
    UPDATE users SET role = 'admin' WHERE nickname = 'myadmin';
    .quit
    ```
    
6.  **启动服务**
    - **开发模式**:
      ```bash
      python server.py
      ```
      服务将运行在 `http://127.0.0.1:5000`。
    - **生产环境 (推荐)**:
      使用 Gunicorn 或其他 WSGI 服务器，并配合反向代理（如 Nginx, Caddy）来处理 HTTPS 和负载。
      ```bash
      gunicorn --worker-class gevent --workers 1 --threads 10 --bind 127.0.0.1:5000 --bind '[::1]:5000' server:app
      ```
   
### 3. 后台管理

`server` 目录下提供了一个强大的命令行管理工具 `generate_invite_code.py`。

#### 用法
```bash
# (确保在 server 目录下，并已激活虚拟环境)

# 方式一：运行交互式菜单 (推荐)
python generate_invite_code.py

# 方式二：使用命令行参数直接操作
# 查看状态
python generate_invite_code.py --status
# 生成5个邀请码
python generate_invite_code.py --generate 5
# 删除用户 'some_user'
python generate_invite_code.py --delete-user some_user
# 为用户 'some_user' 生成密码重置令牌
python generate_invite_code.py --reset-password some_user
```
**核心功能**：生成/删除邀请码、查看状态、删除用户、重置用户密码。

---

## 💻 (二) 客户端 / Client

`client` 目录包含了用户使用的图形界面程序的所有源代码和资源文件。

### 1. 环境与依赖

*   Python 3.8+
*   PySide6 (Qt for Python)
*   依赖库见 `client/requirements.txt`

### 2. 核心资源文件说明

在 `client` 目录下，有几个关键文件：
-   `main.py`: 客户端主程序入口。
-   `MoeFrpClient.mfc`: **加密后的核心组件**。这是客户端与服务端进行版本校验和身份认证的关键部分。
-   `app.ico` / `windows.ico`: 程序的图标文件。
-   `build.bat`: 用于 PyInstaller 打包的批处理脚本。

### 3. 从源码运行

1.  **进入客户端目录**
    ```bash
    cd client
    ```

2.  **创建并激活虚拟环境 (推荐)**
    ```bash
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # macOS / Linux
    source venv/bin/activate
    ```

3.  **安装依赖**
    ```bash
    pip install -r requirements.txt
    ```
    
4.  **运行客户端**
    ```bash
    python main.py
    ```

### 4. 打包为可执行文件 (.exe)

`client` 目录下提供了一个 `build.bat` 批处理脚本，它使用 **PyInstaller** 将所有代码和资源打包成一个独立的 `.exe` 文件。

1.  **安装 PyInstaller**
    ```bash
    pip install pyinstaller
    ```
2.  **执行打包脚本**
    在 `client` 目录下，直接双击运行 `build.bat`，或者在命令行中执行：
    ```bash
    .\build.bat
    ```
3.  打包完成后，最终的可执行文件会出现在 `client/dist` 文件夹内。

### 5. 功能简介

客户端的使用方式非常直观，主要功能包括：
-   **注册/登录**：通过邀请码注册，支持“记住密码”功能。
-   **云同步**：登录后，所有配置（节点、代理规则、订阅）都可与云端同步。
-   **配置分享**：可将自己的配置以“模板”或“完整”模式分享给他人。
-   **订阅系统**：通过分享ID订阅他人配置。
-   **在线管理**：随时随地通过图形界面管理节点和代理规则。
-   **一键测速**：快速测试所有节点的延迟。

详细的使用说明可以在程序界面上通过工具提示（Tooltips）获得。

---

## 📝 开发者说明

-   **服务端安全**：服务端通过 `server.py` 中的 `TRUSTED_CLIENTS` 列表来验证客户端身份。若客户端核心组件 (`MoeFrpClient.mfc`) 或版本密钥 (`version_secret`) 发生变化，需要同时更新客户端和服务端的此部分配置。
-   **API 结构**：客户端的 `api/` 目录清晰地定义了所有与后端交互的接口，方便追踪和调试。
-   **UI与逻辑分离**：客户端 `Dialogs.py` 和 `threads.py` 的设计旨在将UI界面与耗时操作分离，保证了应用的响应性和稳定性。
-   **贡献代码**：欢迎通过 Fork & Pull Request 的方式为项目贡献代码。请确保您的代码风格与现有项目保持一致，并提供清晰的提交信息。
