# -*- coding: utf-8 -*-
"""CSV 读入与「空值」判定（需求 1）。

所有边界假设集中在 README「边界假设」一节，这里只是那些假设的代码化。
"""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

#: 报名表必须存在的列。缺任何一列都直接报错，不做猜测。
REQUIRED_COLUMNS: Tuple[str, ...] = ("姓名", "学号", "邮箱", "志愿1", "志愿2", "推荐人")

#: 按优先级尝试的编码。问卷导出的 CSV 经常带 BOM 或是 GBK，所以逐个试。
ENCODING_CANDIDATES: Tuple[str, ...] = ("utf-8-sig", "utf-8", "gb18030", "gbk")

#: 除空字符串外，还被当作「没填」的占位符。
#: 问卷工具经常把未填写渲染成 "-"、"无"、"N/A" 之类，只判空串会漏掉。
PLACEHOLDER_TOKENS = frozenset(
    {
        "",
        "-",
        "--",
        "---",
        "—",
        "——",
        "/",
        "无",
        "没有",
        "暂无",
        "未填",
        "未填写",
        "N/A",
        "n/a",
        "NA",
        "na",
        "NULL",
        "null",
        "None",
        "none",
        "nan",
        "NaN",
    }
)


def is_blank(value: Optional[str]) -> bool:
    """判定一个单元格是否算「没填」。"""
    if value is None:
        return True
    return str(value).strip() in PLACEHOLDER_TOKENS


def format_ratio(part: int, total: int) -> str:
    """格式化占比，total 为 0 时避免除零。"""
    return "0.0%" if total == 0 else "{:.1f}%".format(part * 100.0 / total)


def detect_encoding(path: str, candidates: Sequence[str] = ENCODING_CANDIDATES) -> str:
    """用候选编码逐个试读整个文件，第一个能完整解码的胜出。"""
    with open(path, "rb") as fh:
        raw = fh.read()
    for enc in candidates:
        try:
            raw.decode(enc)
            return enc
        except (UnicodeDecodeError, LookupError):
            continue
    # 都失败就退回 utf-8 并宽容处理，让 csv 模块自己抛更具体的错
    return "utf-8"


@dataclass
class Dataset:
    """读入后的报名表。

    rows 里的行号（row_no）一律是 **1 起、不含表头** 的数据行号，
    与报错信息、问题清单里给人类看的行号保持一致。
    """

    columns: List[str]
    rows: List[Dict[str, str]]
    encoding: str
    source: str

    @property
    def row_count(self) -> int:
        return len(self.rows)

    def blank_counts(self) -> Dict[str, int]:
        """每一列有多少个「没填」。"""
        return {col: sum(1 for row in self.rows if is_blank(row.get(col))) for col in self.columns}

    def blank_row_numbers(self) -> List[int]:
        """整行全空的行号（通常是导出时多出来的空行）。"""
        return [r["__row_no__"] for r in self.rows if all(is_blank(r.get(c)) for c in self.columns)]

    def row_key(self, row: Dict[str, str]) -> Tuple[str, ...]:
        """整行指纹，用于找完全重复的行。"""
        return tuple((row.get(c) or "") for c in self.columns)

    def duplicate_row_groups(self) -> Dict[Tuple[str, ...], List[int]]:
        """返回内容完全相同的行分组，只保留 size > 1 的组。

        返回 ``{行指纹: [行号, 行号, ...]}``，行号升序。
        """
        buckets: Dict[Tuple[str, ...], List[int]] = {}
        for row in self.rows:
            buckets.setdefault(self.row_key(row), []).append(row["__row_no__"])
        return {key: nums for key, nums in buckets.items() if len(nums) > 1}


def read_csv(
    path: str,
    required_columns: Sequence[str] = REQUIRED_COLUMNS,
    strict: bool = True,
) -> Dataset:
    """读入报名表 CSV。

    - 自动探测编码（BOM / UTF-8 / GBK 都吃得下）
    - 每个单元格做首尾空白 strip
    - 每行附上 ``__row_no__``：1 起的数据行号，供后续报错定位
    - ``strict=True`` 时缺少必需列直接抛 ``ValueError``
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"找不到报名表文件：{path}")

    encoding = detect_encoding(path)
    with open(path, "r", encoding=encoding, newline="") as fh:
        reader = csv.DictReader(fh)
        header: List[str] = [h.strip() for h in (reader.fieldnames or [])]

        missing = [c for c in required_columns if c not in header]
        if missing and strict:
            raise ValueError(
                "报名表缺少必需的列：{}\n实际表头：{}".format("、".join(missing), "、".join(header))
            )

        # 必需列在前、多出来的列保持原顺序排在后面，不丢信息
        extra = [h for h in header if h not in required_columns]
        columns = [c for c in header if c in required_columns] + extra

        rows: List[Dict[str, str]] = []
        for index, raw_row in enumerate(reader, start=1):
            row = {col: (raw_row.get(col) or "").strip() for col in columns}
            row["__row_no__"] = index  # type: ignore[assignment]
            rows.append(row)

    return Dataset(columns=columns, rows=rows, encoding=encoding, source=path)
