# to_pdf.py
import os
import sys
import pathlib
import uuid
import subprocess
import platform
from playwright.async_api import async_playwright
from markdown_it import MarkdownIt
from mdit_py_plugins.dollarmath import dollarmath_plugin

IS_FROZEN = getattr(sys, 'frozen', False)

# ────────────────────── Playwright 环境 ──────────────────────

BROWSERS_DIR = os.path.join(os.path.expanduser("~"), ".videonotes_browsers")


def _ensure_env():
    os.makedirs(BROWSERS_DIR, exist_ok=True)
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", BROWSERS_DIR)


def _is_chromium_installed():
    if not os.path.exists(BROWSERS_DIR):
        return False
    for entry in os.listdir(BROWSERS_DIR):
        if entry.startswith("chromium"):
            chromium_dir = os.path.join(BROWSERS_DIR, entry)
            if os.path.isdir(chromium_dir) and os.listdir(chromium_dir):
                return True
    return False


def _check_and_install_chromium():
    _ensure_env()

    if _is_chromium_installed():
        return  # 已安装

    print("[to_pdf] Chromium not found, installing...")

    # ── 方法 1：Playwright 内置驱动（打包和开发环境都能用）──
    try:
        from playwright._impl._driver import compute_driver_executable, get_driver_env
        driver = str(compute_driver_executable())
        env = get_driver_env()
        env["PLAYWRIGHT_BROWSERS_PATH"] = BROWSERS_DIR
        print(f"[to_pdf] Using driver: {driver}")
        result = subprocess.run(
            [driver, "install", "chromium"],
            env=env,
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode == 0:
            print("[to_pdf] Chromium installed via driver")
            return
        print(f"[to_pdf] Driver method failed: {result.stderr[:300]}")
    except Exception as e:
        print(f"[to_pdf] Driver method error: {e}")

    # ── 方法 2：python -m playwright（仅开发环境）──
    # ★★★ 打包后 sys.executable 是 VideoNotes.exe，绝对不能调用它 ★★★
    if not IS_FROZEN:
        try:
            env = os.environ.copy()
            env["PLAYWRIGHT_BROWSERS_PATH"] = BROWSERS_DIR
            result = subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"],
                env=env,
                capture_output=True,
                text=True,
                timeout=600,
            )
            if result.returncode == 0:
                print("[to_pdf] Chromium installed via python -m playwright")
                return
            print(f"[to_pdf] python -m method failed: {result.stderr[:300]}")
        except Exception as e:
            print(f"[to_pdf] python -m method error: {e}")

        # ── 方法 3：playwright CLI（仅开发环境）──
        try:
            env = os.environ.copy()
            env["PLAYWRIGHT_BROWSERS_PATH"] = BROWSERS_DIR
            result = subprocess.run(
                ["playwright", "install", "chromium"],
                env=env,
                capture_output=True,
                text=True,
                timeout=600,
                shell=True,
            )
            if result.returncode == 0:
                print("[to_pdf] Chromium installed via CLI")
                return
            print(f"[to_pdf] CLI method failed: {result.stderr[:300]}")
        except Exception as e:
            print(f"[to_pdf] CLI method error: {e}")
    else:
        print("[to_pdf] Frozen env: skipped sys.executable methods (fork bomb prevention)")

    print("[to_pdf] WARNING: All install methods failed, PDF conversion may not work")


# ────────────────────── CSS ──────────────────────

CSS_STYLE = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;700&family=Noto+Sans+SC:wght@300;400;500;700&display=swap');

    :root {
        --text-primary: #1a1a2e;
        --text-secondary: #4a4a6a;
        --text-muted: #7a7a9a;
        --accent: #2c5282;
        --accent-light: #ebf4ff;
        --border: #e2e8f0;
        --border-light: #f0f4f8;
        --bg-code: #f8f9fb;
        --bg-blockquote: #fafbfd;
    }

    * { margin: 0; padding: 0; box-sizing: border-box; }

    body {
        font-family: "Noto Sans SC", "PingFang SC", "Microsoft YaHei", -apple-system, sans-serif;
        font-size: 10pt;
        line-height: 1.85;
        color: var(--text-primary);
        background: #fff;
        padding: 0;
        font-weight: 400;
        text-rendering: optimizeLegibility;
        -webkit-font-smoothing: antialiased;
    }

    h1, h2, h3, h4, h5, h6 {
        font-family: "Noto Serif SC", "STSong", "SimSun", serif;
        color: var(--text-primary);
        font-weight: 700;
        line-height: 1.35;
        margin-bottom: 0.6em;
        page-break-after: avoid;
    }

    h1 {
        font-size: 18pt;
        text-align: center;
        margin-top: 0;
        margin-bottom: 0.5em;
        padding-bottom: 0.5em;
        letter-spacing: 0.05em;
    }

    h1 + p {
        text-align: center;
        color: var(--text-secondary);
        font-size: 9pt;
        margin-bottom: 1.5em;
    }

    h2 {
        font-size: 13.5pt;
        margin-top: 2em;
        padding-bottom: 0.35em;
        border-bottom: 1.5px solid var(--accent);
        color: var(--accent);
    }

    h3 {
        font-size: 11.5pt;
        margin-top: 1.5em;
        color: var(--text-primary);
        padding-left: 0.6em;
        border-left: 3px solid var(--accent);
    }

    h4 {
        font-size: 10.5pt;
        margin-top: 1.2em;
        color: var(--text-secondary);
        font-weight: 600;
    }

    h5, h6 {
        font-size: 10pt;
        margin-top: 1em;
        color: var(--text-secondary);
    }

    p {
        margin-top: 0;
        margin-bottom: 0.75em;
        text-align: justify;
        orphans: 3;
        widows: 3;
    }

    a {
        color: var(--accent);
        text-decoration: none;
        border-bottom: 1px dotted var(--accent);
    }

    code {
        font-family: "JetBrains Mono", "Fira Code", "SF Mono", Consolas, "Liberation Mono", Menlo, monospace;
        font-size: 0.85em;
        background: var(--bg-code);
        border: 1px solid var(--border);
        border-radius: 3px;
        padding: 0.15em 0.35em;
        color: #c7254e;
        word-break: break-word;
    }

    pre {
        margin: 0.8em 0 1.2em 0;
        padding: 1em 1.2em;
        background: var(--bg-code);
        border: 1px solid var(--border);
        border-radius: 5px;
        overflow-x: auto;
        line-height: 1.55;
        page-break-inside: avoid;
    }

    pre > code {
        background: none;
        border: none;
        padding: 0;
        color: var(--text-primary);
        font-size: 8.5pt;
    }

    blockquote {
        margin: 0.8em 0;
        padding: 0.6em 1em;
        background: var(--bg-blockquote);
        border-left: 3px solid var(--accent);
        color: var(--text-secondary);
        font-size: 9.5pt;
        border-radius: 0 4px 4px 0;
    }

    blockquote p:last-child { margin-bottom: 0; }

    ul, ol {
        padding-left: 1.5em;
        margin-bottom: 0.75em;
    }

    li { margin-bottom: 0.25em; }
    li > p { margin-bottom: 0.3em; }
    li > ul, li > ol { margin-top: 0.2em; margin-bottom: 0.2em; }

    table {
        width: 100%;
        border-collapse: collapse;
        margin: 1em 0;
        font-size: 9pt;
        page-break-inside: avoid;
    }

    thead th {
        background: var(--accent);
        color: #fff;
        font-weight: 600;
        padding: 0.5em 0.8em;
        text-align: left;
        font-size: 9pt;
    }

    tbody td {
        padding: 0.45em 0.8em;
        border-bottom: 1px solid var(--border);
    }

    tbody tr:nth-child(even) { background: var(--border-light); }
    tbody tr:hover { background: var(--accent-light); }

    hr {
        border: none;
        height: 1px;
        background: linear-gradient(to right, transparent, var(--border), transparent);
        margin: 2em 0;
    }

    img {
        max-width: 90%;
        display: block;
        margin: 1em auto;
        border-radius: 4px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }

    strong { font-weight: 700; color: var(--text-primary); }
    em { font-style: italic; color: var(--text-secondary); }

    mjx-container {
        overflow-x: auto;
        overflow-y: hidden;
        font-size: 105% !important;
    }

    mjx-container[display="true"] {
        display: block;
        text-align: center;
        margin: 0.8em 0;
        padding: 0.3em 0;
    }

    @media print {
        body { padding: 0; }
        h2, h3 { page-break-after: avoid; }
        pre, table, blockquote { page-break-inside: avoid; }
    }
</style>
"""

KATEX_RESOURCES = """
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"></script>
<script>
document.addEventListener("DOMContentLoaded", function() {
    renderMathInElement(document.body, {
        delimiters: [
            {left: "\\\\(", right: "\\\\)", display: false},
            {left: "\\\\[", right: "\\\\]", display: true}
        ],
        throwOnError: false,
        trust: true
    });
    document.body.setAttribute("data-math-rendered", "true");
});
</script>
"""


# ────────────────────── Markdown 解析器 ──────────────────────

def _create_md_parser():
    md = MarkdownIt("commonmark", {"html": True})
    md.enable("table")
    dollarmath_plugin(md, double_inline=True)

    def render_math_inline(self, tokens, idx, options, env):
        return f"\\({tokens[idx].content}\\)"

    def render_math_block(self, tokens, idx, options, env):
        return f'<div class="katex-display">\\[{tokens[idx].content}\\]</div>'

    md.add_render_rule("math_inline", render_math_inline)
    md.add_render_rule("math_block", render_math_block)
    return md


# ────────────────────── 转换器 ──────────────────────

class MarkdownToPdf:
    def __init__(self):
        self.md_parser = _create_md_parser()

    @staticmethod
    def _read_file_auto_encoding(file_path: pathlib.Path) -> str:
        encodings = ["utf-8", "utf-8-sig", "gbk", "gb2312", "gb18030"]
        for enc in encodings:
            try:
                text = file_path.read_text(encoding=enc)
                print(f"  File encoding: {enc}")
                return text
            except (UnicodeDecodeError, UnicodeError):
                continue
        return file_path.read_text(encoding="utf-8", errors="replace")

    async def markdown_to_pdf(self, md_file_path: str, output_pdf_path: str = None):
        md_path = pathlib.Path(md_file_path)

        if not md_path.is_file():
            raise FileNotFoundError(f"File not found: {md_file_path}")
        if md_path.suffix.lower() != ".md":
            raise ValueError(f"Input must be .md file, got '{md_path.suffix}'")

        if output_pdf_path is None:
            output_pdf_path = md_path.with_suffix(".pdf")
        else:
            output_pdf_path = pathlib.Path(output_pdf_path)

        print(f"Converting: {md_path.name} -> {output_pdf_path.name}")

        # ★ 转换前检查浏览器
        _check_and_install_chromium()

        md_content = self._read_file_auto_encoding(md_path)
        html_body = self.md_parser.render(md_content)

        full_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{md_path.stem}</title>
    {CSS_STYLE}
    {KATEX_RESOURCES}
</head>
<body>
{html_body}
</body>
</html>"""

        temp_html_path = md_path.parent / f"_temp_{uuid.uuid4().hex[:8]}.html"

        try:
            temp_html_path.write_text(full_html, encoding="utf-8")

            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page()

                abs_path = temp_html_path.resolve().as_posix()
                await page.goto(f"file:///{abs_path}")
                await page.wait_for_load_state("networkidle")

                await page.wait_for_function(
                    '() => document.body.getAttribute("data-math-rendered") === "true"',
                    timeout=30000,
                )

                await page.wait_for_timeout(1500)

                await page.pdf(
                    path=str(output_pdf_path),
                    format="A4",
                    print_background=True,
                    margin={
                        "top": "20mm",
                        "bottom": "20mm",
                        "left": "15mm",
                        "right": "15mm",
                    },
                )
                await browser.close()

            print(f"[OK] Saved: {output_pdf_path}")
            return str(output_pdf_path)
        except Exception as e:
            print(f"[ERR] Conversion failed: {e}")
            raise
        finally:
            if temp_html_path.exists():
                os.remove(temp_html_path)


async def to_pdf_main(file_path: str):
    tp = MarkdownToPdf()
    result = await tp.markdown_to_pdf(file_path)
    return str(result)


if __name__ == "__main__":
    import asyncio

    async def _test():
        tp = MarkdownToPdf()
        markdown_file = r"d:\Campus\save_markdown\test\test_markdown.md"
        await tp.markdown_to_pdf(markdown_file)

    asyncio.run(_test())