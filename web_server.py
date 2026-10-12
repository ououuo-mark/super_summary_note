"""
Web 服务入口 - 提供简约现代风格的 Web 界面
支持在线配置参数、批量上传多个 MP4 视频、后台异步转写总结及导出成果下载
"""

import os
import sys
import json
import time
import uuid
import asyncio
import threading
import traceback
import webbrowser
import uvicorn
from pathlib import Path
from starlette.applications import Starlette
from starlette.responses import JSONResponse, FileResponse, HTMLResponse
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles

try:
    from api import set_env, task_main, global_loop
except Exception as e:
    print(f"⚠️ 导入 api 模块提示: {e} (如缺少阿里云 SDK，请先安装 pip install aliyun-python-sdk-core alibabacloud_oss_v2)")
    set_env = None
    task_main = None
    global_loop = None

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = Path.home() / ".videonotes_config.json"
tasks_registry = {}

def load_config_data():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_config_data(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        apply_env_from_config(config)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def apply_env_from_config(config):
    if not set_env:
        return
    set_env(
        model_name=config.get("model_name", ""),
        api_key=config.get("api_key", ""),
        base_url=config.get("base_url", ""),
        oss_ak=config.get("oss_ak", ""),
        oss_sk=config.get("oss_sk", ""),
        bucket_name=config.get("bucket_name", ""),
        region=config.get("region", ""),
        markdown_file_path=config.get("save_markdown_path", "") or config.get("markdown_file_path", ""),
        tingwu_ak=config.get("tingwu_ak", ""),
        tingwu_sk=config.get("tingwu_sk", ""),
        tingwu_appkey=config.get("tingwu_appkey", ""),
    )

# 初始化时应用已有配置
initial_cfg = load_config_data()
if initial_cfg:
    try:
        apply_env_from_config(initial_cfg)
    except Exception as e:
        print(f"初始化配置失败: {e}")

# ────────────────────── API 路由 ──────────────────────

async def api_get_config(request):
    cfg = load_config_data()
    # 兼容 markdown_file_path 与 save_markdown_path
    if "save_markdown_path" in cfg and "markdown_file_path" not in cfg:
        cfg["markdown_file_path"] = cfg["save_markdown_path"]
    return JSONResponse(cfg)

async def api_save_config(request):
    try:
        body = await request.json()
        if "markdown_file_path" in body:
            body["save_markdown_path"] = body["markdown_file_path"]
        res = save_config_data(body)
        return JSONResponse(res)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)

def _on_task_done(task_id, future):
    if task_id not in tasks_registry:
        return
    try:
        result = future.result()
        tasks_registry[task_id]["status"] = "completed"
        tasks_registry[task_id]["result"] = str(result) if result else ""
    except asyncio.CancelledError:
        tasks_registry[task_id]["status"] = "cancelled"
    except Exception as e:
        tasks_registry[task_id]["status"] = "error"
        tasks_registry[task_id]["error"] = str(e)
        traceback.print_exc()

async def api_upload_and_run(request):
    """
    处理多视频文件上传并创建总结任务
    """
    try:
        form = await request.form()
    except Exception as e:
        return JSONResponse({"ok": False, "error": f"解析表单失败: {e}"}, status_code=400)

    # 检查环境变量是否完整
    cfg = load_config_data()
    required = [
        "oss_ak", "oss_sk", "tingwu_ak", "tingwu_sk", "tingwu_appkey",
        "api_key", "base_url", "model_name",
        "save_markdown_path", "bucket_name", "region"
    ]
    missing = [k for k in required if not cfg.get(k, "").strip()]
    if missing:
        return JSONResponse({
            "ok": False, 
            "error": f"请先完善配置项: {', '.join(missing)}"
        }, status_code=400)

    files = form.getlist("videos") or form.getlist("file") or form.getlist("files")
    if not files:
        return JSONResponse({"ok": False, "error": "请至少上传一个 mp4 视频文件"}, status_code=400)

    created_tasks = []
    for upload_file in files:
        filename = getattr(upload_file, "filename", None) or f"video_{uuid.uuid4().hex[:6]}.mp4"
        if not filename.lower().endswith(".mp4"):
            continue

        task_id = uuid.uuid4().hex[:8]
        safe_name = f"{task_id}_{filename}"
        saved_path = UPLOAD_DIR / safe_name

        content = await upload_file.read()
        with open(saved_path, "wb") as f:
            f.write(content)

        if not task_main or not global_loop:
            return JSONResponse({"ok": False, "error": "api 核心模块未成功加载，请检查后台日志"}, status_code=500)

        future = asyncio.run_coroutine_threadsafe(task_main(str(saved_path)), global_loop)
        tasks_registry[task_id] = {
            "id": task_id,
            "file_name": filename,
            "file_path": str(saved_path),
            "status": "processing",
            "result": None,
            "error": None,
            "future": future,
            "start_time": time.time(),
        }
        future.add_done_callback(lambda f, tid=task_id: _on_task_done(tid, f))
        created_tasks.append({
            "id": task_id,
            "file_name": filename
        })

    if not created_tasks:
        return JSONResponse({"ok": False, "error": "没有找到有效的 .mp4 视频文件"}, status_code=400)

    return JSONResponse({"ok": True, "tasks": created_tasks})

async def api_get_tasks(request):
    result = []
    for tid, t in sorted(tasks_registry.items(), key=lambda x: x[1]["start_time"], reverse=True):
        elapsed = int(time.time() - t["start_time"])
        result.append({
            "id": t["id"],
            "file_name": t["file_name"],
            "status": t["status"],
            "result": t.get("result"),
            "error": t.get("error"),
            "elapsed": elapsed,
        })
    return JSONResponse({"ok": True, "tasks": result})

async def api_cancel_task(request):
    task_id = request.path_params.get("task_id")
    if task_id in tasks_registry:
        t = tasks_registry[task_id]
        future = t.get("future")
        if future and not future.done():
            future.cancel()
            t["status"] = "cancelled"
            return JSONResponse({"ok": True})
    return JSONResponse({"ok": False, "error": "任务不存在或已结束"}, status_code=404)

async def api_delete_task(request):
    task_id = request.path_params.get("task_id")
    if task_id in tasks_registry:
        del tasks_registry[task_id]
        return JSONResponse({"ok": True})
    return JSONResponse({"ok": False, "error": "任务不存在"}, status_code=404)

async def api_download_result(request):
    task_id = request.path_params.get("task_id")
    if task_id not in tasks_registry:
        return JSONResponse({"error": "任务不存在"}, status_code=404)
    task = tasks_registry[task_id]
    result_path = task.get("result")
    if not result_path or not os.path.exists(result_path):
        return JSONResponse({"error": "输出文件不存在或尚未生成"}, status_code=404)

    return FileResponse(
        path=result_path,
        filename=os.path.basename(result_path),
        media_type="application/pdf" if result_path.endswith(".pdf") else "application/octet-stream"
    )

async def index_page(request):
    index_file = WEB_DIR / "index.html"
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<h1>Web 前端未构建，请检查 web/index.html</h1>", status_code=404)

routes = [
    Route("/", index_page),
    Route("/api/config", api_get_config, methods=["GET"]),
    Route("/api/config", api_save_config, methods=["POST"]),
    Route("/api/tasks", api_get_tasks, methods=["GET"]),
    Route("/api/upload", api_upload_and_run, methods=["POST"]),
    Route("/api/tasks/{task_id}/cancel", api_cancel_task, methods=["POST"]),
    Route("/api/tasks/{task_id}", api_delete_task, methods=["DELETE"]),
    Route("/api/tasks/{task_id}/download", api_download_result, methods=["GET"]),
    Mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")
]

app = Starlette(routes=routes)

def _open_browser(url, delay=1.5):
    def _open():
        time.sleep(delay)
        webbrowser.open(url)
    threading.Thread(target=_open, daemon=True).start()

def run_server(host="127.0.0.1", port=8000):
    url = f"http://{host}:{port}"
    print("=" * 60)
    print(f"🚀 视频智能笔记服务已启动: {url}")
    print("=" * 60)
    _open_browser(url)
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    run_server()
