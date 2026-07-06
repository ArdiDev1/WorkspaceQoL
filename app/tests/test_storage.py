from wlm.models import Layout, WindowSlot
from wlm.storage import LayoutStorageService


def test_load_layouts_when_file_missing_returns_empty():
    svc = LayoutStorageService()
    assert svc.load_layouts() == []


def test_save_creates_new_layout():
    svc = LayoutStorageService()
    layout = Layout(name="office", windows=[WindowSlot(title="Notepad", width=800, height=600)])

    svc.save_layout(layout)

    loaded = svc.load_layouts()
    assert [l.name for l in loaded] == ["office"]
    assert loaded[0].windows[0].title == "Notepad"


def test_save_upserts_by_case_insensitive_name():
    svc = LayoutStorageService()
    svc.save_layout(Layout(name="Office", windows=[]))
    svc.save_layout(Layout(name="office", windows=[WindowSlot(title="Updated")]))

    loaded = svc.load_layouts()

    assert len(loaded) == 1
    assert loaded[0].windows[0].title == "Updated"


def test_delete_removes_layout_case_insensitively():
    svc = LayoutStorageService()
    svc.save_layout(Layout(name="temp", windows=[]))

    svc.delete_layout("TEMP")

    assert svc.load_layouts() == []


def test_delete_missing_layout_is_a_no_op():
    svc = LayoutStorageService()
    svc.save_layout(Layout(name="keep-me", windows=[]))

    svc.delete_layout("does-not-exist")

    assert [l.name for l in svc.load_layouts()] == ["keep-me"]
