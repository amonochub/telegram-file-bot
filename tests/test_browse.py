from app.handlers import browse

"""
from app.handlers import browse

def test_list_drive_files_returns_list(monkeypatch):
    dummy_files = ["a.txt", "b.pdf"]

    # Тест-заглушка для browse (MEGA)
    monkeypatch.setattr(browse, "list_children", lambda folder_id: dummy_files)

    files = browse.list_drive_files("root_id")
    assert files == dummy_files
"""
