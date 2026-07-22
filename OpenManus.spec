# -*- mode: python ; coding: utf-8 -*-
"""livan Windows 打包配置（PyInstaller）。

用法（推荐走 build_windows.ps1）：
  pyinstaller --noconfirm --clean OpenManus.spec
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

block_cipher = None

hiddenimports = collect_submodules("app") + [
    "tkinter",
    "tkinter.scrolledtext",
    "markdown",
    "markdown.extensions.fenced_code",
    "markdown.extensions.tables",
    "markdown.extensions.nl2br",
    "markdown.extensions.sane_lists",
    "tkinterweb",
    "pydantic",
    "pydantic_core",
    "loguru",
    "openai",
    "httpx",
    "httpx._transports.default",
    "tiktoken",
    "tiktoken_ext",
    "tiktoken_ext.openai_public",
    "tomllib",
    "certifi",
    "anyio",
    "anyio._backends._asyncio",
    "mcp",
    "mcp.client",
    "mcp.client.sse",
    "mcp.client.stdio",
    "multiprocessing",
    "multiprocessing.popen_spawn_win32",
    # 浏览器相关按需加载；仍列入 hiddenimports，便于真正使用时可用
    "browser_use",
    "playwright",
    "playwright.sync_api",
    "playwright.async_api",
    "greenlet",
]

datas = []
datas += collect_data_files("certifi")
try:
    datas += collect_data_files("tiktoken")
except Exception:
    pass
try:
    datas += collect_data_files("tiktoken_ext")
except Exception:
    pass
# browser_use 操作网页依赖 dom/buildDomTree.js（色块高亮与元素索引）
try:
    datas += collect_data_files("browser_use")
except Exception:
    pass
try:
    datas += collect_data_files("tkinterweb")
except Exception:
    pass
try:
    datas += collect_data_files("markdown")
except Exception:
    pass
for pkg in ("openai", "httpx", "certifi", "browser_use", "playwright", "markdown", "tkinterweb"):
    try:
        datas += copy_metadata(pkg)
    except Exception:
        pass

# 排除 torch 等重型原生库：打包后常见 WinError 1114（DLL 初始化失败）
excludes = [
    "pytest",
    "pytest_asyncio",
    "torch",
    "torchvision",
    "torchaudio",
    "torchgen",
    "functorch",
    "triton",
    "nvidia",
    "tensorflow",
    "tensorboard",
    "keras",
    "jax",
    "jaxlib",
    "transformers",
    "sentence_transformers",
    "sklearn",
    "scikit-learn",
]

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 二次清理：分析阶段仍可能扫到的 torch 相关二进制/纯 Python 模块
a.binaries = [b for b in a.binaries if "torch" not in b[0].lower() and "nvidia" not in b[0].lower()]
a.datas = [d for d in a.datas if "torch" not in d[0].lower() and "nvidia" not in d[0].lower()]
a.pure = [p for p in a.pure if not p[0].startswith("torch") and not p[0].startswith("nvidia")]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="livan",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="livan",
)
