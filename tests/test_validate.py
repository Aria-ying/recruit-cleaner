# -*- coding: utf-8 -*-
"""需求 2 的测试：学号/邮箱校验、重复报名、问题清单导出。"""
from __future__ import annotations

import csv
import os
import tempfile
import unittest
from typing import Sequence

from recruit_tool.csvio import REQUIRED_COLUMNS, Dataset
from recruit_tool.exporter import issue_rows, write_issues_csv
from recruit_tool.validate import (
    ERROR,
    RULES,
    WARNING,
    RowReport,
    split_by_severity,
    validate_dataset,
)


def make_ds(rows: Sequence[Sequence[str]]) -> Dataset:
    """直接用二维数据构造 Dataset，避免测试里到处写临时文件。"""
    built = []
    for i, values in enumerate(rows, start=1):
        row = dict(zip(REQUIRED_COLUMNS, values))
        row["__row_no__"] = i
        built.append(row)
    return Dataset(columns=list(REQUIRED_COLUMNS), rows=built, encoding="utf-8", source="test")


def codes_of(report: RowReport) -> list[str]:
    return [f.code for f in report.findings]


class TestStudentId(unittest.TestCase):
    def test_valid_digits_pass(self):
        ds = make_ds([["张三", "2023010101", "2023010101@smbu.edu.cn", "技术部", "宣传部", ""]])
        report = validate_dataset(ds)[0]
        self.assertEqual(report.error_codes, [])

    def test_non_digit_is_error(self):
        ds = make_ds([["孙八", "2023010A06", "2023010106@smbu.edu.cn", "技术部", "", ""]])
        report = validate_dataset(ds)[0]
        self.assertIn("E002", codes_of(report))

    def test_blank_student_id_is_error(self):
        ds = make_ds([["周九", "", "2023010107@smbu.edu.cn", "宣传部", "", ""]])
        report = validate_dataset(ds)[0]
        self.assertIn("E001", codes_of(report))

    def test_length_out_of_range_is_warning_only(self):
        ds = make_ds([["张三", "123", "123@smbu.edu.cn", "技术部", "宣传部", ""]])
        report = validate_dataset(ds, min_sid_len=6, max_sid_len=12)[0]
        self.assertIn("W101", codes_of(report))
        self.assertEqual(report.error_codes, [])


class TestEmail(unittest.TestCase):
    def test_wrong_domain_is_error(self):
        ds = make_ds([["钱七", "2023010105", "2023010105@qq.com", "宣传部", "技术部", ""]])
        self.assertIn("E005", codes_of(validate_dataset(ds)[0]))

    def test_missing_at_sign_is_error(self):
        ds = make_ds([["钱七", "2023010105", "2023010105.smbu.edu.cn", "宣传部", "", ""]])
        self.assertIn("E005", codes_of(validate_dataset(ds)[0]))

    def test_prefix_mismatch_is_error(self):
        ds = make_ds([["秦九", "2023010118", "2023010119@smbu.edu.cn", "技术部", "", ""]])
        self.assertIn("E006", codes_of(validate_dataset(ds)[0]))

    def test_prefix_check_skipped_when_sid_invalid(self):
        """学号本身就非法时，不要再建议「应为 2023010A06@...」这种废话。"""
        ds = make_ds([["孙八", "2023010A06", "2023010106@smbu.edu.cn", "技术部", "", ""]])
        codes = codes_of(validate_dataset(ds)[0])
        self.assertIn("E002", codes)
        self.assertNotIn("E006", codes)

    def test_domain_case_insensitive_but_warned(self):
        ds = make_ds([["赵六", "2023010104", "2023010104@SMBU.edu.cn", "外联部", "", ""]])
        report = validate_dataset(ds)[0]
        self.assertIn("W104", codes_of(report))
        self.assertEqual(report.error_codes, [])  # 大小写不判错

    def test_blank_email_is_error(self):
        ds = make_ds([["吴十", "2023010108", "", "外联部", "", ""]])
        self.assertIn("E004", codes_of(validate_dataset(ds)[0]))


class TestDuplicate(unittest.TestCase):
    def test_second_occurrence_flagged(self):
        ds = make_ds(
            [
                ["张三", "2023010101", "2023010101@smbu.edu.cn", "技术部", "宣传部", "李四"],
                ["朱八", "2023010101", "2023010101@smbu.edu.cn", "外联部", "", ""],
            ]
        )
        first, second = validate_dataset(ds)
        self.assertNotIn("E008", codes_of(first))
        self.assertIn("E008", codes_of(second))
        self.assertIn("第 1 行", second.reason)

    def test_blank_student_ids_are_not_duplicates_of_each_other(self):
        ds = make_ds(
            [
                ["周九", "", "a@smbu.edu.cn", "宣传部", "", ""],
                ["吴十", "", "b@smbu.edu.cn", "外联部", "", ""],
            ]
        )
        reports = validate_dataset(ds)
        self.assertNotIn("E008", codes_of(reports[0]))
        self.assertNotIn("E008", codes_of(reports[1]))


class TestChoices(unittest.TestCase):
    def test_blank_first_choice_is_error(self):
        ds = make_ds([["郑十一", "2023010109", "2023010109@smbu.edu.cn", "", "", ""]])
        self.assertIn("E007", codes_of(validate_dataset(ds)[0]))

    def test_blank_second_choice_is_warning_only(self):
        ds = make_ds([["李四", "2023010102", "2023010102@smbu.edu.cn", "宣传部", "", ""]])
        report = validate_dataset(ds)[0]
        self.assertIn("W102", codes_of(report))
        self.assertEqual(report.error_codes, [])

    def test_same_two_choices_is_warning(self):
        ds = make_ds([["尤十", "2023010119", "2023010119@smbu.edu.cn", "宣传部", "宣传部", ""]])
        self.assertIn("W103", codes_of(validate_dataset(ds)[0]))


class TestBlankRow(unittest.TestCase):
    def test_fully_blank_row(self):
        ds = make_ds([["", "", "", "", "", ""]])
        report = validate_dataset(ds)[0]
        self.assertEqual(codes_of(report), ["E009"])


class TestSplit(unittest.TestCase):
    def setUp(self):
        self.ds = make_ds(
            [
                ["张三", "2023010101", "2023010101@smbu.edu.cn", "技术部", "宣传部", "李四"],
                ["李四", "2023010102", "2023010102@smbu.edu.cn", "宣传部", "", ""],  # 仅警告
                ["孙八", "2023010A06", "2023010106@smbu.edu.cn", "技术部", "", ""],  # 错误
            ]
        )
        self.reports = validate_dataset(self.ds)

    def test_clean_rows_exclude_errors_but_keep_warnings(self):
        clean, problematic = split_by_severity(self.reports)
        self.assertEqual(len(clean), 2)
        self.assertEqual([r["姓名"] for r in clean], ["张三", "李四"])

    def test_problematic_contains_only_rows_with_findings(self):
        _, problematic = split_by_severity(self.reports)
        self.assertEqual([r.row_no for r in problematic], [2, 3])

    def test_original_rows_are_not_mutated(self):
        """只读原始数据的承诺：校验过程不能改动行内容。"""
        before = [dict(r) for r in self.ds.rows]
        validate_dataset(self.ds)
        self.assertEqual(self.ds.rows, before)


class TestIssueExport(unittest.TestCase):
    def test_issues_csv_content(self):
        ds = make_ds([["孙八", "2023010A06", "2023010106@smbu.edu.cn", "技术部", "", ""]])
        reports = validate_dataset(ds)
        fd, path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        self.addCleanup(os.remove, path)

        write_issues_csv(path, reports)
        with open(path, "r", encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["行号"], "1")
        self.assertEqual(rows[0]["严重级别"], ERROR)
        self.assertEqual(rows[0]["姓名"], "孙八")
        self.assertIn("E002", rows[0]["问题代码"])
        self.assertIn("不是纯数字", rows[0]["问题说明"])

    def test_issue_rows_skip_clean_rows(self):
        ds = make_ds([["张三", "2023010101", "2023010101@smbu.edu.cn", "技术部", "宣传部", ""]])
        self.assertEqual(issue_rows(validate_dataset(ds)), [])


class TestRulesTable(unittest.TestCase):
    def test_every_code_has_severity_and_desc(self):
        for code, rule in RULES.items():
            self.assertIn(rule["severity"], (ERROR, WARNING))
            self.assertTrue(rule["desc"].strip())


if __name__ == "__main__":
    unittest.main()
