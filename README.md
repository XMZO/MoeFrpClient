# 萌！FRP 高级客户端 / Moe! FRP Client

<div align="center">

![Python](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python)
![PySide6](https://img.shields.io/badge/UI-PySide6-orange?logo=qt)
![License](https://img.shields.io/badge/License-MIT-green)
[![GitHub stars](https://img.shields.io/github/stars/XMZO/MoeFrpClient?style=social)](https://github.com/XMZO/MoeFrpClient/stargazers)

一份为 [frp](https://github.com/fatedier/frp) 设计的、拥有完整生态的现代化跨平台桌面客户端。

A modern, cross-platform desktop client for [frp](https://github.com/fatedier/frp), designed as a complete ecosystem.

</div>

---

<details>
<summary><strong>中文说明 (Click to expand)</strong></summary>

## 简介

**萌！FRP 客户端** 并不仅仅是一个 `frp` 的图形化界面，它是一个包含**云端同步、配置分享、安全认证、多账户体系**的完整解决方案。无论您是个人开发者、团队协作者，还是需要为他人提供内网穿透服务的管理者，本工具都能提供前所未有的便捷与安全。

![软件截图](assets/screenshot.png)

## 核心理念

*   **☁️ 云原生 (Cloud-Native)**: 所有配置（个人配置、订阅）均可与云端服务器无缝同步。一次配置，多端使用。
*   **🔒 安全第一 (Security First)**: 从客户端到服务器，我们设计了多层安全机制，包括版本校验、挑战-响应式登录、本地设置加密等，确保您的数据和连接安全。
*   **🤝 分享与协作 (Sharing & Collaboration)**: 内建强大的分享系统，您可以将配置作为**完整包**或**模板**分享给他人，极大地方便了团队协作和批量部署。

## ✨ 主要功能

### **账户与配置管理**
*   **完整的用户系统**: 支持注册、登录、密码重置。
*   **多配置管理**:
    *   **游客模式**: 无需登录，用于本地临时配置和快速测试。
    *   **云端配置**: 登录后，您的个人配置将自动保存在云端，多设备同步。
    *   **订阅模式**: 可一键添加他人分享的配置，并自动同步更新。
*   **强大的分享系统**:
    *   **完整分享**: 分享一个固定的、不可修改的 `frp` 配置。
    *   **模板分享**: 分享一个模板，订阅者可以选择节点、自定义本地端口等，兼具便利性与灵活性。
    *   **分享管理**: 您可以随时查看、撤销自己创建的分享。

### **安全特性**
*   **客户端校验**: 客户端与服务器之间通过版本号、版本密钥和核心组件 (`.mfc`) 的哈希值进行严格校验，杜绝非法或过期的客户端连接。
*   **挑战-响应式登录**: 登录过程采用动态挑战码 (`challenge`) 和登录证明 (`proof`) 机制，有效防御重放攻击。
*   **本地设置强加密**: “记住密码”和应用设置等敏感信息，通过派生自**机器唯一ID**的密钥进行加密，并安全地存储在操作系统的**密钥环 (Keyring)** 中。
*   **防爆破登录延时**: 登录时采用基于 **Argon2** 的计算密集型延时，显著增加暴力破解的成本。
*   **服务器端速率限制**: 所有敏感API（如登录、注册）均有速率限制，防止恶意请求。

### **用户体验**
*   **智能日志解析**: 不再是杂乱的 `frpc` 日志！客户端会自动解析日志，只显示“代理启动成功”、“连接失败”等关键的、人类可读的信息。
*   **高级图片查看器**:
    *   支持 **GIF** 动画播放。
    *   **Ctrl + 滚轮**进行无级缩放。
    *   图片过大时可**拖动平移**。
    *   支持**右键复制和保存**图片。
*   **随机背景图**: 每次启动时从多个在线API源（如 `lolicon.app`, `anosu.top`）随机获取背景图片。
*   **一键节点测速**: 快速测试所有服务器节点的延迟，并直观地显示在下拉列表中。
*   **应用级代理设置**: 可独立设置客户端自身的网络代理（用于API请求、图片下载），而不影响 `frp` 核心隧道的连接。
*   **右键快捷菜单**: 在主界面的图片上右键，可快速刷新、复制或另存为图片。

### **灵活的运行模式**
*   **GUI 模式**: 为日常使用提供完整的图形化管理界面。
*   **命令行模式**: 支持通过命令行参数直接启动 `frpc` 服务，便于集成到自动化脚本中。

## 🚀 快速开始

### 1. 先决条件

*   Python 3.12 或更高版本
*   pip 包管理器
*   **重要**: 确保核心组件 `MoeFrpClient.mfc` 与主程序在同一目录下。

### 2. 安装

```bash
# 1. 克隆本仓库到本地
git clone https://github.com/XMZO/MoeFrpClient.git

# 2. 进入项目目录
cd MoeFrpClient

# 3. (推荐) 创建并激活一个虚拟环境
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 4. 安装依赖
pip install -r requirements.txt

# 5. 如果您需要使用SOCKS5代理，请额外安装
pip install "requests[socks]"
```

### 3. 如何使用

直接运行 `main.py` 即可启动图形界面：

```bash
python main.py
```

## 🤝 贡献

欢迎任何形式的贡献！如果您有好的建议或发现了 Bug，请随时提出 Issue。如果您想贡献代码，请 Fork 本仓库并发起一个 Pull Request。

## 📄 开源许可

本项目基于 [MIT License](LICENSE) 开源。

</details>

---

<details>
<summary><strong>English Description (Click to expand)</strong></summary>

## Introduction

**Moe! FRP Client** is not just a graphical user interface for `frp`; it is a complete solution that includes **cloud synchronization, configuration sharing, robust security authentication, and a multi-account system**. Whether you are an individual developer, a team collaborator, or an administrator providing intranet penetration services, this tool offers unprecedented convenience and security.

![Application Screenshot](assets/screenshot.png)

## Core Philosophy

*   **☁️ Cloud-Native**: All configurations (personal profiles, subscriptions) are seamlessly synchronized with a cloud server. Configure once, use everywhere.
*   **🔒 Security First**: We have designed a multi-layered security mechanism from the client to the server, including version validation, challenge-response login, and local settings encryption, to ensure the security of your data and connections.
*   **🤝 Sharing & Collaboration**: The built-in sharing system allows you to share configurations as a **complete package** or as a **template**, greatly facilitating teamwork and batch deployment.

## ✨ Key Features

### **Account & Profile Management**
*   **Full User System**: Supports registration, login, and password reset.
*   **Multi-Profile Management**:
    *   **Guest Mode**: Use local temporary configurations for quick tests without logging in.
    *   **Cloud Profiles**: After logging in, your personal configurations are automatically saved to the cloud for multi-device sync.
    *   **Subscription Mode**: One-click subscription to configurations shared by others, with automatic updates.
*   **Powerful Sharing System**:
    *   **Full Share**: Share a fixed, non-editable `frp` configuration.
    *   **Template Share**: Share a template where subscribers can select nodes, customize local ports, etc., balancing convenience and flexibility.
    *   **Share Management**: View and revoke your created shares at any time.

### **Security Features**
*   **Client Validation**: Strict validation between the client and server based on version number, version secret, and the hash of the core component (`.mfc`), preventing connections from illegal or outdated clients.
*   **Challenge-Response Login**: The login process uses a dynamic challenge and proof mechanism to effectively defend against replay attacks.
*   **Strong Local Encryption**: Sensitive information like "Remember Me" credentials and app settings are encrypted with a key derived from a **unique machine ID** and securely stored in the OS's native **Keyring**.
*   **Anti-Brute-Force Delay**: A computationally intensive delay based on **Argon2** is implemented during login to significantly increase the cost of brute-force attacks.
*   **Server-Side Rate Limiting**: All sensitive APIs (e.g., login, register) are rate-limited to prevent malicious requests.

### **User Experience (UX)**
*   **Intelligent Log Parsing**: No more cluttered `frpc` logs! The client automatically parses logs to display key, human-readable information like "Proxy started successfully" or "Connection failed".
*   **Advanced Image Viewer**:
    *   Supports **GIF** animation playback.
    *   **Ctrl + Scroll** for smooth zooming.
    *   **Drag to pan** large images.
    *   **Right-click to copy and save** the image.
*   **Random Background Images**: Fetches background images from multiple online API sources (e.g., `lolicon.app`, `anosu.top`) on startup.
*   **One-Click Node Ping Test**: Quickly test the latency of all server nodes and display the results intuitively.
*   **App-Level Proxy Settings**: Independently configure the client's own network proxy for API requests and image downloads, without affecting the core FRP tunnel connections.
*   **Context Menu**: Right-click on the image in the main window to quickly refresh, copy, or save it.

### **Flexible Operation Modes**
*   **GUI Mode**: Provides a full graphical interface for daily use.
*   **Command-line Mode**: Supports launching the `frpc` service directly
