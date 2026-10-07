# -*- coding: utf-8 -*-
"""导出模块。所有导出都写新文件，从不覆盖 --input 指向的原始 CSV。"""
from __future__ import annotations

import csv
import os
from typing import Dict, List, Sequence

from .validate import RowReport

#: 问题清单的列：先给人看的诊断信息，再是原始字段，方便对照着改。
ISSUE_COLUMNS = [
    "行号",
    "严重级别",
    "问题代码",
    "问题说明",
    "姓名",
    "学号",
    "邮箱",
    "志愿1",
    "志愿2",
    "推荐人",
]


def ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)


def write_csv(path: str, columns: Sequence[str], rows: Sequence[Dict[str, str]]) -> str:
    """通用的 CSV 写出。用 utf-8-sig，Excel 双击打开不会乱码。"""
    ensure_parent_dir(path)
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in columns})
    return path


def issue_rows(reports: Sequence[RowReport]) -> List[Dict[str, str]]:
    """把 RowReport 拍平成问题清单的行，一行对应一条原始记录。"""
    rows: List[Dict[str, str]] = []
    for r in reports:
        if not r.findings:
            continue
        item: Dict[str, str] = {
            "行号": str(r.row_no),
            "严重级别": r.severity,
            "问题代码": ",".join(f.code for f in r.findings),
            "问题说明": r.reason,
        }
        for col in ("姓名", "学号", "邮箱", "志愿1", "志愿2", "推荐人"):
            item[col] = r.row.get(col, "")
        rows.append(item)
    return rows


def write_issues_csv(path: str, reports: Sequence[RowReport]) -> str:
    return write_csv(path, ISSUE_COLUMNS, issue_rows(reports))
