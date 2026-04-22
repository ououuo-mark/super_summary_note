"""
视频笔记助手 - 主入口
"""

import sys
import os
import io

def _fix_stdio():
    log_path = os.path.join(os.path.expanduser("~"), ".videonotes_debug.log")
    try:
        log_file = open(log_path, "w", encoding="utf-8")
    except Exception:
        log_file = io.StringIO()

    if sys.stdout is None or not hasattr(sys.stdout, 'write'):
        sys.stdout = log_file
    else:
        try:
            sys.stdout = io.TextIOWrapper(
                sys.stdout.buffer, encoding='utf-8', errors='replace'
            )
        except Exception:
            sys.stdout = log_file

    if sys.stderr is None or not hasattr(sys.stderr, 'write'):
        sys.stderr = log_file
    else:
        try:
            sys.stderr = io.TextIOWrapper(
                sys.stderr.buffer, encoding='utf-8', errors='replace'
            )
        except Exception:
            sys.stderr = log_file

_fix_stdio()

import webview
import json
import time
import uuid
import asyncio
import traceback
import subprocess
import platform

IS_FROZEN = getattr(sys, 'frozen', False)

print(f"[BOOT] Python {sys.version}")
print(f"[BOOT] frozen={IS_FROZEN}")
print(f"[BOOT] exe={sys.executable}")


# ────────────────────── 路径处理 ──────────────────────

def get_resource_path(relative_path):
    if IS_FROZEN:
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


# ────────────────────── Playwright 自动安装 ──────────────────────

BROWSERS_DIR = os.path.join(os.path.expanduser("~"), ".videonotes_browsers")


def setup_playwright_env():
    os.makedirs(BROWSERS_DIR, exist_ok=True)
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = BROWSERS_DIR


def is_chromium_installed():
    if not os.path.exists(BROWSERS_DIR):
        return False
    for entry in os.listdir(BROWSERS_DIR):
        if entry.startswith("chromium"):
            chromium_dir = os.path.join(BROWSERS_DIR, entry)
            if os.path.isdir(chromium_dir) and os.listdir(chromium_dir):
                return True
    return False


def install_chromium():
    print("=" * 50)
    print("  [SETUP] Downloading PDF browser component...")
    print("  This may take 1~3 minutes...")
    print("=" * 50)

    # ★★★ 方法 1：用 Playwright 内置驱动（打包环境和开发环境都能用）★★★
    try:
        from playwright._impl._driver import compute_driver_executable, get_driver_env
        driver = str(compute_driver_executable())
        env = get_driver_env()
        env["PLAYWRIGHT_BROWSERS_PATH"] = BROWSERS_DIR
        print(f"[SETUP] Using playwright driver: {driver}")
        result = subprocess.run(
            [driver, "install", "chromium"],
            env=env, capture_output=True, text=True, timeout=600,
        )
        if result.returncode == 0:
            print("[OK] Browser installed via playwright driver")
            return True
        print(f"[!!] Driver method failed: {result.stderr[:300]}")
    except Exception as e:
        print(f"[!!] Driver method error: {e}")

    # ★★★ 方法 2：仅在非打包环境才用 sys.executable ★★★
    if not IS_FROZEN:
        try:
            env = os.environ.copy()
            env["PLAYWRIGHT_BROWSERS_PATH"] = BROWSERS_DIR
            result = subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"],
                env=env, capture_output=True, text=True, timeout=600,
            )
            if result.returncode == 0:
                print("[OK] Browser installed via python -m playwright")
                return True
            print(f"[!!] python -m method failed: {result.stderr[:300]}")
        except Exception as e:
            print(f"[!!] python -m method error: {e}")

        # 方法 3：直接调 playwright CLI
        try:
            env = os.environ.copy()
            env["PLAYWRIGHT_BROWSERS_PATH"] = BROWSERS_DIR
            result = subprocess.run(
                ["playwright", "install", "chromium"],
                env=env, capture_output=True, text=True, timeout=600,
                shell=True,
            )
            if result.returncode == 0:
                print("[OK] Browser installed via playwright CLI")
                return True
            print(f"[!!] CLI method failed: {result.stderr[:300]}")
        except Exception as e:
            print(f"[!!] CLI method error: {e}")
    else:
        print("[!!] Frozen environment, skipping sys.executable methods to prevent fork bomb")

    print("[ERR] All browser install methods failed")
    return False


def ensure_playwright():
    setup_playwright_env()
    if is_chromium_installed():
        print("[OK] Chromium already installed")
        return True
    print("[*] Chromium not found, installing...")
    return install_chromium()


# ────────────────────── 配置 ──────────────────────

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".videonotes_config.json")

tasks_registry = {}


class Api:
    def __init__(self):
        self._window = None
        self._browser_ready = False

    def set_window(self, window):
        self._window = window

    def set_browser_ready(self, ready):
        self._browser_ready = ready

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_config(self, config):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            self._apply_env(config)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _apply_env(self, config):
        from api import set_env
        set_env(
            model_name=config.get("model_name", ""),
            api_key=config.get("api_key", ""),
            base_url=config.get("base_url", ""),
            oss_ak=config.get("oss_ak", ""),
            oss_sk=config.get("oss_sk", ""),
            bucket_name=config.get("bucket_name", ""),
            region=config.get("region", ""),
            markdown_file_path=config.get("save_markdown_path", ""),
            tingwu_ak=config.get("tingwu_ak", ""),
            tingwu_sk=config.get("tingwu_sk", ""),
            tingwu_appkey=config.get("tingwu_appkey", ""),
        )

    def select_files(self):
        try:
            result = self._window.create_file_dialog(
                webview.OPEN_DIALOG,
                allow_multiple=True,
                file_types=("Video files (*.mp4)",),
            )
            if result:
                return list(result)
        except Exception as e:
            print(f"File dialog error: {e}")
        return []

    def select_folder(self):
        try:
            result = self._window.create_file_dialog(webview.FOLDER_DIALOG)
            if result and len(result) > 0:
                return result[0]
        except Exception as e:
            print(f"Folder dialog error: {e}")
        return None

    def submit_tasks(self, file_paths):
        from api import task_main, global_loop
        submitted = []
        for fp in file_paths:
            task_id = uuid.uuid4().hex[:8]
            future = asyncio.run_coroutine_threadsafe(task_main(fp), global_loop)
            tasks_registry[task_id] = {
                "id": task_id,
                "file_name": os.path.basename(fp),
                "file_path": fp,
                "status": "processing",
                "result": None,
                "error": None,
                "future": future,
                "start_time": time.time(),
            }
            future.add_done_callback(
                lambda f, tid=task_id: self._on_task_done(tid, f)
            )
            submitted.append({"id": task_id, "file_name": os.path.basename(fp)})
        return submitted

    def _on_task_done(self, task_id, future):
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

    def get_tasks(self):
        result = []
        for tid, t in tasks_registry.items():
            elapsed = int(time.time() - t["start_time"])
            result.append({
                "id": t["id"],
                "file_name": t["file_name"],
                "status": t["status"],
                "result": t.get("result"),
                "error": t.get("error"),
                "elapsed": elapsed,
            })
        return result
    
    
    def open_url(self, url):
        """用系统默认浏览器打开 URL"""
        import webbrowser
        try:
            webbrowser.open(url)
            return True
        except Exception:
            return False

    def cancel_task(self, task_id):
        if task_id in tasks_registry:
            future = tasks_registry[task_id].get("future")
            if future and not future.done():
                future.cancel()
                tasks_registry[task_id]["status"] = "cancelled"
                return True
        return False

    def remove_task(self, task_id):
        if task_id in tasks_registry:
            del tasks_registry[task_id]
            return True
        return False

    def open_file(self, path):
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":
                subprocess.call(["open", path])
            else:
                subprocess.call(["xdg-open", path])
            return True
        except Exception:
            return False

    def open_folder(self, path):
        try:
            if platform.system() == "Windows":
                subprocess.Popen(f'explorer /select,"{path}"')
            elif platform.system() == "Darwin":
                subprocess.call(["open", "-R", path])
            else:
                subprocess.call(["xdg-open", os.path.dirname(path)])
            return True
        except Exception:
            return False

    def check_config_complete(self):
        config = self.load_config()
        required = [
            "oss_ak", "oss_sk", "tingwu_ak", "tingwu_sk", "tingwu_appkey",
            "api_key", "base_url", "model_name",
            "save_markdown_path", "bucket_name", "region",
        ]
        missing = [k for k in required if not config.get(k, "").strip()]
        return {"complete": len(missing) == 0, "missing": missing}

    def get_browser_status(self):
        return {"ready": self._browser_ready}
    
    def has_agreed_disclaimer(self):
        """检查用户是否已同意免责声明"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
                return config.get("_disclaimer_agreed", False) is True
            except Exception:
                return False
        return False
    def save_disclaimer_agreement(self):
        """保存用户已同意免责声明"""
        config = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except Exception:
                config = {}
        config["_disclaimer_agreed"] = True
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    def exit_app(self):
        """用户拒绝协议，关闭窗口"""
        if self._window:
            self._window.destroy()
        os._exit(0)


# ────────────────────── 启动 ──────────────────────

def main():
    try:
        print("[BOOT] ensure_playwright...")
        browser_ok = ensure_playwright()

        api = Api()
        api.set_browser_ready(browser_ok)

        print("[BOOT] importing api module...")
        import api as api_module  # noqa

        print("[BOOT] loading config...")
        config = api.load_config()
        if config:
            try:
                api._apply_env(config)
                print("[OK] Config loaded")
            except Exception as e:
                print(f"[!!] Config load failed: {e}")
        else:
            print("[i] First launch")

        web_dir = get_resource_path("web")
        index_path = os.path.join(web_dir, "index.html")
        print(f"[BOOT] web_dir={web_dir}")
        print(f"[BOOT] index exists={os.path.exists(index_path)}")

        window = webview.create_window(
            title="VideoNotes",
            url=index_path,
            js_api=api,
            width=1000,
            height=700,
            min_size=(820, 580),
            background_color="#FFFAF5",
        )
        api.set_window(window)

        print("[BOOT] starting webview...")
        webview.start(debug=False)

    except Exception as e:
        print(f"[FATAL] {type(e).__name__}: {e}")
        traceback.print_exc()
        try:
            import ctypes
            log_path = os.path.join(os.path.expanduser("~"), ".videonotes_debug.log")
            ctypes.windll.user32.MessageBoxW(
                0,
                f"Startup failed:\n{e}\n\nLog: {log_path}",
                "VideoNotes Error",
                0x10
            )
        except Exception:
            pass

    os._exit(0)


if __name__ == "__main__":
    main()