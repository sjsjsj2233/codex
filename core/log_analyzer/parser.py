# 파일 시작 부분에 추가
import os
import re
from datetime import datetime
from PyQt5.QtCore import QThread, pyqtSignal

from .constants import (SYSLOG_LEVELS, LOG_PATTERNS, SEVERITY_COLORS, 
                       NETWORK_EVENTS, SECURITY_EVENTS)

# 나머지 코드는 그대로 유지


class LogParserThread(QThread):
    """백그라운드에서 로그 파싱을 실행하는 쓰레드"""
    progress_update = pyqtSignal(int)
    parsing_complete = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, file_path, device_type=None):
        super().__init__()
        self.file_path = file_path
        self.device_type = device_type

        # 다양한 인코딩 시도
        self.encodings = ['utf-8', 'euc-kr', 'cp949', 'latin-1']
        
    def run(self):
        try:
            # 파일 존재 확인
            if not os.path.exists(self.file_path):
                self.error_occurred.emit(f"오류: 파일을 찾을 수 없습니다: {self.file_path}")
                return
                
            # 파일 크기 확인
            file_size = os.path.getsize(self.file_path)
            if file_size == 0:
                self.error_occurred.emit(f"오류: 파일이 비어 있습니다: {self.file_path}")
                return
                
            # 대용량 파일 처리를 위한 준비
            if file_size > 20 * 1024 * 1024:  # 20MB 이상
                self.progress_update.emit(5)
                self.parse_large_file()
            else:
                self.progress_update.emit(5)
                self.parse_normal_file()
                
        except Exception as e:
            self.error_occurred.emit(f"파싱 오류: {str(e)}")
            
    def parse_normal_file(self):
        """일반 크기 파일 파싱"""
        try:
            # 파일 읽기
            with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 장비 유형이 선택되지 않은 경우 자동 감지 시도
            if not self.device_type:
                self.device_type = self.detect_device_type(content)
                
            patterns = LOG_PATTERNS.get(self.device_type, [])
            if not patterns:
                self.error_occurred.emit(f"오류: '{self.device_type}' 장비 유형에 대한 패턴이 정의되지 않았습니다.")
                return
                
            lines = content.split('\n')
            total_lines = len(lines)
            logs = []
            
            for i, line in enumerate(lines):
                # 진행 상황 업데이트 (10%마다)
                if i % (max(1, total_lines // 10)) == 0:
                    progress = min(100, int(5 + (i / total_lines) * 90))
                    self.progress_update.emit(progress)
                
                # 발견된 로그 항목
                log_entry = None
                
                # 모든 패턴 시도
                for pattern in patterns:
                    match = re.search(pattern, line)
                    if match:
                        # 장비 유형별 파싱 적용
                        log_entry = self.parse_log_by_device_type(self.device_type, match, line)
                        if log_entry:
                            break
                
                if log_entry:
                    # 추가 분석 수행
                    log_entry = self.analyze_log_entry(log_entry)
                    logs.append(log_entry)
            
            # 완료 신호 및 데이터 전송
            self.progress_update.emit(100)
            self.parsing_complete.emit(logs)
            
        except Exception as e:
            self.error_occurred.emit(f"파싱 오류: {str(e)}")
            
    def parse_large_file(self):
        """대용량 파일 라인별 처리"""
        try:
            # 장비 유형 결정
            if not self.device_type:
                # 샘플로 처음 1000라인 읽어서 장비 유형 감지
                with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    sample_content = ''.join([next(f) for _ in range(1000) if f])
                self.device_type = self.detect_device_type(sample_content)
            
            patterns = LOG_PATTERNS.get(self.device_type, [])
            if not patterns:
                self.error_occurred.emit(f"오류: '{self.device_type}' 장비 유형에 대한 패턴이 정의되지 않았습니다.")
                return
                
            # 파일 크기 확인
            file_size = os.path.getsize(self.file_path)
            
            # 라인 수 추정 (샘플링)
            line_count_estimate = self.estimate_line_count()
            if line_count_estimate <= 0:
                line_count_estimate = 10000  # 기본값
                
            logs = []
            processed_size = 0
            
            with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for i, line in enumerate(f):
                    # 진행 상황 업데이트 
                    processed_size += len(line.encode('utf-8'))
                    if i % 1000 == 0:
                        progress = min(95, int(5 + (processed_size / file_size) * 90))
                        self.progress_update.emit(progress)
                    
                    # 발견된 로그 항목
                    log_entry = None
                    
                    # 모든 패턴 시도
                    for pattern in patterns:
                        match = re.search(pattern, line)
                        if match:
                            # 장비 유형별 파싱 적용
                            log_entry = self.parse_log_by_device_type(self.device_type, match, line)
                            if log_entry:
                                break
                    
                    if log_entry:
                        # 추가 분석 수행
                        log_entry = self.analyze_log_entry(log_entry)
                        logs.append(log_entry)
            
            # 완료 신호 및 데이터 전송
            self.progress_update.emit(100)
            self.parsing_complete.emit(logs)
            
        except Exception as e:
            self.error_occurred.emit(f"대용량 파일 파싱 오류: {str(e)}")
    
    def estimate_line_count(self):
        """파일의 라인 수 추정"""
        try:
            # 파일 크기
            file_size = os.path.getsize(self.file_path)
            
            # 파일이 너무 작으면 모든 라인 계산
            if file_size < 2 * 1024 * 1024:  # 2MB 미만
                with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return sum(1 for _ in f)
            
            # 샘플링: 처음/중간/끝 부분에서 1000라인씩 읽어 평균 라인 길이 계산
            avg_line_length = 0
            sample_lines = 0
            
            # 파일 시작 부분
            with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                start_lines = [next(f) for _ in range(1000) if f]
                start_size = sum(len(line.encode('utf-8')) for line in start_lines)
                sample_lines += len(start_lines)
            
            # 파일 중간 부분
            mid_position = max(0, file_size // 2 - 50000)
            with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(mid_position)
                f.readline()  # 현재 라인 끝까지 이동 (부분 라인 건너뛰기)
                mid_lines = [next(f) for _ in range(1000) if f]
                mid_size = sum(len(line.encode('utf-8')) for line in mid_lines)
                sample_lines += len(mid_lines)
            
            # 파일 끝 부분
            end_position = max(0, file_size - 100000)
            with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(end_position)
                f.readline()  # 현재 라인 끝까지 이동 (부분 라인 건너뛰기)
                end_lines = [next(f) for _ in range(1000) if f]
                end_size = sum(len(line.encode('utf-8')) for line in end_lines)
                sample_lines += len(end_lines)
            
            # 평균 라인 길이 계산
            if sample_lines > 0:
                avg_line_length = (start_size + mid_size + end_size) / sample_lines
                
            # 라인 수 추정
            if avg_line_length > 0:
                return int(file_size / avg_line_length)
            else:
                return 0
                
        except Exception as e:
            print(f"라인 수 추정 오류: {str(e)}")
            return 0
            
    def detect_device_type(self, sample_content):
        """로그 내용 기반으로 장비 유형 자동 감지"""
        # 각 장비 유형별 샘플 로그 분석
        matches = {}
        
        for device_type, patterns in LOG_PATTERNS.items():
            matches[device_type] = 0
            for pattern in patterns:
                # 패턴 매칭 시도
                pattern_matches = re.findall(pattern, sample_content)
                matches[device_type] += len(pattern_matches)
        
        # 가장 많은 매칭이 있는 장비 유형 선택
        if max(matches.values()) > 0:
            return max(matches, key=matches.get)
        
        # 기본값
        return 'ios_xe'
    
    def parse_timestamp(self, timestamp_str):
        """다양한 Cisco 타임스탬프 형식을 datetime 객체로 변환"""
        # 타임스탬프 문자열 정리
        timestamp_str = timestamp_str.strip()
        
        # '*' 제거 (IOS에서 자주 발생)
        if timestamp_str.startswith('*'):
            timestamp_str = timestamp_str[1:].strip()
        
        # 다양한 타임스탬프 형식 처리
        formats = [
            # 표준 IOS 포맷 "Mar 15 23:48:12"
            '%b %d %H:%M:%S',
            '%b %d %H:%M:%S.%f',
            # 연도가 포함된 포맷 "Mar 15 2023 23:48:12"
            '%b %d %Y %H:%M:%S',
            '%b %d %Y %H:%M:%S.%f',
            # 또는 "Mar 15 2023: 23:48:12"
            '%b %d %Y: %H:%M:%S',
            '%b %d %Y: %H:%M:%S.%f',
            # NX-OS 포맷 "2023 Mar 15 23:48:12"
            '%Y %b %d %H:%M:%S',
            '%Y %b %d %H:%M:%S.%f',
            # ISO 포맷 "2023-03-15T23:48:12"
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%f',
            # ISO 포맷 타임존 포함 "2023-03-15T23:48:12+00:00"
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%dT%H:%M:%S.%f%z',
        ]
        
        # 현재 연도 (타임스탬프에 연도가 없는 경우 사용)
        current_year = datetime.now().year
        
        # 모든 포맷 시도
        for fmt in formats:
            try:
                dt = datetime.strptime(timestamp_str, fmt)
                
                # 연도가 없는 포맷이면 현재 연도 할당
                if dt.year == 1900:
                    dt = dt.replace(year=current_year)
                
                return dt
            except ValueError:
                continue
        
        # 모든 포맷 실패 시 None 반환
        return None
        
    # 수정 코드:
    def analyze_log_entry(self, log_entry):
        """로그 항목에 대한 추가 분석 수행"""
        if not log_entry or 'raw' not in log_entry:
            return log_entry
            
        raw_message = log_entry['raw']
        
        # 네트워크 이벤트 분석
        for event_type, patterns in NETWORK_EVENTS.items():
            for pattern in patterns:
                if re.search(pattern, raw_message, re.IGNORECASE):
                    log_entry['event_type'] = event_type
                    log_entry['event_category'] = 'network'
                    break
            
            # 이벤트 찾았으면 중단
            if 'event_type' in log_entry:
                break
                
        # 보안 이벤트 분석 (네트워크 이벤트가 없는 경우)
        if 'event_type' not in log_entry:
            for event_type, patterns in SECURITY_EVENTS.items():
                for pattern in patterns:
                    if re.search(pattern, raw_message, re.IGNORECASE):
                        log_entry['event_type'] = event_type
                        log_entry['event_category'] = 'security'
                        break
                
                # 이벤트 찾았으면 중단
                if 'event_type' in log_entry:
                    break

        return log_entry  # 올바른 들여쓰기

    
    def parse_log_by_device_type(self, device_type, match, line):
        """장비 유형별 로그 파싱 로직"""
        log_entry = {
            'raw': line.strip(),
            'timestamp_obj': None  # datetime 객체
        }
        
        try:
            if device_type in ['ios', 'ios_xe', 'wlc']:
                # 기본 IOS/IOS-XE 형식 처리
                if len(match.groups()) >= 4:
                    timestamp, severity, facility, message = match.groups()[:4]
                    
                    # 심각도가 KST나 다른 일반적이지 않은 값인 경우 수정
                    if not severity.upper() in SEVERITY_COLORS:
                        # severity가 숫자인 경우(syslog 레벨) 변환
                        if severity.isdigit() and int(severity) in SYSLOG_LEVELS:
                            severity = SYSLOG_LEVELS[int(severity)]
                        else:
                            # 메시지에서 심각도 정보 찾기
                            severity_match = re.search(r'-(\d)-', facility)
                            if severity_match:
                                sev_level = int(severity_match.group(1))
                                if sev_level in SYSLOG_LEVELS:
                                    severity = SYSLOG_LEVELS[sev_level]
                            else:
                                severity = 'INFO'  # 기본값
                    
                    log_entry.update({
                        'timestamp': timestamp,
                        'severity': severity.upper(),
                        'facility': facility,
                        'message': message,
                    })
                    
                    # 타임스탬프 객체 변환 시도
                    try:
                        log_entry['timestamp_obj'] = self.parse_timestamp(timestamp)
                    except:
                        pass
            
            elif device_type == 'nxos':
                # NX-OS 형식 처리
                if len(match.groups()) >= 4:
                    timestamp, severity, facility, message = match.groups()[:4]
                    
                    # 심각도 처리
                    if not severity.upper() in SEVERITY_COLORS:
                        # facility에서 심각도 레벨 찾기
                        severity_match = re.search(r'-(\d)-', facility)
                        if severity_match:
                            sev_level = int(severity_match.group(1))
                            if sev_level in SYSLOG_LEVELS:
                                severity = SYSLOG_LEVELS[sev_level]
                        else:
                            severity = 'INFO'  # 기본값
                    
                    log_entry.update({
                        'timestamp': timestamp,
                        'severity': severity.upper(),
                        'facility': facility,
                        'message': message
                    })
                    
                    # 타임스탬프 객체 변환 시도
                    try:
                        log_entry['timestamp_obj'] = self.parse_timestamp(timestamp)
                    except:
                        pass
            
            elif device_type == 'asa':
                # ASA/FTD 형식 처리
                if len(match.groups()) >= 4:
                    timestamp = match.groups()[0]
                    
                    # ASA 형식은 %ASA-심각도레벨-메시지코드: 형식
                    if re.search(r'%ASA-(\d)-', line):
                        asa_match = re.search(r'%ASA-(\d)-(\w+):\s+(.*)', line)
                        if asa_match:
                            sev_level, facility, message = asa_match.groups()
                            severity = SYSLOG_LEVELS.get(int(sev_level), 'INFO')
                        else:
                            severity, facility, message = 'INFO', 'ASA', ''
                    else:
                        # 일반 형식 시도
                        parts = match.groups()
                        if len(parts) >= 4:
                            timestamp, sev_level, facility, message = parts[:4]
                            if sev_level.isdigit():
                                severity = SYSLOG_LEVELS.get(int(sev_level), 'INFO')
                            else:
                                severity = sev_level
                        else:
                            severity, facility, message = 'INFO', 'ASA', ''
                    
                    log_entry.update({
                        'timestamp': timestamp,
                        'severity': severity.upper(),
                        'facility': facility,
                        'message': message
                    })
                    
                    # 타임스탬프 객체 변환 시도
                    try:
                        log_entry['timestamp_obj'] = self.parse_timestamp(timestamp)
                    except:
                        pass
            
            elif device_type == 'router':
                # ISR/ASR 라우터 형식 처리
                if len(match.groups()) >= 4:
                    parts = match.groups()
                    
                    if len(parts) == 5:
                        timestamp, component, sev_level, facility, message = parts
                        if sev_level.isdigit():
                            severity = SYSLOG_LEVELS.get(int(sev_level), 'INFO')
                        else:
                            severity = 'INFO'
                    else:
                        timestamp, facility, message = parts[0], parts[2], parts[-1]
                        severity = 'INFO'
                        
                        # 시설에서 심각도 레벨 찾기
                        severity_match = re.search(r'-(\d)-', facility)
                        if severity_match:
                            sev_level = int(severity_match.group(1))
                            if sev_level in SYSLOG_LEVELS:
                                severity = SYSLOG_LEVELS[sev_level]
                    
                    log_entry.update({
                        'timestamp': timestamp,
                        'severity': severity.upper(),
                        'facility': facility,
                        'message': message
                    })
                    
                    # 타임스탬프 객체 변환 시도
                    try:
                        log_entry['timestamp_obj'] = self.parse_timestamp(timestamp)
                    except:
                        pass
            
            elif device_type == 'sdwan':
                # SD-WAN 형식 처리
                if len(match.groups()) >= 3:
                    timestamp, severity, facility, *message_parts = match.groups()
                    
                    # 메시지 결합
                    message = ' '.join(message_parts) if message_parts else ''
                    
                    # 심각도 처리
                    if not severity.upper() in SEVERITY_COLORS:
                        severity = 'INFO'  # 기본값
                    
                    log_entry.update({
                        'timestamp': timestamp,
                        'severity': severity.upper(),
                        'facility': facility,
                        'message': message
                    })
                    
                    # 타임스탬프 객체 변환 시도
                    try:
                        log_entry['timestamp_obj'] = self.parse_timestamp(timestamp)
                    except:
                        pass
            
            return log_entry
            
        except Exception as e:
            print(f"로그 파싱 오류: {str(e)}")
            return log_entry