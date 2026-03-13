"""
core.parsers 모듈 테스트
"""
import unittest
import sys
import os

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.parsers import DeviceParser


class TestDeviceParser(unittest.TestCase):
    """DeviceParser 클래스 테스트"""

    def setUp(self):
        """테스트 전 설정"""
        self.parser = DeviceParser()

    # ========== Cisco IOS 파싱 테스트 ==========

    def test_parse_run_hostname_success(self):
        """hostname 파싱 성공 테스트"""
        content = """
hostname Router1
interface GigabitEthernet0/0
 ip address 192.168.1.1 255.255.255.0
"""
        result = self.parser.parse_run_hostname(content)
        self.assertEqual(result, "Router1")

    def test_parse_run_hostname_not_found(self):
        """hostname이 없을 때 N/A 반환 테스트"""
        content = "interface GigabitEthernet0/0"
        result = self.parser.parse_run_hostname(content)
        self.assertEqual(result, "N/A")

    def test_parse_show_version_success(self):
        """버전 정보 파싱 성공 테스트"""
        content = """
Cisco IOS Software, C2960 Software (C2960-LANBASEK9-M), Version 15.0(2)SE11, RELEASE SOFTWARE (fc3)
Model number : WS-C2960-24TT-L
"""
        ios_version, sw_version, model = self.parser.parse_show_version(content)
        self.assertEqual(ios_version, "15.0(2)SE11")
        self.assertEqual(sw_version, "15.0(2)SE11")
        self.assertEqual(model, "WS-C2960-24TT-L")

    def test_parse_show_version_with_c_model(self):
        """C#### 모델 패턴 파싱 테스트"""
        content = """
Cisco IOS Software, Version 12.4(15)T1
cisco C2811 (revision 53.51) with 249856K/12288K bytes of memory.
"""
        ios_version, sw_version, model = self.parser.parse_show_version(content)
        self.assertEqual(model, "C2811")

    def test_parse_memory_processor_pool(self):
        """Processor Pool 메모리 파싱 테스트"""
        content = """
Processor Pool Total:  536870912 Used:  322961408 Free:  213909504
"""
        total, used, free, usage = self.parser.parse_memory(content)
        self.assertEqual(total, 536870912)
        self.assertEqual(used, 322961408)
        self.assertEqual(free, 213909504)
        self.assertEqual(usage, "60.16%")

    def test_parse_memory_system_memory(self):
        """System memory 파싱 테스트"""
        content = """
System memory : 524288K total, 314572K used, 209716K free
"""
        total, used, free, usage = self.parser.parse_memory(content)
        self.assertEqual(total, 524288)
        self.assertEqual(used, 314572)
        self.assertEqual(free, 209716)
        self.assertEqual(usage, "60.0%")

    def test_parse_memory_not_found(self):
        """메모리 정보가 없을 때 N/A 반환 테스트"""
        content = "Some other content"
        total, used, free, usage = self.parser.parse_memory(content)
        self.assertEqual(total, "N/A")
        self.assertEqual(used, "N/A")
        self.assertEqual(free, "N/A")
        self.assertEqual(usage, "N/A")

    def test_parse_cpu_success(self):
        """CPU 사용률 파싱 성공 테스트"""
        content = """
CPU utilization for five seconds: 5%/2%; one minute: 4%; five minutes: 3%
"""
        result = self.parser.parse_cpu(content)
        self.assertEqual(result, "5%")

    def test_parse_cpu_not_found(self):
        """CPU 정보가 없을 때 N/A 반환 테스트"""
        content = "Some other content"
        result = self.parser.parse_cpu(content)
        self.assertEqual(result, "N/A")

    def test_parse_uptime_success(self):
        """가동시간 파싱 성공 테스트"""
        content = """
Router1 uptime is 2 weeks, 3 days, 4 hours, 30 minutes
"""
        result = self.parser.parse_uptime(content)
        self.assertEqual(result, "2 weeks, 3 days, 4 hours, 30 minutes")

    def test_parse_uptime_not_found(self):
        """가동시간 정보가 없을 때 N/A 반환 테스트"""
        content = "Some other content"
        result = self.parser.parse_uptime(content)
        self.assertEqual(result, "N/A")

    # ========== Nexus 파싱 테스트 ==========

    def test_parse_show_version_nexus_success(self):
        """Nexus 버전 정보 파싱 테스트"""
        content = """
Device name: Nexus-Core-1
NXOS: version 7.0(3)I7(8)
Hardware : cisco Nexus9000 N9K-C9396PX
"""
        hostname, nxos_version, model = self.parser.parse_show_version_nexus(content)
        self.assertEqual(hostname, "Nexus-Core-1")
        self.assertEqual(nxos_version, "7.0(3)I7(8)")
        self.assertEqual(model, "N9K-C9396PX")

    def test_parse_system_resources_success(self):
        """Nexus 시스템 리소스 파싱 테스트"""
        content = """
CPU states : 10.5% user, 5.2% kernel, 84.3% idle
Memory usage: 8388608K total, 4194304K used, 4194304K free
Kernel uptime is 30 day(s), 12 hour(s), 45 minute(s), 20 second(s)
"""
        cpu, total, used, free, mem_usage, uptime = self.parser.parse_system_resources(content)
        self.assertEqual(cpu, "15.7%")
        self.assertEqual(total, 8388608)
        self.assertEqual(used, 4194304)
        self.assertEqual(free, 4194304)
        self.assertEqual(mem_usage, "50.0%")
        self.assertEqual(uptime, "30일 12시간 45분 20초")

    def test_parse_host_from_filename_success(self):
        """파일명에서 호스트명 추출 테스트"""
        result = self.parser.parse_host_from_filename("/path/to/CNS22_3F_MDF_BB_2.txt")
        self.assertEqual(result, "CNS22_3F_MDF_BB_2")

    def test_parse_host_from_filename_invalid(self):
        """잘못된 파일명 테스트"""
        result = self.parser.parse_host_from_filename("/path/to/invalid@file.txt")
        self.assertEqual(result, "N/A")

    def test_parse_last_reboot_success(self):
        """재부팅 시간 파싱 테스트"""
        content = """
Last reset at 532453 usecs after Mon Jan 15 10:30:45 2024 Reason: Reset Requested by CLI command reload
"""
        result = self.parser.parse_last_reboot(content)
        self.assertEqual(result, "532453 usecs after Mon Jan 15 10:30:45 2024")

    # ========== 통합 파싱 테스트 ==========

    def test_parse_device_info_complete(self):
        """IOS 장비 정보 종합 파싱 테스트"""
        content = """
hostname TestRouter
Cisco IOS Software, Version 15.2(4)M6a
Model number : C2911-SEC/K9
Processor Pool Total:  1073741824 Used:  536870912 Free:  536870912
CPU utilization for five seconds: 8%/3%; one minute: 7%; five minutes: 6%
TestRouter uptime is 50 days, 10 hours, 25 minutes
"""
        device_info = self.parser.parse_device_info(content, "/path/to/TestRouter.txt")

        self.assertEqual(device_info['hostname'], "TestRouter")
        self.assertEqual(device_info['ios_version'], "15.2(4)M6a")
        self.assertEqual(device_info['model'], "C2911-SEC/K9")
        self.assertEqual(device_info['cpu'], "8%")
        self.assertEqual(device_info['memory_usage'], "50.0%")
        self.assertEqual(device_info['filename'], "TestRouter")


class TestParserEdgeCases(unittest.TestCase):
    """엣지 케이스 테스트"""

    def test_empty_content(self):
        """빈 컨텐츠 처리 테스트"""
        parser = DeviceParser()
        content = ""

        hostname = parser.parse_run_hostname(content)
        self.assertEqual(hostname, "N/A")

        cpu = parser.parse_cpu(content)
        self.assertEqual(cpu, "N/A")

    def test_malformed_content(self):
        """잘못된 형식의 컨텐츠 테스트"""
        parser = DeviceParser()
        content = "!@#$%^&*()_+{}|:\"<>?[]\\;',./`~"

        # 예외가 발생하지 않고 N/A를 반환해야 함
        hostname = parser.parse_run_hostname(content)
        self.assertEqual(hostname, "N/A")


if __name__ == '__main__':
    unittest.main()
