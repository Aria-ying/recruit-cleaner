# -*- coding: utf-8 -*-
"""需求 3 的测试：分组统计、志愿完整度、干净数据与汇总表导出。"""
from __future__ import annotations

import csv
import os
import tempfile
import unittest
from typing import Dict, Sequence

from recruit_tool.exporter import normalize_clean_row, write_clean_csv, write_summary_csv
from recruit_tool.stats import (
    COMPLETENESS_KEYS,
    build_summary,
    clean_export_columns,
    count_by_first_choice,
    count_completeness,
    summary_rows,
)


def row(first: str, second: str, **kw: str) -> Dict[str, str]:
    base = {"姓名": "某人", "学号": "2023010101", "邮箱": "2023010101@smbu.edu.cn",
            "志愿1": first, "志愿2": second, "推荐人": "", "__row_no__": 1}
    base.update(kw)
    return base


class TestCountByFirstChoice(unittest.TestCase):
    def test_counts_and_sorted_by_count_desc(self):
        rows = [row("技术部", ""), row("技术部", "宣传部"), row("宣传部", ""), row("外联部", "")]
        # 人数并列时按 Unicode 码点排：「外」U+5916 < 「宣」U+5BA3
        self.assertEqual(
            count_by_first_choice(rows),
            [("技术部", 2), ("外联部", 1), ("宣传部", 1)],
        )

    def test_tie_broken_by_name(self):
        rows = [row("宣传部", ""), row("外联部", "")]
        self.assertEqual(count_by_first_choice(rows), [("外联部", 1), ("宣传部", 1)])

    def test_blank_first_choice_excluded(self):
        self.assertEqual(count_by_first_choice([row("", "宣传部")]), [])


class TestCompleteness(unittest.TestCase):
    def test_both_filled(self):
        result = count_completeness([row("技术部", "宣传部")])
        self.assertEqual(result["两个志愿都填了"], 1)

    def test_only_first(self):
        result = count_completeness([row("技术部", "")])
        self.assertEqual(result["只填了第一志愿"], 1)

    def test_only_second(self):
        result = count_completeness([row("", "宣传部")])
        self.assertEqual(result["只填了第二志愿"], 1)

    def test_placeholder_counts_as_unfilled(self):
        """「-」「N/A」这类占位符不能算填了。"""
        result = count_completeness([row("技术部", "-")])
        self.assertEqual(result["只填了第一志愿"], 1)
        self.assertEqual(result["两个志愿都填了"], 0)

    def test_same_department_counted_separately(self):
        """两个志愿填同一部门：与 W103 口径一致，不算「都填了」。"""
        result = count_completeness([row("宣传部", "宣传部")])
        self.assertEqual(result["两个志愿填了同一部门"], 1)
        self.assertEqual(result["两个志愿都填了"], 0)

    def test_categories_are_mutually_exclusive_and_exhaustive(self):
        rows = [
            row("技术部", "宣传部"),
            row("技术部", ""),
            row("", "宣传部"),
            row("宣传部", "宣传部"),
            row("", ""),
        ]
        result = count_completeness(rows)
        self.assertEqual(sum(result.values()), len(rows))
        self.assertEqual(set(result), set(COMPLETENESS_KEYS))


class TestBuildSummary(unittest.TestCase):
    def test_totals(self):
        rows = [row("技术部", "宣传部"), row("技术部", ""), row("宣传部", "宣传部")]
        info = build_summary(rows)
        self.assertEqual(info["total"], 3)
        self.assertEqual(info["both_filled"], 1)
        self.assertEqual(info["only_one_filled"], 1)


class TestSummaryRows(unittest.TestCase):
    def test_has_two_blocks_and_total_row(self):
        rows = [row("技术部", "宣传部"), row("技术部", "")]
        out = summary_rows(rows)
        dims = {r["统计维度"] for r in out}
        self.assertEqual(dims, {"第一志愿分布", "志愿完整度"})
        total_row = next(r for r in out if r["分组"] == "(合计)")
        self.assertEqual(total_row["人数"], "2")
        self.assertEqual(total_row["占比"], "100.0%")

    def test_all_completeness_keys_present(self):
        out = summary_rows([row("技术部", "")])
        keys = {r["分组"] for r in out if r["统计维度"] == "志愿完整度"}
        self.assertEqual(keys, set(COMPLETENESS_KEYS))


class TestNormalize(unittest.TestCase):
    def test_placeholder_becomes_empty_string(self):
        out = normalize_clean_row({"志愿2": "-", "推荐人": "N/A", "姓名": "张三"})
        self.assertEqual(out["志愿2"], "")
        self.assertEqual(out["推荐人"], "")
        self.assertEqual(out["姓名"], "张三")

    def test_email_domain_lowered(self):
        out = normalize_clean_row({"邮箱": "2023010104@SMBU.edu.cn"})
        self.assertEqual(out["邮箱"], "2023010104@smbu.edu.cn")

    def test_internal_row_number_dropped(self):
        self.assertNotIn("__row_no__", normalize_clean_row({"__row_no__": 1, "姓名": "张三"}))

    def test_input_row_not_mutated(self):
        original = {"志愿2": "-"}
        normalize_clean_row(original)
        self.assertEqual(original["志愿2"], "-")


class TestCleanExport(unittest.TestCase):
    def setUp(self):
        self.rows: Sequence[Dict[str, str]] = [row("技术部", "宣传部", 姓名="张三")]
        self.fd, self.path = tempfile.mkstemp(suffix=".csv")
        os.close(self.fd)
        self.addCleanup(os.remove, self.path)

    def test_internal_row_number_column_is_dropped(self):
        cols = ["姓名", "学号", "邮箱", "志愿1", "志愿2", "推荐人", "__row_no__"]
        self.assertNotIn("__row_no__", clean_export_columns(cols))

    def test_extra_columns_are_preserved(self):
        cols = ["姓名", "学号", "邮箱", "志愿1", "志愿2", "推荐人", "提交时间"]
        self.assertEqual(clean_export_columns(cols)[-1], "提交时间")

    def test_clean_csv_has_no_internal_column(self):
        cols = ["姓名", "学号", "邮箱", "志愿1", "志愿2", "推荐人", "__row_no__"]
        write_clean_csv(self.path, cols, self.rows)
        with open(self.path, encoding="utf-8-sig", newline="") as fh:
            header = next(csv.reader(fh))
        self.assertNotIn("__row_no__", header)
        self.assertEqual(header[0], "姓名")

    def test_summary_csv_has_expected_header(self):
        write_summary_csv(self.path, self.rows)
        with open(self.path, encoding="utf-8-sig", newline="") as fh:
            header = next(csv.reader(fh))
        self.assertEqual(header, ["统计维度", "分组", "人数", "占比"])


if __name__ == "__main__":
    unittest.main()
