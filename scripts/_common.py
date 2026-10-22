#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_common.py — trace_numbers.py 与 scan_privacy.py 共用的文件遍历工具

单独拆出来是为了让"哪些文件算文本文件、哪些目录该跳过"只有一处定义。
两个工具都要遍历工作区，如果各写一份，迟早会在某个仓库上给出不一致的结果
（一个扫了 node_modules，另一个没扫），而用户只会觉得工具不可靠。
"""
import os
from pathlib import Path

# 默认跳过的目录：依赖、构建产物、VCS 元数据
DEFAULT_EXCLUDE_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv", "venv",
    "env", "dist", "build", "target", ".idea", ".mypy_cache", ".pytest_cache",
    ".ruff_cache", ".tox", ".next", ".cache",
}

# 明显是二进制的扩展名，直接跳过（避免把图片当文本解码）
BINARY_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp", ".tif", ".tiff",
    ".pdf", ".zip", ".gz", ".tar", ".7z", ".rar", ".xz", ".bz2",
    ".pt", ".pth", ".ckpt", ".onnx", ".h5", ".pkl", ".joblib", ".npy", ".npz",
    ".parquet", ".feather", ".db", ".sqlite", ".sqlite3",
    ".exe", ".dll", ".so", ".dylib", ".bin", ".woff", ".woff2", ".ttf", ".otf",
    ".mp4", ".mov", ".avi", ".mp3", ".wav", ".flac",
}


def iter_files(root, exclude_dirs=None, max_bytes=2_000_000):
    """产出可扫描的文本文件路径；root 可以是目录，也可以是单个文件。"""
    exclude_dirs = DEFAULT_EXCLUDE_DIRS if exclude_dirs is None else exclude_dirs
    root = Path(root)
    if root.is_file():
        yield root
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
        for name in filenames:
            p = Path(dirpath) / name
            if p.suffix.lower() in BINARY_EXTS:
                continue
            try:
                if p.stat().st_size > max_bytes:
                    continue
            except OSError:
                continue
            yield p


def read_text(path):
    """尽力以文本方式读取；解不了就当二进制跳过（返回 None）。"""
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def relative_label(path, root):
    """把路径显示成相对于工作区的形式，跨平台统一用 /。"""
    try:
        rel = str(Path(path).resolve().relative_to(Path(root).resolve()))
    except ValueError:
        rel = str(path)
    return rel.replace("\\", "/")
