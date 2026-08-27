"""Windows user-bound protection for locally stored Sera API credentials."""

from __future__ import annotations

import base64
import ctypes
import os
from ctypes import wintypes


_CRYPTPROTECT_UI_FORBIDDEN = 0x1
_DESCRIPTION = "Sera LLM API credential"


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_ubyte)),
    ]


def protect_secret(secret: str) -> str:
    """Encrypt a secret for the current Windows user and return base64 data."""

    if os.name != "nt":
        raise RuntimeError("Sera in-app credential storage requires Windows DPAPI.")
    if not secret:
        raise ValueError("API credential cannot be empty.")
    plain = secret.encode("utf-8")
    plain_buffer = ctypes.create_string_buffer(plain)
    input_blob = _DataBlob(
        len(plain),
        ctypes.cast(plain_buffer, ctypes.POINTER(ctypes.c_ubyte)),
    )
    output_blob = _DataBlob()
    crypt32 = ctypes.WinDLL("Crypt32.dll", use_last_error=True)
    kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
    crypt32.CryptProtectData.argtypes = [
        ctypes.POINTER(_DataBlob),
        wintypes.LPCWSTR,
        ctypes.POINTER(_DataBlob),
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(_DataBlob),
    ]
    crypt32.CryptProtectData.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    if not crypt32.CryptProtectData(
        ctypes.byref(input_blob),
        _DESCRIPTION,
        None,
        None,
        None,
        _CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(output_blob),
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        encrypted = ctypes.string_at(output_blob.pbData, output_blob.cbData)
        return base64.b64encode(encrypted).decode("ascii")
    finally:
        kernel32.LocalFree(output_blob.pbData)


def unprotect_secret(protected_value: str) -> str:
    """Decrypt base64 DPAPI data for the current Windows user."""

    if os.name != "nt":
        raise RuntimeError("Sera in-app credential storage requires Windows DPAPI.")
    try:
        encrypted = base64.b64decode(protected_value, validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError("Stored API credential is not valid encrypted data.") from exc
    encrypted_buffer = ctypes.create_string_buffer(encrypted)
    input_blob = _DataBlob(
        len(encrypted),
        ctypes.cast(encrypted_buffer, ctypes.POINTER(ctypes.c_ubyte)),
    )
    output_blob = _DataBlob()
    crypt32 = ctypes.WinDLL("Crypt32.dll", use_last_error=True)
    kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
    crypt32.CryptUnprotectData.argtypes = [
        ctypes.POINTER(_DataBlob),
        ctypes.POINTER(wintypes.LPWSTR),
        ctypes.POINTER(_DataBlob),
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(_DataBlob),
    ]
    crypt32.CryptUnprotectData.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    description = wintypes.LPWSTR()
    if not crypt32.CryptUnprotectData(
        ctypes.byref(input_blob),
        ctypes.byref(description),
        None,
        None,
        None,
        _CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(output_blob),
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        plain = ctypes.string_at(output_blob.pbData, output_blob.cbData)
        return plain.decode("utf-8")
    finally:
        if description:
            kernel32.LocalFree(description)
        kernel32.LocalFree(output_blob.pbData)
