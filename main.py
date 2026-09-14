"""Run Miao, a local Python desktop pet using the supplied keyed videos."""
from __future__ import annotations

import argparse
import logging
from pathlib import Path
import subprocess
import sys

from pet.paths import default_save, log_root

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description="喵伴 MIAO · 桌宠养成")
    parser.add_argument("--desktop-only", action="store_true", help="只显示桌面小猫")
    parser.add_argument("--save", type=Path, default=default_save(), help="存档位置")
    parser.add_argument("--snapshot-dir", type=Path, help="开发验证：启动后导出应用窗口渲染与状态")
    parser.add_argument("--self-test", type=Path, help="开发验证：使用隔离存档进行打包自检并退出")
    args = parser.parse_args()
    if args.self_test:
        args.self_test = args.self_test.resolve()
        args.save = args.self_test / "test_pet.json"
    from PySide6.QtCore import QLockFile
    from PySide6.QtWidgets import QApplication, QMessageBox

    app = QApplication(sys.argv[:1])
    app.setApplicationName("喵伴 MIAO")
    app.setOrganizationName("MiaoClub")
    from pet.fonts import configure_fonts
    configure_fonts(app)
    app.setQuitOnLastWindowClosed(False)
    args.save = args.save.resolve()
    args.save.parent.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(args.save.with_suffix(".lock")))
    lock.setStaleLockTime(0)
    if not lock.tryLock(100):
        QMessageBox.information(None, "小猫已经在啦", "喵伴已经运行。双击桌面小猫，或点击右下角托盘图标，即可打开面板。")
        return 0
    log_dir = log_root()
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=str(log_dir / "miao.log"), encoding="utf-8", level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    def report_error(kind, value, tb):
        logging.error("Unexpected error", exc_info=(kind, value, tb))
        QMessageBox.critical(None, "喵伴遇到了一点问题", f"{value}\n\n详细信息已写入 {log_dir / 'miao.log'}。")

    sys.excepthook = report_error
    if not (ROOT / "assets" / "manifest.json").exists():
        if getattr(sys, "frozen", False):
            QMessageBox.critical(None, "素材不完整", "程序内的宠物动画缺失，请重新获取完整的 miaomiao.exe。")
            return 1
        QMessageBox.information(None, "正在准备小猫", "首次运行需要处理绿幕视频，可能需要几分钟。处理完成后小猫会自动出现。")
        process = subprocess.run([sys.executable, str(ROOT / "tools" / "prepare_assets.py")], cwd=ROOT, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
        if process.returncode:
            QMessageBox.critical(None, "素材准备失败", "请运行 python tools/prepare_assets.py 查看错误。")
            return 1
    from pet.app import Companion
    companion = Companion(args.save, show_panel=not args.desktop_only)
    if args.snapshot_dir:
        from PySide6.QtCore import QTimer
        import json

        def snapshot():
            args.snapshot_dir.mkdir(parents=True, exist_ok=True)
            companion.panel.grab().save(str(args.snapshot_dir / "native_panel.png"))
            companion.pet.grab().save(str(args.snapshot_dir / "native_pet.png"))
            status = {"platform": app.platformName(), "panel_visible": companion.panel.isVisible(), "pet_visible": companion.pet.isVisible(), "panel_geometry": companion.panel.geometry().getRect(), "pet_geometry": companion.pet.geometry().getRect(), "name": companion.game.state.name, "animation_frame": companion.player.movie.currentFrameNumber()}
            (args.snapshot_dir / "native_status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")

        QTimer.singleShot(1600, snapshot)
    app.aboutToQuit.connect(companion.save)
    if args.self_test:
        from pet.diagnostics import schedule_self_test
        schedule_self_test(companion, args.self_test)
    code = app.exec()
    lock.unlock()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
