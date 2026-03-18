"""
네트워크 장비 설정 비교 모듈

이 모듈은 네트워크 장비의 설정 파일을 비교하고 차이점을 분석합니다.
"""

import difflib
import re
from typing import List, Tuple, Dict
from dataclasses import dataclass
from enum import Enum


class DiffType(Enum):
    """차이점 유형"""
    ADDED = "added"      # 추가된 줄
    REMOVED = "removed"  # 삭제된 줄
    MODIFIED = "modified"  # 수정된 줄
    UNCHANGED = "unchanged"  # 변경 없음


@dataclass
class DiffLine:
    """차이점 라인 정보"""
    line_number_old: int
    line_number_new: int
    content: str
    diff_type: DiffType
    is_important: bool = False  # 중요한 변경사항인지 여부


@dataclass
class DiffSummary:
    """비교 요약 정보"""
    total_lines_old: int
    total_lines_new: int
    added_count: int
    removed_count: int
    modified_count: int
    unchanged_count: int
    important_changes: List[str]  # 중요한 변경사항 목록


class ConfigComparator:
    """네트워크 설정 파일 비교기"""

    # 중요한 설정 키워드
    IMPORTANT_KEYWORDS = [
        r'hostname',
        r'interface\s+\S+',
        r'ip\s+address',
        r'ip\s+route',
        r'ip\s+default-gateway',
        r'access-list',
        r'ip\s+access-group',
        r'router\s+\w+',
        r'snmp-server',
        r'username',
        r'enable\s+secret',
        r'enable\s+password',
        r'line\s+vty',
        r'line\s+con',
        r'vlan\s+\d+',
        r'spanning-tree',
        r'switchport',
        r'crypto\s+',           # VPN/IPSec/SSH crypto
        r'aaa\s+',              # AAA 인증/권한
        r'ntp\s+server',        # NTP 서버
        r'banner\s+',           # 로그인 배너
        r'service\s+',          # service 명령어
        r'license\s+',          # 라이선스
        r'version\s+\d+\.\d+',  # IOS 버전
        r'class-map',           # QoS
        r'policy-map',          # QoS
        r'ip\s+nat',            # NAT
        r'ip\s+helper-address', # DHCP relay
        r'standby\s+',          # HSRP
        r'vrrp\s+',             # VRRP
        r'redundancy',          # 이중화
        r'boot\s+system',       # 부팅 이미지
    ]

    # 무시할 줄 (노이즈 제거)
    IGNORE_PATTERNS = [
        r'^\s*!',                      # 주석
        r'^\s*$',                      # 빈 줄
        r'Building configuration',
        r'Current configuration',
        r'Last configuration change',
        r'NVRAM config last updated',
        r'ntp clock-period',
        r'.*uptime\s+is\s+',           # show version의 uptime (재부팅 후 항상 변경)
        r'Uptime for this control',
        r'^\s*System\s+restarted\s+at',
    ]

    def __init__(self):
        self.ignore_whitespace = True
        self.ignore_comments = True
        self.case_sensitive = False

    def compare_files(self, file1_path: str, file2_path: str) -> Tuple[List[DiffLine], DiffSummary]:
        """
        두 설정 파일을 비교합니다.

        Args:
            file1_path: 첫 번째 파일 경로 (이전 설정)
            file2_path: 두 번째 파일 경로 (현재 설정)

        Returns:
            (차이점 라인 리스트, 요약 정보)
        """
        try:
            with open(file1_path, 'r', encoding='utf-8') as f1:
                lines1 = f1.readlines()
        except UnicodeDecodeError:
            with open(file1_path, 'r', encoding='latin-1') as f1:
                lines1 = f1.readlines()

        try:
            with open(file2_path, 'r', encoding='utf-8') as f2:
                lines2 = f2.readlines()
        except UnicodeDecodeError:
            with open(file2_path, 'r', encoding='latin-1') as f2:
                lines2 = f2.readlines()

        return self.compare_lines(lines1, lines2)

    def compare_strings(self, config1: str, config2: str) -> Tuple[List[DiffLine], DiffSummary]:
        """
        두 설정 문자열을 비교합니다.

        Args:
            config1: 첫 번째 설정 문자열 (이전)
            config2: 두 번째 설정 문자열 (현재)

        Returns:
            (차이점 라인 리스트, 요약 정보)
        """
        lines1 = config1.splitlines(keepends=True)
        lines2 = config2.splitlines(keepends=True)
        return self.compare_lines(lines1, lines2)

    def compare_lines(self, lines1: List[str], lines2: List[str]) -> Tuple[List[DiffLine], DiffSummary]:
        """
        두 설정 라인 리스트를 비교합니다.

        Args:
            lines1: 첫 번째 설정 라인 (이전)
            lines2: 두 번째 설정 라인 (현재)

        Returns:
            (차이점 라인 리스트, 요약 정보)
        """
        # 전처리
        if self.ignore_whitespace or self.ignore_comments:
            lines1 = [self._preprocess_line(line) for line in lines1]
            lines2 = [self._preprocess_line(line) for line in lines2]

            # 빈 줄 제거
            lines1 = [line for line in lines1 if line.strip()]
            lines2 = [line for line in lines2 if line.strip()]

        # difflib를 사용한 차이점 분석
        diff = difflib.unified_diff(
            lines1, lines2,
            lineterm='',
            n=0  # 컨텍스트 라인 수
        )

        diff_lines = []
        line_num_old = 0
        line_num_new = 0

        added_count = 0
        removed_count = 0
        modified_count = 0
        unchanged_count = 0
        important_changes = []

        # unified_diff 결과 파싱
        for line in diff:
            if line.startswith('---') or line.startswith('+++'):
                continue
            elif line.startswith('@@'):
                # 라인 번호 정보 추출
                match = re.search(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', line)
                if match:
                    line_num_old = int(match.group(1))
                    line_num_new = int(match.group(3))
                continue
            elif line.startswith('-'):
                # 삭제된 줄
                content = line[1:].rstrip()
                is_important = self._is_important_line(content)
                diff_lines.append(DiffLine(
                    line_number_old=line_num_old,
                    line_number_new=-1,
                    content=content,
                    diff_type=DiffType.REMOVED,
                    is_important=is_important
                ))
                if is_important:
                    important_changes.append(f"삭제: {content[:80]}")
                line_num_old += 1
                removed_count += 1
            elif line.startswith('+'):
                # 추가된 줄
                content = line[1:].rstrip()
                is_important = self._is_important_line(content)
                diff_lines.append(DiffLine(
                    line_number_old=-1,
                    line_number_new=line_num_new,
                    content=content,
                    diff_type=DiffType.ADDED,
                    is_important=is_important
                ))
                if is_important:
                    important_changes.append(f"추가: {content[:80]}")
                line_num_new += 1
                added_count += 1
            else:
                # 변경 없는 줄
                unchanged_count += 1
                line_num_old += 1
                line_num_new += 1

        # 요약 정보 생성
        summary = DiffSummary(
            total_lines_old=len(lines1),
            total_lines_new=len(lines2),
            added_count=added_count,
            removed_count=removed_count,
            modified_count=modified_count,
            unchanged_count=unchanged_count,
            important_changes=important_changes
        )

        return diff_lines, summary

    def _preprocess_line(self, line: str) -> str:
        """줄 전처리 (공백, 주석 제거)"""
        # 무시할 패턴 체크
        for pattern in self.IGNORE_PATTERNS:
            if re.match(pattern, line):
                return ''

        # 공백 정규화
        if self.ignore_whitespace:
            line = ' '.join(line.split())

        # 대소문자 무시
        if not self.case_sensitive:
            line = line.lower()

        return line

    def _is_important_line(self, line: str) -> bool:
        """중요한 설정 라인인지 확인"""
        for keyword_pattern in self.IMPORTANT_KEYWORDS:
            if re.search(keyword_pattern, line, re.IGNORECASE):
                return True
        return False

    # ── Side-by-side helpers ─────────────────────────────────────

    def _make_sidebyside_rows(self, lines1: List[str], lines2: List[str]) -> list:
        """
        SequenceMatcher로 두 줄 목록을 정렬하여 (left, right, type) 튜플 리스트 반환.
        type: 'equal' | 'replace' | 'delete' | 'insert'
        """
        sm = difflib.SequenceMatcher(None, lines1, lines2, autojunk=False)
        rows = []
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == 'equal':
                for k in range(i2 - i1):
                    rows.append((lines1[i1 + k], lines2[j1 + k], 'equal'))
            elif op == 'replace':
                lb, rb = lines1[i1:i2], lines2[j1:j2]
                for k in range(max(len(lb), len(rb))):
                    l = lb[k] if k < len(lb) else None
                    r = rb[k] if k < len(rb) else None
                    rows.append((l, r, 'replace'))
            elif op == 'delete':
                for l in lines1[i1:i2]:
                    rows.append((l, None, 'delete'))
            elif op == 'insert':
                for r in lines2[j1:j2]:
                    rows.append((None, r, 'insert'))
        return rows

    def _inline_diff_html(self, text1: str, text2: str) -> tuple:
        """
        문자 단위 비교 → (html1, html2).
        달라진 부분에 <span class='hi'>…</span> 마킹.
        """
        sm = difflib.SequenceMatcher(None, text1, text2, autojunk=False)
        h1, h2 = [], []
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            s1 = self._escape_html(text1[i1:i2])
            s2 = self._escape_html(text2[j1:j2])
            if op == 'equal':
                h1.append(s1)
                h2.append(s2)
            elif op == 'replace':
                if s1:
                    h1.append(f'<span class="hi">{s1}</span>')
                if s2:
                    h2.append(f'<span class="hi">{s2}</span>')
            elif op == 'delete':
                if s1:
                    h1.append(f'<span class="hi">{s1}</span>')
            elif op == 'insert':
                if s2:
                    h2.append(f'<span class="hi">{s2}</span>')
        return ''.join(h1), ''.join(h2)

    def generate_sidebyside_html(self, config1: str, config2: str,
                                 title: str = "설정 비교 결과") -> str:
        """
        두 설정을 나란히 비교하는 HTML 보고서 생성.
        - 줄 정렬 : SequenceMatcher
        - 인라인 하이라이트 : 달라진 문자/단어에만 빨간 배경
        """
        lines1 = config1.splitlines()
        lines2 = config2.splitlines()

        # 노이즈 필터링 (옵션 적용)
        if self.ignore_whitespace or self.ignore_comments:
            lines1 = [l for l in lines1 if self._preprocess_line(l).strip()]
            lines2 = [l for l in lines2 if self._preprocess_line(l).strip()]

        rows = self._make_sidebyside_rows(lines1, lines2)

        added   = sum(1 for _, r, t in rows if t == 'insert')
        removed = sum(1 for l, _, t in rows if t == 'delete')
        changed = sum(1 for _, _, t in rows if t == 'replace' and _ is not None)
        total   = added + removed + changed

        # 줄 번호 카운터
        ln1 = ln2 = 0

        tbody_rows = []
        for left, right, rtype in rows:
            # 줄 번호
            if left is not None:
                ln1 += 1
                ln1_str = str(ln1)
            else:
                ln1_str = ''
            if right is not None:
                ln2 += 1
                ln2_str = str(ln2)
            else:
                ln2_str = ''

            if rtype == 'equal':
                le = self._escape_html(left)
                re_ = self._escape_html(right)
                tbody_rows.append(
                    f'<tr class="eq">'
                    f'<td class="ln">{ln1_str}</td><td class="lc">{le}</td>'
                    f'<td class="ln">{ln2_str}</td><td class="rc">{re_}</td>'
                    f'</tr>'
                )
            elif rtype == 'replace':
                if left is not None and right is not None:
                    lh, rh = self._inline_diff_html(left, right)
                    tbody_rows.append(
                        f'<tr class="ch">'
                        f'<td class="ln">{ln1_str}</td><td class="lc del">{lh}</td>'
                        f'<td class="ln">{ln2_str}</td><td class="rc add">{rh}</td>'
                        f'</tr>'
                    )
                elif left is not None:
                    le = self._escape_html(left)
                    tbody_rows.append(
                        f'<tr class="ch">'
                        f'<td class="ln">{ln1_str}</td><td class="lc del">{le}</td>'
                        f'<td class="ln"></td><td class="rc empty"></td>'
                        f'</tr>'
                    )
                else:
                    re_ = self._escape_html(right)
                    tbody_rows.append(
                        f'<tr class="ch">'
                        f'<td class="ln"></td><td class="lc empty"></td>'
                        f'<td class="ln">{ln2_str}</td><td class="rc add">{re_}</td>'
                        f'</tr>'
                    )
            elif rtype == 'delete':
                le = self._escape_html(left)
                tbody_rows.append(
                    f'<tr class="ch">'
                    f'<td class="ln">{ln1_str}</td><td class="lc del">{le}</td>'
                    f'<td class="ln"></td><td class="rc empty"></td>'
                    f'</tr>'
                )
            elif rtype == 'insert':
                re_ = self._escape_html(right)
                tbody_rows.append(
                    f'<tr class="ch">'
                    f'<td class="ln"></td><td class="lc empty"></td>'
                    f'<td class="ln">{ln2_str}</td><td class="rc add">{re_}</td>'
                    f'</tr>'
                )

        tbody_html = '\n'.join(tbody_rows)

        return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{self._escape_html(title)}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: Consolas, 'Courier New', monospace; font-size: 12px;
          background: #f1f5f9; color: #1e293b; }}
  .header {{ background: #1e293b; color: #f8fafc; padding: 16px 24px; }}
  .header h1 {{ font-size: 18px; font-weight: 700; }}
  .header p  {{ font-size: 11px; color: #94a3b8; margin-top: 4px; }}
  .stats {{ display: flex; gap: 12px; padding: 12px 24px;
            background: #fff; border-bottom: 1px solid #e2e8f0; flex-wrap: wrap; }}
  .badge {{ padding: 4px 12px; border-radius: 12px; font-size: 11px; font-weight: 700; }}
  .b-add {{ background: #dcfce7; color: #15803d; }}
  .b-del {{ background: #fee2e2; color: #b91c1c; }}
  .b-chg {{ background: #fef3c7; color: #92400e; }}
  .b-tot {{ background: #eff6ff; color: #1d4ed8; }}
  .wrap {{ padding: 16px 24px; }}
  table {{ border-collapse: collapse; width: 100%; background: #fff;
           border-radius: 6px; overflow: hidden;
           box-shadow: 0 1px 4px rgba(0,0,0,.1); }}
  col.ln {{ width: 42px; }}
  col.code {{ width: calc(50% - 42px); }}
  thead tr {{ background: #334155; color: #f1f5f9; }}
  thead th {{ padding: 8px 10px; font-size: 11px; font-weight: 700;
              text-align: left; border: none; }}
  .ln {{ width: 42px; min-width: 42px; text-align: right; padding: 2px 6px;
         color: #94a3b8; background: #f8fafc; border-right: 1px solid #e2e8f0;
         user-select: none; font-size: 10px; vertical-align: top; }}
  td.lc, td.rc {{ padding: 2px 8px; white-space: pre-wrap; word-break: break-all;
                  vertical-align: top; }}
  tr.eq td.lc, tr.eq td.rc {{ background: #fff; }}
  td.del {{ background: #fef2f2; }}
  td.add {{ background: #f0fdf4; }}
  td.empty {{ background: #f8fafc; }}
  span.hi {{ background: #fca5a5; border-radius: 2px; padding: 0 1px; }}
  td.add span.hi {{ background: #86efac; }}
  .mid {{ width: 1px; background: #e2e8f0; }}
  tbody tr:hover td {{ filter: brightness(0.97); }}
</style>
</head>
<body>
<div class="header">
  <h1>{self._escape_html(title)}</h1>
  <p>생성: {self._get_current_time()} &nbsp;|&nbsp;
     Before: {ln1}줄 &nbsp;|&nbsp; After: {ln2}줄</p>
</div>
<div class="stats">
  <span class="badge b-del">삭제 {removed}줄</span>
  <span class="badge b-add">추가 {added}줄</span>
  <span class="badge b-chg">수정 {changed}줄</span>
  <span class="badge b-tot">총 변경 {total}줄</span>
</div>
<div class="wrap">
<table>
  <colgroup>
    <col class="ln"><col class="code"><col class="ln"><col class="code">
  </colgroup>
  <thead>
    <tr>
      <th>#</th><th>업그레이드 전 (Before)</th>
      <th>#</th><th>업그레이드 후 (After)</th>
    </tr>
  </thead>
  <tbody>
{tbody_html}
  </tbody>
</table>
</div>
</body>
</html>"""

    def generate_html_report(self, diff_lines: List[DiffLine], summary: DiffSummary,
                            title: str = "설정 비교 결과") -> str:
        """
        HTML 형식의 비교 리포트를 생성합니다.

        Args:
            diff_lines: 차이점 라인 리스트
            summary: 요약 정보
            title: 리포트 제목

        Returns:
            HTML 문자열
        """
        html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: 'Consolas', 'Monaco', monospace;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background-color: #2c3e50;
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .summary {{
            background-color: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .summary-item {{
            display: inline-block;
            margin-right: 20px;
            padding: 10px;
        }}
        .added {{ background-color: #d4edda; color: #155724; }}
        .removed {{ background-color: #f8d7da; color: #721c24; }}
        .modified {{ background-color: #fff3cd; color: #856404; }}
        .important {{ border-left: 4px solid #ff6b6b; padding-left: 8px; font-weight: bold; }}
        .diff-container {{
            background-color: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .diff-line {{
            padding: 4px 8px;
            margin: 2px 0;
            font-size: 13px;
            line-height: 1.6;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        .line-number {{
            display: inline-block;
            width: 60px;
            text-align: right;
            margin-right: 10px;
            color: #666;
            user-select: none;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{title}</h1>
        <p>생성 시간: {self._get_current_time()}</p>
    </div>

    <div class="summary">
        <h2>📊 비교 요약</h2>
        <div class="summary-item added">
            ➕ 추가: {summary.added_count}줄
        </div>
        <div class="summary-item removed">
            ➖ 삭제: {summary.removed_count}줄
        </div>
        <div class="summary-item">
            📝 총 변경: {summary.added_count + summary.removed_count}줄
        </div>
        <div style="margin-top: 15px;">
            <strong>이전 설정:</strong> {summary.total_lines_old}줄 |
            <strong>현재 설정:</strong> {summary.total_lines_new}줄
        </div>
"""

        # 중요한 변경사항 표시
        if summary.important_changes:
            html += """
        <div style="margin-top: 15px;">
            <h3>⚠️ 주요 변경사항</h3>
            <ul>
"""
            for change in summary.important_changes[:10]:  # 최대 10개만 표시
                html += f"                <li>{change}</li>\n"
            html += """            </ul>
        </div>
"""

        html += """    </div>

    <div class="diff-container">
        <h2>🔍 상세 차이점</h2>
"""

        # 차이점 라인 표시
        for line in diff_lines:
            css_class = f"diff-line {line.diff_type.value}"
            if line.is_important:
                css_class += " important"

            line_num = ""
            if line.diff_type == DiffType.REMOVED:
                line_num = f"<span class='line-number'>-{line.line_number_old}</span>"
                prefix = "- "
            elif line.diff_type == DiffType.ADDED:
                line_num = f"<span class='line-number'>+{line.line_number_new}</span>"
                prefix = "+ "
            else:
                line_num = f"<span class='line-number'>{line.line_number_old}</span>"
                prefix = "  "

            content = self._escape_html(line.content)
            html += f'        <div class="{css_class}">{line_num}{prefix}{content}</div>\n'

        html += """    </div>
</body>
</html>
"""
        return html

    def generate_text_report(self, diff_lines: List[DiffLine], summary: DiffSummary) -> str:
        """
        텍스트 형식의 비교 리포트를 생성합니다.

        Args:
            diff_lines: 차이점 라인 리스트
            summary: 요약 정보

        Returns:
            텍스트 문자열
        """
        lines = []
        lines.append("=" * 80)
        lines.append("설정 비교 결과")
        lines.append("=" * 80)
        lines.append(f"생성 시간: {self._get_current_time()}")
        lines.append("")

        # 요약
        lines.append("📊 비교 요약")
        lines.append("-" * 80)
        lines.append(f"이전 설정: {summary.total_lines_old}줄")
        lines.append(f"현재 설정: {summary.total_lines_new}줄")
        lines.append(f"추가된 줄: {summary.added_count}")
        lines.append(f"삭제된 줄: {summary.removed_count}")
        lines.append(f"총 변경: {summary.added_count + summary.removed_count}줄")
        lines.append("")

        # 중요한 변경사항
        if summary.important_changes:
            lines.append("⚠️ 주요 변경사항")
            lines.append("-" * 80)
            for change in summary.important_changes[:10]:
                lines.append(f"  • {change}")
            lines.append("")

        # 상세 차이점
        lines.append("🔍 상세 차이점")
        lines.append("-" * 80)

        for line in diff_lines:
            if line.diff_type == DiffType.REMOVED:
                prefix = "- "
                marker = "[삭제] " if line.is_important else ""
            elif line.diff_type == DiffType.ADDED:
                prefix = "+ "
                marker = "[추가] " if line.is_important else ""
            else:
                prefix = "  "
                marker = ""

            lines.append(f"{prefix}{marker}{line.content}")

        return "\n".join(lines)

    def _escape_html(self, text: str) -> str:
        """HTML 특수 문자 이스케이프"""
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#39;'))

    def _get_current_time(self) -> str:
        """현재 시간 문자열 반환"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# 편의 함수
def compare_config_files(file1: str, file2: str) -> Tuple[List[DiffLine], DiffSummary]:
    """
    두 설정 파일을 비교합니다 (간편 함수).

    Args:
        file1: 이전 설정 파일 경로
        file2: 현재 설정 파일 경로

    Returns:
        (차이점 라인 리스트, 요약 정보)
    """
    comparator = ConfigComparator()
    return comparator.compare_files(file1, file2)


def generate_diff_report(file1: str, file2: str, output_path: str, format: str = 'html'):
    """
    설정 비교 리포트를 생성하고 파일로 저장합니다.

    Args:
        file1: 이전 설정 파일 경로
        file2: 현재 설정 파일 경로
        output_path: 출력 파일 경로
        format: 출력 형식 ('html' 또는 'text')
    """
    comparator = ConfigComparator()
    diff_lines, summary = comparator.compare_files(file1, file2)

    if format.lower() == 'html':
        report = comparator.generate_html_report(diff_lines, summary)
    else:
        report = comparator.generate_text_report(diff_lines, summary)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)
