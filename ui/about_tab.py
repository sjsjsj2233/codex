"""
정보 탭
"""
import json
import os
import webbrowser
from core.i18n import tr
from core.updater import UpdateChecker, AutoUpdater, CURRENT_VERSION
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QProgressBar, QApplication, QDialog, QMessageBox,
    QCheckBox,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor, QPainter, QBrush, QLinearGradient, QPen
import subprocess

def _config_path() -> str:
    d = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'NetworkAutomation')
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, 'config.json')


def _load_auto_update() -> bool:
    """config.json 에서 auto_update 설정 읽기 (기본값 True)"""
    try:
        _cp = _config_path()
        if os.path.exists(_cp):
            with open(_cp, encoding='utf-8') as f:
                return json.load(f).get('auto_update', True)
    except Exception:
        pass
    return True


def _save_auto_update(enabled: bool):
    """config.json 에 auto_update 설정 저장"""
    cfg = {}
    try:
        _cp = _config_path()
        if os.path.exists(_cp):
            with open(_cp, encoding='utf-8') as f:
                cfg = json.load(f)
    except Exception:
        pass
    cfg['auto_update'] = enabled
    try:
        with open(_config_path(), 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
    except Exception:
        pass


class AboutTab(QWidget):
    def __init__(self, parent=None, license_manager=None):
        super().__init__(parent)
        self._lm = license_manager
        self._update_info = None   # 서버에서 받은 업데이트 정보 캐시
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet('background:#f1f5f9')

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        hdr = _MiniHeader()
        hdr.setFixedHeight(120)
        root.addWidget(hdr)

        body = QWidget()
        body.setStyleSheet('background:transparent')
        bv = QVBoxLayout(body)
        bv.setContentsMargins(40, 28, 40, 28)
        bv.setSpacing(14)

        # ── 버전 정보 카드 ────────────────────────────────────────
        ver_card = _card()
        vc = QVBoxLayout(ver_card)
        vc.setContentsMargins(20, 16, 20, 16)
        vc.setSpacing(6)
        _row(vc, tr('버전'),    f'v {CURRENT_VERSION}', bold_val=True, val_color='#2563eb')
        _row(vc, tr('빌드'),    '2026.03.17')
        _row(vc, tr('플랫폼'),  'Windows (PyQt5)')
        bv.addWidget(ver_card)

        # ── 업데이트 카드 ─────────────────────────────────────────
        upd_card = _card()
        uc = QVBoxLayout(upd_card)
        uc.setContentsMargins(20, 14, 20, 14)
        uc.setSpacing(8)

        upd_title_row = QHBoxLayout()
        upd_title_lbl = QLabel(tr('업데이트'))
        upd_title_lbl.setFont(QFont('맑은 고딕', 9, QFont.Bold))
        upd_title_lbl.setStyleSheet('color:#334155;background:transparent')
        upd_title_row.addWidget(upd_title_lbl)
        upd_title_row.addStretch()

        self._upd_check_btn = _btn(tr('🔄 업데이트 확인'), '#6366f1')
        self._upd_check_btn.setFixedHeight(28)
        self._upd_check_btn.clicked.connect(self._check_update)
        upd_title_row.addWidget(self._upd_check_btn)
        uc.addLayout(upd_title_row)

        self._upd_status_lbl = QLabel(tr('확인하려면 버튼을 누르세요.'))
        self._upd_status_lbl.setFont(QFont('맑은 고딕', 9))
        self._upd_status_lbl.setStyleSheet('color:#64748b;background:transparent')
        uc.addWidget(self._upd_status_lbl)

        # 자동 업데이트 체크 on/off
        auto_row = QHBoxLayout()
        self._auto_upd_chk = QCheckBox(tr('시작 시 자동으로 업데이트 확인'))
        self._auto_upd_chk.setFont(QFont('맑은 고딕', 9))
        self._auto_upd_chk.setStyleSheet('color:#475569;background:transparent')
        self._auto_upd_chk.setChecked(_load_auto_update())
        self._auto_upd_chk.toggled.connect(self._on_auto_update_toggled)
        auto_row.addWidget(self._auto_upd_chk)
        auto_row.addStretch()
        uc.addLayout(auto_row)

        # 업데이트 있을 때만 표시되는 설치 버튼
        self._upd_install_btn = _btn(tr('⬇ 지금 업데이트'), '#d97706')
        self._upd_install_btn.setFixedHeight(28)
        self._upd_install_btn.clicked.connect(self._start_auto_update)
        self._upd_install_btn.hide()
        uc.addWidget(self._upd_install_btn, 0, Qt.AlignLeft)

        bv.addWidget(upd_card)

        # ── 라이센스 카드 ─────────────────────────────────────────
        lic_card = _card()
        lc = QVBoxLayout(lic_card)
        lc.setContentsMargins(20, 16, 20, 16)
        lc.setSpacing(6)

        if self._lm:
            info = self._lm.get_info()
            if info:
                # 정식 라이센스 활성화
                _row(lc, tr('상태'),   tr('활성화됨'),
                     bold_val=True, val_color='#16a34a')
                _row(lc, tr('만료일'), info.get('expires_at', '-'))
                mid = self._lm.get_machine_id()
                _row(lc, tr('기기 ID'), f'{mid[:10]}···')
            else:
                # 미활성화
                _row(lc, tr('상태'), tr('미활성화'),
                     bold_val=True, val_color='#dc2626')
                mid = self._lm.get_machine_id()
                _row(lc, tr('기기 ID'), mid)
                _row(lc, tr('안내'),
                     tr('라이센스 발급은 이메일로 문의해주세요.'),
                     val_color='#64748b')
                _email_row(lc, tr('문의'), 'doaslove962@gmail.com')
        else:
            _row(lc, tr('상태'), '-', val_color='#64748b')

        bv.addWidget(lic_card)

        # ── 버튼 행 ───────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        if self._lm and not self._lm.is_licensed():
            b_lic = _btn(tr('🔑 라이센스 활성화'), '#2563eb')
            b_lic.clicked.connect(self._open_license_dialog)
            btn_row.addWidget(b_lic)

        b_terms = _btn(tr('📋 이용약관'), '#475569')
        b_terms.clicked.connect(self._show_terms)
        btn_row.addWidget(b_terms)

        b_web = _btn(tr('🌐 웹사이트'), '#10b981')
        b_web.clicked.connect(lambda: webbrowser.open('https://auto-network.co.kr'))
        btn_row.addWidget(b_web)
        btn_row.addStretch()
        bv.addLayout(btn_row)

        bv.addStretch()
        root.addWidget(body, 1)

    def _show_terms(self):
        from ui.disclaimer_dialog import DisclaimerDialog
        DisclaimerDialog(self, view_only=True).exec_()

    def _open_license_dialog(self):
        from ui.license_dialog import LicenseDialog
        dlg = LicenseDialog(self._lm, self)
        if dlg.exec_():
            # 라이센스 성공 → 카드 갱신
            self._refresh()

    def showEvent(self, event):
        """탭이 표시될 때마다 라이센스 상태 갱신"""
        super().showEvent(event)
        self._refresh()

    def _refresh(self):
        """라이센스 상태 갱신 — 레이아웃 전체 재구성"""
        # 기존 레이아웃과 위젯 완전히 제거
        old_layout = self.layout()
        if old_layout:
            while old_layout.count():
                item = old_layout.takeAt(0)
                w = item.widget()
                if w:
                    w.hide()
                    w.deleteLater()
            QWidget().setLayout(old_layout)
        self._build_ui()

    def _on_auto_update_toggled(self, checked: bool):
        _save_auto_update(checked)
        if checked:
            self._upd_status_lbl.setStyleSheet('color:#64748b;background:transparent')
            self._upd_status_lbl.setText(tr('확인하려면 버튼을 누르세요.'))
        else:
            self._upd_status_lbl.setStyleSheet('color:#94a3b8;background:transparent')
            self._upd_status_lbl.setText(tr('자동 업데이트 확인이 비활성화되어 있습니다.'))
        self._upd_install_btn.hide()

    # ── 업데이트 확인 ────────────────────────────────────────────
    def _check_update(self):
        self._upd_check_btn.setEnabled(False)
        self._upd_install_btn.hide()
        self._upd_status_lbl.setStyleSheet('color:#64748b;background:transparent')
        self._upd_status_lbl.setText(tr('확인 중...'))

        self._check_update_found = False
        self._checker = UpdateChecker()
        self._checker.update_available.connect(self._on_update_found)
        self._checker.check_failed.connect(self._on_check_failed)
        self._checker.finished.connect(self._on_check_finished)
        self._checker.start()

    def _on_check_finished(self):
        self._upd_check_btn.setEnabled(True)
        if not self._check_update_found and not self._upd_status_lbl.text().startswith(tr('서버')):
            self._upd_status_lbl.setStyleSheet('color:#16a34a;background:transparent;font-weight:bold')
            self._upd_status_lbl.setText(tr('✔  최신 버전입니다.'))

    def _on_update_found(self, info: dict):
        self._check_update_found = True
        self._update_info = info
        ver  = info.get('version', '?')
        date = info.get('release_date', '')
        self._upd_status_lbl.setStyleSheet('color:#d97706;background:transparent;font-weight:bold')
        self._upd_status_lbl.setText(
            f'v{ver}  {tr("업데이트 가능")}  ({date})'
        )
        self._upd_install_btn.show()

    def _on_check_failed(self, err: str):
        self._upd_status_lbl.setStyleSheet('color:#dc2626;background:transparent')
        self._upd_status_lbl.setText(tr('서버에 연결할 수 없습니다.'))

    def _start_auto_update(self):
        if not self._update_info:
            return
        url = self._update_info.get('download_url', '')
        if not url:
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(tr('업데이트 중...'))
        dlg.setFixedSize(400, 130)
        dlg.setWindowFlags(dlg.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        from PyQt5.QtWidgets import QVBoxLayout as VL
        v = VL(dlg)
        v.setContentsMargins(20, 16, 20, 16)
        v.setSpacing(10)

        status_lbl = QLabel(tr('다운로드 준비 중...'))
        status_lbl.setFont(QFont('맑은 고딕', 9))
        v.addWidget(status_lbl)

        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(0)
        bar.setFixedHeight(18)
        v.addWidget(bar)

        cancel_btn = QPushButton(tr('취소'))
        cancel_btn.setFixedHeight(28)
        cancel_btn.setFont(QFont('맑은 고딕', 9))
        v.addWidget(cancel_btn, 0, Qt.AlignRight)

        self._auto_updater = AutoUpdater(url)

        def _on_progress(pct, msg):
            bar.setValue(pct)
            status_lbl.setText(msg)

        def _on_finished(success, result):
            dlg.accept()
            if success:
                QMessageBox.information(
                    self, tr('업데이트'),
                    tr('다운로드 완료. 프로그램을 재시작하여 업데이트를 적용합니다.')
                )
                try:
                    subprocess.Popen(['cmd', '/c', result],
                                     creationflags=subprocess.CREATE_NEW_CONSOLE)
                except Exception:
                    pass
                QApplication.quit()
            else:
                QMessageBox.warning(self, tr('업데이트 실패'),
                                    f'{tr("다운로드 오류")}:\n{result}')

        cancel_btn.clicked.connect(lambda: (
            self._auto_updater.terminate(), dlg.reject()
        ))
        self._auto_updater.progress.connect(_on_progress)
        self._auto_updater.finished.connect(_on_finished)
        self._auto_updater.start()
        dlg.exec_()


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────
def _card() -> QFrame:
    f = QFrame()
    f.setStyleSheet(
        'QFrame{background:#ffffff;border-radius:10px;border:1px solid #e2e8f0}'
    )
    return f


def _email_row(layout, label: str, email: str):
    """클릭 시 Gmail 작성 창을 여는 이메일 행"""
    row = QHBoxLayout()
    row.setSpacing(0)

    lbl_k = QLabel(label)
    lbl_k.setFont(QFont('맑은 고딕', 9))
    lbl_k.setStyleSheet('color:#94a3b8;background:transparent')
    lbl_k.setFixedWidth(72)

    lbl_v = QLabel(f'<a href="mailto:{email}" style="color:#2563eb;text-decoration:none">{email}</a>')
    lbl_v.setFont(QFont('맑은 고딕', 9))
    lbl_v.setOpenExternalLinks(True)
    lbl_v.setCursor(Qt.PointingHandCursor)
    lbl_v.setStyleSheet('background:transparent')
    lbl_v.setToolTip('클릭하여 이메일 작성')

    row.addWidget(lbl_k)
    row.addWidget(lbl_v)
    row.addStretch()
    layout.addLayout(row)


def _row(layout, label: str, value: str,
         bold_val=False, val_color='#334155'):
    row = QHBoxLayout()
    row.setSpacing(0)

    lbl_k = QLabel(label)
    lbl_k.setFont(QFont('맑은 고딕', 9))
    lbl_k.setStyleSheet('color:#94a3b8;background:transparent')
    lbl_k.setFixedWidth(72)

    lbl_v = QLabel(value)
    lbl_v.setFont(QFont('맑은 고딕', 9, QFont.Bold if bold_val else QFont.Normal))
    lbl_v.setStyleSheet(f'color:{val_color};background:transparent')

    row.addWidget(lbl_k)
    row.addWidget(lbl_v)
    row.addStretch()
    layout.addLayout(row)


def _btn(text: str, color: str) -> QPushButton:
    b = QPushButton(text)
    b.setFont(QFont('맑은 고딕', 9, QFont.Bold))
    b.setFixedHeight(32)
    b.setCursor(Qt.PointingHandCursor)
    b.setStyleSheet(
        f'QPushButton{{background:{color};color:#fff;border:none;'
        f'border-radius:7px;padding:0 18px}}'
        f'QPushButton:hover{{opacity:0.9}}'
    )
    return b


# ── 미니 헤더 ──────────────────────────────────────────────────────────────────
class _MiniHeader(QWidget):
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0.0, QColor('#0f172a'))
        grad.setColorAt(1.0, QColor('#1e40af'))
        p.fillRect(self.rect(), QBrush(grad))

        p.setOpacity(0.06)
        p.setBrush(QBrush(QColor('#ffffff')))
        p.setPen(Qt.NoPen)
        p.drawEllipse(self.width() - 100, -30, 180, 180)
        p.setOpacity(1.0)

        p.setPen(QPen(QColor('#f8fafc')))
        p.setFont(QFont('맑은 고딕', 17, QFont.Bold))
        p.drawText(32, 52, 'Network Automation  v8.0')

        p.setPen(QPen(QColor('#94a3b8')))
        p.setFont(QFont('맑은 고딕', 9))
        p.drawText(34, 74, tr('버전 정보 · 라이센스'))

        p.end()
