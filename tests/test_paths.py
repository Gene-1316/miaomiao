import sys

from pet import paths


def test_source_save_stays_in_project(monkeypatch):
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    assert paths.default_save() == paths.RESOURCE_ROOT / "save_data" / "pet.json"


def test_packaged_save_and_log_stay_outside_extraction(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "user_data"))
    monkeypatch.setattr(paths, "RESOURCE_ROOT", tmp_path / "_MEI123")
    assert paths.default_save() == tmp_path / "user_data" / "miaomiao" / "save_data" / "pet.json"
    assert paths.log_root() == tmp_path / "user_data" / "miaomiao" / "logs"
    assert not paths.default_save().is_relative_to(paths.RESOURCE_ROOT)
