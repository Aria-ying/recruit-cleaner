# -*- coding: utf-8 -*-
"""控制台报告打印。"""
from __future__ import annotations

import sys
from typing import Dict, List, Sequence

from .validate import ERROR, RULES, WARNING, RowReport


def count_by_code(reports: Sequence[RowReport]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for r in reports:
        for f in r.findings:
            counts[f.code] = counts.get(f.code, 0) + 1
    return counts


def print_check_report(
    reports: Sequence[RowReport],
    issues_path: str | None = None,
    stream=None,
) -> Dict[str, int]:
    """打印校验报告，返回各问题代码的命中次数。stream 在调用时解析，便于测试捕获。"""
    if stream is None:
        stream = sys.stdout
    counts = count_by_code(reports)
    error_rows = [r for r in reports if r.severity == ERROR]
    warn_rows = [r for r in reports if r.severity == WARNING]
    ok_rows = [r for r in reports if r.severity == "ok"]

    print("=" * 56, file=stream)
    print("校验报告", file=stream)
    print("=" * 56, file=stream)
    print(f"总行数        : {len(reports)}", file=stream)
    print(f"完全没问题    : {len(ok_rows)} 行", file=stream)
    print(f"有错误(error) : {len(error_rows)} 行  -> 不会进入干净数据", file=stream)
    print(f"仅警告(warn)  : {len(warn_rows)} 行  -> 仍算干净数据", file=stream)
    print(file=stream)

    if counts:
        print("-- 问题分布 " + "-" * 44, file=stream)
        for code in sorted(counts):
            rule = RULES.get(code, {})
            mark = "E" if rule.get("severity") == ERROR else "W"
            print(f"  [{mark}] {code}  {rule.get('desc', '')}  x{counts[code]}", file=stream)
        print(file=stream)

    if error_rows:
        print("-- 被判为有问题的行（前 20 条）" + "-" * 24, file=stream)
        for r in error_rows[:20]:
            name = r.row.get("姓名") or "(无名)"
            print(f"  第 {str(r.row_no).rjust(3)} 行  {name}  ->  {r.reason}", file=stream)
        if len(error_rows) > 20:
            print(f"  ... 另有 {len(error_rows) - 20} 行，详见问题清单", file=stream)
        print(file=stream)

    if issues_path:
        print(f"问题清单已导出: {issues_path}", file=stream)
    print("=" * 56, file=stream)

    return counts


def print_rules(stream=None) -> None:
    """打印规则速查表（--explain）。"""
    if stream is None:
        stream = sys.stdout
    print("校验规则速查表", file=stream)
    print("E = 错误，该行不会进入干净数据；W = 警告，仅提示", file=stream)
    print(file=stream)
    for code in sorted(RULES):
        rule = RULES[code]
        mark = "错误" if rule["severity"] == ERROR else "警告"
        print(f"  {code}  [{mark}]  {rule['desc']}", file=stream)
