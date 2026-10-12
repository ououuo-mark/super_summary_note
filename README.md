# 🎬 Super Summary Note (视频智能总结笔记助手)

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python" alt="Python Version" />
  <img src="https://img.shields.io/badge/Framework-Starlette%20%7C%20FastAPI-green?style=flat-square" alt="Framework" />
  <img src="https://img.shields.io/badge/AI-DeepSeek%20%2F%20Qwen-purple?style=flat-square" alt="LLM Support" />
  <img src="https://img.shields.io/badge/Speech%20Recognition-Aliyun%20Tingwu-orange?style=flat-square" alt="Tingwu" />
  <img src="https://img.shields.io/badge/License-MIT-lightgrey?style=flat-square" alt="License" />
</p>

<p align="center">
  <b>一键将音视频长内容转化为结构清晰、图文并茂的高质量 Markdown 与 PDF 精品笔记。</b>
  <br />
  集成了语音转写、大模型分层提炼、关键帧画面提取与高颜值排版导出，支持 Web UI 与客户端双模式体验。
</p>

---

## ✨ 核心特性

- 🎙️ **高精度语音转写**：依托阿里云通义听悟 API，秒级定位视频音频发言与时间戳。
- 🧠 **大模型深度总结**：兼容 DeepSeek、通义千问等主流大语言模型，自动提炼核心议题、思维导图式脉络与要点摘要。
- 📸 **时间戳智能截帧**：依据关键时间节点对视频自动截取高清图解画面，避免死板文字，实现图文互印。
- 📄 **多端精美导出**：一键生成排版工整的 Markdown 讲义，并支持批量渲染导出为高质感 PDF。
- 🖥️ **现代友好交互**：
  - **Web 模式**：内置现代化 Starlette 网页界面，支持批量拖拽上传、异步处理队列、实时状态与进度展示。
  - **GUI 客户端**：内置 `pywebview` 桌面窗体支持，开箱即用。
  - **API 模式**：提供清晰的代码级调用入口，方便无缝集成到自动化流水线。
- ⚙️ **配置持久化**：用户凭据与大模型参数本地保存（`~/.videonotes_config.json`），随时自由切换。

---

## 🛠️ 项目架构

```text
super_summary_note/
├── web/                    # 现代化 Web 前端静态界面
│   └── index.html          # 单页应用界面 (上传、配置、实时进度跟踪)
├── web_server.py           # Starlette Web 后端服务
├── main.py                 # pywebview 桌面客户端入口
├── api.py                  # 核心任务调度与流水线入口
├── tingwu.py               # 阿里云听悟 ASR 语音转写
├── graph.py                # LLM 结构化总结提炼
├── markdown_process.py     # 视频智能截帧与图文拼接逻辑
├── to_pdf.py               # Markdown 转高颜值 PDF 渲染器
├── requirements.txt        # Python 依赖清单
└── run.bat                 # Windows 一键启动脚本
```

---

## 🚀 快速开始

### 1. 克隆仓库与安装依赖

```bash
git clone https://github.com/ououuo-mark/super_summary_note.git
cd super_summary_note

# 建议在虚拟环境中安装
pip install -r requirements.txt
```

> **系统提示**：处理视频截帧需确保系统已安装 [FFmpeg](https://ffmpeg.org/) 并已配置在系统 `PATH` 环境变量中。

### 2. 启动方式

#### 方式 A：Web 服务启动（推荐）

直接双击运行根目录下的 `run.bat`，或者在终端运行：

```bash
python web_server.py
```

服务启动后，浏览器打开访问：**`http://127.0.0.1:8000`** 即可进入操作面板。

#### 方式 B：桌面客户端启动

```bash
python main.py
```

#### 方式 C：Python 脚本直接调用

```python
import asyncio
from api import set_env, task_main

# 1. 配置参数
set_env(
    model_name="deepseek-v4.1-flash",
    api_key="your_llm_api_key",
    base_url="https://maas.qianwenaiapi.com/compatible-mode/v1",
    oss_ak="your_oss_ak",
    oss_sk="your_oss_sk",
    bucket_name="your_bucket_name",
    region="cn-beijing",
    markdown_file_path=r"D:\output\note.md",
    tingwu_ak="your_tingwu_ak",
    tingwu_sk="your_tingwu_sk",
    tingwu_appkey="your_tingwu_appkey",
)

# 2. 执行视频处理任务
asyncio.run(task_main(r"D:\videos\example.mp4"))
```

---

## 📋 准备与配置项说明

首次使用时，需在 Web 界面或通过 `set_env` 填写如下必要参数：

| 参数类别 | 字段名 | 说明 |
| :--- | :--- | :--- |
| **大模型配置** | `model_name` | LLM 模型名（如 `deepseek-v4.1-flash`、`qwen-plus` 等） |
| | `api_key` | 大模型 API Key |
| | `base_url` | OpenAI 兼容接口地址 |
| **转写与存储** | `oss_ak` / `oss_sk` | 阿里云 AccessKey，用于转写音频临时存储 |
| | `bucket_name` / `region` | OSS 存储空间名称及所在地域 |
| | `tingwu_ak` / `tingwu_sk` | 通义听悟 AccessKey ID 及 Secret |
| | `tingwu_appkey` | 通义听悟应用 AppKey |
| **输出路径** | `markdown_file_path` | 默认 Markdown / PDF 保存目标目录 |

---

## 💡 Web 平台 API 接口

| 接口 | 方法 | 说明 |
| :--- | :---: | :--- |
| `/` | `GET` | Web 交互首页 |
| `/api/config` | `GET` / `POST` | 读取 / 持久化配置信息 |
| `/api/upload` | `POST` | 批量上传音视频并创建解析任务队列 |
| `/api/tasks` | `GET` | 轮询查询所有任务执行进度与状态 |
| `/api/tasks/{id}/cancel` | `POST` | 中止执行中的任务 |
| `/api/tasks/{id}/download` | `GET` | 下载已生成好的 PDF 笔记成果 |

---

## 🔒 安全说明

- 请妥善保管个人云服务密钥与大模型 Token，**切勿将真实 API Key 提交推送到公开 Git 仓库**。
- Web 界面配置已针对敏感项进行掩码保护，并仅保存在本机用户主目录下。

---

## 📄 开源许可证

本项目基于 [MIT License](LICENSE) 开源发布。
