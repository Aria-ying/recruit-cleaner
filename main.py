# -*- coding: utf-8 -*-
"""招新报名表处理工具 - 命令行入口。

    python main.py overview -i data/sample.csv
    python main.py check    -i data/sample.csv --issues-out output/issues.csv
"""
from __future__ import annotations

import argparse
import os
import sys

from recruit_tool import __version__
from recruit_tool.csvio import read_csv
from recruit_tool.exporter import (
    write_clean_csv,
    write_issues_csv,
    write_summary_csv,
)
from recruit_tool.overview import print_overview
from recruit_tool.report import print_check_report, print_rules
from recruit_tool.stats import print_summary
from recruit_tool.validate import (
    DEFAULT_MAX_SID_LEN,
    DEFAULT_MIN_SID_LEN,
    split_by_severity,
    validate_dataset,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="recruit-csv-tool",
        description="协会招新报名表 CSV 处理工具",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_overview = sub.add_parser("overview", help="读入 CSV 并打印概览（需求 1）")
    p_overview.add_argument("--input", "-i", required=True, help="报名表 CSV 路径")

    p_check = sub.add_parser("check", help="校验并导出问题清单（需求 2）")
    p_check.add_argument("--input", "-i", required=True, help="报名表 CSV 路径")
    p_check.add_argument(
        "--issues-out", "-o", default="output/issues.csv", help="问题清单输出路径"
    )
    p_check.add_argument(
        "--min-sid-length", type=int, default=DEFAULT_MIN_SID_LEN, help="学号最小位数"
    )
    p_check.add_argument(
        "--max-sid-length", type=int, default=DEFAULT_MAX_SID_LEN, help="学号最大位数"
    )
    p_check.add_argument("--explain", action="store_true", help="打印校验规则速查表后退出")

    p_stats = sub.add_parser("stats", help="统计并导出干净数据（需求 3）")
    p_stats.add_argument("--input", "-i", required=True, help="报名表 CSV 路径")
    p_stats.add_argument("--clean-out", default="output/clean.csv", help="干净数据输出路径")
    p_stats.add_argument("--summary-out", default="output/summary.csv", help="汇总表输出路径")

    p_run = sub.add_parser("run", help="一条命令跑完三个需求")
    p_run.add_argument("--input", "-i", required=True, help="报名表 CSV 路径")
    p_run.add_argument("--outdir", "-d", default="output", help="所有产物的输出目录")
    return parser


def main(argv: list[str] | None = None) -> int:
    # Windows 控制台默认是 GBK，强制用 UTF-8 输出，避免中文乱码
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    args = _build_parser().parse_args(argv)

    if args.command == "overview":
        ds = read_csv(args.input)
        print_overview(ds)
        return 0

    if args.command == "check":
        if args.explain:
            print_rules()
            return 0
        ds = read_csv(args.input)
        reports = validate_dataset(ds, args.min_sid_length, args.max_sid_length)
        # 原文件只读：问题清单写到独立路径，绝不回写 --input
        issues_path = write_issues_csv(args.issues_out, reports)
        print_check_report(reports, issues_path=issues_path)
        return 0

    if args.command in ("stats", "run"):
        if args.command == "run":
            out_issues = os.path.join(args.outdir, "issues.csv")
            out_clean = os.path.join(args.outdir, "clean.csv")
            out_summary = os.path.join(args.outdir, "summary.csv")
        else:
            out_issues = None
            out_clean = args.clean_out
            out_summary = args.summary_out

        ds = read_csv(args.input)

        if args.command == "run":
            print_overview(ds)
            print()

        reports = validate_dataset(ds)
        if out_issues:
            issues_path = write_issues_csv(out_issues, reports)
            print_check_report(reports, issues_path=issues_path)
            print()

        clean_rows, _ = split_by_severity(reports)
        clean_path = write_clean_csv(out_clean, ds.columns, clean_rows)
        summary_path = write_summary_csv(out_summary, clean_rows)
        print_summary(clean_rows)

        print(f"\n干净数据已导出: {clean_path}")
        print(f"汇总表已导出  : {summary_path}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
