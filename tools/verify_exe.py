"""Run the release from a standalone Unicode path without Python on PATH."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "dist" / "miaomiao.exe"
test_root = ROOT / "artifacts" / ("exe-release-check-" + time.strftime("%Y%m%d-%H%M%S"))
standalone = test_root / "独立程序 folder"
standalone.mkdir(parents=True, exist_ok=False)
executable = standalone / "miaomiao.exe"
shutil.copy2(source, executable)
env = os.environ.copy()
windows = Path(env.get("SystemRoot", "C:/Windows"))
env["PATH"] = str(windows / "System32") + os.pathsep + str(windows)
for key in ["PYTHONHOME", "PYTHONPATH", "QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH", "QML2_IMPORT_PATH", "QT_QPA_PLATFORM"]:
    env.pop(key, None)
env["LOCALAPPDATA"] = str(test_root / "isolated-user-data")
output = test_root / "result"
result = {"exe": str(source), "sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "bytes": source.stat().st_size, "isolated_location": str(executable), "runs": []}
for run in (1, 2):
    previous = json.loads((output / "test_pet.json").read_text(encoding="utf-8")) if run == 2 else None
    start = time.monotonic()
    completed = subprocess.run([str(executable), "--self-test", str(output)], cwd=standalone, env=env, timeout=150, capture_output=True)
    if completed.returncode:
        (test_root / "boot-error.txt").write_bytes(completed.stdout + completed.stderr)
    assert completed.returncode == 0, f"Executable returned {completed.returncode}; inspect {output}"
    report = json.loads((output / "report.json").read_text(encoding="utf-8"))
    assert report["passed"] and report["frozen"] and len(report["decoded_clips"]) == 27
    assert Path(report["default_save"]).is_relative_to(Path(env["LOCALAPPDATA"]))
    saved = json.loads((output / "test_pet.json").read_text(encoding="utf-8"))
    assert saved["name"] == "miaomiao"
    assert not Path(report["resource_root"]).exists(), "One-file temporary extraction directory was not cleaned up"
    if previous:
        assert saved["coins"] == previous["coins"] + 2, "Saved economy did not survive process restart"
        assert saved["xp"] > previous["xp"], "Growth did not survive process restart"
    result["runs"].append({"run": run, "seconds": round(time.monotonic() - start, 2), "report": report})
    print(f"PASS {run}/2: standalone executable, 27 clips, game actions, persistent save", flush=True)
result["passed"] = True
(ROOT / "artifacts" / "exe-verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Verified {source} ({source.stat().st_size / 1024 / 1024:.1f} MiB)", flush=True)
