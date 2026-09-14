# Rebuild: python -m PyInstaller --workpath build/standalone miaomiao.spec
from pathlib import Path
import os
import sys

# The desktop tool environment adds PDF/image DLL directories to PATH. In
# particular Poppler's icuuc.dll is incompatible with Qt's Windows ICU imports.
# Restrict dependency discovery to Python, Windows and Qt's own hook paths.
windows = Path(os.environ.get("SystemRoot", "C:/Windows"))
os.environ["PATH"] = os.pathsep.join([str(Path(sys.executable).parent), str(windows / "System32"), str(windows)])

project = Path(SPECPATH)
asset_data = [(str(project / "assets" / "manifest.json"), "assets")]
for folder, pattern in [("animations", "*.webp"), ("posters", "*.png")]:
    asset_data.extend((str(path), f"assets/{folder}") for path in sorted((project / "assets" / folder).glob(pattern)))

a = Analysis(
    [str(project / "main.py")],
    pathex=[str(project)],
    binaries=[],
    datas=asset_data,
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=["cv2", "numpy", "PIL", "pytest", "tkinter", "matplotlib", "PyQt5", "PyQt6", "PySide2", "IPython", "PySide6.QtTest"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="miaomiao",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    icon=str(project / "assets" / "posters" / "08_loop.png"),
)
