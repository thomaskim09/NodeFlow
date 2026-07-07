from __future__ import annotations

import main


class _Kernel32:
    def __init__(self, last_error: int):
        self.last_error = last_error
        self.closed_handles: list[int] = []

    def CreateMutexW(self, _security, _initial_owner, _name):
        return 123

    def GetLastError(self):
        return self.last_error

    def CloseHandle(self, handle):
        self.closed_handles.append(handle)
        return True


class _WinDLL:
    def __init__(self, kernel32: _Kernel32):
        self.kernel32 = kernel32


def test_single_instance_lock_rejects_second_windows_launch(monkeypatch):
    kernel32 = _Kernel32(main.ERROR_ALREADY_EXISTS)
    monkeypatch.setattr(main.sys, "platform", "win32")
    monkeypatch.setattr(main.ctypes, "windll", _WinDLL(kernel32), raising=False)

    assert main.acquire_single_instance_lock() is False
    assert kernel32.closed_handles == [123]
