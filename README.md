# 萌！FRP 高级客户端 / Moe! FRP Client

<div align="center">
   
> ⚠️ **提示**：本项目部分代码由 Google Gemini 2.5 Pro 辅助编写。

![Python](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python)
![PySide6](https://img.shields.io/badge/UI-PySide6-orange?logo=qt)
![Flask](https://img.shields.io/badge/Backend-Flask-black?logo=flask)
![License](https://img.shields.io/badge/License-MIT-green)
[![GitHub stars](https://img.shields.io/github/stars/XMZO/MoeFrpClient?style=social)](https://github.com/XMZO/MoeFrpClient/stargazers)

一份为 [frp](https://github.com/fatedier/frp) 设计的、集成了云同步与配置分享功能的现代化跨平台桌面客户端。

A modern, cross-platform desktop client for [frp](https://github.com/fatedier/frp), featuring cloud synchronization and profile sharing capabilities.

</div>

![软件截图](assets/screenshot.png)

## 🏗️ 架构 / Architecture

![项目架构图](assets/architecture.svg)

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
*   **完整的用户系统**: 支持用户注册、登录，并提供安全的、基于令牌的密码重置流程。
*   **强大的分享系统**:
    *   **完整分享**: 分享一个固定的、不可修改的 `frp` 配置包。
    *   **模板分享**: 分享一个可定制的模板，允许订阅者选择节点、自定义本地端口等。
    *   **分享管理**: 用户可以随时查看、管理或撤销自己创建的分享。

### **安全机制**
*   **客户端校验**: 客户端与服务器之间通过版本密钥和核心组件哈希进行严格的双向校验，防止非法客户端接入。
*   **挑战-响应登录**: 登录过程采用动态挑战码 (`Challenge`) 与登录证明 (`Proof`) 机制，有效防御重放攻击。
*   **分层本地加密**: 应用设置和“记住密码”等敏感信息，使用派生自机器唯一ID的密钥进行二次加密后，安全地存储在操作系统的密钥环 (Keyring) 中。
*   **防爆破延时**: 登录时采用基于 **Argon2** 的计算密集型延时，显著增加暴力破解的攻击成本。
*   **服务端安全**: 后端使用强密码哈希（Argon2）并对核心API（如登录、注册）设置了速率限制，以抵御恶意请求。

### **用户体验优化**
*   **智能日志解析**: 自动解析 `frpc` 的原始日志，仅呈现“代理启动成功”、“连接失败”等关键的、结构化的信息。
*   **美观的UI与交互**: 每次启动时从多个在线API源随机获取背景图片，并内置了支持 GIF 动画、无级缩放、拖动平移和右键保存的高级图片查看器。
*   **一键节点测速**: 快速测试所有服务器节点的网络延迟，并直观地在下拉列表中展示结果。
*   **应用级代理**: 支持独立设置客户端自身的网络代理（HTTP/SOCKS5），用于API请求和图片下载，该设置不影响`frp`核心隧道的连接。
*   **灵活的账户管理**: 提供“退出登录”（保留凭证）和“切换账户”（清除凭证）两种退出方式。

## 🚀 部署与使用

### **1. 核心组件说明**
*   **MoeFrpClient.mfc**: 这是 `frpc` 的核心动态链接库。 **你必须提供此文件**，并将其与主程序 `main.py` 放置在同一目录下，客户端才能启动FRP隧道。
*   **server.py**: 这是可选的后端服务器。如果你想拥有自己的账户系统和云同步功能，你需要部署它。如果你只是想连接到一个已有的服务，你则无需关心此文件。
*   **generate_invite_code.py**: 服务端管理工具，用于生成邀请码、管理用户等。

### **2. 服务端部署 (自托管用户)**
```bash
# 1. 进入服务端目录
cd frp_end/server

# 2. (推荐) 创建并激活虚拟环境
python -m venv venv
# Windows: venv\Scripts\activate | macOS/Linux: source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 首次运行会自动初始化数据库
python server.py
