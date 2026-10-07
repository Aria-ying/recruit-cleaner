# -*- coding: utf-8 -*-
"""招新报名表处理工具 - 命令行入口。

    python main.py overview --input data/sample.csv
"""
from __future__ import annotations

import argparse
import sys

from recruit_tool import __version__
from recruit_tool.csvio import read_csv
from recruit_tool.overview import print_overview


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="recruit-csv-tool",
        description="协会招新报名表 CSV 处理工具",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_overview = sub.add_parser("overview", help="读入 CSV 并打印概览")
    p_overview.add_argument("--input", "-i", required=True, help="报名表 CSV 路径")
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

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
