from __future__ import annotations

import ctypes
import json
import platform
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CPP_BUILD_DIR = ROOT / "build"


def _library_name() -> str:
    system = platform.system().lower()
    if system == "darwin":
        return "libcertigap_core.dylib"
    if system == "windows":
        return "certigap_core.dll"
    return "libcertigap_core.so"


def library_path() -> Path:
    return CPP_BUILD_DIR / _library_name()


class CppCertiGap:
    def __init__(self, path: Path | None = None) -> None:
        path = path or library_path()
        if not path.exists():
            raise FileNotFoundError(f"C++ core library not found at {path}")
        self._lib = ctypes.CDLL(str(path))
        self._lib.certigap_fit_json.argtypes = [
            ctypes.POINTER(ctypes.c_double),
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_double,
        ]
        self._lib.certigap_fit_json.restype = ctypes.c_void_p
        self._lib.certigap_free_string.argtypes = [ctypes.c_void_p]
        self._lib.certigap_free_string.restype = None

    def fit(self, weights: list[float], budget: int, eta: float) -> dict:
        n = len(weights)
        arr = (ctypes.c_double * n)(*weights)
        raw_ptr = self._lib.certigap_fit_json(arr, n, budget, eta)
        if not raw_ptr:
            raise RuntimeError("C++ core returned null")
        try:
            payload = ctypes.string_at(raw_ptr).decode("utf-8")
        finally:
            self._lib.certigap_free_string(raw_ptr)
        return json.loads(payload)
