# -*- coding: utf-8 -*-
"""CLI 层测试：退出码、友好报错、run 一键流程的产物。"""
from __future__ import annotations

import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Sequence

from main import main

SAMPLE = str(Path(__file__).resolve().parent.parent / "data" / "sample.csv")


def run_cli(argv: Sequence[str]) -> tuple[int, str, str]:
    """跑一次 CLI，返回 (退出码, stdout, stderr)。"""
    out, err = StringIO(), StringIO()
    code = 0
    try:
        with redirect_stdout(out), redirect_stderr(err):
            code = main(list(argv))
    except SystemExit as exc:
        code = exc.code or 0
    return code, out.getvalue(), err.getvalue()


class TestExitCodes(unittest.TestCase):
    def test_overview_success(self):
        code, out, _ = run_cli(["overview", "-i", SAMPLE])
        self.assertEqual(code, 0)
        self.assertIn("报名表概览", out)

    def test_explain_success(self):
        code, out, _ = run_cli(["check", "--explain"])
        self.assertEqual(code, 0)
        self.assertIn("E002", out)

    def test_missing_file_exits_2_with_friendly_message(self):
        code, _, err = run_cli(["overview", "-i", "绝不存在的文件.csv"])
        self.assertEqual(code, 2)
        self.assertIn("找不到报名表文件", err)
        self.assertNotIn("Traceback", err)

    def test_missing_columns_exits_2_with_friendly_message(self):
        fd, path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        self.addCleanup(os.remove, path)
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write("姓名,学号\n张三,123\n")

        code, _, err = run_cli(["overview", "-i", path])
        self.assertEqual(code, 2)
        self.assertIn("缺少必需的列", err)
        self.assertNotIn("Traceback", err)


class TestRunPipeline(unittest.TestCase):
    def test_run_produces_all_three_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out, _ = run_cli(["run", "-i", SAMPLE, "-d", tmp])
            self.assertEqual(code, 0)
            for name in ("issues.csv", "clean.csv", "summary.csv"):
                self.assertTrue(os.path.isfile(os.path.join(tmp, name)), f"{name} 未生成")
            # 三个需求的输出都出现在同一次运行里
            self.assertIn("报名表概览", out)
            self.assertIn("校验报告", out)
            self.assertIn("统计汇总", out)

    def test_run_never_touches_input_file(self):
        """原文件只读：跑完之后 sample.csv 的内容必须一字不改。"""
        before = Path(SAMPLE).read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            run_cli(["run", "-i", SAMPLE, "-d", tmp])
        self.assertEqual(Path(SAMPLE).read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
