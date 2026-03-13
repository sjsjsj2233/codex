import sys
import os
import re
import time
import socket
import logging
import subprocess
import threading
import paramiko
import datetime
import telnetlib
from concurrent.futures import ThreadPoolExecutor
import queue
import random

# PyQt5 라이브러리
from PyQt5.QtCore import QThread, pyqtSignal, QMutex


# ===== 설정 상수 =====
class NetworkConfig:
    """네트워크 연결 설정 상수"""
    # 타임아웃 설정 (초)
    DEFAULT_TIMEOUT = 15
    BANNER_TIMEOUT = 10
    AUTH_TIMEOUT = 10
    CONNECT_TIMEOUT = 15
    COMMAND_TIMEOUT = 30

    # 터미널 설정 명령어
    TERMINAL_LENGTH_CMD = "terminal length 0"
    TERMINAL_WIDTH_CMD = "terminal width 132"

    # 연결 재시도 설정
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # 초

    # 버퍼 설정
    SSH_BUFFER_SIZE = 8192
    MAX_BUFFER_SIZE = 1024 * 1024  # 1MB

    # 대기 시간
    PARAMIKO_INIT_DELAY = 0.5
    COMMAND_DELAY = 0.5
    PROMPT_CHECK_DELAY = 0.1


# ===== 초기화 관련 추가 (이 부분을 추가하세요) =====
# paramiko 초기화 강제 실행
def initialize_paramiko():
    """paramiko 라이브러리를 미리 초기화하여 첫 연결 시 발생하는 문제 방지"""
    try:
        # 더미 SSH 클라이언트 생성으로 라이브러리 초기화
        dummy_ssh = paramiko.SSHClient()
        dummy_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        del dummy_ssh
        logging.info("[INIT] paramiko 초기화 완료")
        return True
    except Exception as e:
        logging.warning(f"[INIT] paramiko 초기화 실패: {e}")
        return False

# 애플리케이션 시작 시 한 번 실행
_paramiko_initialized = False
def ensure_paramiko_initialized():
    """paramiko가 초기화되었는지 확인하고, 필요시 초기화"""
    global _paramiko_initialized
    if not _paramiko_initialized:
        _paramiko_initialized = initialize_paramiko()
        # 추가 대기 시간으로 완전한 초기화 보장
        time.sleep(0.5)
    return _paramiko_initialized
# ===== 추가 끝 =====


class NetworkWorker(QThread):
    # 기존 시그널들
    progress_updated = pyqtSignal(int)
    task_completed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    debug_log = pyqtSignal(str)
    
    # 실시간 상태 업데이트를 위한 새로운 시그널
    status_update = pyqtSignal(str, str)  # IP, 상태 메시지

    def __init__(self, ip, username, password, enable_password, use_ssh, save_path, commands, ssh_port=22):
        super().__init__()
        self.ip = ip
        self.username = username
        self.password = password
        self.enable_password = enable_password
        self.use_ssh = use_ssh
        self.save_path = save_path
        self.commands = commands
        self.ssh_port = ssh_port
        self._stop_flag = False
        self._mutex = QMutex()
        self.filename_format = "hostname_only"  # 기본값 설정
        
        # 연결 재시도 설정
        self.max_retries = NetworkConfig.MAX_RETRIES
        self.retry_delay = NetworkConfig.RETRY_DELAY

    def _emit_status(self, message):
        """상태 업데이트와 로그를 동시에 처리"""
        self.status_update.emit(self.ip, message)
        self._log_debug(message)

    def _log_debug(self, message):
        """디버그 메시지 로깅 및 시그널 방출"""
        logging.debug(f"[{self.ip}] {message}")
        self.debug_log.emit(f"[{self.ip}] {str(message)}")

    def stop(self):
        """스레드 중지를 요청합니다."""
        self._mutex.lock()
        self._stop_flag = True
        self._mutex.unlock()
        self._emit_status("중지 요청됨")

    def is_stopped(self):
        """스레드 중지 여부를 확인합니다."""
        self._mutex.lock()
        flag = self._stop_flag
        self._mutex.unlock()
        return flag

    def run(self):
        try:
            if self.is_stopped():
                self.task_completed.emit(f"[INFO] 작업 중지됨: {self.ip}")
                return

            # paramiko 초기화 확인
            if self.use_ssh:
                self._emit_status("SSH 라이브러리 초기화 확인 중...")
                if not ensure_paramiko_initialized():
                    self._emit_status("SSH 라이브러리 초기화 실패, 재시도...")
                    time.sleep(1)
                    ensure_paramiko_initialized()

            # 연결 시도 (재시도 로직 포함)
            success = False
            last_error = None
            
            for attempt in range(self.max_retries):
                if self.is_stopped():
                    self.task_completed.emit(f"[INFO] 작업 중지됨: {self.ip}")
                    return
                
                try:
                    if attempt > 0:
                        self._emit_status(f"연결 재시도 {attempt + 1}/{self.max_retries}...")
                        time.sleep(self.retry_delay)
                    
                    if self.use_ssh:
                        self.connect_via_ssh()
                    else:
                        self.connect_via_telnet()
                    
                    success = True
                    break
                    
                except Exception as e:
                    last_error = e
                    error_msg = str(e)
                    self._log_debug(f"연결 시도 {attempt + 1} 실패: {error_msg}")
                    
                    # 특정 오류의 경우 즉시 중단
                    if "authentication failed" in error_msg.lower() or "access denied" in error_msg.lower():
                        self._emit_status("인증 실패 - 재시도 중단")
                        break
                    
                    if attempt < self.max_retries - 1:
                        self._emit_status(f"연결 실패, {self.retry_delay}초 후 재시도... ({error_msg})")
            
            if success:
                if not self.is_stopped():
                    self.task_completed.emit(f"[SUCCESS] 작업 완료: {self.ip}")
                    self.progress_updated.emit(1)
                else:
                    self.task_completed.emit(f"[INFO] 작업 인터럽트됨: {self.ip}")
            else:
                raise last_error if last_error else Exception("모든 연결 시도 실패")
                
        except Exception as e:
            logging.error(f"[ERROR] {self.ip}: {e}")
            self.error_occurred.emit(f"[ERROR] {self.ip}: {e}")

    def enhanced_login_handler(self, connection, connection_type="ssh"):
        """
        향상된 로그인 처리 (TACACS+ 지원)
        """
        try:
            # 초기 출력 읽기
            initial_output = ""
            if connection_type == "ssh":
                time.sleep(2)
                initial_output = self._read_until_prompt_ssh(connection, timeout=10)
            else:  # telnet
                time.sleep(2)
                initial_output = self._read_until_prompt_telnet(connection, timeout=10)
            
            self._log_debug(f"[LOGIN] 초기 출력: {repr(initial_output)}")
            
            # 이미 로그인된 상태인지 확인 (프롬프트가 있는 경우)
            if initial_output.strip():
                lines = initial_output.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if re.search(r'[#>]\s*$', line):
                        self._emit_status("이미 로그인된 상태")
                        return True
            
            # 로그인 유형 감지 (우선순위 순서)
            login_patterns = {
                'ssh_standard': r'login as:',
                'password_only': r'[Pp]assword\s*:\s*',  # Password만 물어보는 케이스 (높은 우선순위)
                'tacacs_username': r'[Uu]sername\s*:\s*',
                'cisco_username': r'[Uu]ser\s*[Nn]ame\s*:\s*',
                'generic_username': r'[Ll]ogin\s*:\s*'
            }

            login_type = None
            for pattern_name, pattern in login_patterns.items():
                if re.search(pattern, initial_output, re.IGNORECASE):
                    login_type = pattern_name
                    self._log_debug(f"[LOGIN] 패턴 매칭: '{pattern_name}' - {pattern}")
                    break

            self._log_debug(f"[LOGIN] 감지된 로그인 유형: {login_type}")

            if login_type == 'ssh_standard':
                # 표준 SSH 로그인 (이미 연결 단계에서 처리됨)
                return True

            elif login_type == 'password_only':
                # Password만 물어보는 경우 (Username 입력 없이 바로 Password)
                self._emit_status("Password-only 로그인 감지")
                return self._handle_password_only_login(connection, connection_type, initial_output)

            elif login_type in ['tacacs_username', 'cisco_username', 'generic_username']:
                # TACACS+ 또는 장비 로그인 (Username + Password)
                return self._handle_tacacs_login(connection, connection_type, initial_output)

            else:
                # 알 수 없는 패턴 - 기본 처리
                self._log_debug("[LOGIN] 알 수 없는 로그인 패턴, 기본 처리")
                return self._handle_default_login(connection, connection_type)
                
        except Exception as e:
            self._log_debug(f"[LOGIN] 로그인 처리 실패: {e}")
            return False

    def _handle_password_only_login(self, connection, connection_type, initial_output):
        """
        Password만 물어보는 로그인 처리 (Username 프롬프트 없음)

        일부 장비는 Telnet 접속 시 Username 없이 바로 Password만 물어봅니다.
        예: "Password:" 또는 "password:"
        """
        try:
            self._log_debug(f"[PASSWORD_ONLY] 초기 출력: {repr(initial_output)}")

            # Password 프롬프트 확인
            password_patterns = [
                r'[Pp]assword\s*:',
                r'[Pp]ass\s*:',
                r'Password\s*for\s+\w+\s*:',
                r'Enter\s+password\s*:',
            ]

            password_found = False
            for pattern in password_patterns:
                if re.search(pattern, initial_output, re.IGNORECASE):
                    password_found = True
                    self._log_debug(f"[PASSWORD_ONLY] Password 프롬프트 발견: {pattern}")
                    break

            if not password_found:
                self._log_debug("[PASSWORD_ONLY] Password 프롬프트를 찾을 수 없음")
                return False

            # Password 입력
            self._emit_status("Password 입력 중 (Username 없음)...")

            if connection_type == "ssh":
                connection.send(f"{self.password}\n")
                time.sleep(3)
                login_result = self._read_until_prompt_ssh(connection, timeout=20)
            else:  # telnet
                connection.write(self.password.encode('ascii') + b"\n")
                time.sleep(3)
                login_result = self._read_until_prompt_telnet(connection, timeout=20)

            self._log_debug(f"[PASSWORD_ONLY] 로그인 결과: {repr(login_result)}")

            # 로그인 실패 확인
            failure_indicators = [
                'authentication failed', 'login incorrect', 'access denied',
                'invalid password', 'login failed', 'authentication error',
                'denied', 'refused', 'bad password', 'incorrect',
                '인증 실패', '로그인 실패', 'Authentication failure'
            ]

            login_result_lower = login_result.lower()
            for indicator in failure_indicators:
                if indicator in login_result_lower:
                    raise Exception(f"Password-only 인증 실패: {indicator}")

            # 로그인 성공 확인 (프롬프트 존재)
            lines = login_result.strip().split('\n')
            for line in lines:
                line = line.strip()
                if re.search(r'[#>]\s*$', line):
                    self._emit_status("Password-only 로그인 성공")
                    return True

            # 프롬프트가 없으면 추가 확인
            self._log_debug("[PASSWORD_ONLY] 프롬프트 재확인 시도")
            if connection_type == "ssh":
                connection.send("\n")
                time.sleep(1)
                final_check = self._read_until_prompt_ssh(connection, timeout=10)
            else:  # telnet
                connection.write(b"\n")
                time.sleep(1)
                final_check = self._read_until_prompt_telnet(connection, timeout=10)

            self._log_debug(f"[PASSWORD_ONLY] 최종 확인 결과: {repr(final_check)}")

            lines = final_check.strip().split('\n')
            for line in lines:
                line = line.strip()
                if re.search(r'[#>]\s*$', line):
                    self._emit_status("Password-only 로그인 성공 (재확인)")
                    return True

            raise Exception("로그인 후 올바른 프롬프트를 받지 못했습니다")

        except Exception as e:
            self._emit_status(f"Password-only 로그인 실패: {str(e)}")
            self._log_debug(f"[PASSWORD_ONLY] 상세 오류: {str(e)}")
            return False

    def _handle_tacacs_login(self, connection, connection_type, initial_output):
            """
            강화된 TACACS+ 로그인 처리
            """
            try:
                self._log_debug(f"[TACACS] 초기 출력 전체: {repr(initial_output)}")

                # Username 입력이 필요한지 확인
                username_needed = True

                # Username이 비어있거나 None인 경우 Password-only 모드로 전환
                if not self.username or self.username.strip() == "":
                    self._log_debug("[TACACS] Username이 비어있음 - Password-only 모드로 전환")
                    return self._handle_password_only_login(connection, connection_type, initial_output)

                if re.search(r'username\s*:\s*\w+', initial_output, re.IGNORECASE):
                    # 이미 username이 입력된 상태
                    username_needed = False
                    self._log_debug("[TACACS] Username이 이미 입력된 상태 감지")

                current_output = initial_output

                if username_needed:
                    # Username 프롬프트가 있다면 사용자명 입력
                    self._emit_status("사용자명 입력 중...")

                    if connection_type == "ssh":
                        connection.send(f"{self.username}\n")
                        time.sleep(2)  # 대기 시간 증가
                        username_response = self._read_until_prompt_ssh(connection, timeout=15)
                    else:
                        connection.write(self.username.encode('ascii') + b"\n")
                        time.sleep(2)  # 대기 시간 증가
                        username_response = self._read_until_prompt_telnet(connection, timeout=15)

                    current_output += username_response
                    self._log_debug(f"[TACACS] Username 입력 후 응답: {repr(username_response)}")
                
                # 강화된 Password 프롬프트 감지
                password_prompts = [
                    r'[Pp]assword\s*:',
                    r'[Pp]ass\s*:',
                    r'Password\s*for\s+\w+\s*:',
                    r'Enter\s+password\s*:',
                    r'User\s+Password\s*:',
                    r'\w+\s*password\s*:',
                    r'암호\s*:',
                    r'비밀번호\s*:'
                ]
                
                password_found = False
                max_attempts = 10  # 최대 시도 횟수 증가
                
                for attempt in range(max_attempts):
                    self._log_debug(f"[TACACS] Password 프롬프트 찾기 시도 {attempt + 1}/{max_attempts}")
                    self._log_debug(f"[TACACS] 현재 누적 출력: {repr(current_output[-200:])}")  # 마지막 200자만 표시
                    
                    # 현재 출력에서 password 프롬프트 찾기
                    for i, pattern in enumerate(password_prompts):
                        if re.search(pattern, current_output, re.IGNORECASE):
                            password_found = True
                            self._log_debug(f"[TACACS] Password 프롬프트 발견 (패턴 {i+1}): {pattern}")
                            break
                    
                    if password_found:
                        break
                    
                    # 추가 출력 읽기 - 더 긴 대기 시간
                    time.sleep(1.0)  # 1초 대기
                    if connection_type == "ssh":
                        additional_output = self._read_until_prompt_ssh(connection, timeout=5)
                    else:
                        additional_output = self._read_until_prompt_telnet(connection, timeout=5)
                    
                    if additional_output:
                        current_output += additional_output
                        self._log_debug(f"[TACACS] 추가 출력 {attempt+1}: {repr(additional_output)}")
                    else:
                        self._log_debug(f"[TACACS] 추가 출력 없음 {attempt+1}")
                    
                    # 혹시 이미 로그인된 상태인지 확인
                    lines = current_output.strip().split('\n')
                    for line in lines[-3:]:  # 마지막 3줄 확인
                        line = line.strip()
                        if re.search(r'[#>]\s*$', line):
                            self._emit_status("Password 없이 로그인 완료")
                            return True
                
                if not password_found:
                    # 마지막 시도: 강제로 password 입력해보기
                    self._log_debug("[TACACS] Password 프롬프트 감지 실패, 강제 입력 시도")
                    self._emit_status("Password 프롬프트 감지 실패, 강제 입력 시도...")
                    
                    if connection_type == "ssh":
                        connection.send(f"{self.password}\n")
                        time.sleep(3)
                        login_result = self._read_until_prompt_ssh(connection, timeout=15)
                    else:
                        connection.write(self.password.encode('ascii') + b"\n")
                        time.sleep(3)
                        login_result = self._read_until_prompt_telnet(connection, timeout=15)
                    
                    self._log_debug(f"[TACACS] 강제 입력 후 결과: {repr(login_result)}")
                    
                    # 강제 입력 후 성공 여부 확인
                    lines = login_result.strip().split('\n')
                    for line in lines:
                        line = line.strip()
                        if re.search(r'[#>]\s*$', line):
                            self._emit_status("강제 Password 입력으로 로그인 성공")
                            return True
                    
                    raise Exception("Password 프롬프트를 찾을 수 없습니다")
                
                # Password 입력
                self._emit_status("패스워드 입력 중...")
                
                if connection_type == "ssh":
                    connection.send(f"{self.password}\n")
                    time.sleep(3)  # 대기 시간 증가
                    login_result = self._read_until_prompt_ssh(connection, timeout=20)
                else:
                    connection.write(self.password.encode('ascii') + b"\n")
                    time.sleep(3)  # 대기 시간 증가
                    login_result = self._read_until_prompt_telnet(connection, timeout=20)
                
                self._log_debug(f"[TACACS] 로그인 결과: {repr(login_result)}")
                
                # 로그인 성공 여부 확인
                failure_indicators = [
                    'authentication failed', 'login incorrect', 'access denied',
                    'invalid username', 'invalid password', 'login failed',
                    'authentication error', 'denied', 'refused', 'bad password',
                    'incorrect', 'invalid', '인증 실패', '로그인 실패'
                ]
                
                login_result_lower = login_result.lower()
                for indicator in failure_indicators:
                    if indicator in login_result_lower:
                        raise Exception(f"TACACS+ 인증 실패: {indicator}")
                
                # 성공적인 로그인 확인 (프롬프트 존재)
                lines = login_result.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if re.search(r'[#>]\s*$', line):
                        self._emit_status("TACACS+ 로그인 성공")
                        return True
                
                # 프롬프트가 없으면 추가로 한 번 더 확인
                self._log_debug("[TACACS] 프롬프트 재확인 시도")
                if connection_type == "ssh":
                    connection.send("\n")
                    time.sleep(1)
                    final_check = self._read_until_prompt_ssh(connection, timeout=10)
                else:
                    connection.write(b"\n")
                    time.sleep(1)
                    final_check = self._read_until_prompt_telnet(connection, timeout=10)
                
                self._log_debug(f"[TACACS] 최종 확인 결과: {repr(final_check)}")
                
                lines = final_check.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if re.search(r'[#>]\s*$', line):
                        self._emit_status("TACACS+ 로그인 성공 (재확인)")
                        return True
                
                raise Exception("로그인 후 올바른 프롬프트를 받지 못했습니다")
                    
            except Exception as e:
                self._emit_status(f"TACACS+ 로그인 실패: {str(e)}")
                self._log_debug(f"[TACACS] 상세 오류: {str(e)}")
                return False

    def _handle_default_login(self, connection, connection_type):
        """
        기본 로그인 처리
        """
        try:
            # 간단한 Enter 입력으로 프롬프트 확인
            if connection_type == "ssh":
                connection.send("\n")
                time.sleep(1)
                response = self._read_until_prompt_ssh(connection, timeout=5)
            else:
                connection.write(b"\n")
                time.sleep(1) 
                response = self._read_until_prompt_telnet(connection, timeout=5)
            
            # 프롬프트가 있으면 이미 로그인된 상태
            lines = response.strip().split('\n')
            for line in lines:
                line = line.strip()
                if re.search(r'[#>]\s*$', line):
                    self._emit_status("이미 로그인된 상태")
                    return True
            
            return False
            
        except Exception as e:
            self._log_debug(f"[LOGIN] 기본 로그인 처리 실패: {e}")
            return False

    def connect_via_ssh(self):
        ssh = None
        shell = None
        output_data = {}
        hostname = None
        try:
            self._emit_status("SSH 연결 시도 중...")
            
            # paramiko 초기화 재확인 (이 2줄을 추가하세요)
            ensure_paramiko_initialized()
            
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # TACACS+ 환경을 고려한 연결 시도
            # 연결 설정 개선
            connect_kwargs = {
                'hostname': self.ip,
                'port': self.ssh_port,
                'username': self.username,
                'password': self.password,
                'timeout': 15,  # 타임아웃 증가
                'banner_timeout': 10,  # 배너 타임아웃 증가
                'auth_timeout': 10,  # 인증 타임아웃 증가
                'compress': True,
                'look_for_keys': False,
                'allow_agent': False,
                'sock': None,  # 소켓 명시적 설정
                'gss_auth': False,  # GSS 인증 비활성화
                'gss_kex': False,   # GSS 키 교환 비활성화
                'disabled_algorithms': {},  # 알고리즘 제한 없음
            }

            # TACACS+ 환경을 고려한 연결 시도
            auth_success = False
            try:
                # 1단계: 기본 인증 시도
                self._emit_status("SSH 기본 인증 시도 중...")
                ssh.connect(**connect_kwargs)
                self._emit_status("SSH 기본 인증 성공")
                auth_success = True
                
            except paramiko.AuthenticationException:
                self._emit_status("기본 인증 실패, TACACS+ 수동 인증 시도...")
                try:
                    # 2단계: 인증 정보 없이 연결 시도
                    ssh.connect(
                        self.ip, 
                        port=self.ssh_port, 
                        timeout=10,
                        banner_timeout=10,
                        look_for_keys=False,
                        allow_agent=False
                    )
                    self._emit_status("SSH 연결 성공 (수동 인증 필요)")
                    auth_success = False  # 수동 인증 필요
                    
                except Exception as e2:
                    raise Exception(f"SSH 연결 완전 실패: {e2}")
                    
            except Exception as e:
                raise Exception(f"SSH 연결 실패: {e}")
            
            # 셸 세션 생성
            self._emit_status("셸 세션 생성 중...")
            shell = ssh.invoke_shell(term='vt100', width=80, height=24)
            
            # 인증이 필요한 경우 향상된 로그인 핸들러 사용
            if not auth_success:
                login_success = self.enhanced_login_handler(shell, "ssh")
                if not login_success:
                    raise Exception("SSH 인증 실패")
            else:
                # 기본 인증 성공 시에도 프롬프트 확인
                time.sleep(2)
                initial_output = self._read_until_prompt_ssh(shell, timeout=10)
                self._log_debug(f"[SSH] 초기 프롬프트: {repr(initial_output)}")
            
            # Enable 모드 진입
            if self.enable_password is not None:
                self._emit_status("Enable 모드 진입 중...")
                # 현재 상태 확인
                shell.send("\n")
                time.sleep(0.5)
                current_output = self._read_until_prompt_ssh(shell, timeout=5)
                
                if not self._is_enable_mode(current_output):
                    shell.send("enable\n")
                    time.sleep(1)
                    enable_output = self._read_until_prompt_ssh(shell, timeout=10)
                    
                    if "Password" in enable_output or "password" in enable_output:
                        if self.enable_password:
                            shell.send(f"{self.enable_password}\n")
                        else:
                            shell.send("\n")
                        time.sleep(1)
                        result = self._read_until_prompt_ssh(shell, timeout=10)
                        
                        if not self._is_enable_mode(result):
                            raise Exception("Enable 모드 진입 실패")
                        self._emit_status("Enable 모드 진입 성공")
                    else:
                        self._emit_status("Enable 모드 이미 활성화됨")
                else:
                    self._emit_status("이미 Enable 모드")
            
            # 터미널 설정
            self._emit_status("터미널 설정 중...")
            shell.send(f"{NetworkConfig.TERMINAL_LENGTH_CMD}\n")
            time.sleep(NetworkConfig.COMMAND_DELAY)
            shell.send(f"{NetworkConfig.TERMINAL_WIDTH_CMD}\n")
            time.sleep(NetworkConfig.COMMAND_DELAY)
            self._read_until_prompt_ssh(shell, timeout=5)
            
            # Hostname 추출
            self._emit_status("Hostname 추출 중...")
            hostname = self._extract_hostname_ssh(shell)
            self._log_debug(f"[SSH] 추출된 hostname: {hostname}")
            
            # 출력 파일 생성
            output_file_path = self.generate_output_filename(hostname, self.filename_format)
            self._create_output_file_header(output_file_path, "SSH", hostname)

            # 명령어 실행 (공통 메서드 사용)
            output_data = self._execute_commands_common(
                shell,
                "SSH",
                output_file_path,
                lambda conn: self._read_until_prompt_ssh(conn, timeout=30)
            )
            
        finally:
            if shell:
                try:
                    shell.close()
                except:
                    pass
            if ssh:
                try:
                    ssh.close()
                except:
                    pass
        
        return output_data

    def connect_via_telnet(self):
        output_data = {}
        hostname = None
        try:
            self._emit_status("Telnet 연결 시도 중...")
            with telnetlib.Telnet(self.ip, timeout=10) as tn:
                self._emit_status("Telnet 연결 성공")
                
                # 향상된 로그인 핸들러 사용
                login_success = self.enhanced_login_handler(tn, "telnet")
                if not login_success:
                    raise Exception("Telnet 로그인 실패")
                
                # 현재 출력 읽기
                time.sleep(1)
                initial_output = self._read_until_prompt_telnet(tn, timeout=5)
                
                # Enable 모드 진입
                if self.enable_password is not None:
                    self._emit_status("Enable 모드 진입 중...")
                    if not self._is_enable_mode(initial_output):
                        tn.write(b"enable\n")
                        time.sleep(1)
                        enable_output = tn.read_until(b":", timeout=5)
                        
                        if b"Password" in enable_output or b"password" in enable_output:
                            if self.enable_password:
                                tn.write(self.enable_password.encode('ascii') + b"\n")
                            else:
                                tn.write(b"\n")
                            time.sleep(1)
                            result = self._read_until_prompt_telnet(tn, timeout=10)
                            
                            if not self._is_enable_mode(result):
                                raise Exception("Enable 모드 진입 실패")
                            self._emit_status("Enable 모드 진입 성공")
                        else:
                            self._emit_status("Enable 모드 이미 활성화됨")
                    else:
                        self._emit_status("이미 Enable 모드")
                
                # 터미널 설정
                self._emit_status("터미널 설정 중...")
                tn.write(f"{NetworkConfig.TERMINAL_LENGTH_CMD}\n".encode('ascii'))
                time.sleep(NetworkConfig.COMMAND_DELAY)
                tn.write(f"{NetworkConfig.TERMINAL_WIDTH_CMD}\n".encode('ascii'))
                time.sleep(NetworkConfig.COMMAND_DELAY)
                self._read_until_prompt_telnet(tn, timeout=5)
                
                # Hostname 추출
                self._emit_status("Hostname 추출 중...")
                hostname = self._extract_hostname_telnet(tn)
                self._log_debug(f"[TELNET] 추출된 hostname: {hostname}")
                
                # 출력 파일 생성
                output_file_path = self.generate_output_filename(hostname, self.filename_format)
                self._create_output_file_header(output_file_path, "Telnet", hostname)

                # 명령어 실행 (공통 메서드 사용)
                output_data = self._execute_commands_common(
                    tn,
                    "Telnet",
                    output_file_path,
                    lambda conn: self._read_until_prompt_telnet(conn, timeout=30)
                )
                
        except socket.timeout:
            raise Exception("Telnet 연결 시간 초과")
        except Exception as e:
            raise Exception(f"Telnet 연결 실패: {e}")
        
        return output_data

    def _extract_hostname_ssh(self, shell):
        """SSH에서 hostname 추출 (개선된 방법)"""
        hostname = None
        
        # 방법 1: show running-config | include hostname (가장 확실한 방법)
        try:
            self._log_debug("[HOSTNAME] show running-config 시도")
            shell.send("show running-config | include hostname\n")
            time.sleep(2)
            running_output = self._read_until_prompt_ssh(shell, timeout=15)
            self._log_debug(f"[HOSTNAME] running-config 출력: {repr(running_output)}")
            
            for line in running_output.split('\n'):
                line = line.strip()
                if line.lower().startswith('hostname '):
                    parts = line.split()
                    if len(parts) >= 2:
                        hostname = parts[1]
                        if self._is_valid_hostname(hostname):
                            self._log_debug(f"[HOSTNAME] running-config에서 추출 성공: {hostname}")
                            return hostname
        except Exception as e:
            self._log_debug(f"[HOSTNAME] running-config 방법 실패: {e}")
        
        # 방법 2: show hostname 명령어 시도
        try:
            self._log_debug("[HOSTNAME] show hostname 시도")
            shell.send("show hostname\n")
            time.sleep(1)
            hostname_output = self._read_until_prompt_ssh(shell, timeout=10)
            self._log_debug(f"[HOSTNAME] show hostname 출력: {repr(hostname_output)}")
            
            for line in hostname_output.split('\n'):
                line = line.strip()
                if (line and not 'show hostname' in line.lower() and 
                    not line.endswith('#') and not line.endswith('>') and
                    self._is_valid_hostname(line)):
                    self._log_debug(f"[HOSTNAME] show hostname에서 추출 성공: {line}")
                    return line
        except Exception as e:
            self._log_debug(f"[HOSTNAME] show hostname 방법 실패: {e}")
        
        # 방법 3: 프롬프트에서 추출
        try:
            self._log_debug("[HOSTNAME] 프롬프트에서 추출 시도")
            shell.send("\n")
            time.sleep(0.5)
            prompt_output = self._read_until_prompt_ssh(shell, timeout=5)
            hostname = self._extract_hostname_from_prompt(prompt_output)
            if hostname:
                self._log_debug(f"[HOSTNAME] 프롬프트에서 추출 성공: {hostname}")
                return hostname
        except Exception as e:
            self._log_debug(f"[HOSTNAME] 프롬프트 방법 실패: {e}")
        
        self._log_debug("[HOSTNAME] 모든 방법 실패")
        return None

    def _extract_hostname_telnet(self, tn):
        """Telnet에서 hostname 추출"""
        hostname = None
        
        # 방법 1: show running-config | include hostname
        try:
            self._log_debug("[HOSTNAME] Telnet - show running-config 시도")
            tn.write(b"show running-config | include hostname\n")
            time.sleep(2)
            running_output = self._read_until_prompt_telnet(tn, timeout=15)
            self._log_debug(f"[HOSTNAME] running-config 출력: {repr(running_output)}")
            
            for line in running_output.split('\n'):
                line = line.strip()
                if line.lower().startswith('hostname '):
                    parts = line.split()
                    if len(parts) >= 2:
                        hostname = parts[1]
                        if self._is_valid_hostname(hostname):
                            self._log_debug(f"[HOSTNAME] running-config에서 추출 성공: {hostname}")
                            return hostname
        except Exception as e:
            self._log_debug(f"[HOSTNAME] running-config 방법 실패: {e}")
        
        # 방법 2: show hostname 명령어 시도
        try:
            self._log_debug("[HOSTNAME] Telnet - show hostname 시도")
            tn.write(b"show hostname\n")
            time.sleep(1)
            hostname_output = self._read_until_prompt_telnet(tn, timeout=10)
            self._log_debug(f"[HOSTNAME] show hostname 출력: {repr(hostname_output)}")
            
            for line in hostname_output.split('\n'):
                line = line.strip()
                if (line and not 'show hostname' in line.lower() and 
                    not line.endswith('#') and not line.endswith('>') and
                    self._is_valid_hostname(line)):
                    self._log_debug(f"[HOSTNAME] show hostname에서 추출 성공: {line}")
                    return line
        except Exception as e:
            self._log_debug(f"[HOSTNAME] show hostname 방법 실패: {e}")
        
        # 방법 3: 프롬프트에서 추출
        try:
            self._log_debug("[HOSTNAME] Telnet - 프롬프트에서 추출 시도")
            tn.write(b"\n")
            time.sleep(0.5)
            prompt_output = self._read_until_prompt_telnet(tn, timeout=5)
            hostname = self._extract_hostname_from_prompt(prompt_output)
            if hostname:
                self._log_debug(f"[HOSTNAME] 프롬프트에서 추출 성공: {hostname}")
                return hostname
        except Exception as e:
            self._log_debug(f"[HOSTNAME] 프롬프트 방법 실패: {e}")
        
        self._log_debug("[HOSTNAME] 모든 방법 실패")
        return None

    def _extract_hostname_from_prompt(self, prompt_text):
        """프롬프트에서 hostname 추출"""
        if not prompt_text:
            return None
        
        lines = prompt_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 프롬프트 패턴 매칭
            patterns = [
                r'^([a-zA-Z][a-zA-Z0-9\-_\.]{1,62})[#>]\s*$',
                r'^([a-zA-Z][a-zA-Z0-9\-_\.]{1,62})\([^)]+\)[#>]\s*$',
                r'([a-zA-Z][a-zA-Z0-9\-_\.]{1,62})[#>]$'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, line)
                if match:
                    hostname = match.group(1)
                    if self._is_valid_hostname(hostname):
                        return hostname
        
        return None

    def _is_valid_hostname(self, hostname):
        """hostname 유효성 검사"""
        if not hostname or len(hostname) < 2 or len(hostname) > 63:
            return False
        
        if hostname.isdigit():
            return False
        
        # 너무 일반적인 기본값들만 제외 (CISCO는 실제 장비명이므로 허용)
        invalid_names = {
            'switch', 'router', 'device', 'host', 'localhost',
            'console', 'admin', 'user', 'guest', 'default', 'test', 'demo'
        }
        
        if hostname.lower() in invalid_names:
            return False
        
        # 유효한 문자만 포함
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9\-_\.]*$', hostname):
            return False
        
        return True

    def _is_enable_mode(self, output):
        """Enable 모드 여부 확인"""
        lines = output.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line.endswith('#'):
                return True
        return False

    def _read_until_prompt_ssh(self, shell, timeout=10):
        """SSH 프롬프트까지 읽기"""
        buffer = ""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if shell.recv_ready():
                try:
                    chunk = shell.recv(8192).decode("utf-8", errors="replace")
                    if chunk:
                        buffer += chunk
                        
                        # 프롬프트 감지
                        lines = buffer.split('\n')
                        for line in lines[-3:]:
                            line = line.strip()
                            if line.endswith('#') or line.endswith('>'):
                                return buffer
                except Exception:
                    break
            time.sleep(0.1)
        
        return buffer

    def _read_until_prompt_telnet(self, tn, timeout=10):
        """향상된 Telnet 프롬프트까지 읽기"""
        buffer = ""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                if tn.sock_avail():
                    data = tn.read_very_eager().decode('ascii', errors="replace")
                    if data:
                        buffer += data
                        self._log_debug(f"[TELNET_READ] 수신 데이터: {repr(data)}")
                    
                    # 다양한 프롬프트 패턴 확인
                    prompt_patterns = [
                        r'[#>]\s*$',
                        r'[#>]\s*\r?\n?$',
                        r'\w+[#>]\s*$',
                        r'[Pp]assword\s*:\s*$',
                        r'[Uu]sername\s*:\s*$'
                    ]
                    
                    for pattern in prompt_patterns:
                        if re.search(pattern, buffer.strip(), re.MULTILINE):
                            self._log_debug(f"[TELNET_READ] 프롬프트 패턴 감지: {pattern}")
                            return buffer
                    
                    # 특정 문자열로 끝나는 경우도 확인
                    stripped = buffer.strip()
                    if stripped.endswith(('>', '#', ':', 'Password:', 'Username:')):
                        return buffer
                        
            except Exception as e:
                self._log_debug(f"[TELNET_READ] 읽기 오류: {e}")
                pass
            time.sleep(0.1)
        
        self._log_debug(f"[TELNET_READ] 타임아웃, 버퍼 내용: {repr(buffer)}")
        return buffer

    def _create_output_file_header(self, output_file_path, connection_type, hostname):
        """출력 파일 헤더 생성 (공통 메서드)"""
        with open(output_file_path, "w", encoding="utf-8") as output_file:
            output_file.write(f"--- {connection_type} 연결 결과: {self.ip} ---\n")
            if hostname:
                output_file.write(f"장비 Hostname: {hostname}\n")
            output_file.write(f"실행 시간: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            output_file.write(f"{'=' * 50}\n\n")

    def _execute_commands_common(self, connection, connection_type, output_file_path, read_func):
        """명령어 실행 공통 로직 (SSH/Telnet 통합)

        Args:
            connection: SSH shell 또는 Telnet 연결 객체
            connection_type: "SSH" 또는 "Telnet"
            output_file_path: 출력 파일 경로
            read_func: 출력 읽기 함수 (lambda)

        Returns:
            dict: 각 명령어별 출력 데이터
        """
        output_data = {}
        total_commands = len(self.commands)

        for idx, command in enumerate(self.commands, 1):
            if self.is_stopped():
                break

            try:
                self._emit_status(f"명령어 실행 중 ({idx}/{total_commands}): {command}")

                # 명령어 전송 (SSH/Telnet에 따라 다름)
                if connection_type == "SSH":
                    connection.send(f"{command}\n")
                else:  # Telnet
                    connection.write(command.encode('ascii') + b"\n")

                time.sleep(0.5)
                output = read_func(connection)
                cleaned_output = self._clean_output(output, command)

                # 결과 파일에 기록
                with open(output_file_path, "a", encoding="utf-8") as output_file:
                    output_file.write(f"Command: {command}\n{cleaned_output}\n{'-' * 50}\n\n")

                self._emit_status(f"명령어 완료 ({idx}/{total_commands}): {command}")
                output_data[command] = cleaned_output

            except Exception as e:
                error_msg = f"명령어 '{command}' 실행 중 오류: {e}"
                self._emit_status(error_msg)

                with open(output_file_path, "a", encoding="utf-8") as output_file:
                    output_file.write(f"Command: {command}\nERROR: {error_msg}\n{'-' * 50}\n\n")

                output_data[command] = f"ERROR: {error_msg}"

        self._emit_status("모든 명령어 실행 완료")
        return output_data

    def generate_output_filename(self, hostname=None, filename_format="hostname_only"):
        """출력 파일명 생성"""
        ip_part = self.ip.replace('.', '_')
        
        def safe_filename(name):
            return re.sub(r'[<>:"/\\|?*]', '_', name)
        
        if filename_format == "ip_only":
            filename = f"{ip_part}.txt"
        elif filename_format == "hostname_only":
            if hostname:
                safe_hostname = safe_filename(hostname)
                filename = f"{safe_hostname}.txt"
            else:
                filename = f"{ip_part}.txt"
        elif filename_format == "ip_hostname":
            if hostname:
                safe_hostname = safe_filename(hostname)
                filename = f"{ip_part}_{safe_hostname}.txt"
            else:
                filename = f"{ip_part}.txt"
        elif filename_format == "hostname_ip":
            if hostname:
                safe_hostname = safe_filename(hostname)
                filename = f"{safe_hostname}_{ip_part}.txt"
            else:
                filename = f"{ip_part}.txt"
        else:
            filename = f"{ip_part}.txt"
        
        return os.path.join(self.save_path, filename)

    def _clean_output(self, output, command):
        """출력 텍스트 정리"""
        lines = output.splitlines()
        clean_lines = []
        command_found = False
        
        for line in lines:
            if not line.strip():
                continue
            
            if not command_found and command in line:
                command_found = True
                continue
            
            if line.strip().endswith(">") or line.strip().endswith("#"):
                continue
            
            clean_lines.append(line)
        
        return "\n".join(line.rstrip() for line in clean_lines)




class WorkflowEngine(QThread):
    # 워크플로우 진행 상태 시그널 (현재 단계, 총 단계, 메시지)
    workflow_progress = pyqtSignal(int, int, str)
    # 워크플로우 특정 단계 결과 시그널 (단계 인덱스, 성공여부, 결과 메시지/데이터)
    step_result = pyqtSignal(int, bool, object)
    # 워크플로우 전체 완료 시그널
    workflow_finished = pyqtSignal()
    # 워크플로우 오류 발생 시그널
    workflow_error = pyqtSignal(str)

    def __init__(self, workflow_steps, main_app_ref=None):
        super().__init__()
        self.workflow_steps = workflow_steps
        self.main_app = main_app_ref # MainWindow 참조 (필요시)
        self._is_running = True

    def stop(self):
        self._is_running = False
        logging.info("[WORKFLOW_ENGINE] 워크플로우 실행 중지 요청됨.")
        # TODO: 현재 실행 중인 하위 작업(NetworkWorker 등)도 중지시키는 로직 필요

    def run(self):
        total_steps = len(self.workflow_steps)
        logging.info(f"[WORKFLOW_ENGINE] 워크플로우 실행 시작. 총 {total_steps} 단계.")

        for i, step in enumerate(self.workflow_steps):
            if not self._is_running:
                self.workflow_error.emit(self.tr("워크플로우 실행이 사용자에 의해 중지되었습니다."))
                return

            current_step_num = i + 1
            step_type = step.get("type")
            step_name = step.get("name", f"단계 {current_step_num}")
            params = step.get("params", {})

            self.workflow_progress.emit(current_step_num, total_steps, f"'{step_name}' ({step_type}) 실행 시작...")
            logging.info(f"[WORKFLOW_ENGINE] 단계 {current_step_num}/{total_steps}: '{step_name}' ({step_type}) 실행")

            success = False
            result_data = None

            try:
                # === 각 액션 타입별 실행 로직 ===
                # 이 부분은 각 기능 모듈과 연동하여 실제 작업을 수행해야 합니다.
                # 예를 들어, NetworkTab의 명령어 실행 기능을 호출하거나,
                # MonitoringTab의 Ping 기능을 직접 호출하는 방식이 될 수 있습니다.
                # 또는, 각 기능에 대한 독립적인 실행 함수/클래스를 만들고 여기서 호출합니다.

                if step_type == self.tr("명령어 실행"):
                    # 예시: NetworkWorker를 사용하는 방식 (실제로는 더 정교한 연동 필요)
                    # 필요한 파라미터: ips, username, password, enable_password, use_ssh, commands, ssh_port
                    # 이 정보들은 self.main_app.network_tab 등에서 가져오거나, 워크플로우 단계에 저장되어 있어야 함.
                    logging.info(f"[WORKFLOW_ENGINE] '{step_name}': 명령어 실행 파라미터: {params}")
                    # target_ips = params.get("ips", "").split(',')
                    # commands_to_run = params.get("commands", "").splitlines()
                    # if not target_ips or not commands_to_run:
                    #    raise ValueError("명령어 실행 단계에 필요한 IP 또는 명령어가 없습니다.")
                    
                    # 여기에 NetworkWorker를 생성하고 실행하는 로직...
                    # worker = NetworkWorker(...)
                    # worker.task_completed.connect(...)
                    # worker.error_occurred.connect(...)
                    # worker.start()
                    # worker.wait() # 동기 실행 예시, 실제로는 비동기 처리 및 결과 수집 필요

                    # 임시 성공 처리
                    success = True
                    result_data = f"'{step_name}' 명령어 실행 완료 (가상)"
                    time.sleep(1) # 가상 작업 시간


                elif step_type == self.tr("Ping 테스트"):
                    logging.info(f"[WORKFLOW_ENGINE] '{step_name}': Ping 테스트 파라미터: {params}")
                    # ping_ips = params.get("ping_ips", "").split(',')
                    # ping_count = int(params.get("ping_count", "4"))
                    # 여기에 PingThread 또는 유사 로직 실행...

                    success = True
                    result_data = f"'{step_name}' Ping 테스트 완료 (가상)"
                    time.sleep(0.5)


                # ... 다른 액션 타입들에 대한 처리 ...

                else:
                    logging.warning(f"[WORKFLOW_ENGINE] 알 수 없는 액션 타입: {step_type}")
                    result_data = f"알 수 없는 액션 타입: {step_type}"
                    success = False
                
                self.step_result.emit(i, success, result_data)
                if not success:
                    # 단계 실패 시 워크플로우 중단 또는 다음 단계 진행 여부 결정 로직 추가 가능
                    self.workflow_error.emit(f"'{step_name}' 단계 실행 실패: {result_data}")
                    return # 예시로 바로 중단

            except Exception as e:
                error_msg = f"'{step_name}' 단계 실행 중 오류 발생: {str(e)}"
                logging.error(f"[WORKFLOW_ENGINE] {error_msg}", exc_info=True)
                self.step_result.emit(i, False, error_msg)
                self.workflow_error.emit(error_msg)
                return # 오류 발생 시 워크플로우 중단

            self.workflow_progress.emit(current_step_num, total_steps, f"'{step_name}' 실행 완료.")
            time.sleep(0.1) # 각 단계 후 짧은 딜레이

        if self._is_running: # 중지되지 않고 모든 단계를 마쳤다면
            logging.info("[WORKFLOW_ENGINE] 워크플로우 모든 단계 실행 완료.")
            self.workflow_finished.emit()

    def tr(self, text): # 간단한 번역 함수 (실제로는 main_app의 translator 사용 권장)
        if self.main_app and hasattr(self.main_app, 'translate'):
            return self.main_app.translate(text)
        return text


class BulkNetworkManager:
    def __init__(self, max_workers=10, progress_callback=None, error_callback=None):
        """
        대량 장비 관리를 위한 매니저
        
        Args:
            max_workers (int): 최대 동시 작업 스레드 수
            progress_callback: 진행 상황 콜백 함수
            error_callback: 오류 발생 시 콜백 함수
        """
        self.max_workers = max_workers
        self.progress_callback = progress_callback
        self.error_callback = error_callback
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.results = {}
        self._stop_flag = False
        self._result_queue = queue.Queue()
    
    def stop(self):
        """작업 중지 요청"""
        self._stop_flag = True
    
    def execute_device(self, ip, username, password, enable_password, use_ssh, save_path, commands, ssh_port=22):
        """단일 장비에 대한 작업 실행"""
        if self._stop_flag:
            return {"status": "stopped", "message": "작업이 중지되었습니다."}
        
        try:
            # 기존 NetworkWorker 클래스 사용
            worker = NetworkWorker(
                ip, username, password, enable_password, use_ssh, save_path, commands, ssh_port
            )
            
            # telnet 또는 ssh 연결 실행
            if use_ssh:
                result = worker.connect_via_ssh()
            else:
                result = worker.connect_via_telnet()
            
            # 결과 반환
            return {"status": "success", "data": result}
        except Exception as e:
            error_msg = f"장비 {ip} 연결 실패: {str(e)}"
            logging.error(error_msg)
            return {"status": "error", "message": error_msg}
    
    def process_devices(self, devices_config, save_path):
        """여러 장비 연결 작업 실행
        
        Args:
            devices_config: 장비 정보 리스트
            save_path: 결과 저장 경로
            
        Returns:
            dict: 각 IP에 대한 실행 결과
        """
        futures = []
        self.results = {}
        self._stop_flag = False
        
        # 각 장비마다 작업 제출
        for device in devices_config:
            if self._stop_flag:
                break
                
            future = self.executor.submit(
                self.execute_device,
                device['ip'],
                device['username'],
                device['password'],
                device.get('enable_password', ''),
                device.get('use_ssh', True),
                save_path,
                device['commands'],
                device.get('ssh_port', 22)
            )
            futures.append((device['ip'], future))
        
        # 결과 수집 (완료되는 대로)
        for ip, future in futures:
            if self._stop_flag:
                break
                
            try:
                result = future.result(timeout=120)  # 2분 타임아웃 설정
                self.results[ip] = result
                
                # 진행 상황 콜백 호출
                if self.progress_callback:
                    self.progress_callback(ip, result)
                    
            except Exception as e:
                error_msg = f"장비 {ip} 작업 실패: {str(e)}"
                self.results[ip] = {"status": "error", "message": error_msg}
                
                # 오류 콜백 호출
                if self.error_callback:
                    self.error_callback(ip, str(e))
        
        return self.results
    
    def process_devices_sequential(self, devices_config, save_path):
        """장비를 순차적으로 처리 (배치 방식)
        
        큰 규모의 장비를 배치(batch)로 나누어 순차 처리
        """
        self.results = {}
        self._stop_flag = False
        batch_size = self.max_workers  # 배치 크기는 동시 작업 수와 동일하게 설정
        
        # 장비를 배치로 나누기
        device_batches = [devices_config[i:i+batch_size] for i in range(0, len(devices_config), batch_size)]
        
        for batch_idx, batch in enumerate(device_batches):
            if self._stop_flag:
                break
                
            logging.info(f"배치 {batch_idx+1}/{len(device_batches)} 처리 중 ({len(batch)} 장비)")
            
            # 현재 배치에 대한 작업 제출
            futures = []
            for device in batch:
                future = self.executor.submit(
                    self.execute_device,
                    device['ip'],
                    device['username'],
                    device['password'],
                    device.get('enable_password', ''),
                    device.get('use_ssh', True),
                    save_path,
                    device['commands'],
                    device.get('ssh_port', 22)
                )
                futures.append((device['ip'], future))
            
            # 현재 배치 결과 수집
            for ip, future in futures:
                if self._stop_flag:
                    break
                    
                try:
                    result = future.result(timeout=120)
                    self.results[ip] = result
                    
                    # 진행 상황 콜백 호출
                    if self.progress_callback:
                        self.progress_callback(ip, result)
                        
                except Exception as e:
                    error_msg = f"장비 {ip} 작업 실패: {str(e)}"
                    self.results[ip] = {"status": "error", "message": error_msg}
                    
                    # 오류 콜백 호출
                    if self.error_callback:
                        self.error_callback(ip, str(e))
        
        return self.results
    
    def shutdown(self):
        """리소스 정리 (스레드 풀 종료)"""
        self.executor.shutdown(wait=False)






class PingThread(QThread):
    result_ready = pyqtSignal(str, str, str)  # IP, 결과, 색상
    
    def __init__(self, ip_list, interval, timeout, repeat, packet_size, check_tcp):
        super().__init__()
        self.ip_list = ip_list
        self.interval = interval
        self.timeout = timeout
        self.repeat = repeat
        self.packet_size = packet_size
        self.check_tcp = check_tcp
        self._stop_flag = False
        self._mutex = QMutex()
    
    def stop(self):
        """스레드 중지 요청"""
        self._mutex.lock()
        self._stop_flag = True
        self._mutex.unlock()
    
    def is_stopped(self):
        """스레드 중지 여부 확인"""
        self._mutex.lock()
        flag = self._stop_flag
        self._mutex.unlock()
        return flag
    
    def run(self):
        count = 0
        # 무제한이거나 지정된 횟수만큼 반복
        while (self.repeat == 0 or count < self.repeat) and not self.is_stopped():
            for ip in self.ip_list:
                if self.is_stopped():
                    return
                
                # Ping 수행
                ping_result = self.ping(ip, self.timeout, self.packet_size)
                
                # LED 상태 결정: Ping 성공이면 green, 실패면 red
                led_status = "green" if "성공" in ping_result else "red"
                self.result_ready.emit(ip, ping_result, led_status)
                
                # TCP 체크 옵션이 선택되고 Ping이 성공인 경우, 포트 22와 23 상태 확인
                if self.check_tcp and "성공" in ping_result:
                    port22 = self.check_tcp_port(ip, 22, timeout=0.5)
                    self.result_ready.emit(ip, f"Port 22: {'Open' if port22 else 'Closed'}", 'green' if port22 else 'red')
                    
                    port23 = self.check_tcp_port(ip, 23, timeout=0.5)
                    self.result_ready.emit(ip, f"Port 23: {'Open' if port23 else 'Closed'}", 'green' if port23 else 'red')
            
            # 마지막 반복이 아니라면 간격만큼 대기
            if self.repeat == 0 or count < self.repeat - 1:
                for i in range(self.interval):
                    if self.is_stopped():
                        return
                    time.sleep(1)
            
            count += 1
            if self.repeat > 0:
                self.result_ready.emit("", f"반복 {count}/{self.repeat} 완료", "blue")
            else:
                self.result_ready.emit("", f"반복 {count} 완료", "blue")
    
    def ping(self, ip, timeout, packet_size):
        """Ping을 수행하여 응답 여부를 확인"""
        try:
            if sys.platform == "win32":
                # Windows
                ping_params = ["-n", "1", "-w", str(timeout * 1000), "-l", str(packet_size)]
                command = ["ping"] + ping_params + [ip]
                
                # Windows에서는 창이 보이지 않도록 creationflags 추가
                result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                    text=True, timeout=timeout+1, 
                                    creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                # Linux/Mac
                ping_params = ["-c", "1", "-W", str(timeout), "-s", str(packet_size)]
                command = ["ping"] + ping_params + [ip]
                
                # Linux/Mac에서는 일반적인 방식으로 실행
                result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                    text=True, timeout=timeout+1)
            
            # 한국어 Windows에서는 '의 응답:' 문자열이 있으면 성공
            if result.returncode == 0 and "의 응답:" in result.stdout:
                # TTL 추출
                ttl_match = re.search(r"TTL=(\d+)", result.stdout, re.IGNORECASE)
                ttl = ttl_match.group(1) if ttl_match else "N/A"
                
                # 시간 추출
                time_match = re.search(r"시간=(\d+)ms", result.stdout, re.IGNORECASE)
                resp_time = time_match.group(1) if time_match else "N/A"
                
                # TTL과 시간이 모두 추출되었을 때만 성공으로 처리
                if ttl != "N/A" and resp_time != "N/A":
                    return f"Ping 성공 (TTL={ttl}, Time={resp_time}ms)"
                else:
                    return "Ping 실패 (응답 데이터 불완전)"
            else:
                return "Ping 실패"
        except subprocess.TimeoutExpired:
            return "Ping 실패 (Timeout)"
        except Exception as e:
            return f"Ping 실패: {str(e)}"
    
    def check_tcp_port(self, ip, port, timeout=0.5):
        """TCP 포트가 열려 있는지 확인"""
        try:
            with socket.create_connection((ip, port), timeout):
                return True
        except Exception:
            return False


class TCPingThread(QThread):
    result_ready = pyqtSignal(str, int, str, str, object)  # 호스트, 포트, 결과, 색상, 응답시간(ms)
    
    def __init__(self, host, ports, interval, timeout, repeat):
        super().__init__()
        self.host = host
        self.ports = ports
        self.interval = interval
        self.timeout = timeout
        self.repeat = repeat
        self._stop_flag = False
        self._mutex = QMutex()
    
    def stop(self):
        """스레드 중지 요청"""
        self._mutex.lock()
        self._stop_flag = True
        self._mutex.unlock()
    
    def is_stopped(self):
        """스레드 중지 여부 확인"""
        self._mutex.lock()
        flag = self._stop_flag
        self._mutex.unlock()
        return flag
    
    def run(self):
        count = 0
        # 무제한이거나 지정된 횟수만큼 반복
        while (self.repeat == 0 or count < self.repeat) and not self.is_stopped():
            for port in self.ports:
                if self.is_stopped():
                    return
                
                # TCPing 수행
                is_open, response_time = self.check_tcp_port(self.host, port, self.timeout)
                
                # 결과 상태 결정: 포트 열림/닫힘
                if is_open:
                    status = "Open"
                    color = "green"
                    self.result_ready.emit(self.host, port, status, color, response_time)
                else:
                    status = "Closed or Filtered"
                    color = "red"
                    self.result_ready.emit(self.host, port, status, color, None)
            
            # 마지막 반복이 아니라면 간격만큼 대기
            if self.repeat == 0 or count < self.repeat - 1:
                for i in range(self.interval):
                    if self.is_stopped():
                        return
                    time.sleep(1)
            
            count += 1
            if self.repeat > 0:
                self.result_ready.emit(self.host, None, f"반복 {count}/{self.repeat} 완료", "blue", None)
            else:
                self.result_ready.emit(self.host, None, f"반복 {count} 완료", "blue", None)
    
    def check_tcp_port(self, host, port, timeout):
        """TCP 포트 열림 여부 확인 및 응답 시간 측정"""
        try:
            start_time = time.time()
            with socket.create_connection((host, port), timeout):
                end_time = time.time()
                # 밀리초 단위로 반환
                response_time = round((end_time - start_time) * 1000, 2)
                return True, response_time
        except socket.timeout:
            return False, None
        except ConnectionRefusedError:
            return False, None
        except Exception:
            return False, None


class EnhancedPingThread(QThread):
    ping_result = pyqtSignal(str, bool, float, str)  # IP, 성공여부, 응답시간, 메시지
    chart_update = pyqtSignal(dict)  # 차트 데이터
    
    def __init__(self, ip_list, interval, timeout):
        super().__init__()
        self.ip_list = ip_list
        self.interval = interval
        self.timeout = timeout
        self._stop_flag = False
        self._mutex = QMutex()
        
    def stop(self):
        self._mutex.lock()
        self._stop_flag = True
        self._mutex.unlock()
        
    def is_stopped(self):
        self._mutex.lock()
        flag = self._stop_flag
        self._mutex.unlock()
        return flag
        
    def run(self):
        while not self.is_stopped():
            # 모든 IP에 대해 ping 수행
            chart_data = {}
            
            for ip in self.ip_list:
                if self.is_stopped():
                    return
                    
                # ping 수행
                success, response_time, message = self.ping_host(ip)
                
                # 결과 전송
                self.ping_result.emit(ip, success, response_time, message)
                
                # 차트 데이터 수집
                chart_data[ip] = response_time if success else 0
            
            # 차트 업데이트 시그널 발생
            self.chart_update.emit(chart_data)
            
            # 간격만큼 대기
            for i in range(self.interval):
                if self.is_stopped():
                    return
                time.sleep(1)
    
    def ping_host(self, ip):
        try:
            if sys.platform == "win32":
                # Windows ping
                command = ["ping", "-n", "1", "-w", str(self.timeout * 1000), ip]
                result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                     text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                
                if result.returncode == 0 and "의 응답:" in result.stdout:
                    # TTL 추출
                    ttl_match = re.search(r"TTL=(\d+)", result.stdout, re.IGNORECASE)
                    
                    # 시간 추출
                    time_match = re.search(r"시간=(\d+)ms", result.stdout, re.IGNORECASE)
                    if time_match:
                        response_time = float(time_match.group(1))
                        return True, response_time, "성공"
            
                return False, 0.0, "실패"
            else:
                # Linux/Mac ping
                command = ["ping", "-c", "1", "-W", str(self.timeout), ip]
                result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                
                if result.returncode == 0 and "bytes from" in result.stdout:
                    time_match = re.search(r"time=([\d\.]+) ms", result.stdout)
                    if time_match:
                        response_time = float(time_match.group(1))
                        return True, response_time, "성공"
                
                return False, 0.0, "실패"
                
        except Exception as e:
            return False, 0.0, str(e)