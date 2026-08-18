巧克力曰：
这是一个能自动检测你发的视频链接或者抖音图文的机器人，并且无视平台用户是否设置了该视频/图文可供下载。

需要准备的是：一个闲置的QQ（防止有被封号的风险，虽然我没有）
             耐心
 
 此脚本用DeepSeek4辅助开发
 当你绑定了NapCat以后，脚本会自动帮你登录，没有采用NacCat自身的扫描二维码登录，因为调试次数过多会进风控而无法登录。
 
 因为抖音太屌了所以在提取抖音平台的时候可能会存在失败的情况，这个时候请过一会再进行提取。B站则不会出现这种状况。
 
 设置了超过50MB的视频会转发文件，5分钟以内的非超高画质视频差不多是没有问题的

 目前的缺点是：这个机器人目前依赖NapCat，所以NapCat所支持的QQ版本号是不能变的，否则会失败，意味着你的QQ不能开启自动更新，并且设置了QQ机器人的那个账号需要在电脑上登陆。同时要注意缓存累积，最好不要放在C盘里。
 




接下来是AI对该机器人的介绍
# QQ 视频下载机器人

基于 [NoneBot2](https://github.com/nonebot/nonebot2) + [NapCat](https://github.com/NapNeko/NapCatQQ) 的 QQ 机器人。检测群聊/私聊中的视频链接，下载后发回。

## ✨ 功能特性

- 🔗 识别消息中的视频链接（纯文本、分享卡片、json/xml 小程序卡片）
- 🎬 支持抖音（视频 + 图文）和 B 站等 yt-dlp 支持的平台
- ✅ 检测到链接先询问「是否要下载？」，回复「是」才下载
- 📦 超过 50MB 自动改发文件（避免 QQ 视频消息发送失败）
- 👤 支持对指定 QQ 用户添加自定义称呼前缀
- 🖼️ 抖音图文（图片笔记）自动下载全部图片并逐张发送

## 🏗️ 架构

```
QQ 用户 ←→ QQ 客户端 (NTQQ) ←→ NapCat (OneBot V11) ←→ NoneBot2 (本仓库)
                                                          │
                                           ┌──────────────┴──────────────┐
                                           │ 抖音: dwo.cc 解析接口         │
                                           │ B站等: yt-dlp + ffmpeg       │
                                           └─────────────────────────────┘
```

| 组件 | 作用 | 部署位置 |
|------|------|---------|
| **NoneBot2**（本仓库） | 机器人框架、消息处理、视频下载 | 任意（本地/服务器） |
| **NapCat** | OneBot V11 协议端，登录 QQ | 需与 QQ 客户端同机 |
| **QQ 客户端 (NTQQ)** | 提供 QQ 协议 | Windows |

## 📦 依赖

- **Python** 3.9+
- **ffmpeg**（视频合并转 mp4 必需）
- Python 包见 [`requirements.txt`](requirements.txt)

## 🚀 部署

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

安装 ffmpeg（Windows，用 winget）：

```bash
winget install Gyan.FFmpeg
```

### 2. 配置

```bash
cp .env.example .env
```

默认配置即可运行（监听 `127.0.0.1:8080`）。

### 3. 部署 NapCat（登录 QQ）

> ⚠️ **关键**：NapCat 对 QQ 版本有要求，请使用 **QQ 9.9.31**（新版本可能报 `PacketBackend 不支持当前QQ版本架构`）。

1. 安装官方 QQ（NT 架构，版本 9.9.31）
2. 下载 [NapCat](https://github.com/NapNeko/NapCatQQ/releases) 的 **Shell 手动版**（`NapCat.Shell.zip`，解压后含 `launcher.bat`）
3. 先手动打开 QQ 登录，然后运行 NapCat 快速登录：

   ```bat
   cd NapCat.Shell
   launcher-user.bat <你的QQ号>
   ```

4. 打开 NapCat WebUI（`http://127.0.0.1:6099/webui`），配置**反向 WebSocket**：

   ```
   ws://127.0.0.1:8080/onebot/v11/ws
   ```

### 4. 启动机器人

```bash
python bot.py
```

看到 `Uvicorn running on http://127.0.0.1:8080` 即启动成功。

## 📖 使用

1. 在群里 / 私聊发一个视频链接（抖音 / B 站）
2. 机器人回复「检测到链接，是否要下载？」
3. 回复 **「是」** 开始下载，回复其他内容取消
4. 下载完成后自动发送视频 / 图文

## ⚙️ 自定义配置

### 特定用户称呼前缀

在 `src/plugins/video_downloader/__init__.py` 中，将占位符替换为实际的 QQ 号和昵称：

```python
prefix = "好的！尊敬的【你的昵称】大人\n" if event.get_user_id() == "【你的QQ号】" else ""
```

- `【你的QQ号】`：需要特殊称呼的 QQ 号
- `【你的昵称】`：该用户对应的称呼

### 下载大小上限

修改同一个文件中的 `MAX_VIDEO_SIZE`（默认 `50 * 1024 * 1024`，即 50MB）。超过该大小的视频会自动改发文件（避免 QQ 视频消息发送失败）。

## ⚠️ 注意事项

### QQ 版本约束
NapCat 与 QQ 版本强绑定。本项目基于 **QQ 9.9.31 + NapCat v4.18.x** 测试通过。升级 QQ 前请确认 NapCat 是否已适配。

### 抖音下载
- 抖音走第三方免费接口 [dwo.cc](https://dwo.cc)，**可能限流**（返回 429），限流时请稍后重试
- 接口可能失效，失效需更换 `_parse_douyin()` 中的解析接口

### Cookie（可选）
B 站高清视频下载可能需要 cookie。可将浏览器导出的 cookie（Netscape 格式）放到：

```
src/plugins/video_downloader/cookies.txt
```

> ⚠️ 此文件含登录态，**已在 `.gitignore` 中忽略，切勿上传**。

## 📁 目录结构

```
qq-bot/
├── bot.py                      # 入口文件
├── requirements.txt            # Python 依赖
├── .env.example                # 配置示例
├── .gitignore
└── src/plugins/video_downloader/
    ├── __init__.py             # 视频下载插件（核心逻辑）
    ├── cookies.txt             # 可选：B站 cookie（已忽略）
    └── downloads/              # 下载缓存（已忽略）
```

## 📄 许可与声明

本项目仅供个人学习与技术研究使用。请遵守相关平台的服务条款及版权法规，勿用于商业用途或大规模分发受版权保护的内容。
