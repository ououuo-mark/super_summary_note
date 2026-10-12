# VideoNotes Web 使用说明

## 快速启动

### 1. 环境要求
- Python 环境（已安装项目依赖）
- 确保已安装所有 requirements.txt 中的依赖包
- 特别注意：需要安装阿里云 SDK（如未安装会有提示）

### 2. 启动 Web 服务

使用对应的 Python 环境运行：

```bash
# 使用 ssnm 环境启动（根据你的实际环境调整）
D:\miniconda\envs\ssnm\python.exe web_server.py

# 或者如果已激活环境
python web_server.py
```

启动成功后，服务运行在：**http://127.0.0.1:8000**

### 3. 使用流程

1. **打开浏览器** 访问 http://127.0.0.1:8000
2. **填写配置参数**（左侧表单）：
   - 大模型配置：model_name, api_key, base_url
   - Markdown 保存目录：生成的笔记保存位置
   - 阿里云 OSS 配置：用于视频临时存储
   - 通义听悟配置：用于语音转写
3. **点击"保存并应用配置"**，配置会持久化到本地
4. **上传视频**（右侧上传区域）：
   - 支持拖拽或点击选择多个 MP4 视频文件
   - 点击"开始批量总结"提交任务
5. **实时监控任务进度**：
   - 处理中：显示实时耗时与进度动画
   - 完成：显示"下载 PDF 笔记"按钮
   - 失败：显示错误信息
6. **下载成果**：任务完成后点击下载按钮获取 PDF 笔记

## 核心特性

✅ **简约现代界面**：基于 Starlette 的轻量级前后端分离架构  
✅ **配置持久化**：所有配置自动保存到用户目录 `~/.videonotes_config.json`  
✅ **批量处理**：支持同时上传多个视频并发总结  
✅ **异步任务队列**：后台异步执行，不阻塞前端交互  
✅ **实时状态监控**：每 3 秒自动刷新任务状态  
✅ **一键下载成果**：生成的 PDF 笔记可直接在线下载  

## 文件结构

```
super_summary_note-main/
├── web_server.py          # Web 服务入口（新增）
├── web/                   # 前端资源目录（新增）
│   └── index.html         # 单页应用前端
├── api.py                 # 核心任务处理逻辑
├── tingwu.py             # 阿里云听悟转写
├── graph.py              # 大模型总结
├── markdown_process.py   # 视频截帧与 Markdown 处理
├── to_pdf.py             # PDF 导出
└── uploads/              # 视频上传临时目录（自动创建）
```

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 前端主页 |
| `/api/config` | GET | 获取当前配置 |
| `/api/config` | POST | 保存配置并即时生效 |
| `/api/upload` | POST | 批量上传视频并创建任务 |
| `/api/tasks` | GET | 获取所有任务状态 |
| `/api/tasks/{id}/cancel` | POST | 取消指定任务 |
| `/api/tasks/{id}` | DELETE | 删除任务记录 |
| `/api/tasks/{id}/download` | GET | 下载任务生成的 PDF |

## 注意事项

1. **首次使用**需先完整填写所有配置项（11 个必填项）
2. 确保 **Markdown 保存目录** 存在且有写入权限
3. 视频文件会先上传到 `uploads/` 目录，处理完成后可手动清理
4. 任务执行时间取决于视频时长与网络状态（转写 + AI 总结 + 截帧 + PDF 生成）
5. 如遇依赖缺失错误，请按提示安装对应的 Python 包

## 原有入口保留

原有的命令行方式 `api.py` 仍然可用：

```python
from api import set_env, task_main
import asyncio

set_env(model_name="...", api_key="...", ...)
asyncio.run(task_main(r"D:\video_save\test.mp4"))
```

---

**开发完成时间**：2026-10-12  
**技术栈**：Starlette + Uvicorn + Vanilla JS + 简约现代 CSS 设计
