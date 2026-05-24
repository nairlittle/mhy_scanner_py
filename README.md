# MHY Scanner Py

米哈游扫码登录器 (Web版) — 基于原版 [MHY_Scanner](https://github.com/Theresa-0328/MHY_Scanner) 的 Python 重构版本。

将原版 C++/Qt 桌面应用重构为 FastAPI + Web 前端架构，支持在浏览器中完成米哈游游戏账号的扫码登录和抢码功能。

## 功能和特性

- **扫码登录**: 从屏幕自动获取二维码登录，适用于大部分登录情景
- **直播抢码**: 从 B站/抖音直播流获取二维码登录，适用于抢码登录情景
- **账号管理**: 表格化管理多账号，支持 Cookie 导入和备注编辑
- **多游戏支持**: 崩坏3 / 原神 / 星穹铁道 / 绝区零 (官服 & Bilibili服)

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI (Python) |
| 数据库 | SQLite |
| 前端 | 原生 HTML/CSS/JS (SPA) |
| 实时通信 | WebSocket |
| QR检测 | OpenCV (WeChatQRCode) |
| 直播流处理 | FFmpeg |

## 快速开始

### 环境要求

- Python 3.10+
- FFmpeg (用于直播流功能)

### 安装

```bash
pip install -r requirements.txt
```

### 运行

```bash
python run.py
```

浏览器访问 `http://localhost:8000`

## 使用说明

1. **添加账号**: 在"扫码登录"页面，通过二维码、Cookie 或短信方式登录你的米哈游账号
2. **监视屏幕**: 在"监视屏幕"页面选择账号和游戏，点击开始后自动识别屏幕上的二维码
3. **监视直播间**: 在"监视直播间"页面选择平台、输入房间号(RID)，点击开始

## 相关项目

- [MHY_Scanner](https://github.com/Theresa-0328/MHY_Scanner) — 原版 C++ 桌面端
- [HonkaiScanner](https://github.com/HonkaiScanner)
- [BililiveRecorder](https://github.com/BililiveRecorder/BililiveRecorder)
- [Snap.Hutao](https://github.com/DGP-Studio/Snap.Hutao)

## 许可证

GPL-3.0 License — 免费开源，禁止商业化用途。
