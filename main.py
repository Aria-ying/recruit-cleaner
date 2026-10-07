# -*- coding: utf-8 -*-
"""招新报名表处理工具 - 命令行入口。

    python main.py overview -i data/sample.csv
    python main.py check    -i data/sample.csv --issues-out output/issues.csv
"""
from __future__ import annotations

import argparse
import sys

from recruit_tool import __version__
from recruit_tool.csvio import read_csv
from recruit_tool.exporter import write_issues_csv
from recruit_tool.overview import print_overview
from recruit_tool.report import print_check_report, print_rules
from recruit_tool.validate import DEFAULT_MAX_SID_LEN, DEFAULT_MIN_SID_LEN, validate_dataset


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

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
