# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules("PySide6") + collect_submodules("spes_tools")

a = Analysis(
    ["run.py"],
    pathex=["app"],
    binaries=[],
    datas=[("assets", "assets")],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Consolle SPES Ginnastica Mestre",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    target_arch=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Consolle SPES Ginnastica Mestre",
)

app = BUNDLE(
    coll,
    name="Consolle SPES Ginnastica Mestre.app",
    icon=None,
    bundle_identifier="it.spesginnasticamestre.consolle",
    info_plist={
        "CFBundleName": "Consolle SPES Ginnastica Mestre",
        "CFBundleDisplayName": "Consolle SPES Ginnastica Mestre",
        "CFBundleShortVersionString": "6.0.5",
        "CFBundleVersion": "6.0.5",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "11.0",
    },
)
