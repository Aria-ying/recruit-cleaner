# -*- coding: utf-8 -*-
"""导出模块。所有导出都写新文件，从不覆盖 --input 指向的原始 CSV。"""
from __future__ import annotations

import csv
import os
from typing import Dict, List, Sequence

from .csvio import is_blank
from .stats import SUMMARY_COLUMNS, clean_export_columns, summary_rows
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


def normalize_clean_row(row: Dict[str, str]) -> Dict[str, str]:
    """干净数据的归一化。两件事：

    1. 占位符（``-`` ``N/A`` ``无`` …）统一写成空串——既然判定它们是「没填」，
       导出时就不该还留着一个连下游 Excel 都会当成真值的 ``-``。
    2. 邮箱域名转小写——校验时说「已按小写处理」，导出时就得真这么做。

    返回新 dict，不改动传入的行。
    """
    out: Dict[str, str] = {}
    for key, value in row.items():
        if key == "__row_no__":
            continue
        v = "" if is_blank(value) else value
        if key == "邮箱" and "@" in v:
            local, _, domain = v.rpartition("@")
            v = f"{local}@{domain.lower()}"
        out[key] = v
    return out


def write_clean_csv(path: str, columns: Sequence[str], rows: Sequence[Dict[str, str]]) -> str:
    """导出清洗后的干净数据：剔除内部行号列，并做归一化。"""
    normalized = [normalize_clean_row(r) for r in rows]
    return write_csv(path, clean_export_columns(columns), normalized)


def write_summary_csv(path: str, rows: Sequence[Dict[str, str]]) -> str:
    """导出汇总表（第一志愿分布 + 志愿完整度）。"""
    return write_csv(path, SUMMARY_COLUMNS, summary_rows(rows))
