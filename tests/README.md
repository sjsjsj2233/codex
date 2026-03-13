# 테스트 가이드

이 디렉토리는 Network Automation 프로젝트의 자동화 테스트를 포함합니다.

## 테스트 실행 방법

### 모든 테스트 실행

```bash
# 프로젝트 루트 디렉토리에서
python -m unittest discover tests -v
```

### 특정 테스트 파일 실행

```bash
# parsers 테스트만 실행
python -m unittest tests.test_parsers -v

# workers 테스트만 실행
python -m unittest tests.test_workers -v
```

### 특정 테스트 클래스 실행

```bash
python -m unittest tests.test_parsers.TestDeviceParser -v
```

### 특정 테스트 메서드 실행

```bash
python -m unittest tests.test_parsers.TestDeviceParser.test_parse_run_hostname_success -v
```

## 테스트 커버리지

### test_parsers.py (19 테스트)
- Cisco IOS 파싱 기능 테스트
- Nexus 파싱 기능 테스트
- 엣지 케이스 테스트

### test_workers.py (14 테스트)
- NetworkWorker 초기화 테스트
- 호스트명 추출 및 검증 테스트
- 파일명 생성 테스트
- 출력 정리 테스트

## 테스트 작성 가이드

### 1. 테스트 파일 위치
- 모든 테스트 파일은 `tests/` 디렉토리에 위치
- 테스트 파일명은 `test_*.py` 형식

### 2. 테스트 클래스 구조
```python
import unittest

class TestClassName(unittest.TestCase):
    def setUp(self):
        """각 테스트 전에 실행"""
        pass

    def tearDown(self):
        """각 테스트 후에 실행"""
        pass

    def test_something(self):
        """테스트 메서드는 test_로 시작"""
        self.assertEqual(actual, expected)
```

### 3. 테스트 명명 규칙
- 테스트 메서드: `test_기능_조건`
  - 예: `test_parse_hostname_success`
  - 예: `test_parse_hostname_not_found`

### 4. 주요 Assertion 메서드
```python
self.assertEqual(a, b)          # a == b
self.assertNotEqual(a, b)       # a != b
self.assertTrue(x)              # bool(x) is True
self.assertFalse(x)             # bool(x) is False
self.assertIsNone(x)           # x is None
self.assertIsNotNone(x)        # x is not None
self.assertIn(a, b)            # a in b
self.assertNotIn(a, b)         # a not in b
self.assertRaises(Exception)   # 예외 발생 확인
```

## 테스트 결과 해석

```
Ran 33 tests in 0.014s

OK
```

- `Ran X tests`: X개의 테스트 실행
- `OK`: 모든 테스트 통과
- `FAILED (failures=N)`: N개의 테스트 실패
- `FAILED (errors=N)`: N개의 테스트에서 에러 발생

## CI/CD 통합

향후 GitHub Actions 또는 다른 CI/CD 도구와 통합 가능:

```yaml
# .github/workflows/test.yml 예시
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: python -m unittest discover tests -v
```

## 모의 테스트 (Mocking)

네트워크 연결 테스트는 실제 장비 없이 mock을 사용:

```python
from unittest.mock import Mock, patch

@patch('paramiko.SSHClient')
def test_ssh_connection(self, mock_ssh):
    # 테스트 코드
    pass
```

## 개선 계획

- [ ] 코드 커버리지 도구 추가 (coverage.py)
- [ ] 통합 테스트 추가
- [ ] 성능 테스트 추가
- [ ] UI 테스트 추가 (PyQt5)
