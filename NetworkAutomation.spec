# -*- mode: python ; coding: utf-8 -*-
"""
NetworkAutomation PyInstaller Spec File
모든 필요한 모듈 포함 - 최종 빌드
"""

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('icons', 'icons'),  # icons 폴더 포함
    ],
    hiddenimports=[
        # PyQt5
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'PyQt5.sip',
        # 네트워크 라이브러리
        'paramiko',
        'openpyxl',
        # 데이터 분석 라이브러리
        'pandas',
        'numpy',
        'matplotlib',
        'matplotlib.pyplot',
        'matplotlib.backends.backend_qt5agg',
        'PIL',
        'Pillow',
        # UI 모듈
        'ui',
        'ui.main_window',
        'ui.network_tab',
        'ui.about_tab',
        'ui.report_tab',
        'ui.theme',
        'ui.dogu_tab',
        'ui.auto_analysis_tab',
        'ui.log_analyzer_tab',
        'ui.monitoring_tab',
        # Core 모듈
        'core',
        'core.workers',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 정말 불필요한 모듈만 제외
        'scipy',
        'tkinter',
        'unittest',
        'pydoc',
        'doctest',
        'test',
        'tests',
        '_pytest',
        'pytest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='NetworkAutomation',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # UPX 압축 활성화
    console=False,  # 콘솔 창 숨김
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=r'D:\5. 개발\최신 program network auto 2025.06.25 (파일명 형식)\icons\app_icon.ico',  # 아이콘 파일
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='NetworkAutomation',
)
