from pathlib import Path
from PySide6.QtGui import QFont, QFontDatabase


def configure_fonts(app):
    """Explicit loading also makes headless Windows renders use CJK glyphs."""
    for file in ("msyh.ttc", "msyhbd.ttc"):
        path = Path("C:/Windows/Fonts") / file
        if path.exists():
            QFontDatabase.addApplicationFont(str(path))
    app.setFont(QFont("Microsoft YaHei UI", 10))
