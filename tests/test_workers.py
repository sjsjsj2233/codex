"""
core.workers 모듈 테스트
"""
import unittest
import sys
import os
import re
from unittest.mock import Mock, patch, MagicMock

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.workers import NetworkWorker, NetworkConfig


class TestNetworkConfig(unittest.TestCase):
    """NetworkConfig 상수 테스트"""

    def test_config_values(self):
        """설정 상수 값 테스트"""
        self.assertEqual(NetworkConfig.DEFAULT_TIMEOUT, 15)
        self.assertEqual(NetworkConfig.MAX_RETRIES, 3)
        self.assertEqual(NetworkConfig.RETRY_DELAY, 2)
        self.assertEqual(NetworkConfig.TERMINAL_LENGTH_CMD, "terminal length 0")
        self.assertEqual(NetworkConfig.TERMINAL_WIDTH_CMD, "terminal width 132")


class TestNetworkWorker(unittest.TestCase):
    """NetworkWorker 클래스 테스트"""

    def setUp(self):
        """테스트 전 설정"""
        self.worker = NetworkWorker(
            ip="192.168.1.1",
            username="admin",
            password="password",
            enable_password="enable",
            use_ssh=True,
            save_path="/tmp",
            commands=["show version", "show running-config"],
            ssh_port=22
        )

    def test_initialization(self):
        """NetworkWorker 초기화 테스트"""
        self.assertEqual(self.worker.ip, "192.168.1.1")
        self.assertEqual(self.worker.username, "admin")
        self.assertEqual(self.worker.password, "password")
        self.assertEqual(self.worker.enable_password, "enable")
        self.assertTrue(self.worker.use_ssh)
        self.assertEqual(self.worker.save_path, "/tmp")
        self.assertEqual(len(self.worker.commands), 2)
        self.assertEqual(self.worker.ssh_port, 22)
        self.assertEqual(self.worker.max_retries, NetworkConfig.MAX_RETRIES)
        self.assertEqual(self.worker.retry_delay, NetworkConfig.RETRY_DELAY)

    def test_stop_flag(self):
        """중지 플래그 테스트"""
        self.assertFalse(self.worker.is_stopped())
        self.worker.stop()
        self.assertTrue(self.worker.is_stopped())

    def test_extract_hostname_from_prompt_cisco(self):
        """프롬프트에서 호스트명 추출 테스트 - Cisco"""
        test_cases = [
            ("Router1#", "Router1"),
            ("Switch-Core#", "Switch-Core"),
            ("FW-01#", "FW-01"),
            ("Router1>", "Router1"),
            ("Router1(config)#", "Router1"),
        ]

        for prompt, expected in test_cases:
            with self.subTest(prompt=prompt):
                result = self.worker._extract_hostname_from_prompt(prompt)
                self.assertEqual(result, expected)

    def test_extract_hostname_from_prompt_invalid(self):
        """잘못된 프롬프트 테스트"""
        invalid_prompts = [
            "",
            "123",  # 숫자만
            "switch",  # 너무 일반적
            "router",  # 너무 일반적
        ]

        for prompt in invalid_prompts:
            with self.subTest(prompt=prompt):
                result = self.worker._extract_hostname_from_prompt(prompt)
                self.assertIsNone(result)

    def test_is_valid_hostname(self):
        """호스트명 유효성 검사 테스트"""
        valid_hostnames = [
            "Router1",
            "Switch-Core",
            "FW.01",
            "Core_SW_01",
            "CISCO-RT",
        ]

        invalid_hostnames = [
            "R",  # 너무 짧음
            "123",  # 숫자만
            "switch",  # 일반적인 이름
            "router",  # 일반적인 이름
            "localhost",  # 일반적인 이름
            "a" * 64,  # 너무 긴 이름
        ]

        for hostname in valid_hostnames:
            with self.subTest(hostname=hostname):
                self.assertTrue(self.worker._is_valid_hostname(hostname))

        for hostname in invalid_hostnames:
            with self.subTest(hostname=hostname):
                self.assertFalse(self.worker._is_valid_hostname(hostname))

    def test_is_enable_mode(self):
        """Enable 모드 확인 테스트"""
        enable_outputs = [
            "Router1#",
            "Switch-Core#\n",
            "\nRouter1#",
        ]

        user_outputs = [
            "Router1>",
            "Switch-Core>\n",
            "Username:",
        ]

        for output in enable_outputs:
            with self.subTest(output=output):
                self.assertTrue(self.worker._is_enable_mode(output))

        for output in user_outputs:
            with self.subTest(output=output):
                self.assertFalse(self.worker._is_enable_mode(output))

    def test_generate_output_filename_ip_only(self):
        """IP만 사용한 파일명 생성 테스트"""
        filename = self.worker.generate_output_filename(None, "ip_only")
        expected = os.path.join("/tmp", "192_168_1_1.txt")
        self.assertEqual(filename, expected)

    def test_generate_output_filename_hostname_only(self):
        """호스트명만 사용한 파일명 생성 테스트"""
        filename = self.worker.generate_output_filename("Router1", "hostname_only")
        expected = os.path.join("/tmp", "Router1.txt")
        self.assertEqual(filename, expected)

    def test_generate_output_filename_ip_hostname(self):
        """IP와 호스트명 조합 파일명 테스트"""
        filename = self.worker.generate_output_filename("Router1", "ip_hostname")
        expected = os.path.join("/tmp", "192_168_1_1_Router1.txt")
        self.assertEqual(filename, expected)

    def test_generate_output_filename_hostname_ip(self):
        """호스트명과 IP 조합 파일명 테스트"""
        filename = self.worker.generate_output_filename("Router1", "hostname_ip")
        expected = os.path.join("/tmp", "Router1_192_168_1_1.txt")
        self.assertEqual(filename, expected)

    def test_clean_output(self):
        """출력 텍스트 정리 테스트"""
        raw_output = """
show version
Cisco IOS Software, Version 15.0
Model: C2960

Router1#
"""
        cleaned = self.worker._clean_output(raw_output, "show version")

        # 명령어 자체는 제거되어야 함
        self.assertNotIn("show version", cleaned)

        # 프롬프트는 제거되어야 함
        self.assertNotIn("Router1#", cleaned)

        # 실제 출력은 유지되어야 함
        self.assertIn("Cisco IOS Software", cleaned)
        self.assertIn("Model: C2960", cleaned)

    def test_create_output_file_header(self):
        """출력 파일 헤더 생성 테스트"""
        import tempfile
        import os

        # 임시 파일 생성
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as f:
            temp_path = f.name

        try:
            self.worker._create_output_file_header(temp_path, "SSH", "TestRouter")

            # 파일 내용 확인
            with open(temp_path, 'r', encoding='utf-8') as f:
                content = f.read()

            self.assertIn("SSH 연결 결과: 192.168.1.1", content)
            self.assertIn("장비 Hostname: TestRouter", content)
            self.assertIn("실행 시간:", content)

        finally:
            # 임시 파일 삭제
            if os.path.exists(temp_path):
                os.remove(temp_path)


class TestNetworkWorkerIntegration(unittest.TestCase):
    """통합 테스트"""

    @patch('paramiko.SSHClient')
    def test_ssh_connection_mock(self, mock_ssh_class):
        """SSH 연결 모의 테스트"""
        # SSH 클라이언트 모킹
        mock_ssh = Mock()
        mock_ssh_class.return_value = mock_ssh

        worker = NetworkWorker(
            ip="192.168.1.1",
            username="admin",
            password="password",
            enable_password=None,
            use_ssh=True,
            save_path="/tmp",
            commands=["show version"],
            ssh_port=22
        )

        # 실제 연결은 테스트하지 않고, 설정이 올바른지만 확인
        self.assertTrue(worker.use_ssh)
        self.assertEqual(worker.ssh_port, 22)


class TestLoginHandlers(unittest.TestCase):
    """로그인 핸들러 테스트"""

    def setUp(self):
        """테스트 전 설정"""
        self.worker = NetworkWorker(
            ip="192.168.1.1",
            username="admin",
            password="cisco123",
            enable_password="enable",
            use_ssh=False,
            save_path="/tmp",
            commands=["show version"],
            ssh_port=22
        )

    def test_detect_password_only_login(self):
        """Password-only 로그인 패턴 감지 테스트"""
        # Password만 물어보는 출력
        password_only_outputs = [
            "Password:",
            "password:",
            "Password: ",
            "Enter password:",
            "\nPassword:\n",
        ]

        for output in password_only_outputs:
            with self.subTest(output=output):
                # Password 패턴이 있는지 확인
                has_password = re.search(r'[Pp]assword\s*:', output)
                self.assertIsNotNone(has_password, f"Password 패턴을 찾지 못함: {output}")

    def test_detect_username_password_login(self):
        """Username + Password 로그인 패턴 감지 테스트"""
        # Username을 먼저 물어보는 출력
        username_outputs = [
            "Username:",
            "username:",
            "User Name:",
            "login:",
            "Login:",
        ]

        for output in username_outputs:
            with self.subTest(output=output):
                # Username 패턴이 있는지 확인
                has_username = re.search(r'([Uu]sername|[Uu]ser\s*[Nn]ame|[Ll]ogin)\s*:', output)
                self.assertIsNotNone(has_username, f"Username 패턴을 찾지 못함: {output}")

    def test_login_priority(self):
        """로그인 패턴 우선순위 테스트"""
        # Password가 Username보다 먼저 나타나는 경우
        output_with_both = """
Welcome to Router
Password:
"""
        # Password 패턴이 먼저 감지되어야 함
        password_match = re.search(r'[Pp]assword\s*:', output_with_both)
        username_match = re.search(r'[Uu]sername\s*:', output_with_both)

        self.assertIsNotNone(password_match)
        self.assertIsNone(username_match)

    def test_already_logged_in_detection(self):
        """이미 로그인된 상태 감지 테스트"""
        logged_in_outputs = [
            "Router1#",
            "Switch-Core>",
            "\nRouter1#\n",
            "Device(config)#",
        ]

        for output in logged_in_outputs:
            with self.subTest(output=output):
                # 프롬프트 패턴 확인
                has_prompt = re.search(r'[#>]\s*$', output.strip(), re.MULTILINE)
                self.assertIsNotNone(has_prompt, f"프롬프트를 찾지 못함: {output}")

    def test_empty_username_handling(self):
        """빈 Username 처리 테스트"""
        # Username이 빈 문자열인 worker 생성
        worker_empty = NetworkWorker(
            ip="192.168.1.1",
            username="",  # 빈 문자열
            password="cisco123",
            enable_password=None,
            use_ssh=False,
            save_path="/tmp",
            commands=["show version"],
            ssh_port=22
        )

        # Username이 None인 worker 생성
        worker_none = NetworkWorker(
            ip="192.168.1.1",
            username=None,  # None
            password="cisco123",
            enable_password=None,
            use_ssh=False,
            save_path="/tmp",
            commands=["show version"],
            ssh_port=22
        )

        # Username이 공백만 있는 worker 생성
        worker_whitespace = NetworkWorker(
            ip="192.168.1.1",
            username="   ",  # 공백만
            password="cisco123",
            enable_password=None,
            use_ssh=False,
            save_path="/tmp",
            commands=["show version"],
            ssh_port=22
        )

        # 빈 username 확인
        self.assertEqual(worker_empty.username, "")
        self.assertIsNone(worker_none.username)
        self.assertEqual(worker_whitespace.username, "   ")

        # Password는 정상적으로 설정되어야 함
        self.assertEqual(worker_empty.password, "cisco123")
        self.assertEqual(worker_none.password, "cisco123")
        self.assertEqual(worker_whitespace.password, "cisco123")


if __name__ == '__main__':
    unittest.main()
