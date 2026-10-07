# -*- coding: utf-8 -*-
"""概览打印（需求 1）：总行数、每列空值、完全重复的行。"""
from __future__ import annotations

import sys
from typing import Any, Dict, List

from .csvio import Dataset, format_ratio, is_blank


def build_overview(ds: Dataset) -> Dict[str, Any]:
    """把概览算成结构化数据，方便测试和后续复用。"""
    blank_counts = ds.blank_counts()
    dup_groups = ds.duplicate_row_groups()
    dup_rows = sorted(n for nums in dup_groups.values() for n in nums)

    return {
        "source": ds.source,
        "encoding": ds.encoding,
        "row_count": ds.row_count,
        "column_count": len(ds.columns),
        "columns": list(ds.columns),
        "blank_counts": blank_counts,
        "duplicate_row_groups": [
            {"row_numbers": nums, "preview": " | ".join(key)} for key, nums in sorted(dup_groups.items(), key=lambda kv: kv[1][0])
        ],
        "duplicate_row_count": len(dup_rows),
        "blank_row_numbers": ds.blank_row_numbers(),
    }


def _ratio(part: int, total: int) -> str:
    return format_ratio(part, total)


def print_overview(ds: Dataset, stream=sys.stdout) -> Dict[str, Any]:
    """打印人类可读的概览，同时返回结构化结果。"""
    info = build_overview(ds)
    total = info["row_count"]

    print("=" * 56, file=stream)
    print("报名表概览", file=stream)
    print("=" * 56, file=stream)
    print(f"源文件     : {info['source']}", file=stream)
    print(f"编码       : {info['encoding']}", file=stream)
    print(f"总行数     : {total} 行（不含表头）", file=stream)
    print(f"列数       : {info['column_count']} 列", file=stream)
    print(file=stream)

    print("-- 每列空值统计 " + "-" * 39, file=stream)
    width = max((len(c) for c in info["columns"]), default=4)
    width = max(width, 4)
    for col in info["columns"]:
        n = info["blank_counts"][col]
        bar = "#" * int(round(n * 20 / total)) if total else ""
        print(f"  {col.ljust(width)}  {str(n).rjust(4)} 个空值  ({_ratio(n, total).rjust(6)})  {bar}", file=stream)
    print(file=stream)

    print("-- 完全重复的行 " + "-" * 40, file=stream)
    groups = info["duplicate_row_groups"]
    if not groups:
        print("  没有发现内容完全相同的行", file=stream)
    else:
        print(f"  发现 {len(groups)} 组、共 {info['duplicate_row_count']} 行存在完全重复：", file=stream)
        for g in groups:
            nums = "、".join(f"第 {n} 行" for n in g["row_numbers"])
            print(f"    {nums}  <-  {g['preview']}", file=stream)
    print(file=stream)

    print("-- 整行全空 " + "-" * 43, file=stream)
    blanks = info["blank_row_numbers"]
    if not blanks:
        print("  没有整行全空的记录", file=stream)
    else:
        print(f"  {len(blanks)} 行整行全空：第 " + "、".join(str(n) for n in blanks) + " 行", file=stream)
    print("=" * 56, file=stream)

    return info
