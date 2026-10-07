# -*- coding: utf-8 -*-
"""统计与汇总（需求 3）。

统计口径：只统计**干净数据**（无 error 的行）。
脏数据统计进去会让部门人数虚高，宁可先让人去修问题清单。
"""
from __future__ import annotations

import sys
from collections import Counter
from typing import Any, Dict, List, Sequence, Tuple

from .csvio import REQUIRED_COLUMNS, format_ratio, is_blank

#: 志愿完整度的分类，**互斥且穷尽**：各类人数相加等于总人数。
#: 注意「两个志愿填了同一部门」被单列出来，不计入「两个志愿都填了」——
#: 因为它和校验规则 W103 的口径必须一致（填了同一个部门 ≈ 没有有效第二志愿）。
COMPLETENESS_KEYS = (
    "两个志愿都填了",
    "只填了第一志愿",
    "只填了第二志愿",
    "两个志愿填了同一部门",
    "两个都没填",
)

SUMMARY_COLUMNS = ["统计维度", "分组", "人数", "占比"]


def count_by_first_choice(rows: Sequence[Dict[str, str]]) -> List[Tuple[str, int]]:
    """按第一志愿分组统计人数。

    排序：人数多的在前，人数相同则按部门名升序（中文按 Unicode 码点）。
    """
    counter = Counter(r.get("志愿1", "").strip() for r in rows if not is_blank(r.get("志愿1")))
    return sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))


def count_completeness(rows: Sequence[Dict[str, str]]) -> Dict[str, int]:
    """统计「两个志愿都填了」和「只填一个」的人数。"""
    result = {key: 0 for key in COMPLETENESS_KEYS}
    for row in rows:
        first = (row.get("志愿1") or "").strip()
        second = (row.get("志愿2") or "").strip()
        has_first = not is_blank(first)
        has_second = not is_blank(second)
        if has_first and has_second:
            if first == second:
                result["两个志愿填了同一部门"] += 1
            else:
                result["两个志愿都填了"] += 1
        elif has_first:
            result["只填了第一志愿"] += 1
        elif has_second:
            result["只填了第二志愿"] += 1
        else:
            result["两个都没填"] += 1
    return result


def build_summary(rows: Sequence[Dict[str, str]]) -> Dict[str, Any]:
    """把汇总算成结构化数据。"""
    groups = count_by_first_choice(rows)
    completeness = count_completeness(rows)
    total = len(rows)
    return {
        "total": total,
        "by_first_choice": groups,
        "completeness": completeness,
        "both_filled": completeness["两个志愿都填了"],
        "only_one_filled": completeness["只填了第一志愿"] + completeness["只填了第二志愿"],
    }


def summary_rows(rows: Sequence[Dict[str, str]]) -> List[Dict[str, str]]:
    """把汇总拍平成长表，方便一次性导出成 summary.csv。

    列：统计维度 / 分组 / 人数 / 占比。两个区块（第一志愿分布、志愿完整度）
    放在同一张表里，用「统计维度」区分。
    """
    info = build_summary(rows)
    total = info["total"]
    out: List[Dict[str, str]] = []

    for name, count in info["by_first_choice"]:
        out.append(
            {
                "统计维度": "第一志愿分布",
                "分组": name,
                "人数": str(count),
                "占比": format_ratio(count, total),
            }
        )
    out.append(
        {
            "统计维度": "第一志愿分布",
            "分组": "(合计)",
            "人数": str(sum(c for _, c in info["by_first_choice"])),
            "占比": format_ratio(sum(c for _, c in info["by_first_choice"]), total),
        }
    )

    for key in COMPLETENESS_KEYS:
        count = info["completeness"][key]
        out.append(
            {
                "统计维度": "志愿完整度",
                "分组": key,
                "人数": str(count),
                "占比": format_ratio(count, total),
            }
        )
    return out


def print_summary(rows: Sequence[Dict[str, str]], stream=None) -> Dict[str, Any]:
    """打印汇总表，同时返回结构化结果。stream 在调用时解析，便于测试捕获。"""
    if stream is None:
        stream = sys.stdout
    info = build_summary(rows)
    total = info["total"]

    print("=" * 56, file=stream)
    print("统计汇总（仅统计干净数据）", file=stream)
    print("=" * 56, file=stream)
    print(f"干净数据总人数 : {total} 人", file=stream)
    print(file=stream)

    print("-- 按第一志愿分组 " + "-" * 39, file=stream)
    if not info["by_first_choice"]:
        print("  （没有可统计的数据）", file=stream)
    else:
        width = max(len(name) for name, _ in info["by_first_choice"])
        width = max(width, 6)
        for name, count in info["by_first_choice"]:
            bar = "#" * int(round(count * 24 / total)) if total else ""
            print(
                f"  {name.ljust(width)}  {str(count).rjust(4)} 人  "
                f"({format_ratio(count, total).rjust(6)})  {bar}",
                file=stream,
            )
    print(file=stream)

    print("-- 志愿填写完整度 " + "-" * 38, file=stream)
    comp = info["completeness"]
    # 各类互斥，相加等于总人数
    print(f"  两个志愿都填了     : {comp['两个志愿都填了']} 人", file=stream)
    print(f"  只填了一个         : {info['only_one_filled']} 人", file=stream)
    print(f"    ├ 只填第一志愿   : {comp['只填了第一志愿']} 人", file=stream)
    print(f"    └ 只填第二志愿   : {comp['只填了第二志愿']} 人", file=stream)
    print(
        f"  两个志愿同一部门   : {comp['两个志愿填了同一部门']} 人  (无有效第二志愿，单列)"
        , file=stream,
    )
    print(f"  两个都没填         : {comp['两个都没填']} 人", file=stream)
    print("=" * 56, file=stream)

    return info


def clean_export_columns(columns: Sequence[str]) -> List[str]:
    """干净数据的导出列：去掉内部用的行号列，必需列在前。"""
    base = [c for c in REQUIRED_COLUMNS if c in columns]
    extra = [c for c in columns if c not in REQUIRED_COLUMNS and c != "__row_no__"]
    return base + extra
