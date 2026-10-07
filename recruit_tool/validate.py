# -*- coding: utf-8 -*-
"""校验与清洗（需求 2）。

核心原则：**只读原始文件，绝不回写**。有问题的行原样导出到「问题清单」，
原文件和干净数据各走各的输出路径。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from .csvio import Dataset, is_blank

#: 学校邮箱域名。比较时统一转小写，但会单独提醒大小写不规范。
SCHOOL_EMAIL_DOMAIN = "smbu.edu.cn"

#: 学号长度的宽松区间。需求没说几位，所以只给警告不判错。
DEFAULT_MIN_SID_LEN = 6
DEFAULT_MAX_SID_LEN = 12

ERROR = "error"
WARNING = "warning"

#: 规则速查表，README 和 --explain 都从这里生成，避免文档和代码对不上。
RULES: Dict[str, Dict[str, str]] = {
    "E001": {"severity": ERROR, "desc": "学号为空"},
    "E002": {"severity": ERROR, "desc": "学号不是纯数字（含字母、符号或空格）"},
    "E003": {"severity": ERROR, "desc": "姓名为空"},
    "E004": {"severity": ERROR, "desc": "邮箱为空"},
    "E005": {"severity": ERROR, "desc": "邮箱域名不是 smbu.edu.cn"},
    "E006": {"severity": ERROR, "desc": "邮箱前缀与学号不一致"},
    "E007": {"severity": ERROR, "desc": "第一志愿为空"},
    "E008": {"severity": ERROR, "desc": "学号重复报名（保留首次出现，后续判为重复）"},
    "E009": {"severity": ERROR, "desc": "整行全空"},
    "W101": {"severity": WARNING, "desc": "学号长度不在合理区间（仅提示，不判错）"},
    "W102": {"severity": WARNING, "desc": "第二志愿为空（允许，仅提示）"},
    "W103": {"severity": WARNING, "desc": "两个志愿填了同一个部门"},
    "W104": {"severity": WARNING, "desc": "邮箱域名大小写不规范（已按小写处理，不判错）"},
}


@dataclass(frozen=True)
class Finding:
    """一条校验结论。"""

    code: str
    severity: str
    message: str


@dataclass
class RowReport:
    """一行报名记录的校验结果。"""

    row_no: int
    row: Dict[str, str]
    findings: List[Finding] = field(default_factory=list)

    @property
    def error_codes(self) -> List[str]:
        return [f.code for f in self.findings if f.severity == ERROR]

    @property
    def warning_codes(self) -> List[str]:
        return [f.code for f in self.findings if f.severity == WARNING]

    @property
    def has_error(self) -> bool:
        return bool(self.error_codes)

    @property
    def severity(self) -> str:
        return ERROR if self.has_error else (WARNING if self.warning_codes else "ok")

    @property
    def reason(self) -> str:
        """给人看的原因串，多条用「；」连接。"""
        return "；".join(f.message for f in self.findings)


def _check_student_id(row: Dict[str, str], report: RowReport, min_len: int, max_len: int) -> str:
    sid = row.get("学号", "")
    if is_blank(sid):
        report.findings.append(Finding("E001", ERROR, "学号为空，无法确认身份"))
        return ""
    if not sid.isdigit():
        report.findings.append(
            Finding("E002", ERROR, f"学号「{sid}」不是纯数字（含字母、符号或空格）")
        )
    elif not (min_len <= len(sid) <= max_len):
        report.findings.append(
            Finding(
                "W101",
                WARNING,
                f"学号「{sid}」长度 {len(sid)} 位，不在预期的 {min_len}-{max_len} 位区间",
            )
        )
    return sid


def _check_name(row: Dict[str, str], report: RowReport) -> None:
    if is_blank(row.get("姓名")):
        report.findings.append(Finding("E003", ERROR, "姓名为空"))


def _check_email(row: Dict[str, str], report: RowReport, sid: str) -> None:
    email = row.get("邮箱", "")
    if is_blank(email):
        report.findings.append(Finding("E004", ERROR, "邮箱为空"))
        return

    if "@" not in email:
        report.findings.append(
            Finding("E005", ERROR, f"邮箱「{email}」缺少 @ 符号，无法确认域名是 {SCHOOL_EMAIL_DOMAIN}")
        )
        return

    local, _, domain = email.rpartition("@")

    if domain.lower() != SCHOOL_EMAIL_DOMAIN:
        report.findings.append(
            Finding("E005", ERROR, f"邮箱域名「{domain}」不是 {SCHOOL_EMAIL_DOMAIN}")
        )
    elif domain != SCHOOL_EMAIL_DOMAIN:
        # 域名对但大小写不规范：@SMBU.edu.cn 这种
        report.findings.append(
            Finding(
                "W104",
                WARNING,
                f"邮箱域名写作「{domain}」，大小写不规范（已按小写 {SCHOOL_EMAIL_DOMAIN} 处理）",
            )
        )

    # 学号为空或本身非法时就无从比对，跳过，避免报出「应为 2023010A06@...」这种废话
    if sid and sid.isdigit() and local != sid:
        report.findings.append(
            Finding("E006", ERROR, f"邮箱前缀「{local}」与学号「{sid}」不一致，应为 {sid}@{SCHOOL_EMAIL_DOMAIN}")
        )


def _check_choices(row: Dict[str, str], report: RowReport) -> None:
    first = row.get("志愿1", "")
    second = row.get("志愿2", "")

    if is_blank(first):
        report.findings.append(Finding("E007", ERROR, "第一志愿为空，无法分部门"))

    if is_blank(second):
        report.findings.append(Finding("W102", WARNING, "第二志愿为空（允许，只填一个志愿）"))
    elif first and first == second:
        report.findings.append(
            Finding("W103", WARNING, f"两个志愿都填了「{first}」，等同于没填第二志愿")
        )


def validate_dataset(
    ds: Dataset,
    min_sid_len: int = DEFAULT_MIN_SID_LEN,
    max_sid_len: int = DEFAULT_MAX_SID_LEN,
) -> List[RowReport]:
    """对整个数据集跑校验，返回逐行的 RowReport（顺序与输入一致）。"""
    columns = [c for c in ds.columns]

    # 先扫一遍学号，建立「首次出现行号」索引，用于判重复报名
    first_seen: Dict[str, int] = {}
    for row in ds.rows:
        sid = row.get("学号", "")
        if not is_blank(sid):
            first_seen.setdefault(sid, row["__row_no__"])

    reports: List[RowReport] = []
    for row in ds.rows:
        row_no = row["__row_no__"]
        report = RowReport(row_no=row_no, row=row)

        # 整行全空单独处理，没必要再逐字段报错
        if all(is_blank(row.get(c)) for c in columns):
            report.findings.append(Finding("E009", ERROR, "整行全空，疑似导出时多出的空行"))
            reports.append(report)
            continue

        sid = _check_student_id(row, report, min_sid_len, max_sid_len)
        _check_name(row, report)
        _check_email(row, report, sid)
        _check_choices(row, report)

        if sid and first_seen.get(sid) != row_no:
            report.findings.append(
                Finding(
                    "E008",
                    ERROR,
                    f"学号「{sid}」与第 {first_seen[sid]} 行重复报名（保留首次，本行判为重复）",
                )
            )

        reports.append(report)

    return reports


def split_by_severity(
    reports: Sequence[RowReport],
) -> tuple[List[Dict[str, str]], List[RowReport]]:
    """拆出「干净数据」和「有问题的数据」。

    - 干净数据：一条 error 都没有的行（warning 保留，因为那只是提示）
    - 有问题：至少有一条 error，或至少有一条 warning 的行
    """
    clean = [r.row for r in reports if not r.has_error]
    problematic = [r for r in reports if r.findings]
    return clean, problematic
