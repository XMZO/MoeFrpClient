# 萌！FRP 高级客户端 / Moe! FRP Client

<div align="center">
   
> ⚠️ **提示**：本项目部分代码由 Google Gemini 2.5 Pro 辅助编写。

![Python](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python)
![PySide6](https://img.shields.io/badge/UI-PySide6-orange?logo=qt)
![License](https://img.shields.io/badge/License-MIT-green)
[![GitHub stars](https://img.shields.io/github/stars/XMZO/MoeFrpClient?style=social)](https://github.com/XMZO/MoeFrpClient/stargazers)

一份为 [frp](https://github.com/fatedier/frp) 设计的、集成了云同步与配置分享功能的现代化跨平台桌面客户端。

A modern, cross-platform desktop client for [frp](https://github.com/fatedier/frp), featuring cloud synchronization and profile sharing capabilities.

</div>

![软件截图](assets/screenshot.png)

---

<details>
<summary><strong>中文说明 (Click to expand)</strong></summary>

## 简介

**萌！FRP 客户端** 是一个基于 Python 和 PySide6 构建的 `frp` 图形化工具。它旨在提供一个比原生命令行更直观、更易于管理的 `frpc` 操作体验，并引入了**云端同步**和**配置分享**等高级功能，以满足个人开发者和团队的复杂需求。

## ✨ 主要功能

### **账户与配置管理**
*   **多模式配置**:
    *   **游客模式**: 无需登录，用于本地临时配置和快速测试。
    *   **云端配置**: 登录后，个人配置将自动与云端服务器同步，实现多设备共享。
    *   **订阅模式**: 支持一键添加他人分享的配置，并能与分享源保持同步更新。
*   **完整的用户系统**: 支持用户注册、登录，并提供安全的密码重置流程。
*   **强大的分享系统**:
    *   **完整分享**: 分享一个固定的、不可修改的 `frp` 配置包。
    *   **模板分享**: 分享一个可定制的模板，允许订阅者选择节点、自定义本地端口等。
    *   **分享管理**: 用户可以随时查看、管理或撤销自己创建的分享。

### **安全机制**
*   **客户端校验**: 客户端与服务器之间通过版本密钥和核心组件哈希进行严格的双向校验，防止非法客户端接入。
*   **挑战-响应登录**: 登录过程采用动态挑战码 (`Challenge`) 与登录证明 (`Proof`) 机制，有效防御重放攻击。
*   **本地加密**: 应用设置和“记住密码”等敏感信息，使用派生自机器唯一ID的密钥加密后，安全地存储在操作系统的密钥环 (Keyring) 中。
*   **防爆破延时**: 登录时采用基于 **Argon2** 的计算密集型延时，显著增加暴力破解的攻击成本。
*   **服务端速率限制**: 核心API（如登录、注册）均设置了速率限制，以抵御恶意请求。

### **用户体验优化**
*   **智能日志解析**: 自动解析 `frpc` 的原始日志，仅呈现“代理启动成功”、“连接失败”等关键的、结构化的信息。
*   **高级图片查看器**: 内置图片查看器支持 **GIF** 动画播放、**Ctrl+滚轮** 无级缩放、大图拖动平移以及右键复制和保存功能。
*   - **随机背景图**: 每次启动时从多个在线API源（如 `lolicon.app`, `anosu.top`）随机获取背景图片。
*   **一键节点测速**: 快速测试所有服务器节点的网络延迟，并直观地在下拉列表中展示结果。
*   **应用级代理**: 支持独立设置客户端自身的网络代理（HTTP/SOCKS5），用于API请求和图片下载，该设置不影响`frp`核心隧道的连接。

### **灵活的运行模式**
*   **GUI 模式**: 为日常使用提供功能完善的图形化管理界面。
*   **命令行模式**: 支持通过命令行参数直接启动 `frpc` 服务，便于集成到自动化脚本中。

## 🚀 快速开始

### 1. 先决条件

*   Python 3.12 或更高版本
*   pip 包管理器
*   **注意**: 核心组件 `MoeFrpClient.mfc` 必须与主程序位于同一目录下。

### 2. 安装

```bash
# 1. 克隆本仓库
git clone https://github.com/XMZO/MoeFrpClient.git

# 2. 进入项目目录
cd MoeFrpClient

# 3. (推荐) 创建并激活虚拟环境
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate

# 4. 安装依赖
pip install -r requirements.txt

# 5. [可选] 如需使用SOCKS5代理，请额外安装
pip install "requests[socks]"
```

### 3. 如何使用

直接运行 `main.py` 启动图形界面：

```bash
python main.py
```

## 🤝 贡献

欢迎任何形式的贡献。如果您有改进建议或发现 Bug，请随时提出 Issue。如果您希望贡献代码，请遵循标准的 Fork & Pull Request 流程。

## 📄 开源许可

本项目基于 [MIT License](LICENSE) 开源。

</details>

---

<details>
<summary><strong>English Description (Click to expand)</strong></summary>

## Introduction

**Moe! FRP Client** is a graphical tool for `frp` built with Python and PySide6. It aims to provide a more intuitive and manageable user experience for `frpc` compared to the native command line, introducing advanced features like **cloud synchronization** and **profile sharing** to meet the complex needs of individual developers and teams.

## ✨ Key Features

### **Account & Profile Management**
*   **Multi-Mode Configuration**:
    *   **Guest Mode**: No login required for local, temporary configurations and quick testing.
    *   **Cloud Profiles**: After logging in, personal profiles are automatically synchronized with the cloud server for multi-device access.
    *   **Subscription Mode**: Supports one-click subscription to profiles shared by others, with automatic updates from the source.
*   **Complete User System**: Supports user registration, login, and a secure password reset process.
*   **Powerful Sharing System**:
    *   **Full Share**: Share a fixed, non-editable `frp` configuration package.
    *   **Template Share**: Share a customizable template that allows subscribers to select nodes, define local ports, etc.
    *   **Share Management**: Users can view, manage, or revoke their created shares at any time.

### **Security Mechanisms**
*   **Client Validation**: Strict two-way validation between the client and server using a version secret and core component hash to prevent unauthorized client access.
*   **Challenge-Response Login**: The login process employs a dynamic challenge and proof mechanism to effectively defend against replay attacks.
*   **Local Encryption**: Sensitive information, such as application settings and "Remember Me" credentials, is encrypted with a key derived from a unique machine ID and securely stored in the OS's native Keyring.
*   **Anti-Brute-Force Delay**: A computationally intensive delay based on **Argon2** is implemented during login to significantly increase the cost of brute-force attacks.
*   **Server-Side Rate Limiting**: Core APIs (e.g., login, register) are rate-limited to mitigate malicious requests.

### **User Experience Enhancements**
*   **Intelligent Log Parsing**: Automatically parses raw `frpc` logs to present only key, structured information, such as "Proxy started successfully" or "Connection failed".
*   **Advanced Image Viewer**: The built-in image viewer supports **GIF** animation playback, smooth zooming with **Ctrl+Scroll**, panning for large images, and right-click to copy/save.
*   **Randomized Backgrounds**: Fetches a random background image on startup from multiple online API sources (e.g., `lolicon.app`, `anosu.top`).
*   **One-Click Node Ping Test**: Quickly tests the network latency of all server nodes and displays the results intuitively in a dropdown list.
*   **Application-Level Proxy**: Supports independent configuration of a network proxy (HTTP/SOCKS5) for the client itself, used for API requests and image downloads, without affecting the core `frp` tunnel connection.

### **Flexible Operation Modes**
*   **GUI Mode**: Provides a full-featured graphical interface for daily use.
*   **Command-line Mode**: Supports launching the `frpc` service directly via command-line arguments, ideal for integration into automation scripts.

## 🚀 Getting Started

### 1. Prerequisites

*   Python 3.12+
*   pip Package Manager
*   **Note**: The core component `MoeFrpClient.mfc` must be in the same directory as the main executable.

### 2. Installation

```bash
# 1. Clone the repository
git clone https://github.com/XMZO/MoeFrpClient.git

# 2. Navigate to the project directory
cd MoeFrpClient

# 3. (Recommended) Create and activate a virtual environment
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. [Optional] For SOCKS5 proxy support, install this extra
pip install "requests[socks]"
```

### 3. Usage

Simply run `main.py` to launch the graphical interface:

```bash
python main.py
```

## 🤝 Contributing

Contributions of any kind are welcome. If you have suggestions for improvement or find a bug, please feel free to open an Issue. If you'd like to contribute code, please follow the standard Fork & Pull Request workflow.

## 📄 License

This project is licensed under the [MIT License](LICENSE).

</details>
