# 萌！Frp 客户端 / Moe! Frp Client

<div align="center">

![Python](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python)
![PySide6](https://img.shields.io/badge/UI-PySide6-orange?logo=qt)
![License](https://img.shields.io/badge/License-MIT-green)
[![GitHub stars](https://img.shields.io/github/stars/XMZO/MoeFrpClient?style=social)](https://github.com/XMZO/MoeFrpClient/stargazers)

一份为 [frp](https://github.com/fatedier/frp) 设计的、拥有现代化图形界面的跨平台桌面客户端。

A modern, cross-platform desktop client with a graphical user interface designed for [frp](https://github.com/fatedier/frp).

</div>

---

<details>
<summary><strong>中文说明 (Click to expand)</strong></summary>

## 简介

**Moe! Frp 客户端** 是一个基于 Python 和 PySide6 构建的 `frp` 图形化工具，旨在为用户提供一个比命令行更直观、更易于管理的 `frpc` 操作体验。无论您是 `frp` 的新手还是资深用户，本工具都能帮助您简化配置管理、监控日志和控制服务启停。

![软件截图](assets/screenshot.png)

## ✨ 主要功能

*   **直观的图形界面**: 忘掉复杂的命令行参数吧！通过图形界面轻松管理您的 `frpc` 连接。
*   **配置管理**: 方便地加载、编辑和保存您的 `frpc` 配置文件。
*   **实时日志**: 内嵌的日志窗口可以实时显示 `frpc` 的输出，支持彩色高亮关键信息，便于快速定位问题。
*   **系统托盘支持**: 关闭主窗口后，程序可以最小化到系统托盘，保持 `frpc` 服务在后台持续运行。通过托盘菜单可以快速控制服务的启停或退出程序。
*   **主题自适应**: 完美适配您操作系统的浅色/深色模式，并能实时跟随系统主题变化，提供舒适的视觉体验。
*   **全局复制拦截 (特色功能)**: 启动此功能后，在系统的任何地方复制符合特定格式的穿透地址（如 `ssh://...` 或 `tcp://...`），程序会自动解析并弹出提示，方便您一键启动连接。
*   **灵活的启动模式**:
    *   **GUI 模式**: 为日常使用提供完整的图形化管理界面。
    *   **命令行模式**: 支持通过命令行参数直接启动 `frpc` 服务，便于集成到自动化脚本中。

## 🚀 快速开始

### 1. 先决条件

*   Python 3.12 或更高版本
*   pip 包管理器

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
```

### 3. 如何使用

#### GUI 模式

直接运行 `main.py` 即可启动图形界面：

```bash
python main.py
```
在主窗口中，您可以加载配置文件，点击“启动”按钮来运行 `frpc` 服务。

#### 命令行模式

如果您只想以后台服务的形式运行 `frpc`，可以使用以下命令：

```bash
python main.py [您的配置文件路径] [您的dll依赖路径]
```
*   `[您的配置文件路径]`: 指向您的 `frpc` 配置文件，例如 `frpc.toml`。
*   `[您的dll依赖路径]`: 指向 `frpc` 服务所需的依赖库路径。

## 🤝 贡献

欢迎任何形式的贡献！如果您有好的建议或发现了 Bug，请随时提出 Issue。如果您想贡献代码，请：

1.  Fork 本仓库
2.  创建您的特性分支 (`git checkout -b feature/AmazingFeature`)
3.  提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4.  推送到分支 (`git push origin feature/AmazingFeature`)
5.  提交一个 Pull Request

## 📄 开源许可

本项目基于 [MIT License](LICENSE) 开源。

## 🙏 致谢

*   感谢 [fatedier/frp](https://github.com/fatedier/frp) 提供了如此强大的内网穿透工具。
*   感谢 [PySide6](https://www.qt.io/qt-for-python) 框架的支持。

</details>

---

<details>
<summary><strong>English Description (Click to expand)</strong></summary>

## Introduction

**Moe! Frp Client** is a graphical tool for `frp`, built with Python and PySide6. It aims to provide a more intuitive and manageable user experience for `frpc` compared to the command line. Whether you are a novice or an advanced user of `frp`, this tool can help you simplify configuration management, monitor logs, and control the service.

![Application Screenshot](assets/screenshot.png)

## ✨ Key Features

*   **Intuitive GUI**: Forget complex command-line arguments! Easily manage your `frpc` connections through a graphical interface.
*   **Configuration Management**: Conveniently load, edit, and save your `frpc` configuration files.
*   **Real-time Log Viewer**: The embedded log window displays `frpc` output in real-time with color-highlighting for critical information, making troubleshooting easier.
*   **System Tray Support**: The application can be minimized to the system tray after closing the main window, keeping the `frpc` service running in the background. You can quickly start/stop the service or exit the application from the tray menu.
*   **Adaptive Theming**: Seamlessly adapts to your OS's light/dark mode and responds to theme changes in real-time, providing a comfortable visual experience.
*   **Global Copy Interceptor (Special Feature)**: When enabled, copying a penetration address in a specific format (e.g., `ssh://...` or `tcp://...`) anywhere in the system will be automatically parsed by the application, which then prompts you for one-click connection startup.
*   **Flexible Launch Modes**:
    *   **GUI Mode**: Provides a full graphical interface for daily use.
    *   **Command-line Mode**: Supports launching the `frpc` service directly via command-line arguments, ideal for integration with automation scripts.

## 🚀 Getting Started

### 1. Prerequisites

*   Python 3.12+
*   pip Package Manager

### 2. Installation

```bash
# 1. Clone this repository
git clone https://github.com/XMZO/MoeFrpClient.git

# 2. Navigate to the project directory
cd MoeFrpClient

# 3. (Recommended) Create and activate a virtual environment
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt
```

### 3. How to Use

#### GUI Mode

Simply run `main.py` to launch the graphical interface:

```bash
python main.py
```
In the main window, you can load your configuration file and click the "Start" button to run the `frpc` service.

#### Command-line Mode

If you only want to run `frpc` as a background service, use the following command:

```bash
python main.py [path/to/your/config] [path/to/your/dll]
```
*   `[path/to/your/config]`: The path to your `frpc` configuration file (e.g., `frpc.toml`).
*   `[path/to/your/dll]`: The path to a required DLL dependency for the `frpc` service.

## 🤝 Contributing

Contributions of any kind are welcome! If you have suggestions or have found a bug, please feel free to open an Issue. If you'd like to contribute code, please:

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

## 📄 License

This project is licensed under the [MIT License](LICENSE).

## 🙏 Acknowledgements

*   Thanks to [fatedier/frp](https://github.com/fatedier/frp) for providing such a powerful network penetration tool.
*   Thanks to the [PySide6](https://www.qt.io/qt-for-python) framework.

</details>
