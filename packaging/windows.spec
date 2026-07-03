# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


ROOT = Path(SPECPATH).parent
QT_MATERIAL_ICON_DATAS = collect_data_files("qt_material_icons")
QT_MATERIAL_ICON_IMPORTS = collect_submodules("qt_material_icons")
QT_MATERIAL_ICON_RESOURCE_IMPORTS = collect_submodules("qt_material_icons.resources")

datas = QT_MATERIAL_ICON_DATAS + [
    (str(ROOT / "resource"), "resource"),
    (str(ROOT / "locales"), "locales"),
]

hiddenimports = QT_MATERIAL_ICON_IMPORTS + [
    "qt_material_icons.resources",
    *QT_MATERIAL_ICON_RESOURCE_IMPORTS,
]


a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="NodeFlow",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
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
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="NodeFlow",
)
