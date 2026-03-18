"""
파일 뷰어 탭 — LOG · TXT 통합 뷰어
검색, 줄 번호, 구문 강조, 인코딩 선택, 파일 목록
"""
import os
import re
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QPlainTextEdit, QComboBox,
    QFrame, QSplitter, QListWidget, QListWidgetItem,
    QCheckBox, QShortcut, QInputDialog, QMessageBox, QTextEdit,
    QSizePolicy,
)
from PyQt5.QtGui import (
    QFont, QColor, QTextCharFormat, QSyntaxHighlighter,
    QPainter, QKeySequence, QBrush, QTextCursor, QTextDocument,
)
from PyQt5.QtCore import Qt, QRect, QSize, QRegExp


# ── 인코딩 자동 감지 ─────────────────────────────────────────────────────────
def _detect_enc(raw: bytes) -> str:
    for enc in ('utf-8-sig', 'utf-8', 'cp949', 'euc-kr', 'latin-1'):
        try:
            raw.decode(enc)
            return enc
        except (UnicodeDecodeError, LookupError):
            pass
    return 'latin-1'


# ── 텍스트 서식 헬퍼 ─────────────────────────────────────────────────────────
def _tf(bg=None, fg=None, bold=False):
    f = QTextCharFormat()
    if bg:
        f.setBackground(QBrush(QColor(bg)))
    if fg:
        f.setForeground(QBrush(QColor(fg)))
    if bold:
        f.setFontWeight(QFont.Bold)
    return f


# ── 세로 구분선 헬퍼 ─────────────────────────────────────────────────────────
def _vline():
    f = QFrame()
    f.setFrameShape(QFrame.VLine)
    f.setFixedWidth(1)
    f.setStyleSheet('QFrame{background:#e2e8f0;border:none}')
    return f


# ── 줄 번호 영역 ─────────────────────────────────────────────────────────────
class _LNArea(QWidget):
    def __init__(self, ed):
        super().__init__(ed)
        self.ed = ed

    def sizeHint(self):
        return QSize(self.ed._ln_w(), 0)

    def paintEvent(self, e):
        self.ed._draw_ln(e)


# ── 에디터 (읽기 전용 + 줄 번호) ─────────────────────────────────────────────
class _Ed(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._ln = _LNArea(self)
        self.setReadOnly(True)
        self.setFont(QFont('Consolas', 10))
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setStyleSheet(
            'QPlainTextEdit{'
            '  background:#0d1117;color:#e6edf3;border:none;'
            '  selection-background-color:#264f78;'
            '}'
            'QScrollBar:vertical{background:#161b22;width:10px}'
            'QScrollBar::handle:vertical{background:#30363d;border-radius:5px;min-height:20px}'
            'QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0}'
            'QScrollBar:horizontal{background:#161b22;height:10px}'
            'QScrollBar::handle:horizontal{background:#30363d;border-radius:5px}'
            'QScrollBar::add-line:horizontal,QScrollBar::sub-line:horizontal{width:0}'
        )
        self.blockCountChanged.connect(self._upd_w)
        self.updateRequest.connect(self._upd_area)
        self._upd_w()

    def _ln_w(self):
        d = max(4, len(str(max(1, self.blockCount()))))
        return 12 + self.fontMetrics().horizontalAdvance('0') * d

    def _upd_w(self, _=0):
        self.setViewportMargins(self._ln_w(), 0, 0, 0)

    def _upd_area(self, rect, dy):
        if dy:
            self._ln.scroll(0, dy)
        else:
            self._ln.update(0, rect.y(), self._ln.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._upd_w()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        cr = self.contentsRect()
        self._ln.setGeometry(QRect(cr.left(), cr.top(), self._ln_w(), cr.height()))

    def _draw_ln(self, event):
        p = QPainter(self._ln)
        p.fillRect(event.rect(), QColor('#161b22'))
        block = self.firstVisibleBlock()
        n = block.blockNumber()
        top    = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())
        h  = self.fontMetrics().height()
        fs = max(7, self.font().pointSize() - 1)
        p.setFont(QFont('Consolas', fs))
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                # 현재 줄 강조
                cur_line = self.textCursor().blockNumber()
                if n == cur_line:
                    p.fillRect(0, top, self._ln.width(), h, QColor('#1f2937'))
                    p.setPen(QColor('#e2e8f0'))
                else:
                    p.setPen(QColor('#484f58'))
                p.drawText(0, top, self._ln.width() - 4, h, Qt.AlignRight, str(n + 1))
            block  = block.next()
            top    = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            n += 1

    def set_font_size(self, sz):
        f = self.font()
        f.setPointSize(max(7, min(24, sz)))
        self.setFont(f)
        self._upd_w()
        self._ln.update()


# ── 로그 구문 하이라이터 (다크 테마) ─────────────────────────────────────────
class _Hl(QSyntaxHighlighter):
    _R = [
        # Cisco syslog: %FAC-SEV-MNE
        (QRegExp(r'%[A-Z0-9_]+-\d+-[A-Z0-9_]+'),          _tf(fg='#d2a8ff', bold=True)),
        # ISO 날짜시간
        (QRegExp(r'\b\d{4}[-/]\d{2}[-/]\d{2}[T ]\d{2}:\d{2}(?::\d{2})?'),
         _tf(fg='#7ee787')),
        # Syslog 날짜 (Jan 01 12:00:00)
        (QRegExp(r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}'),
         _tf(fg='#7ee787')),
        # ERROR / CRITICAL / FATAL / DOWN
        (QRegExp(r'\b(?:ERROR|CRITICAL|FATAL|FAIL(?:ED)?|DOWN|UNREACHABLE)\b', Qt.CaseInsensitive),
         _tf(bg='#3d0f0f', fg='#f85149', bold=True)),
        # WARNING
        (QRegExp(r'\b(?:WARN(?:ING)?)\b', Qt.CaseInsensitive),
         _tf(bg='#2d1a00', fg='#e3b341', bold=True)),
        # SUCCESS / OK / UP / CONNECTED
        (QRegExp(r'\b(?:SUCCESS(?:FUL)?|OK|PASS(?:ED)?|UP|CONNECTED|ESTABLISHED)\b', Qt.CaseInsensitive),
         _tf(fg='#3fb950', bold=True)),
        # INFO / NOTICE
        (QRegExp(r'\b(?:INFO(?:RMATION)?|NOTICE)\b', Qt.CaseInsensitive),
         _tf(fg='#58a6ff', bold=True)),
        # DEBUG
        (QRegExp(r'\bDEBUG\b', Qt.CaseInsensitive),
         _tf(fg='#484f58')),
        # IP 주소 (CIDR 포함)
        (QRegExp(r'\b(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?\b'),
         _tf(fg='#79c0ff')),
        # 인터페이스 이름
        (QRegExp(r'\b(?:GigabitEthernet|TenGigabitEthernet|FastEthernet|'
                 r'Loopback|Vlan|Port-channel|Gi|Te|Fa|Lo|Po|Vl|Et|Mg)\d+(?:[/\.]\d+)*\b',
                 Qt.CaseInsensitive),
         _tf(fg='#ffa657')),
        # MAC 주소 (Cisco dot 형식)
        (QRegExp(r'\b(?:[0-9a-fA-F]{4}\.){2}[0-9a-fA-F]{4}\b'),
         _tf(fg='#c9d1d9')),
        # 따옴표 문자열
        (QRegExp(r'"[^"]*"'),
         _tf(fg='#a5d6ff')),
    ]

    def highlightBlock(self, text):
        for pat, fmt in self._R:
            i = pat.indexIn(text)
            while i >= 0:
                self.setFormat(i, pat.matchedLength(), fmt)
                i = pat.indexIn(text, i + pat.matchedLength())


# ── 메인 파일 뷰어 탭 ────────────────────────────────────────────────────────
class FileViewerTab(QWidget):

    _EXT = ('.log', '.txt', '.cfg', '.conf', '.ini', '.csv', '.out', '.syslog')
    _MAX_WARN = 5 * 1024 * 1024   # 5 MB: 경고
    _MAX_SIZE = 30 * 1024 * 1024  # 30 MB: 거부

    def __init__(self, parent=None):
        super().__init__(parent)
        self._file      = ''
        self._enc       = 'utf-8'
        self._folder    = ''
        self._recent    = []        # [path, ...]  최대 10
        self._matches   = []        # [QTextCursor, ...]
        self._match_idx = -1
        self._font_size = 10
        self._hl        = None
        self._build_ui()

    # ── UI 구성 ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        from ui.report_tab import _Header
        self.setObjectName('fileViewerTab')
        self.setStyleSheet('#fileViewerTab { background: #f1f5f9; }')
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(_Header(
            '파일 뷰어',
            'LOG · TXT 파일 분석 · 검색 · 구문 강조 · 인코딩 자동 감지',
            '#0f172a', '#0891b2',
        ))

        body = QWidget()
        body.setObjectName('fileViewerBody')
        body.setStyleSheet('#fileViewerBody { background: transparent; }')
        bv = QVBoxLayout(body)
        bv.setContentsMargins(10, 8, 10, 8)
        bv.setSpacing(5)
        root.addWidget(body, 1)

        bv.addWidget(self._mk_toolbar())
        bv.addWidget(self._mk_search_bar())

        # 메인 스플리터
        self._spl = QSplitter(Qt.Horizontal)
        self._spl.setHandleWidth(4)

        self._file_panel = self._mk_file_panel()
        self._file_panel.hide()
        self._spl.addWidget(self._file_panel)

        self._ed = _Ed()
        self._hl = _Hl(self._ed.document())
        self._ed.cursorPositionChanged.connect(self._on_cursor)
        self._spl.addWidget(self._ed)
        self._spl.setSizes([220, 780])
        bv.addWidget(self._spl, 1)

        bv.addWidget(self._mk_status_bar())

        # 단축키
        QShortcut(QKeySequence.Find,          self, self._focus_search)
        QShortcut(QKeySequence('F3'),         self, self._find_next)
        QShortcut(QKeySequence('Shift+F3'),   self, self._find_prev)
        QShortcut(QKeySequence('Ctrl+G'),     self, self._goto_line)
        QShortcut(QKeySequence('Ctrl+='),     self, lambda: self._set_font(self._font_size + 1))
        QShortcut(QKeySequence('Ctrl+-'),     self, lambda: self._set_font(self._font_size - 1))
        QShortcut(QKeySequence('Ctrl+Home'),  self, lambda: self._ed.moveCursor(QTextCursor.Start))
        QShortcut(QKeySequence('Ctrl+End'),   self, lambda: self._ed.moveCursor(QTextCursor.End))

    # ── 툴바 ─────────────────────────────────────────────────────────────────
    def _mk_toolbar(self):
        bar = QFrame()
        bar.setStyleSheet(
            'QFrame{background:#ffffff;border-radius:8px;border:1px solid #e2e8f0}'
        )
        h = QHBoxLayout(bar)
        h.setContentsMargins(10, 6, 10, 6)
        h.setSpacing(5)

        def _pbtn(label, color, hover, fn, tip=''):
            b = QPushButton(label)
            b.setFixedHeight(30)
            b.setFont(QFont('맑은 고딕', 9, QFont.Bold))
            b.setToolTip(tip)
            b.setStyleSheet(
                f'QPushButton{{background:{color};color:#fff;border:none;'
                f'border-radius:6px;padding:0 12px}}'
                f'QPushButton:hover{{background:{hover}}}'
            )
            b.clicked.connect(fn)
            return b

        def _sbtn(label, fn, tip='', checked=False):
            b = QPushButton(label)
            b.setFixedHeight(30)
            b.setFont(QFont('맑은 고딕', 9))
            b.setToolTip(tip)
            b.setCheckable(checked)
            b.setStyleSheet(
                'QPushButton{background:#f1f5f9;color:#475569;'
                'border:1px solid #e2e8f0;border-radius:6px;padding:0 10px}'
                'QPushButton:hover{background:#e2e8f0}'
                'QPushButton:checked{background:#eff6ff;color:#2563eb;border-color:#bfdbfe}'
            )
            b.clicked.connect(fn)
            return b

        h.addWidget(_pbtn('📂 파일 열기', '#3b82f6', '#2563eb', self._open_file, 'Ctrl+O'))
        h.addWidget(_pbtn('📁 폴더 열기', '#0891b2', '#0e7490', self._open_folder, '폴더 내 파일 목록'))

        # 최근 파일
        self._recent_cb = QComboBox()
        self._recent_cb.setFixedHeight(30)
        self._recent_cb.setMinimumWidth(200)
        self._recent_cb.setMaximumWidth(300)
        self._recent_cb.setFont(QFont('맑은 고딕', 9))
        self._recent_cb.addItem('⏱ 최근 파일...')
        self._recent_cb.setStyleSheet(
            'QComboBox{background:#f8fafc;border:1px solid #e2e8f0;'
            'border-radius:6px;padding:2px 8px;color:#1e293b}'
            'QComboBox::drop-down{border:none;width:20px}'
            'QComboBox QAbstractItemView{background:white;color:#1e293b;'
            'selection-background-color:#eff6ff;selection-color:#2563eb}'
        )
        self._recent_cb.currentIndexChanged.connect(self._open_recent)
        h.addWidget(self._recent_cb)

        h.addWidget(_vline())

        # 인코딩
        lbl = QLabel('인코딩:')
        lbl.setFont(QFont('맑은 고딕', 9))
        lbl.setStyleSheet('color:#64748b;background:transparent;border:none')
        h.addWidget(lbl)

        self._enc_cb = QComboBox()
        self._enc_cb.setFixedHeight(30)
        self._enc_cb.setFixedWidth(110)
        self._enc_cb.addItems(['자동 감지', 'UTF-8', 'CP949', 'EUC-KR', 'Latin-1'])
        self._enc_cb.setFont(QFont('맑은 고딕', 9))
        self._enc_cb.setStyleSheet(
            'QComboBox{background:#f8fafc;border:1px solid #e2e8f0;'
            'border-radius:6px;padding:2px 8px;color:#1e293b}'
            'QComboBox::drop-down{border:none;width:20px}'
        )
        self._enc_cb.currentTextChanged.connect(self._reload_enc)
        h.addWidget(self._enc_cb)

        h.addWidget(_vline())

        # 글꼴 크기
        lbl2 = QLabel('크기:')
        lbl2.setFont(QFont('맑은 고딕', 9))
        lbl2.setStyleSheet('color:#64748b;background:transparent;border:none')
        h.addWidget(lbl2)

        for txt, delta in (('A−', -1), ('A+', 1)):
            b = QPushButton(txt)
            b.setFixedSize(32, 30)
            b.setFont(QFont('맑은 고딕', 9, QFont.Bold))
            b.setStyleSheet(
                'QPushButton{background:#f1f5f9;color:#475569;'
                'border:1px solid #e2e8f0;border-radius:6px}'
                'QPushButton:hover{background:#e2e8f0}'
            )
            d = delta
            b.clicked.connect(lambda _, dv=d: self._set_font(self._font_size + dv))
            h.addWidget(b)

        self._fz_lbl = QLabel('10')
        self._fz_lbl.setFixedWidth(22)
        self._fz_lbl.setAlignment(Qt.AlignCenter)
        self._fz_lbl.setFont(QFont('맑은 고딕', 9, QFont.Bold))
        self._fz_lbl.setStyleSheet('color:#1e293b;background:transparent;border:none')
        h.addWidget(self._fz_lbl)

        h.addWidget(_vline())

        self._wrap_btn = _sbtn('⏎ 줄바꿈', self._toggle_wrap, '긴 줄 자동 줄바꿈', checked=True)
        self._wrap_btn.setChecked(False)
        h.addWidget(self._wrap_btn)

        self._hl_btn = _sbtn('🎨 색상', self._toggle_hl, '구문 색상 강조', checked=True)
        self._hl_btn.setChecked(True)
        h.addWidget(self._hl_btn)

        self._list_btn = _sbtn('≡ 파일 목록', self._toggle_file_list, '폴더 파일 목록 표시', checked=True)
        self._list_btn.setChecked(False)
        h.addWidget(self._list_btn)

        h.addStretch()

        # 오른쪽 유틸 버튼
        h.addWidget(_sbtn('복사', self._copy_text, '선택 텍스트 복사 (없으면 전체)'))

        goto_btn = _sbtn('줄 이동', self._goto_line, 'Ctrl+G — 특정 줄로 이동')
        h.addWidget(goto_btn)

        save_btn = QPushButton('💾 저장')
        save_btn.setFixedHeight(30)
        save_btn.setFont(QFont('맑은 고딕', 9))
        save_btn.setStyleSheet(
            'QPushButton{background:#10b981;color:#fff;border:none;'
            'border-radius:6px;padding:0 12px}'
            'QPushButton:hover{background:#059669}'
        )
        save_btn.clicked.connect(self._save_as)
        h.addWidget(save_btn)

        return bar

    # ── 검색바 ───────────────────────────────────────────────────────────────
    def _mk_search_bar(self):
        bar = QFrame()
        bar.setStyleSheet(
            'QFrame{background:#ffffff;border-radius:8px;border:1px solid #e2e8f0}'
        )
        h = QHBoxLayout(bar)
        h.setContentsMargins(10, 5, 10, 5)
        h.setSpacing(5)

        icon = QLabel('🔍')
        icon.setFont(QFont('맑은 고딕', 11))
        icon.setStyleSheet('background:transparent;border:none')
        h.addWidget(icon)

        self._search_in = QLineEdit()
        self._search_in.setPlaceholderText('검색어 입력  (F3: 다음  Shift+F3: 이전  Ctrl+F: 포커스)')
        self._search_in.setFont(QFont('맑은 고딕', 10))
        self._search_in.setFixedHeight(28)
        self._search_in.setStyleSheet(
            'QLineEdit{background:#f8fafc;border:1px solid #e2e8f0;'
            'border-radius:6px;padding:2px 8px;color:#1e293b}'
            'QLineEdit:focus{border:1px solid #3b82f6}'
        )
        self._search_in.textChanged.connect(self._do_search)
        self._search_in.returnPressed.connect(self._find_next)
        h.addWidget(self._search_in, 4)

        for lbl, fn in (('◀', self._find_prev), ('▶', self._find_next)):
            b = QPushButton(lbl)
            b.setFixedSize(28, 28)
            b.setFont(QFont('맑은 고딕', 9, QFont.Bold))
            b.setStyleSheet(
                'QPushButton{background:#f1f5f9;color:#475569;'
                'border:1px solid #e2e8f0;border-radius:6px}'
                'QPushButton:hover{background:#e2e8f0}'
            )
            b.clicked.connect(fn)
            h.addWidget(b)

        clr_btn = QPushButton('✕')
        clr_btn.setFixedSize(28, 28)
        clr_btn.setFont(QFont('맑은 고딕', 9))
        clr_btn.setStyleSheet(
            'QPushButton{background:#fee2e2;color:#dc2626;border:none;border-radius:6px}'
            'QPushButton:hover{background:#fecaca}'
        )
        clr_btn.clicked.connect(lambda: self._search_in.clear())
        h.addWidget(clr_btn)

        h.addWidget(_vline())

        for attr, lbl, tip in (
            ('_case_cb', 'Aa', '대소문자 구분'),
            ('_regex_cb', '.*', '정규식 사용'),
            ('_word_cb',  'W',  '단어 전체 일치'),
        ):
            cb = QCheckBox(lbl)
            cb.setFont(QFont('맑은 고딕', 9, QFont.Bold))
            cb.setToolTip(tip)
            cb.setStyleSheet('QCheckBox{color:#475569;background:transparent;border:none}')
            cb.toggled.connect(self._do_search)
            setattr(self, attr, cb)
            h.addWidget(cb)

        h.addWidget(_vline())

        self._match_lbl = QLabel('—')
        self._match_lbl.setFont(QFont('맑은 고딕', 9, QFont.Bold))
        self._match_lbl.setStyleSheet('color:#3b82f6;background:transparent;border:none')
        self._match_lbl.setMinimumWidth(62)
        h.addWidget(self._match_lbl)

        h.addStretch()

        # 로그 레벨 필터
        lbl_f = QLabel('필터:')
        lbl_f.setFont(QFont('맑은 고딕', 9))
        lbl_f.setStyleSheet('color:#64748b;background:transparent;border:none')
        h.addWidget(lbl_f)

        self._filter_cb = QComboBox()
        self._filter_cb.setFixedHeight(28)
        self._filter_cb.setFixedWidth(120)
        self._filter_cb.addItems(['전체 표시', 'ERROR+', 'WARNING+', 'INFO+', 'DEBUG'])
        self._filter_cb.setFont(QFont('맑은 고딕', 9))
        self._filter_cb.setStyleSheet(
            'QComboBox{background:#f8fafc;border:1px solid #e2e8f0;'
            'border-radius:6px;padding:2px 8px;color:#1e293b}'
            'QComboBox::drop-down{border:none;width:20px}'
        )
        self._filter_cb.currentTextChanged.connect(self._apply_filter)
        h.addWidget(self._filter_cb)

        return bar

    # ── 파일 목록 패널 ────────────────────────────────────────────────────────
    def _mk_file_panel(self):
        panel = QFrame()
        panel.setFixedWidth(230)
        panel.setStyleSheet(
            'QFrame{background:#ffffff;border-radius:8px;border:1px solid #e2e8f0}'
        )
        v = QVBoxLayout(panel)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(5)

        hdr = QHBoxLayout()
        t = QLabel('📁 파일 목록')
        t.setFont(QFont('맑은 고딕', 9, QFont.Bold))
        t.setStyleSheet('color:#1e293b;background:transparent;border:none')
        hdr.addWidget(t)
        hdr.addStretch()
        v.addLayout(hdr)

        self._dir_lbl = QLabel('')
        self._dir_lbl.setFont(QFont('맑은 고딕', 7))
        self._dir_lbl.setStyleSheet('color:#94a3b8;background:transparent;border:none')
        self._dir_lbl.setWordWrap(True)
        v.addWidget(self._dir_lbl)

        # 파일 검색
        self._flist_search = QLineEdit()
        self._flist_search.setPlaceholderText('🔎 파일명 검색...')
        self._flist_search.setFixedHeight(26)
        self._flist_search.setFont(QFont('맑은 고딕', 9))
        self._flist_search.setStyleSheet(
            'QLineEdit{background:#f8fafc;border:1px solid #e2e8f0;'
            'border-radius:5px;padding:1px 6px;color:#1e293b}'
        )
        self._flist_search.textChanged.connect(self._filter_filelist)
        v.addWidget(self._flist_search)

        self._file_list = QListWidget()
        self._file_list.setFont(QFont('맑은 고딕', 9))
        self._file_list.setStyleSheet(
            'QListWidget{background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px}'
            'QListWidget::item{padding:5px 8px;border-bottom:1px solid #f1f5f9}'
            'QListWidget::item:selected{background:#eff6ff;color:#2563eb}'
            'QListWidget::item:hover:!selected{background:#f1f5f9}'
        )
        self._file_list.itemDoubleClicked.connect(self._on_flist_dblclick)
        self._file_list.itemClicked.connect(self._on_flist_click)
        v.addWidget(self._file_list, 1)

        self._fcount_lbl = QLabel('0 개 파일')
        self._fcount_lbl.setFont(QFont('맑은 고딕', 8))
        self._fcount_lbl.setStyleSheet('color:#94a3b8;background:transparent;border:none')
        v.addWidget(self._fcount_lbl)
        return panel

    # ── 상태바 ───────────────────────────────────────────────────────────────
    def _mk_status_bar(self):
        bar = QFrame()
        bar.setFixedHeight(28)
        bar.setStyleSheet(
            'QFrame{background:#ffffff;border-radius:6px;border:1px solid #e2e8f0}'
        )
        h = QHBoxLayout(bar)
        h.setContentsMargins(12, 0, 12, 0)
        h.setSpacing(12)

        def _sl(text='', color='#64748b', bold=False):
            l = QLabel(text)
            l.setFont(QFont('맑은 고딕', 8, QFont.Bold if bold else QFont.Normal))
            l.setStyleSheet(f'color:{color};background:transparent;border:none')
            return l

        self._st_file  = _sl('파일을 열어주세요', '#64748b')
        self._st_lines = _sl('—', '#475569')
        self._st_size  = _sl('—', '#475569')
        self._st_pos   = _sl('L1  C1', '#94a3b8')
        self._st_enc   = _sl('—', '#7c3aed', bold=True)
        self._st_date  = _sl('—', '#94a3b8')
        self._st_err   = _sl('', '#dc2626', bold=True)

        h.addWidget(self._st_file, 3)
        h.addWidget(_vline())
        h.addWidget(self._st_lines)
        h.addWidget(_vline())
        h.addWidget(self._st_size)
        h.addWidget(_vline())
        h.addWidget(self._st_pos)
        h.addWidget(_vline())
        h.addWidget(self._st_enc)
        h.addWidget(_vline())
        h.addWidget(self._st_date)
        h.addStretch()
        h.addWidget(self._st_err)
        return bar

    # ── 파일 열기 ─────────────────────────────────────────────────────────────
    def _open_file(self, path=None):
        if not path:
            path, _ = QFileDialog.getOpenFileName(
                self, '파일 열기', '',
                'LOG/TXT 파일 (*.log *.txt *.cfg *.conf *.ini *.csv *.out *.syslog);;'
                '모든 파일 (*)',
            )
        if path:
            self._load_file(path)

    def _open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, '폴더 선택', '')
        if not folder:
            return
        self._open_folder_path(folder)

    def _open_folder_path(self, folder: str):
        """경로를 직접 지정해 폴더 파일 목록 로드 (외부에서 호출 가능)"""
        if not os.path.isdir(folder):
            return
        self._folder = folder
        self._dir_lbl.setText(folder)
        self._populate_filelist(folder)
        # 파일 목록 패널 자동 열기
        if not self._list_btn.isChecked():
            self._list_btn.setChecked(True)

    def _populate_filelist(self, folder):
        self._file_list.clear()
        try:
            entries = []
            for f in os.listdir(folder):
                if any(f.lower().endswith(e) for e in self._EXT):
                    fp = os.path.join(folder, f)
                    try:
                        sz = os.path.getsize(fp)
                        mt = os.path.getmtime(fp)
                        entries.append((f, fp, sz, mt))
                    except OSError:
                        pass
            entries.sort(key=lambda x: x[3], reverse=True)  # 최신순

            for fname, fpath, sz, mt in entries:
                sz_str = self._fmt_size(sz)
                dt_str = datetime.fromtimestamp(mt).strftime('%m/%d %H:%M')
                item = QListWidgetItem(f'{fname}\n{sz_str}  {dt_str}')
                item.setData(Qt.UserRole, fpath)
                # 확장자별 색상
                ext = os.path.splitext(fname)[1].lower()
                if ext == '.log':
                    item.setForeground(QBrush(QColor('#dc2626')))
                elif ext in ('.cfg', '.conf', '.ini'):
                    item.setForeground(QBrush(QColor('#7c3aed')))
                self._file_list.addItem(item)

            self._fcount_lbl.setText(f'{len(entries)} 개 파일')
        except Exception as e:
            self._fcount_lbl.setText(f'오류: {e}')

    def _filter_filelist(self, kw):
        kw = kw.lower()
        for i in range(self._file_list.count()):
            item = self._file_list.item(i)
            item.setHidden(kw and kw not in item.text().lower())

    def _on_flist_dblclick(self, item):
        path = item.data(Qt.UserRole)
        if path:
            self._load_file(path)

    def _on_flist_click(self, item):
        # 단일 클릭 시 미리 보기 (파일 크기 작을 때만)
        path = item.data(Qt.UserRole)
        if path:
            try:
                sz = os.path.getsize(path)
                if sz <= 500 * 1024:  # 500 KB 이하면 즉시 로드
                    self._load_file(path)
            except OSError:
                pass

    # ── 파일 로드 ─────────────────────────────────────────────────────────────
    def _load_file(self, path: str):
        try:
            sz = os.path.getsize(path)
        except OSError as e:
            QMessageBox.warning(self, '오류', f'파일을 열 수 없습니다:\n{e}')
            return

        if sz > self._MAX_SIZE:
            QMessageBox.warning(
                self, '파일 크기 초과',
                f'파일이 너무 큽니다 ({self._fmt_size(sz)}).\n'
                f'최대 {self._fmt_size(self._MAX_SIZE)}까지만 지원합니다.',
            )
            return

        if sz > self._MAX_WARN:
            reply = QMessageBox.question(
                self, '대용량 파일',
                f'파일 크기가 {self._fmt_size(sz)}입니다.\n'
                f'로드하면 시간이 걸릴 수 있습니다. 계속할까요?',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes,
            )
            if reply != QMessageBox.Yes:
                return

        try:
            with open(path, 'rb') as f:
                raw = f.read()
        except OSError as e:
            QMessageBox.warning(self, '읽기 오류', str(e))
            return

        # 인코딩 결정
        enc_choice = self._enc_cb.currentText()
        enc_map = {
            '자동 감지': _detect_enc(raw),
            'UTF-8': 'utf-8',
            'CP949': 'cp949',
            'EUC-KR': 'euc-kr',
            'Latin-1': 'latin-1',
        }
        self._enc = enc_map.get(enc_choice, _detect_enc(raw))

        try:
            text = raw.decode(self._enc, errors='replace')
        except Exception:
            text = raw.decode('latin-1', errors='replace')
            self._enc = 'latin-1'

        self._file = path

        # 구문 강조 — 5 MB 초과 시 자동 비활성화
        hl_on = self._hl_btn.isChecked() and sz <= 5 * 1024 * 1024
        self._hl.setDocument(None)
        self._ed.setPlainText(text)
        if hl_on:
            self._hl.setDocument(self._ed.document())

        self._add_recent(path)
        self._do_search()

        # 상태바 갱신
        lines = text.count('\n') + 1
        mt = datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y-%m-%d %H:%M')
        fname = os.path.basename(path)
        self._st_file.setText(fname)
        self._st_file.setToolTip(path)
        self._st_lines.setText(f'{lines:,} 줄')
        self._st_size.setText(self._fmt_size(sz))
        self._st_enc.setText(self._enc.upper().replace('-SIG', ''))
        self._st_date.setText(mt)

        # ERROR/WARNING 카운트
        n_err  = len(re.findall(r'\b(?:ERROR|CRITICAL|FATAL)\b', text, re.I))
        n_warn = len(re.findall(r'\bWARN(?:ING)?\b', text, re.I))
        parts = []
        if n_err:
            parts.append(f'ERR {n_err}')
        if n_warn:
            parts.append(f'WARN {n_warn}')
        self._st_err.setText('  '.join(parts))

        self._ed.moveCursor(QTextCursor.Start)

    def _add_recent(self, path):
        if path in self._recent:
            self._recent.remove(path)
        self._recent.insert(0, path)
        self._recent = self._recent[:10]
        # 콤보 갱신
        self._recent_cb.blockSignals(True)
        self._recent_cb.clear()
        self._recent_cb.addItem('⏱ 최근 파일...')
        for p in self._recent:
            self._recent_cb.addItem(os.path.basename(p), p)
        self._recent_cb.setCurrentIndex(0)
        self._recent_cb.blockSignals(False)

    def _open_recent(self, idx):
        if idx <= 0:
            return
        path = self._recent_cb.itemData(idx)
        if path and os.path.exists(path):
            self._load_file(path)
        self._recent_cb.setCurrentIndex(0)

    def _reload_enc(self, enc_name):
        if self._file:
            # 인코딩 변경 후 다시 로드
            self._load_file(self._file)

    # ── 검색 ─────────────────────────────────────────────────────────────────
    def _do_search(self):
        text = self._search_in.text()
        doc  = self._ed.document()

        # 이전 하이라이트 제거
        self._ed.setExtraSelections([])
        self._matches   = []
        self._match_idx = -1

        if not text:
            self._match_lbl.setText('—')
            return

        # 검색 옵션
        use_regex = self._regex_cb.isChecked()
        use_case  = self._case_cb.isChecked()
        use_word  = self._word_cb.isChecked()

        cursors = []
        if use_regex:
            rx = QRegExp(text)
            if not use_case:
                rx.setCaseSensitivity(Qt.CaseInsensitive)
            c = doc.find(rx, 0)
            while not c.isNull():
                cursors.append(c)
                c = doc.find(rx, c)
        else:
            opts = QTextDocument.FindFlags()
            if use_case:
                opts |= QTextDocument.FindCaseSensitively
            if use_word:
                opts |= QTextDocument.FindWholeWords
            c = doc.find(text, 0, opts)
            while not c.isNull():
                cursors.append(c)
                c = doc.find(text, c, opts)

        self._matches = cursors

        if not cursors:
            self._match_lbl.setText('없음')
            self._search_in.setStyleSheet(
                'QLineEdit{background:#fff1f2;border:1px solid #fca5a5;'
                'border-radius:6px;padding:2px 8px;color:#dc2626}'
            )
            return

        self._search_in.setStyleSheet(
            'QLineEdit{background:#f0fdf4;border:1px solid #86efac;'
            'border-radius:6px;padding:2px 8px;color:#1e293b}'
        )

        # 모든 결과 하이라이트
        all_fmt = QTextCharFormat()
        all_fmt.setBackground(QBrush(QColor('#78350f')))
        all_fmt.setForeground(QBrush(QColor('#fde68a')))
        sels = []
        for c in cursors:
            es = QTextEdit.ExtraSelection()
            es.cursor = c
            es.format = all_fmt
            sels.append(es)
        self._ed.setExtraSelections(sels)

        # 첫 번째로 이동
        self._match_idx = 0
        self._jump_to_match(0)

    def _jump_to_match(self, idx):
        if not self._matches:
            return
        idx = idx % len(self._matches)
        self._match_idx = idx

        # 현재 매치 강조 갱신
        cur_fmt = QTextCharFormat()
        cur_fmt.setBackground(QBrush(QColor('#b45309')))
        cur_fmt.setForeground(QBrush(QColor('#ffffff')))
        all_fmt = QTextCharFormat()
        all_fmt.setBackground(QBrush(QColor('#78350f')))
        all_fmt.setForeground(QBrush(QColor('#fde68a')))

        sels = []
        for i, c in enumerate(self._matches):
            es = QTextEdit.ExtraSelection()
            es.cursor = c
            es.format = cur_fmt if i == idx else all_fmt
            sels.append(es)
        self._ed.setExtraSelections(sels)

        # 해당 줄로 스크롤
        self._ed.setTextCursor(self._matches[idx])
        self._ed.ensureCursorVisible()
        self._match_lbl.setText(f'{idx + 1} / {len(self._matches)}건')

    def _find_next(self):
        if not self._matches:
            self._focus_search()
            return
        self._jump_to_match(self._match_idx + 1)

    def _find_prev(self):
        if not self._matches:
            self._focus_search()
            return
        self._jump_to_match(self._match_idx - 1)

    def _focus_search(self):
        self._search_in.setFocus()
        self._search_in.selectAll()

    # ── 로그 레벨 필터 ────────────────────────────────────────────────────────
    def _apply_filter(self, level):
        if not self._file or level == '전체 표시':
            if self._file:
                self._load_file(self._file)
            return

        _levels = {
            'ERROR+':   r'\b(?:ERROR|CRITICAL|FATAL|FAIL(?:ED)?)\b',
            'WARNING+': r'\b(?:WARN(?:ING)?|ERROR|CRITICAL|FATAL|FAIL(?:ED)?)\b',
            'INFO+':    r'\b(?:INFO|NOTICE|WARN(?:ING)?|ERROR|CRITICAL|FATAL)\b',
            'DEBUG':    r'\bDEBUG\b',
        }
        pat = _levels.get(level)
        if not pat:
            return

        try:
            with open(self._file, 'rb') as f:
                raw = f.read()
            text = raw.decode(self._enc, errors='replace')
        except Exception:
            return

        lines = [l for l in text.splitlines() if re.search(pat, l, re.I)]
        filtered = '\n'.join(lines)
        self._hl.setDocument(None)
        self._ed.setPlainText(filtered)
        self._hl.setDocument(self._ed.document())
        self._st_lines.setText(f'{len(lines):,} 줄  (필터)')

    # ── 기타 기능 ─────────────────────────────────────────────────────────────
    def _toggle_wrap(self, checked):
        self._ed.setLineWrapMode(
            QPlainTextEdit.WidgetWidth if checked else QPlainTextEdit.NoWrap
        )

    def _toggle_hl(self, checked):
        if checked:
            self._hl.setDocument(self._ed.document())
        else:
            self._hl.setDocument(None)

    def _toggle_file_list(self, checked):
        self._file_panel.setVisible(checked)

    def _set_font(self, sz):
        self._font_size = max(7, min(24, sz))
        self._ed.set_font_size(self._font_size)
        self._fz_lbl.setText(str(self._font_size))

    def _copy_text(self):
        sel = self._ed.textCursor().selectedText()
        text = sel if sel else self._ed.toPlainText()
        from PyQt5.QtWidgets import QApplication
        QApplication.clipboard().setText(text.replace('\u2029', '\n'))

    def _save_as(self):
        if not self._ed.toPlainText():
            QMessageBox.information(self, '알림', '저장할 내용이 없습니다.')
            return
        default = self._file if self._file else ''
        path, _ = QFileDialog.getSaveFileName(
            self, '다른 이름으로 저장', default,
            'TXT 파일 (*.txt);;LOG 파일 (*.log);;모든 파일 (*)',
        )
        if not path:
            return
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self._ed.toPlainText())
            QMessageBox.information(self, '완료', f'저장 완료:\n{path}')
        except Exception as e:
            QMessageBox.warning(self, '오류', f'저장 실패:\n{e}')

    def _goto_line(self):
        total = self._ed.blockCount()
        n, ok = QInputDialog.getInt(
            self, '줄 이동', f'이동할 줄 번호 (1 ~ {total}):',
            value=self._ed.textCursor().blockNumber() + 1,
            min=1, max=total,
        )
        if ok:
            block = self._ed.document().findBlockByNumber(n - 1)
            cur = QTextCursor(block)
            self._ed.setTextCursor(cur)
            self._ed.centerCursor()

    def _on_cursor(self):
        cur  = self._ed.textCursor()
        line = cur.blockNumber() + 1
        col  = cur.columnNumber() + 1
        self._st_pos.setText(f'L{line}  C{col}')
        self._ed._ln.update()

    # ── 유틸 ─────────────────────────────────────────────────────────────────
    @staticmethod
    def _fmt_size(b: int) -> str:
        if b < 1024:
            return f'{b} B'
        if b < 1024 ** 2:
            return f'{b / 1024:.1f} KB'
        return f'{b / 1024 ** 2:.1f} MB'
