# -*- coding: utf-8 -*-
"""需求 1 的测试：读入、空值统计、完全重复行。"""
from __future__ import annotations

import os
import tempfile
import unittest

from recruit_tool.csvio import Dataset, is_blank, read_csv
from recruit_tool.overview import build_overview

HEADER = "姓名,学号,邮箱,志愿1,志愿2,推荐人\n"


def write_tmp(content: str, encoding: str = "utf-8-sig") -> str:
    fd, path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, "w", encoding=encoding, newline="") as fh:
        fh.write(content)
    return path


class TestBlank(unittest.TestCase):
    def test_placeholder_tokens_count_as_blank(self):
        for token in ["", "   ", "-", "无", "N/A", "NULL", "nan"]:
            self.assertTrue(is_blank(token), f"{token!r} 应该被判为空值")
        for token in ["0", "技术部", "张三"]:
            self.assertFalse(is_blank(token), f"{token!r} 不该被判为空值")

    def test_none_is_blank(self):
        self.assertTrue(is_blank(None))


class TestReadCsv(unittest.TestCase):
    def setUp(self):
        self.path = write_tmp(
            HEADER
            + "张三,2023010101,2023010101@smbu.edu.cn,技术部,宣传部,李四\n"
            + "李四,2023010102,2023010102@smbu.edu.cn,宣传部,  ,\n"
        )
        self.addCleanup(os.remove, self.path)

    def test_row_count_and_columns(self):
        ds = read_csv(self.path)
        self.assertEqual(ds.row_count, 2)
        self.assertEqual(ds.columns, ["姓名", "学号", "邮箱", "志愿1", "志愿2", "推荐人"])

    def test_values_are_stripped(self):
        ds = read_csv(self.path)
        self.assertEqual(ds.rows[1]["志愿2"], "")

    def test_row_number_is_one_based(self):
        ds = read_csv(self.path)
        self.assertEqual([r["__row_no__"] for r in ds.rows], [1, 2])

    def test_missing_column_raises(self):
        path = write_tmp("姓名,学号\n张三,123\n")
        self.addCleanup(os.remove, path)
        with self.assertRaises(ValueError) as ctx:
            read_csv(path)
        self.assertIn("邮箱", str(ctx.exception))

    def test_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            read_csv("绝不存在的文件.csv")

    def test_gbk_file_is_readable(self):
        path = write_tmp(HEADER + "王五,2023010103,2023010103@smbu.edu.cn,技术部,,\n", encoding="gbk")
        self.addCleanup(os.remove, path)
        ds = read_csv(path)
        self.assertEqual(ds.rows[0]["姓名"], "王五")


class TestOverview(unittest.TestCase):
    def setUp(self):
        self.path = write_tmp(
            HEADER
            + "张三,2023010101,2023010101@smbu.edu.cn,技术部,宣传部,李四\n"
            + "张三,2023010101,2023010101@smbu.edu.cn,技术部,宣传部,李四\n"
            + "李四,2023010102,2023010102@smbu.edu.cn,宣传部,-,\n"
            + ",,,,,\n"
        )
        self.addCleanup(os.remove, self.path)

    def test_blank_counts(self):
        info = build_overview(read_csv(self.path))
        self.assertEqual(info["row_count"], 4)
        self.assertEqual(info["blank_counts"]["志愿2"], 2)  # 第3行"-"、第4行空
        self.assertEqual(info["blank_counts"]["推荐人"], 2)  # 第3、4行
        self.assertEqual(info["blank_counts"]["姓名"], 1)

    def test_exact_duplicate_rows(self):
        info = build_overview(read_csv(self.path))
        self.assertEqual(len(info["duplicate_row_groups"]), 1)
        self.assertEqual(info["duplicate_row_groups"][0]["row_numbers"], [1, 2])

    def test_fully_blank_row(self):
        info = build_overview(read_csv(self.path))
        self.assertEqual(info["blank_row_numbers"], [4])


if __name__ == "__main__":
    unittest.main()
