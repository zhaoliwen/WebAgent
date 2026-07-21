# -*- mode: python ; coding: utf-8 -*-
"""OpenManus Windows 打包配置（PyInstaller）。

用法（推荐走 build_windows.ps1）：
  pyinstaller --noconfirm --clean OpenManus.spec
"""

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# 尽量收集 app 包下动态导入的子模块
hiddenimports = (
    collect_submodules("app")
    + [
        "tkinter",
        "tkinter.scrolledtext",
        "pydantic",
        "pydantic_core",
        "loguru",
        "openai",
        "httpx",
        "tiktoken",
        "tomllib",
        "browser_use",
        "playwright",
        "mcp",
    ]
)

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 减小体积：测试与无关开发依赖
        "pytest",
        "pytest_asyncio",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="OpenManus",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # GUI 模式，不弹黑框
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
    upx=True,
    upx_exclude=[],
    name="OpenManus",
)
