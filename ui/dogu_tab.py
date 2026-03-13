import sys
import os
import subprocess
import logging

import re


# PyQt5 라이브러리
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, 
    QFileDialog, QListWidget, QTextEdit, QGroupBox, QHBoxLayout, 
    QSplitter, QRadioButton, QFormLayout, QComboBox, QCheckBox,QSpinBox, QMessageBox
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt

# 파일 뷰어 탭 (새로운 기능)
# FileViewerTab 클래스 - 파일 뷰어 기능 추가
class FileViewerTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.current_folder = ""
        self.current_file = ""
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # 경로 선택 영역
        path_layout = QHBoxLayout()
        path_label = QLabel("폴더:")
        self.folder_path = QLineEdit()
        browse_btn = QPushButton("찾기")
        browse_btn.clicked.connect(self.browse_folder)
        refresh_btn = QPushButton("새로고침")
        refresh_btn.clicked.connect(self.refresh_files)
        
        path_layout.addWidget(path_label)
        path_layout.addWidget(self.folder_path, 1)
        path_layout.addWidget(browse_btn)
        path_layout.addWidget(refresh_btn)
        
        # 분할 영역 (파일 목록 + 내용)
        splitter = QSplitter(Qt.Horizontal)
        
        # 파일 목록
        file_list_group = QGroupBox("파일 목록")
        file_list_layout = QVBoxLayout()
        self.file_list = QListWidget()
        self.file_list.itemDoubleClicked.connect(self.on_file_selected)
        file_list_layout.addWidget(self.file_list)
        file_list_group.setLayout(file_list_layout)
        
        # 파일 내용
        file_content_group = QGroupBox("파일 내용")
        file_content_layout = QVBoxLayout()
        
        # 파일 조작 버튼
        file_buttons = QHBoxLayout()
        self.file_name_label = QLabel("선택된 파일: 없음")
        open_external_btn = QPushButton("외부에서 열기")
        open_external_btn.clicked.connect(self.open_file_external)
        save_as_btn = QPushButton("다른 이름으로 저장")
        save_as_btn.clicked.connect(self.save_file_as)
        
        file_buttons.addWidget(self.file_name_label, 1)
        file_buttons.addWidget(open_external_btn)
        file_buttons.addWidget(save_as_btn)
        
        # 파일 내용 표시 영역
        self.file_content = QTextEdit()
        self.file_content.setReadOnly(True)
        
        file_content_layout.addLayout(file_buttons)
        file_content_layout.addWidget(self.file_content)
        file_content_group.setLayout(file_content_layout)
        
        # 스플리터에 추가
        splitter.addWidget(file_list_group)
        splitter.addWidget(file_content_group)
        splitter.setSizes([200, 600])  # 초기 비율 설정
        
        # 레이아웃에 추가
        layout.addLayout(path_layout)
        layout.addWidget(splitter, 1)
        
        self.setLayout(layout)

    def browse_folder(self):
        """폴더 선택 다이얼로그"""
        folder = QFileDialog.getExistingDirectory(self, "폴더 선택", "")
        if folder:
            self.folder_path.setText(folder)
            self.current_folder = folder
            self.refresh_files()

    def refresh_files(self):
        """폴더 내 파일 목록 새로고침"""
        self.file_list.clear()
        folder = self.folder_path.text()
        
        if not folder or not os.path.exists(folder):
            return
            
        try:
            # 파일 목록 가져오기
            files = os.listdir(folder)
            
            # 텍스트 파일 필터링 (옵션)
            text_files = [f for f in files if f.endswith(('.txt', '.log', '.cfg', '.conf', '.ini'))]
            
            # 목록에 추가
            for file in sorted(text_files):
                self.file_list.addItem(file)
                
            # 상태 표시
            if self.parent:
                self.parent.statusBar.showMessage(f"{len(text_files)}개 파일을 찾았습니다.", 3000)
        except Exception as e:
            if self.parent:
                self.parent.statusBar.showMessage(f"오류: {str(e)}", 3000)

    def on_file_selected(self, item):
        """파일 선택 시 내용 표시"""
        filename = item.text()
        file_path = os.path.join(self.folder_path.text(), filename)
        self.current_file = file_path
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                self.file_content.setPlainText(content)
                self.file_name_label.setText(f"선택된 파일: {filename}")
        except Exception as e:
            self.file_content.setPlainText(f"파일을 열 수 없습니다: {str(e)}")
            if self.parent:
                self.parent.statusBar.showMessage(f"파일 열기 오류: {str(e)}", 3000)

    def open_file_external(self):
        """선택된 파일을 외부 프로그램에서 열기"""
        if not self.current_file:
            return
            
        try:
            if sys.platform == "win32":
                os.startfile(self.current_file)
            elif sys.platform == "darwin":  # macOS
                subprocess.call(["open", self.current_file])
            else:  # Linux
                subprocess.call(["xdg-open", self.current_file])
        except Exception as e:
            if self.parent:
                self.parent.statusBar.showMessage(f"외부 열기 오류: {str(e)}", 3000)

    def save_file_as(self):
        """현재 표시된 내용을 다른 이름으로 저장"""
        if not self.current_file:
            return
            
        content = self.file_content.toPlainText()
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "다른 이름으로 저장", "", "텍스트 파일 (*.txt);;모든 파일 (*)"
        )
        
        if not file_path:
            return
            
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            if self.parent:
                self.parent.statusBar.showMessage(f"파일이 저장되었습니다: {file_path}", 3000)
        except Exception as e:
            if self.parent:
                self.parent.statusBar.showMessage(f"저장 오류: {str(e)}", 3000)


    
    # 메뉴바 생성
        self.create_menu_bar()
    
    # 상태바 생성
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("준비 완료")
    
    # 중앙 위젯 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
    
    # 탭 위젯 생성
        self.tabs = QTabWidget()
    
    # 폰트 크기 조정
        tab_font = self.tabs.font()
        tab_font.setPointSize(12)
        self.tabs.setFont(tab_font)
    
    # 탭 생성
        self.network_tab = NetworkTab(self)
        self.ping_test_tab = PingTestTab()
        self.about_tab = AboutTab(self)
        self.file_viewer_tab = FileViewerTab(self)  # 새로운 파일 뷰어 탭 추가
        
        # 아이콘 설정 (아이콘 파일이 있다고 가정)
        self.tabs.addTab(self.network_tab, QIcon("icons/network.png"), "네트워크 자동화")
        self.tabs.addTab(self.ping_test_tab, QIcon("icons/ping.png"), "Ping 테스트")
        self.tabs.addTab(self.file_viewer_tab, QIcon("icons/file.png"), "파일 뷰어")  # 새 탭 추가
        
        main_layout.addWidget(self.tabs)
        
        # 스타일 적용
        self.apply_styles()


import re

import re

import re
import os
import json
import tempfile
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, QListWidget,
    QHBoxLayout, QGroupBox, QComboBox, QCheckBox, QMessageBox, QTabWidget,
    QRadioButton, QButtonGroup, QSlider, QSpinBox, QColorDialog, QSplitter
)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QDesktopServices

class DiagramGeneratorTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.file_paths = []
        self.device_connections = {}
        self.canvas = None
        self.custom_colors = {
            'router': '#ff9e64',     # 라우터: 주황색
            'switch': '#7dcfff',     # 스위치: 하늘색
            'firewall': '#f7768e',   # 방화벽: 빨간색
            'server': '#73daca',     # 서버: 녹색
            'unknown': '#bb9af7'     # 알 수 없음: 보라색
        }
        self.last_diagram_path = None
        self.theme = "dark"  # 기본 테마: 다크
        self.init_ui()
        
    def init_ui(self):
        # 메인 레이아웃
        main_layout = QVBoxLayout()
        
        # 상단 탭 설정 (파일 관리, 스타일 설정, 고급 옵션)
        tabs = QTabWidget()
        
        # ===== 파일 관리 탭 =====
        file_tab = QWidget()
        file_layout = QVBoxLayout(file_tab)
        
        # 파일 선택 그룹박스
        file_group = QGroupBox("CDP/LLDP 출력 파일")
        file_group_layout = QVBoxLayout()
        
        # 파일 목록
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QListWidget.ExtendedSelection)
        
        # 파일 관리 버튼
        file_buttons = QHBoxLayout()
        add_file_btn = QPushButton("파일 추가")
        add_file_btn.clicked.connect(self.add_files)
        add_folder_btn = QPushButton("폴더 추가")
        add_folder_btn.clicked.connect(self.add_folder)
        remove_file_btn = QPushButton("파일 제거")
        remove_file_btn.clicked.connect(self.remove_files)
        clear_files_btn = QPushButton("모두 지우기")
        clear_files_btn.clicked.connect(self.clear_files)
        
        file_buttons.addWidget(add_file_btn)
        file_buttons.addWidget(add_folder_btn)
        file_buttons.addWidget(remove_file_btn)
        file_buttons.addWidget(clear_files_btn)
        
        # 파일 분석 결과 요약
        self.file_summary = QLabel("파일 요약: 0개 파일, 0개 장비 감지됨")
        
        file_group_layout.addWidget(self.file_list)
        file_group_layout.addLayout(file_buttons)
        file_group_layout.addWidget(self.file_summary)
        file_group.setLayout(file_group_layout)
        
        # 프로토콜 선택 그룹
        protocol_group = QGroupBox("네트워크 프로토콜")
        protocol_layout = QHBoxLayout()
        
        self.use_cdp = QCheckBox("CDP 정보 사용")
        self.use_cdp.setChecked(True)
        self.use_lldp = QCheckBox("LLDP 정보 사용")
        self.use_lldp.setChecked(True)
        self.use_bgp = QCheckBox("BGP 피어 정보 사용")
        self.use_bgp.setChecked(False)
        self.use_ospf = QCheckBox("OSPF 이웃 정보 사용")
        self.use_ospf.setChecked(False)
        
        protocol_layout.addWidget(self.use_cdp)
        protocol_layout.addWidget(self.use_lldp)
        protocol_layout.addWidget(self.use_bgp)
        protocol_layout.addWidget(self.use_ospf)
        protocol_group.setLayout(protocol_layout)
        
        # 파일 탭에 추가
        file_layout.addWidget(file_group)
        file_layout.addWidget(protocol_group)
        
        # ===== 스타일 설정 탭 =====
        style_tab = QWidget()
        style_layout = QVBoxLayout(style_tab)
        
        # 테마 선택
        theme_group = QGroupBox("테마 설정")
        theme_layout = QVBoxLayout()
        
        theme_buttons_layout = QHBoxLayout()
        self.theme_group = QButtonGroup(self)
        self.dark_theme_radio = QRadioButton("다크 테마")
        self.light_theme_radio = QRadioButton("라이트 테마")
        self.custom_theme_radio = QRadioButton("커스텀 테마")
        self.theme_group.addButton(self.dark_theme_radio)
        self.theme_group.addButton(self.light_theme_radio)
        self.theme_group.addButton(self.custom_theme_radio)
        self.dark_theme_radio.setChecked(True)
        
        theme_buttons_layout.addWidget(self.dark_theme_radio)
        theme_buttons_layout.addWidget(self.light_theme_radio)
        theme_buttons_layout.addWidget(self.custom_theme_radio)
        
        # 배경색 선택
        bg_color_layout = QHBoxLayout()
        bg_color_layout.addWidget(QLabel("배경색:"))
        self.bg_color_btn = QPushButton()
        self.bg_color_btn.setStyleSheet("background-color: #1f2430; min-width: 60px;")
        self.bg_color_btn.clicked.connect(lambda: self.choose_color('background'))
        bg_color_layout.addWidget(self.bg_color_btn)
        bg_color_layout.addStretch()
        
        theme_layout.addLayout(theme_buttons_layout)
        theme_layout.addLayout(bg_color_layout)
        theme_group.setLayout(theme_layout)
        
        # 장비 색상 설정
        colors_group = QGroupBox("장비 유형별 색상")
        colors_layout = QVBoxLayout()
        
        # 라우터 색상
        router_color_layout = QHBoxLayout()
        router_color_layout.addWidget(QLabel("라우터:"))
        self.router_color_btn = QPushButton()
        self.router_color_btn.setStyleSheet(f"background-color: {self.custom_colors['router']}; min-width: 60px;")
        self.router_color_btn.clicked.connect(lambda: self.choose_color('router'))
        router_color_layout.addWidget(self.router_color_btn)
        router_color_layout.addStretch()
        
        # 스위치 색상
        switch_color_layout = QHBoxLayout()
        switch_color_layout.addWidget(QLabel("스위치:"))
        self.switch_color_btn = QPushButton()
        self.switch_color_btn.setStyleSheet(f"background-color: {self.custom_colors['switch']}; min-width: 60px;")
        self.switch_color_btn.clicked.connect(lambda: self.choose_color('switch'))
        switch_color_layout.addWidget(self.switch_color_btn)
        switch_color_layout.addStretch()
        
        # 방화벽 색상
        firewall_color_layout = QHBoxLayout()
        firewall_color_layout.addWidget(QLabel("방화벽:"))
        self.firewall_color_btn = QPushButton()
        self.firewall_color_btn.setStyleSheet(f"background-color: {self.custom_colors['firewall']}; min-width: 60px;")
        self.firewall_color_btn.clicked.connect(lambda: self.choose_color('firewall'))
        firewall_color_layout.addWidget(self.firewall_color_btn)
        firewall_color_layout.addStretch()
        
        # 서버 색상
        server_color_layout = QHBoxLayout()
        server_color_layout.addWidget(QLabel("서버:"))
        self.server_color_btn = QPushButton()
        self.server_color_btn.setStyleSheet(f"background-color: {self.custom_colors['server']}; min-width: 60px;")
        self.server_color_btn.clicked.connect(lambda: self.choose_color('server'))
        server_color_layout.addWidget(self.server_color_btn)
        server_color_layout.addStretch()
        
        colors_layout.addLayout(router_color_layout)
        colors_layout.addLayout(switch_color_layout)
        colors_layout.addLayout(firewall_color_layout)
        colors_layout.addLayout(server_color_layout)
        colors_group.setLayout(colors_layout)
        
        # 스타일 탭에 추가
        style_layout.addWidget(theme_group)
        style_layout.addWidget(colors_group)
        style_layout.addStretch()
        
        # ===== 고급 설정 탭 =====
        advanced_tab = QWidget()
        advanced_layout = QVBoxLayout(advanced_tab)
        
        # 레이아웃 설정
        layout_group = QGroupBox("레이아웃 설정")
        layout_settings = QVBoxLayout()
        
        # 레이아웃 알고리즘
        algo_layout = QHBoxLayout()
        algo_layout.addWidget(QLabel("레이아웃 알고리즘:"))
        self.layout_combo = QComboBox()
        self.layout_combo.addItems(["계층적", "원형", "힘 기반", "스프링", "쉘", "분광"])
        algo_layout.addWidget(self.layout_combo)
        
        # 노드 간격
        spacing_layout = QHBoxLayout()
        spacing_layout.addWidget(QLabel("노드 간격:"))
        self.spacing_slider = QSlider(Qt.Horizontal)
        self.spacing_slider.setMinimum(5)
        self.spacing_slider.setMaximum(50)
        self.spacing_slider.setValue(30)
        self.spacing_value = QLabel("3.0")
        self.spacing_slider.valueChanged.connect(self.update_spacing_value)
        spacing_layout.addWidget(self.spacing_slider)
        spacing_layout.addWidget(self.spacing_value)
        
        # 노드 크기
        node_size_layout = QHBoxLayout()
        node_size_layout.addWidget(QLabel("노드 크기:"))
        self.node_size_slider = QSlider(Qt.Horizontal)
        self.node_size_slider.setMinimum(30)
        self.node_size_slider.setMaximum(150)
        self.node_size_slider.setValue(80)
        self.node_size_value = QLabel("800")
        self.node_size_slider.valueChanged.connect(self.update_node_size_value)
        node_size_layout.addWidget(self.node_size_slider)
        node_size_layout.addWidget(self.node_size_value)
        
        layout_settings.addLayout(algo_layout)
        layout_settings.addLayout(spacing_layout)
        layout_settings.addLayout(node_size_layout)
        layout_group.setLayout(layout_settings)
        
        # 표시 옵션
        display_group = QGroupBox("표시 옵션")
        display_layout = QVBoxLayout()
        
        # 표시 옵션 체크박스
        display_options = QHBoxLayout()
        self.include_ip = QCheckBox("IP 주소 표시")
        self.include_ip.setChecked(True)
        self.include_interfaces = QCheckBox("인터페이스 표시")
        self.include_interfaces.setChecked(True)
        self.include_device_icon = QCheckBox("장비 아이콘 표시")
        self.include_device_icon.setChecked(True)
        self.show_legend = QCheckBox("범례 표시")
        self.show_legend.setChecked(True)
        
        display_options.addWidget(self.include_ip)
        display_options.addWidget(self.include_interfaces)
        display_options.addWidget(self.include_device_icon)
        display_options.addWidget(self.show_legend)
        
        # 글꼴 크기
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("글꼴 크기:"))
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setMinimum(6)
        self.font_size_spin.setMaximum(18)
        self.font_size_spin.setValue(10)
        font_layout.addWidget(self.font_size_spin)
        font_layout.addStretch()
        
        # 연결선 두께
        edge_layout = QHBoxLayout()
        edge_layout.addWidget(QLabel("연결선 두께:"))
        self.edge_width_spin = QSpinBox()
        self.edge_width_spin.setMinimum(1)
        self.edge_width_spin.setMaximum(10)
        self.edge_width_spin.setValue(2)
        self.edge_width_spin.setSingleStep(1)
        edge_layout.addWidget(self.edge_width_spin)
        edge_layout.addStretch()
        
        display_layout.addLayout(display_options)
        display_layout.addLayout(font_layout)
        display_layout.addLayout(edge_layout)
        display_group.setLayout(display_layout)
        
        # 내보내기 옵션
        export_group = QGroupBox("내보내기 설정")
        export_layout = QVBoxLayout()
        
        # DPI 설정
        dpi_layout = QHBoxLayout()
        dpi_layout.addWidget(QLabel("이미지 해상도(DPI):"))
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setMinimum(72)
        self.dpi_spin.setMaximum(1200)
        self.dpi_spin.setValue(600)
        self.dpi_spin.setSingleStep(100)
        dpi_layout.addWidget(self.dpi_spin)
        dpi_layout.addStretch()
        
        # 이미지 크기
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("이미지 크기:"))
        self.width_spin = QSpinBox()
        self.width_spin.setMinimum(5)
        self.width_spin.setMaximum(50)
        self.width_spin.setValue(10)
        self.height_spin = QSpinBox()
        self.height_spin.setMinimum(5)
        self.height_spin.setMaximum(50)
        self.height_spin.setValue(8)
        size_layout.addWidget(QLabel("너비:"))
        size_layout.addWidget(self.width_spin)
        size_layout.addWidget(QLabel("높이:"))
        size_layout.addWidget(self.height_spin)
        size_layout.addStretch()
        
        export_layout.addLayout(dpi_layout)
        export_layout.addLayout(size_layout)
        export_group.setLayout(export_layout)
        
        # 고급 설정 탭에 추가
        advanced_layout.addWidget(layout_group)
        advanced_layout.addWidget(display_group)
        advanced_layout.addWidget(export_group)
        advanced_layout.addStretch()
        
        # 탭에 추가
        tabs.addTab(file_tab, "파일 관리")
        tabs.addTab(style_tab, "스타일 설정")
        tabs.addTab(advanced_tab, "고급 설정")
        
        # 다이어그램 제어 버튼
        control_layout = QHBoxLayout()
        
        # 미리보기 버튼
        preview_btn = QPushButton("다이어그램 미리보기")
        preview_btn.setIcon(self.style().standardIcon(self.style().SP_FileDialogContentsView))
        preview_btn.clicked.connect(self.generate_diagram)
        preview_btn.setMinimumHeight(40)
        
        # 내보내기 버튼
        export_btn = QPushButton("다이어그램 내보내기")
        export_btn.setIcon(self.style().standardIcon(self.style().SP_DialogSaveButton))
        export_btn.clicked.connect(self.export_diagram)
        export_btn.setMinimumHeight(40)
        
        # 웹페이지로 보기 버튼
        web_view_btn = QPushButton("웹 브라우저로 보기")
        web_view_btn.setIcon(self.style().standardIcon(self.style().SP_ComputerIcon))
        web_view_btn.clicked.connect(self.open_in_browser)
        web_view_btn.setMinimumHeight(40)
        
        control_layout.addWidget(preview_btn)
        control_layout.addWidget(export_btn)
        control_layout.addWidget(web_view_btn)
        
        # 미리보기 영역
        preview_group = QGroupBox("다이어그램 미리보기")
        preview_layout = QVBoxLayout(preview_group)
        self.diagram_preview = QWidget()
        self.diagram_preview.setLayout(QVBoxLayout())
        preview_layout.addWidget(self.diagram_preview)
        
        # 메인 레이아웃에 추가
        main_layout.addWidget(tabs)
        main_layout.addLayout(control_layout)
        main_layout.addWidget(preview_group, 1)  # 1 = 늘어나는 비율
        
        self.setLayout(main_layout)
        
        # 초기 설정 값으로 업데이트
        self.update_spacing_value(self.spacing_slider.value())
        self.update_node_size_value(self.node_size_slider.value())
        
    def update_spacing_value(self, value):
        """노드 간격 슬라이더 값 업데이트"""
        spacing = value / 10.0
        self.spacing_value.setText(f"{spacing:.1f}")
        
    def update_node_size_value(self, value):
        """노드 크기 슬라이더 값 업데이트"""
        # 슬라이더 값을 실제 노드 크기로 변환 (10배)
        node_size = value * 10
        self.node_size_value.setText(f"{node_size}")
    
    def choose_color(self, color_type):
        """색상 선택 대화상자"""
        color_buttons = {
            'background': self.bg_color_btn,
            'router': self.router_color_btn,
            'switch': self.switch_color_btn,
            'firewall': self.firewall_color_btn,
            'server': self.server_color_btn
        }
        
        # 현재 버튼의 색상 가져오기
        current_color = self.get_button_color(color_buttons[color_type])
        
        # 색상 대화상자 표시
        color = QColorDialog.getColor(current_color, self, f"{color_type.capitalize()} 색상 선택")
        
        if color.isValid():
            # 버튼 색상 업데이트
            color_hex = color.name()
            color_buttons[color_type].setStyleSheet(f"background-color: {color_hex}; min-width: 60px;")
            
            # 배경색이 아닌 경우 custom_colors 업데이트
            if color_type != 'background':
                self.custom_colors[color_type] = color_hex
                
            # 커스텀 테마 라디오 버튼 선택
            self.custom_theme_radio.setChecked(True)
    
    def get_button_color(self, button):
        """버튼의 현재 배경색 가져오기"""
        from PyQt5.QtGui import QColor
        stylesheet = button.styleSheet()
        color_match = re.search(r"background-color: ([^;]+);", stylesheet)
        if color_match:
            return QColor(color_match.group(1))
        return QColor('#FFFFFF')  # 기본값
    
    def add_files(self):
        """CDP/LLDP 출력 파일 추가"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, 
            "CDP/LLDP 출력 파일 선택", 
            "", 
            "텍스트 파일 (*.txt);;모든 파일 (*.*)"
        )
        
        if file_paths:
            for file_path in file_paths:
                if file_path not in self.file_paths:
                    self.file_paths.append(file_path)
                    self.file_list.addItem(os.path.basename(file_path))
            
            self.update_file_summary()
            if self.parent:
                self.parent.statusBar.showMessage(f"{len(file_paths)}개 파일이 추가되었습니다.", 3000)
    
    def add_folder(self):
        """폴더 내 모든 텍스트 파일 추가"""
        folder_path = QFileDialog.getExistingDirectory(self, "CDP/LLDP 출력 파일이 있는 폴더 선택")
        
        if not folder_path:
            return
            
        txt_files = [f for f in os.listdir(folder_path) if f.endswith('.txt')]
        
        if not txt_files:
            QMessageBox.warning(self, "파일 없음", "선택한 폴더에 텍스트 파일이 없습니다.")
            return
            
        for file_name in txt_files:
            file_path = os.path.join(folder_path, file_name)
            if file_path not in self.file_paths:
                self.file_paths.append(file_path)
                self.file_list.addItem(file_name)
        
        self.update_file_summary()
        if self.parent:
            self.parent.statusBar.showMessage(f"{len(txt_files)}개 파일이 추가되었습니다.", 3000)
    
    def remove_files(self):
        """선택한 파일 제거"""
        selected_items = self.file_list.selectedItems()
        
        if not selected_items:
            return
            
        for item in selected_items:
            row = self.file_list.row(item)
            self.file_list.takeItem(row)
            file_path = self.file_paths[row]
            self.file_paths.remove(file_path)
        
        self.update_file_summary()
        if self.parent:
            self.parent.statusBar.showMessage(f"{len(selected_items)}개 파일이 제거되었습니다.", 3000)
    
    def clear_files(self):
        """모든 파일 제거"""
        self.file_list.clear()
        self.file_paths = []
        
        self.update_file_summary()
        if self.parent:
            self.parent.statusBar.showMessage("모든 파일이 제거되었습니다.", 3000)
    
    def update_file_summary(self):
        """파일 요약 정보 업데이트"""
        file_count = len(self.file_paths)
        
        if file_count == 0:
            self.file_summary.setText("파일 요약: 0개 파일, 0개 장비 감지됨")
            return
            
        # 파일에서 호스트명 추출
        hostnames = []
        for file_path in self.file_paths:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    hostname_match = re.search(r"hostname ([^\s\n]+)", content)
                    if hostname_match:
                        hostnames.append(hostname_match.group(1).strip())
            except Exception:
                pass
        
        # 중복 제거
        unique_hostnames = list(set(hostnames))
        
        self.file_summary.setText(f"파일 요약: {file_count}개 파일, {len(unique_hostnames)}개 장비 감지됨")
    
    def parse_cisco_output(self, file_path):
        """Cisco 장비의 CDP/LLDP 출력 파싱 - 제공된 예시 파일 형식에 맞게 수정"""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            
            # 호스트 이름 추출 (hostname 명령어로 설정된 값 찾기)
            hostname_match = re.search(r"hostname ([^\s\n]+)", content)
            hostname = hostname_match.group(1).strip() if hostname_match else os.path.basename(file_path).split('.')[0]
            
            connections = []
            
            # CDP 출력 파싱 - 제공된 예시 파일 형식에 맞춤
            if self.use_cdp.isChecked():
                # "Command: sh cdp ne" 섹션 찾기
                cdp_section_match = re.search(r"Command: sh cdp ne(.*?)--------------------------------------------------", content, re.DOTALL)
                
                if cdp_section_match:
                    cdp_section = cdp_section_match.group(1)
                    
                    # CDP 표 형식 데이터에서 각 행 추출 (헤더 제외)
                    cdp_lines = cdp_section.strip().split('\n')
                    
                    # 헤더 제외하고 데이터 행만 처리
                    data_lines = []
                    for line in cdp_lines:
                        if re.match(r"^[A-Za-z0-9\-_]+\s+", line) and not line.startswith("Device ID") and not line.startswith("Capability"):
                            data_lines.append(line)
                    
                    # 각 연결 정보 파싱
                    for line in data_lines:
                        if "Total cdp entries" in line:
                            continue
                            
                        parts = line.split()
                        if len(parts) >= 6:  # 최소 필요 필드 수 확인
                            device_id = parts[0]
                            
                            # 인터페이스 정보 추출 (Gig X/Y 형식)
                            local_intf_idx = 1
                            local_intf = parts[local_intf_idx]
                            if local_intf_idx + 1 < len(parts) and re.match(r"\d+/\d+", parts[local_intf_idx + 1]):
                                local_intf += " " + parts[local_intf_idx + 1]
                                local_intf_idx += 1
                            
                            # 원격 인터페이스는 마지막 필드(들)
                            remote_intf = parts[-1]
                            if len(parts) > 6 and re.match(r"\d+/\d+", parts[-2]):
                                remote_intf = parts[-2] + " " + remote_intf
                            
                            # IP 주소 추출을 위해 "sh ip int b" 명령어 결과 검색
                            ip_address = ""
                            ip_section_match = re.search(r"Command: sh ip int b(.*?)--------------------------------------------------", content, re.DOTALL)
                            if ip_section_match:
                                ip_section = ip_section_match.group(1)
                                for ip_line in ip_section.split('\n'):
                                    # VLAN과 인터페이스 IP 매칭
                                    if "Vlan" in ip_line and re.search(r"\d+\.\d+\.\d+\.\d+", ip_line):
                                        ip_parts = ip_line.split()
                                        if len(ip_parts) >= 2:
                                            ip_address = ip_parts[1]
                                            break
                            
                            connections.append({
                                "neighbor": device_id,
                                "local_intf": local_intf,
                                "remote_intf": remote_intf,
                                "ip": ip_address,
                                "platform": parts[-3] if len(parts) > 6 else "Unknown",
                                "protocol": "CDP"
                            })
            
            # LLDP 출력 파싱 - 필요시 추가 구현
            if self.use_lldp.isChecked():
                lldp_section_match = re.search(r"Command: sh lldp ne(.*?)--------------------------------------------------", content, re.DOTALL)
                
                if lldp_section_match:
                    lldp_section = lldp_section_match.group(1)
                    
                    # LLDP 표 형식 데이터에서 각 행 추출 (헤더 제외)
                    lldp_lines = lldp_section.strip().split('\n')
                    
                    # 헤더 제외하고 데이터 행만 처리
                    data_lines = []
                    for line in lldp_lines:
                        if re.match(r"^[A-Za-z0-9\-_]+\s+", line) and not line.startswith("Device ID") and not line.startswith("Capability"):
                            data_lines.append(line)
                    
                    # 각 연결 정보 파싱
                    for line in data_lines:
                        if "Total lldp entries" in line:
                            continue
                            
                        parts = line.split()
                        if len(parts) >= 6:  # 최소 필요 필드 수 확인
                            device_id = parts[0]
                            
                            # 인터페이스 정보 추출
                            local_intf_idx = 1
                            local_intf = parts[local_intf_idx]
                            if local_intf_idx + 1 < len(parts) and re.match(r"\d+/\d+", parts[local_intf_idx + 1]):
                                local_intf += " " + parts[local_intf_idx + 1]
                                local_intf_idx += 1
                            
                            # 원격 인터페이스는 마지막 필드(들)
                            remote_intf = parts[-1]
                            if len(parts) > 6 and re.match(r"\d+/\d+", parts[-2]):
                                remote_intf = parts[-2] + " " + remote_intf
                            
                            connections.append({
                                "neighbor": device_id,
                                "local_intf": local_intf,
                                "remote_intf": remote_intf,
                                "ip": "",  # LLDP에서는 별도 처리 필요
                                "platform": "Unknown",
                                "protocol": "LLDP"
                            })
            
            # BGP 피어 처리 (확장 기능)
            if self.use_bgp.isChecked():
                bgp_section_match = re.search(r"sh(?:ow)?\s+bgp\s+(?:ipv4\s+uni(?:cast)?\s+)?sum(?:mary)?.*?([\s\S]*?)(?=Command:|$)", content, re.DOTALL)
                if bgp_section_match:
                    bgp_section = bgp_section_match.group(1)
                    # BGP 피어 IP 추출
                    bgp_peers = re.findall(r"(\d+\.\d+\.\d+\.\d+)[^\n]*", bgp_section)
                    
                    for peer_ip in bgp_peers:
                        connections.append({
                            "neighbor": f"BGP-{peer_ip}",  # BGP 식별자 추가
                            "local_intf": "BGP",
                            "remote_intf": "BGP",
                            "ip": peer_ip,
                            "platform": "BGP Peer",
                            "protocol": "BGP"
                        })
            
            # OSPF 이웃 처리 (확장 기능)
            if self.use_ospf.isChecked():
                ospf_section_match = re.search(r"sh(?:ow)?\s+ip\s+ospf\s+nei(?:ghbor)?.*?([\s\S]*?)(?=Command:|$)", content, re.DOTALL)
                if ospf_section_match:
                    ospf_section = ospf_section_match.group(1)
                    # OSPF 이웃 IP 추출
                    ospf_neighbors = re.findall(r"(\d+\.\d+\.\d+\.\d+)[^\n]*", ospf_section)
                    
                    for neighbor_ip in ospf_neighbors:
                        connections.append({
                            "neighbor": f"OSPF-{neighbor_ip}",  # OSPF 식별자 추가
                            "local_intf": "OSPF",
                            "remote_intf": "OSPF",
                            "ip": neighbor_ip,
                            "platform": "OSPF Neighbor",
                            "protocol": "OSPF"
                        })
            
            return hostname, connections
            
        except Exception as e:
            QMessageBox.warning(self, "파싱 오류", f"파일 {os.path.basename(file_path)} 파싱 중 오류: {e}")
            import traceback
            print(traceback.format_exc())
            return None, []
    
    def determine_device_type(self, hostname, platform=None):
        """장비 호스트명이나 플랫폼 정보를 기반으로 장비 타입 추정"""
        hostname = hostname.lower()
        
        # BGP/OSPF 피어는 라우터로 취급
        if hostname.startswith('bgp-') or hostname.startswith('ospf-'):
            return 'router'
        
        # 라우터 식별
        if any(x in hostname for x in ['rtr', 'router', 'rt-', 'r-', '-r-']):
            return 'router'
        # 스위치 식별
        elif any(x in hostname for x in ['sw', 'switch', 'swt', '-s-']):
            return 'switch'
        # 방화벽 식별
        elif any(x in hostname for x in ['fw', 'firewall', 'asa', 'pix', 'ftd']):
            return 'firewall'
        # 서버 식별
        elif any(x in hostname for x in ['srv', 'server', 'host', 'vm']):
            return 'server'
        
        # 플랫폼 정보가 있다면 활용
        if platform:
            platform = platform.lower()
            if any(x in platform for x in ['router', '7200', '7600', 'asr', 'isr']):
                return 'router'
            elif any(x in platform for x in ['switch', 'cat', 'nx-os', 'nexus', '3750', '2960']):
                return 'switch'
            elif any(x in platform for x in ['asa', 'pix', 'firepower', 'ftd']):
                return 'firewall'
        
        # 기본값: 스위치 (가장 일반적인 네트워크 장비)
        return 'switch'
        
    def generate_diagram(self):
        """고급스러운 네트워크 다이어그램 생성"""
        if not self.file_paths:
            QMessageBox.warning(self, "파일 없음", "다이어그램을 생성할 파일이 없습니다. 파일을 추가해주세요.")
            return
            
        try:
            import networkx as nx
            import matplotlib.pyplot as plt
            import matplotlib.patheffects as PathEffects
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
            import numpy as np
            
            # 상태바 메시지
            if self.parent:
                self.parent.statusBar.showMessage("다이어그램 생성 중...", 0)  # 0 = 무기한
            
            # 이전 캔버스 제거
            if self.canvas and self.diagram_preview.layout():
                layout = self.diagram_preview.layout()
                layout.removeWidget(self.canvas)
                self.canvas.deleteLater()
                self.canvas = None
            
            # 다이어그램 생성을 위한 그래프 초기화
            G = nx.Graph()
            self.device_connections = {}
            
            # 노드 타입 딕셔너리 (장비 타입에 따른 스타일링을 위해)
            node_types = {}
            
            # 각 파일 파싱
            for file_path in self.file_paths:
                hostname, connections = self.parse_cisco_output(file_path)
                
                if hostname:
                    # 장비 노드 추가 (기본 타입은 'switch'로 설정)
                    G.add_node(hostname)
                    node_types[hostname] = self.determine_device_type(hostname)
                    self.device_connections[hostname] = connections
                    
                    # 연결 정보 추가
                    for conn in connections:
                        G.add_node(conn["neighbor"])
                        # 이웃 장비의 타입 추정
                        if conn["neighbor"] not in node_types:
                            node_types[conn["neighbor"]] = self.determine_device_type(conn["neighbor"], conn["platform"])
                        
                        # IP 주소와 인터페이스 정보 엣지 속성으로 추가
                        edge_attrs = {
                            "local_intf": conn["local_intf"],
                            "remote_intf": conn["remote_intf"],
                            "ip": conn["ip"],
                            "platform": conn["platform"],
                            "protocol": conn["protocol"]
                        }
                        G.add_edge(hostname, conn["neighbor"], **edge_attrs)
            
            # 노드가 없는 경우
            if not G.nodes():
                QMessageBox.warning(self, "다이어그램 생성 실패", "파일에서 네트워크 연결 정보를 추출할 수 없습니다.")
                if self.parent:
                    self.parent.statusBar.showMessage("다이어그램 생성 실패", 3000)
                return
                
            # 레이아웃 선택
            layout_type = self.layout_combo.currentText()
            k_spacing = self.spacing_slider.value() / 10.0  # 슬라이더 값을 간격 파라미터로 변환
            
            # 레이아웃 함수 선택
            layout_funcs = {
                "계층적": lambda G, k: nx.spring_layout(G, k=k),
                "원형": lambda G, k: nx.circular_layout(G),
                "힘 기반": lambda G, k: nx.kamada_kawai_layout(G),
                "스프링": lambda G, k: nx.spring_layout(G, k=k),
                "쉘": lambda G, k: nx.shell_layout(G),
                "분광": lambda G, k: nx.spectral_layout(G)
            }
            
            # 레이아웃 계산
            pos = layout_funcs.get(layout_type, layout_funcs["스프링"])(G, k_spacing)
            
            # 테마 설정
            if self.dark_theme_radio.isChecked():
                bg_color = '#1f2430'
                text_color = 'white'
                edge_color = 'white'
                plt.style.use('dark_background')
            elif self.light_theme_radio.isChecked():
                bg_color = '#f5f5f5'
                text_color = 'black'
                edge_color = '#555555'
                plt.style.use('default')
            else:  # 커스텀 테마
                bg_color = self.get_button_color(self.bg_color_btn).name()
                text_color = 'white' if self.is_dark_color(bg_color) else 'black'
                edge_color = 'white' if self.is_dark_color(bg_color) else '#555555'
                plt.style.use('default')
                
            # 고급 테마의 그래프 생성
            fig_width = self.width_spin.value()
            fig_height = self.height_spin.value()
            fig, ax = plt.subplots(figsize=(fig_width, fig_height), facecolor=bg_color)
            
            # 노드 크기
            node_size = self.node_size_slider.value() * 10
            
            # 노드 그룹별로 처리
            for node_type, color in self.custom_colors.items():
                # 이 타입에 해당하는 노드들
                node_list = [node for node, ntype in node_types.items() if ntype == node_type]
                if not node_list:
                    continue
                    
                # 노드 그리기 - 타입별 색상과 크기 적용
                nx.draw_networkx_nodes(
                    G, pos, 
                    nodelist=node_list,
                    node_size=node_size, 
                    node_color=color,
                    edgecolors='white' if self.is_dark_color(bg_color) else 'black',
                    linewidths=1.5,
                    alpha=0.9,
                    ax=ax
                )
            
            # 엣지 그리기 (세련된 스타일)
            edge_width = self.edge_width_spin.value()
            nx.draw_networkx_edges(
                G, pos, 
                width=edge_width,
                edge_color=edge_color,
                alpha=0.7,
                arrows=True,
                connectionstyle='arc3,rad=0.1',
                min_source_margin=15,
                min_target_margin=15,
                ax=ax
            )
            
            # 노드 레이블 표시 (가독성 높은 스타일)
            font_size = self.font_size_spin.value()
            labels = nx.draw_networkx_labels(
                G, pos, 
                font_size=font_size, 
                font_weight='bold',
                font_color=text_color,
                bbox=dict(facecolor=bg_color, edgecolor='none', alpha=0.7, pad=3),
                ax=ax
            )
            
            # 텍스트에 테두리 효과 추가하여 가독성 향상
            for text in labels.values():
                text.set_path_effects([PathEffects.withStroke(linewidth=3, foreground=bg_color)])
            
            # 엣지 레이블 표시 (옵션에 따라)
            if self.include_interfaces.isChecked() or self.include_ip.isChecked():
                edge_labels = {}
                for u, v, data in G.edges(data=True):
                    label = ""
                    if self.include_interfaces.isChecked():
                        label += f"{data.get('local_intf', '')} → {data.get('remote_intf', '')}"
                    if self.include_ip.isChecked() and data.get('ip'):
                        if label:
                            label += f"\n{data.get('ip', '')}"
                        else:
                            label += f"{data.get('ip', '')}"
                    edge_labels[(u, v)] = label
                
                if edge_labels:
                    # 세련된 엣지 레이블 스타일링
                    edge_label_font_size = max(6, font_size - 2)  # 노드 폰트보다 약간 작게
                    edge_label_bg = '#364156' if self.is_dark_color(bg_color) else '#e6e6e6'
                    
                    edge_label_pos = nx.draw_networkx_edge_labels(
                        G, pos, 
                        edge_labels=edge_labels, 
                        font_size=edge_label_font_size,
                        font_color=text_color,
                        bbox=dict(facecolor=edge_label_bg, edgecolor='none', alpha=0.7, pad=3),
                        ax=ax
                    )
            
            # 장비 타입 범례 추가
            if self.show_legend.isChecked():
                legend_elements = []
                for node_type, color in self.custom_colors.items():
                    if any(t == node_type for t in node_types.values()):
                        from matplotlib.lines import Line2D
                        legend_elements.append(
                            Line2D([0], [0], marker='o', color=bg_color, 
                                  markerfacecolor=color, markersize=10, 
                                  label=node_type.capitalize())
                        )
                
                if legend_elements:
                    legend_text_color = text_color
                    legend_edge_color = 'white' if self.is_dark_color(bg_color) else 'black'
                    
                    ax.legend(
                        handles=legend_elements, 
                        loc='upper right', 
                        frameon=True, 
                        facecolor=bg_color, 
                        edgecolor=legend_edge_color,
                        labelcolor=legend_text_color
                    )
            
            # 배경색 설정
            ax.set_facecolor(bg_color)
            ax.grid(False)  # 그리드 비활성화
            
            # 제목 추가
            title_text = "네트워크 구성도"
            plt.title(title_text, fontsize=font_size+6, fontweight='bold', color=text_color, pad=20)
            
            # 화면에 맞게 조정
            plt.tight_layout(pad=2)
            plt.axis('off')  # 축 숨기기
            
            # 웹 브라우저용 파일 저장
            self.save_for_browser(fig)
            
            # Canvas에 그림 표시
            self.canvas = FigureCanvas(fig)
            
            # 새로운 위젯 생성 및 레이아웃 설정
            preview_widget = QWidget()
            preview_layout = QVBoxLayout(preview_widget)
            preview_layout.addWidget(self.canvas)
            
            # 기존의 diagram_preview 위젯의 부모 위젯(레이아웃) 가져오기
            parent_layout = self.diagram_preview.parentWidget().layout()
            
            # 기존 위젯 제거 및 새 위젯 추가
            parent_layout.replaceWidget(self.diagram_preview, preview_widget)
            self.diagram_preview.hide()
            self.diagram_preview.deleteLater()
            self.diagram_preview = preview_widget
            
            if self.parent:
                self.parent.statusBar.showMessage("다이어그램 생성 완료", 3000)
                
        except ImportError as e:
            QMessageBox.warning(self, "라이브러리 오류", f"필요한 라이브러리가 설치되지 않았습니다: {e}\n\n관리자에게 문의하세요.")
            if self.parent:
                self.parent.statusBar.showMessage("다이어그램 생성 실패: 라이브러리 오류", 3000)
        except Exception as e:
            QMessageBox.warning(self, "다이어그램 생성 오류", f"다이어그램 생성 중 오류 발생: {e}")
            if self.parent:
                self.parent.statusBar.showMessage(f"다이어그램 생성 오류: {e}", 3000)
            import traceback
            print(traceback.format_exc())
            
    def save_for_browser(self, fig):
            """웹 브라우저에서 볼 수 있도록 임시 HTML 파일 저장"""
            try:
                # 임시 디렉토리 생성
                temp_dir = os.path.join(tempfile.gettempdir(), 'network_diagram')
                os.makedirs(temp_dir, exist_ok=True)
                
                # HTML 파일 경로
                html_path = os.path.join(temp_dir, 'network_diagram.html')
                
                # SVG 파일 경로
                svg_path = os.path.join(temp_dir, 'network_diagram.svg')
                
                # 배경색 처리
                bg_color = fig.get_facecolor()
                # 튜플이면 RGB 색상 코드로 변환
                if isinstance(bg_color, tuple) and len(bg_color) >= 3:
                    r, g, b = bg_color[:3]
                    bg_color_hex = f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
                elif isinstance(bg_color, str):
                    bg_color_hex = bg_color
                else:
                    # 기본값 설정
                    bg_color_hex = "#1f2430"
                
                # SVG로 저장
                fig.savefig(
                    svg_path, 
                    format='svg', 
                    bbox_inches='tight',
                    facecolor=fig.get_facecolor(),
                    edgecolor='none',
                    transparent=False
                )
                
                # 텍스트 색상 결정 (배경이 어두우면 밝은 색, 밝으면 어두운 색)
                is_dark = self.is_dark_color_hex(bg_color_hex)
                text_color = 'white' if is_dark else 'black'
                
                # HTML 파일 생성
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(f"""<!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>네트워크 구성도</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: {bg_color_hex};
                color: {text_color};
            }}
            .diagram-container {{
                max-width: 100%;
                overflow: auto;
                text-align: center;
            }}
            h1 {{
                text-align: center;
                margin-bottom: 20px;
            }}
            svg {{
                max-width: 100%;
                height: auto;
            }}
            .controls {{
                margin: 20px 0;
                text-align: center;
            }}
            button {{
                padding: 10px 15px;
                margin: 0 5px;
                background-color: #4B6EAF;
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
            }}
            button:hover {{
                background-color: #5A7EC2;
            }}
        </style>
    </head>
    <body>
        <h1>네트워크 구성도</h1>
        <div class="controls">
            <button onclick="zoomIn()">확대 (+)</button>
            <button onclick="zoomOut()">축소 (-)</button>
            <button onclick="resetZoom()">원래 크기</button>
            <button onclick="saveDiagram()">다이어그램 저장</button>
        </div>
        <div class="diagram-container">
            <object id="diagram" data="network_diagram.svg" type="image/svg+xml" width="100%"></object>
        </div>
        <script>
            var scale = 1;
            var diagram = document.getElementById('diagram');
            
            function zoomIn() {{
                scale *= 1.2;
                diagram.style.transform = `scale(${{scale}})`;
                diagram.style.transformOrigin = 'center center';
            }}
            
            function zoomOut() {{
                scale /= 1.2;
                diagram.style.transform = `scale(${{scale}})`;
                diagram.style.transformOrigin = 'center center';
            }}
            
            function resetZoom() {{
                scale = 1;
                diagram.style.transform = `scale(${{scale}})`;
            }}
            
            function saveDiagram() {{
                // SVG를 다운로드하는 기능
                var a = document.createElement('a');
                a.href = 'network_diagram.svg';
                a.download = 'network_diagram.svg';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            }}
        </script>
    </body>
    </html>""")
                
                # 저장한 HTML 파일 경로 유지
                self.last_diagram_path = html_path
                
            except Exception as e:
                import traceback
                print(f"웹 브라우저용 파일 저장 오류: {e}")
                print(traceback.format_exc())
            
    def is_dark_color_hex(self, color_hex):
        """HEX 색상 코드가 어두운지 확인"""
        # #으로 시작하면 제거
        if color_hex.startswith('#'):
            color_hex = color_hex[1:]
            
        # RGB 값 추출
        r = int(color_hex[0:2], 16) if len(color_hex) >= 2 else 0
        g = int(color_hex[2:4], 16) if len(color_hex) >= 4 else 0
        b = int(color_hex[4:6], 16) if len(color_hex) >= 6 else 0
        
        # 명도 계산
        brightness = (299 * r + 587 * g + 114 * b) / 1000
        return brightness < 128  # 128보다 작으면 어두운 색상으로 판단
    
    def open_in_browser(self):
        """웹 브라우저에서 다이어그램 열기"""
        if not self.last_diagram_path or not os.path.exists(self.last_diagram_path):
            QMessageBox.warning(self, "브라우저로 보기 오류", "먼저 다이어그램을 생성해주세요.")
            return
            
        try:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.last_diagram_path))
            if self.parent:
                self.parent.statusBar.showMessage("다이어그램이 웹 브라우저에서 열렸습니다.", 3000)
        except Exception as e:
            QMessageBox.warning(self, "브라우저로 보기 오류", f"웹 브라우저에서 열기 실패: {e}")
    
    def export_diagram(self):
        """고품질 다이어그램 내보내기"""
        if not hasattr(self, 'canvas') or not self.canvas:
            QMessageBox.warning(self, "내보내기 오류", "먼저 다이어그램을 생성해주세요.")
            return
            
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self, 
            "다이어그램 내보내기", 
            "network_diagram", 
            "SVG 파일 (*.svg);;고해상도 PNG (*.png);;PDF 파일 (*.pdf)"
        )
        
        if not file_path:
            return
            
        try:
            fig = self.canvas.figure
            dpi = self.dpi_spin.value()
            
            # 선택된 필터에 따라 다른 형식으로 저장
            if "SVG" in selected_filter:
                fig.savefig(
                    file_path if file_path.endswith('.svg') else file_path + '.svg', 
                    format='svg', 
                    bbox_inches='tight',
                    facecolor=fig.get_facecolor(),
                    edgecolor='none',
                    transparent=False
                )
            elif "PNG" in selected_filter:
                fig.savefig(
                    file_path if file_path.endswith('.png') else file_path + '.png', 
                    format='png', 
                    dpi=dpi,  # 사용자 설정 DPI
                    bbox_inches='tight',
                    facecolor=fig.get_facecolor(),
                    edgecolor='none'
                )
            elif "PDF" in selected_filter:
                fig.savefig(
                    file_path if file_path.endswith('.pdf') else file_path + '.pdf',
                    format='pdf',
                    bbox_inches='tight',
                    facecolor=fig.get_facecolor(),
                    edgecolor='none'
                )
                
            QMessageBox.information(self, "내보내기 완료", f"다이어그램이 저장되었습니다:\n{file_path}")
            
            if self.parent:
                self.parent.statusBar.showMessage(f"다이어그램이 저장되었습니다: {file_path}", 3000)
        except Exception as e:
            QMessageBox.critical(self, "내보내기 오류", f"다이어그램을 저장하는 중 오류가 발생했습니다: {e}")
            if self.parent:
                self.parent.statusBar.showMessage(f"내보내기 오류: {e}", 3000)
    
    def is_dark_color(self, color):
        """색상이 어두운지 확인 (텍스트 색상 결정에 사용)"""
        from PyQt5.QtGui import QColor
        
        if isinstance(color, str):
            color = QColor(color)
        
        # 색상의 명도 계산
        brightness = (299 * color.red() + 587 * color.green() + 114 * color.blue()) / 1000
        return brightness < 128  # 128보다 작으면 어두운 색상으로 판단
        
    def save_settings(self):
        """설정을 파일에 저장"""
        settings = {
            "theme": "dark" if self.dark_theme_radio.isChecked() else "light" if self.light_theme_radio.isChecked() else "custom",
            "custom_colors": self.custom_colors,
            "layout_algorithm": self.layout_combo.currentText(),
            "spacing": self.spacing_slider.value(),
            "node_size": self.node_size_slider.value(),
            "font_size": self.font_size_spin.value(),
            "edge_width": self.edge_width_spin.value(),
            "include_ip": self.include_ip.isChecked(),
            "include_interfaces": self.include_interfaces.isChecked(),
            "include_device_icon": self.include_device_icon.isChecked(),
            "show_legend": self.show_legend.isChecked(),
            "dpi": self.dpi_spin.value(),
            "fig_width": self.width_spin.value(),
            "fig_height": self.height_spin.value()
        }
        
        try:
            os.makedirs(os.path.dirname(os.path.join(os.path.expanduser("~"), ".network_diagram")), exist_ok=True)
            with open(os.path.join(os.path.expanduser("~"), ".network_diagram", "settings.json"), "w") as f:
                json.dump(settings, f, indent=4)
            if self.parent:
                self.parent.statusBar.showMessage("다이어그램 설정이 저장되었습니다.", 3000)
        except Exception as e:
            print(f"설정 저장 오류: {e}")
            
    def load_settings(self):
        """저장된 설정 불러오기"""
        settings_path = os.path.join(os.path.expanduser("~"), ".network_diagram", "settings.json")
        if not os.path.exists(settings_path):
            return
            
        try:
            with open(settings_path, "r") as f:
                settings = json.load(f)
                
            # 테마 설정
            if settings.get("theme") == "dark":
                self.dark_theme_radio.setChecked(True)
            elif settings.get("theme") == "light":
                self.light_theme_radio.setChecked(True)
            else:
                self.custom_theme_radio.setChecked(True)
                
            # 커스텀 색상 설정
            if "custom_colors" in settings:
                self.custom_colors = settings["custom_colors"]
                self.router_color_btn.setStyleSheet(f"background-color: {self.custom_colors['router']}; min-width: 60px;")
                self.switch_color_btn.setStyleSheet(f"background-color: {self.custom_colors['switch']}; min-width: 60px;")
                self.firewall_color_btn.setStyleSheet(f"background-color: {self.custom_colors['firewall']}; min-width: 60px;")
                self.server_color_btn.setStyleSheet(f"background-color: {self.custom_colors['server']}; min-width: 60px;")
                
            # 레이아웃 설정
            if "layout_algorithm" in settings:
                index = self.layout_combo.findText(settings["layout_algorithm"])
                if index >= 0:
                    self.layout_combo.setCurrentIndex(index)
                    
            # 간격 설정
            if "spacing" in settings:
                self.spacing_slider.setValue(settings["spacing"])
                
            # 노드 크기 설정
            if "node_size" in settings:
                self.node_size_slider.setValue(settings["node_size"])
                
            # 글꼴 크기
            if "font_size" in settings:
                self.font_size_spin.setValue(settings["font_size"])
                
            # 연결선 두께
            if "edge_width" in settings:
                self.edge_width_spin.setValue(settings["edge_width"])
                
            # 표시 옵션
            if "include_ip" in settings:
                self.include_ip.setChecked(settings["include_ip"])
            if "include_interfaces" in settings:
                self.include_interfaces.setChecked(settings["include_interfaces"])
            if "include_device_icon" in settings:
                self.include_device_icon.setChecked(settings["include_device_icon"])
            if "show_legend" in settings:
                self.show_legend.setChecked(settings["show_legend"])
                
            # 내보내기 설정
            if "dpi" in settings:
                self.dpi_spin.setValue(settings["dpi"])
            if "fig_width" in settings:
                self.width_spin.setValue(settings["fig_width"])
            if "fig_height" in settings:
                self.height_spin.setValue(settings["fig_height"])
                
            if self.parent:
                self.parent.statusBar.showMessage("다이어그램 설정을 불러왔습니다.", 3000)
        except Exception as e:
            print(f"설정 로드 오류: {e}")



