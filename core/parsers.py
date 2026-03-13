"""
네트워크 장비 출력 데이터 파싱 모듈

Cisco IOS 및 Nexus 장비의 show 명령어 출력을 파싱하여 구조화된 데이터로 변환합니다.
"""
import re
import os
import logging
from typing import Dict, List, Tuple, Optional


class DeviceParser:
    """네트워크 장비 데이터 파서 클래스"""

    def __init__(self):
        """파서 초기화"""
        pass

    # ==================== Cisco IOS 파싱 메서드 ====================

    @staticmethod
    def parse_run_hostname(content: str) -> str:
        """설정에서 호스트명 파싱

        Args:
            content: show running-config 출력

        Returns:
            호스트명 또는 "N/A"
        """
        match = re.search(r"^hostname\s+(\S+)", content, re.MULTILINE)
        return match.group(1) if match else "N/A"

    @staticmethod
    def parse_show_version(content: str) -> Tuple[str, str, str]:
        """버전 정보 및 모델 파싱

        Args:
            content: show version 출력

        Returns:
            (ios_version, sw_version, model) 튜플
        """
        # IOS 버전 추출
        ios_version_match = re.search(r"Version\s+([\d\.\(\)A-Za-z]+)", content)
        ios_version = ios_version_match.group(1) if ios_version_match else "N/A"

        # SW 버전은 IOS 버전과 동일하게 설정
        sw_version = ios_version

        # 모델 번호 추출 (우선순위: Model number -> C#### 패턴)
        model_match = re.search(r"Model number\s+:\s+(\S+)", content, re.IGNORECASE)
        if model_match:
            model = model_match.group(1)
        else:
            specific_model_match = re.search(r"\bC\d{4,}\b", content)
            model = specific_model_match.group(0) if specific_model_match else "N/A"

        return ios_version, sw_version, model

    @staticmethod
    def parse_memory(content: str) -> Tuple[int|str, int|str, int|str, str]:
        """메모리 정보 파싱

        Args:
            content: show memory 또는 show version 출력

        Returns:
            (total, used, free, usage_percentage) 튜플
        """
        # Processor Pool 형식 먼저 시도
        match = re.search(
            r"Processor Pool Total:\s+(\d+)\s+Used:\s+(\d+)\s+Free:\s+(\d+)",
            content,
            re.DOTALL
        )
        if match:
            total = int(match.group(1))
            used = int(match.group(2))
            free = int(match.group(3))
            usage_percentage = round((used / total) * 100, 2)
            return total, used, free, f"{usage_percentage}%"

        # System memory 형식 시도
        match = re.search(
            r"System memory\s+:\s+(\d+)K total,\s+(\d+)K used,\s+(\d+)K free",
            content
        )
        if match:
            total = int(match.group(1))
            used = int(match.group(2))
            free = int(match.group(3))
            usage_percentage = round((used / total) * 100, 2)
            return total, used, free, f"{usage_percentage}%"

        return "N/A", "N/A", "N/A", "N/A"

    @staticmethod
    def parse_cpu(content: str) -> str:
        """CPU 사용률 파싱

        Args:
            content: show processes cpu 또는 show version 출력

        Returns:
            CPU 사용률 (예: "5%") 또는 "N/A"
        """
        match = re.search(r"CPU utilization for five seconds:.*?(\d+)%", content)
        return match.group(1) + "%" if match else "N/A"

    @staticmethod
    def parse_uptime(content: str) -> str:
        """장비 가동시간 파싱

        Args:
            content: show version 출력

        Returns:
            가동시간 문자열 또는 "N/A"
        """
        match = re.search(r"uptime is (.+)", content)
        return match.group(1).strip() if match else "N/A"

    @classmethod
    def parse_device_info(cls, content: str, filename: str = None) -> Dict:
        """장비 정보 종합 파싱 (IOS)

        Args:
            content: 장비 출력 전체
            filename: 파일명 (선택)

        Returns:
            파싱된 장비 정보 딕셔너리
        """
        hostname = cls.parse_run_hostname(content)
        ios_version, sw_version, model = cls.parse_show_version(content)
        total_mem, used_mem, free_mem, memory_usage = cls.parse_memory(content)
        cpu_usage = cls.parse_cpu(content)
        uptime = cls.parse_uptime(content)

        device_info = {
            "filename": os.path.splitext(os.path.basename(filename))[0] if filename else "N/A",
            "hostname": hostname,
            "cpu": cpu_usage,
            "memory_total": total_mem,
            "memory_used": used_mem,
            "memory_free": free_mem,
            "memory_usage": memory_usage,
            "uptime": uptime,
            "ios_version": ios_version,
            "sw_version": sw_version,
            "model": model,
            "raw_content": content
        }

        return device_info

    # ==================== Nexus 파싱 메서드 ====================

    @staticmethod
    def parse_show_version_nexus(content: str) -> Tuple[str, str, str]:
        """NX-OS 호스트명, 버전 및 모델 파싱

        Args:
            content: show version 출력

        Returns:
            (hostname, nxos_version, model) 튜플
        """
        # 호스트명 추출
        hostname_match = re.search(r"Device name:\s+(\S+)", content)
        hostname = hostname_match.group(1) if hostname_match else "N/A"

        # NX-OS 버전 추출 (여러 패턴 시도)
        nxos_version_match = re.search(r"NXOS: version\s+([\d\.\(\)A-Za-z]+)", content, re.IGNORECASE)
        if not nxos_version_match:
            nxos_version_match = re.search(r"System version:\s+([\d\.\(\)A-Za-z]+)", content, re.IGNORECASE)
        nxos_version = nxos_version_match.group(1) if nxos_version_match else "N/A"

        # 모델 추출
        model_match = re.search(r"Hardware\s+:\s+cisco\s+Nexus\d+\s+(\S+)", content, re.IGNORECASE)
        if not model_match:
            model_match = re.search(r"\b(N\d[KX]?-\S+)\b", content)
        model = model_match.group(1) if model_match else "N/A"

        return hostname, nxos_version, model

    @staticmethod
    def parse_system_resources(content: str) -> Tuple[str, int|str, int|str, int|str, str, str]:
        """Nexus CPU, 메모리, 가동시간 파싱

        Args:
            content: show system resources 출력

        Returns:
            (cpu_usage, total_mem, used_mem, free_mem, memory_usage, uptime) 튜플
        """
        # CPU 사용률 파싱
        cpu_match = re.search(
            r"CPU states\s+:\s+([\d\.]+)% user,\s+([\d\.]+)% kernel,\s+([\d\.]+)% idle",
            content
        )
        if cpu_match:
            user_cpu = float(cpu_match.group(1))
            kernel_cpu = float(cpu_match.group(2))
            total_cpu = round(user_cpu + kernel_cpu, 2)
            cpu_usage = f"{total_cpu}%"
        else:
            cpu_usage = "N/A"

        # 메모리 사용률 파싱
        mem_match = re.search(
            r"Memory usage:\s+(\d+)K total,\s+(\d+)K used,\s+(\d+)K free",
            content
        )
        if mem_match:
            total_mem = int(mem_match.group(1))
            used_mem = int(mem_match.group(2))
            free_mem = int(mem_match.group(3))
            usage_percentage = round((used_mem / total_mem) * 100, 2)
            memory_usage = f"{usage_percentage}%"
        else:
            total_mem, used_mem, free_mem, memory_usage = "N/A", "N/A", "N/A", "N/A"

        # 가동시간 파싱 (여러 형식 지원)
        uptime_match = re.search(
            r"Kernel uptime is (\d+) day\(s\), (\d+) hour\(s\), (\d+) minute\(s\), (\d+) second\(s\)",
            content
        )
        if uptime_match:
            days, hours, minutes, seconds = uptime_match.groups()
            uptime = f"{days}일 {hours}시간 {minutes}분 {seconds}초"
        else:
            # Alternative uptime format
            uptime_match = re.search(
                r"(\S+) uptime is (\d+ years, )?(\d+ weeks, )?(\d+ days, )?(\d+ hours, )?(\d+ minutes)",
                content
            )
            if uptime_match:
                uptime_parts = [part for part in uptime_match.groups()[1:] if part]
                uptime = ''.join(uptime_parts).strip()
            else:
                uptime = "N/A"

        return cpu_usage, total_mem, used_mem, free_mem, memory_usage, uptime

    @staticmethod
    def parse_last_reboot(content: str) -> str:
        """마지막 재부팅 시간 추출

        Args:
            content: show version 출력

        Returns:
            재부팅 시간 문자열 또는 "N/A"
        """
        reboot_match = re.search(r"Last reset at\s+(.+?)(\s+Reason:|\n)", content)
        return reboot_match.group(1).strip() if reboot_match else "N/A"

    @staticmethod
    def parse_host_from_filename(file_path: str) -> str:
        """파일명에서 호스트명 추출

        Args:
            file_path: 파일 경로

        Returns:
            추출된 호스트명 또는 "N/A"
        """
        filename = os.path.basename(file_path)
        host = os.path.splitext(filename)[0]  # 확장자 제거

        # 간단한 호스트명 검증 (예: CNS22_3F_MDF_BB_2)
        if re.match(r'^[\w\-\.]+$', host):
            return host
        return "N/A"

    @classmethod
    def parse_nexus_device_info(cls, content: str, filename: str = None) -> Dict:
        """Nexus 장비 정보 종합 파싱

        Args:
            content: 장비 출력 전체
            filename: 파일명 (선택)

        Returns:
            파싱된 장비 정보 딕셔너리
        """
        hostname, nxos_version, model = cls.parse_show_version_nexus(content)
        cpu_usage, total_mem, used_mem, free_mem, memory_usage, uptime = cls.parse_system_resources(content)
        host_from_filename = cls.parse_host_from_filename(filename) if filename else "N/A"
        last_reboot = cls.parse_last_reboot(content)

        device_info = {
            "filename": os.path.splitext(os.path.basename(filename))[0] if filename else "N/A",
            "hostname": hostname if hostname != "N/A" else host_from_filename,
            "cpu": cpu_usage,
            "memory_total": total_mem,
            "memory_used": used_mem,
            "memory_free": free_mem,
            "memory_usage": memory_usage,
            "uptime": uptime,
            "nxos_version": nxos_version,
            "model": model,
            "last_reboot": last_reboot,
            "raw_content": content
        }

        return device_info

    @classmethod
    def parse_file(cls, file_path: str, device_type: str = "ios") -> Optional[Dict]:
        """파일에서 장비 정보 파싱

        Args:
            file_path: 파싱할 파일 경로
            device_type: 장비 타입 ("ios" 또는 "nexus")

        Returns:
            파싱된 장비 정보 딕셔너리 또는 None (실패 시)
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            if device_type.lower() == "nexus":
                return cls.parse_nexus_device_info(content, file_path)
            else:
                return cls.parse_device_info(content, file_path)

        except Exception as e:
            logging.error(f"파일 파싱 실패 ({file_path}): {e}")
            return None

    @classmethod
    def parse_files(cls, file_paths: List[str], device_type: str = "ios") -> List[Dict]:
        """여러 파일 일괄 파싱

        Args:
            file_paths: 파싱할 파일 경로 리스트
            device_type: 장비 타입 ("ios" 또는 "nexus")

        Returns:
            파싱된 장비 정보 리스트
        """
        results = []
        for file_path in file_paths:
            device_info = cls.parse_file(file_path, device_type)
            if device_info:
                results.append(device_info)
        return results


# 하위 호환성을 위한 함수 래퍼 (기존 코드가 직접 함수를 호출하는 경우)
def parse_run_hostname(content: str) -> str:
    """하위 호환성 래퍼"""
    return DeviceParser.parse_run_hostname(content)


def parse_show_version(content: str) -> Tuple[str, str, str]:
    """하위 호환성 래퍼"""
    return DeviceParser.parse_show_version(content)


def parse_memory(content: str) -> Tuple[int|str, int|str, int|str, str]:
    """하위 호환성 래퍼"""
    return DeviceParser.parse_memory(content)


def parse_cpu(content: str) -> str:
    """하위 호환성 래퍼"""
    return DeviceParser.parse_cpu(content)


def parse_uptime(content: str) -> str:
    """하위 호환성 래퍼"""
    return DeviceParser.parse_uptime(content)
