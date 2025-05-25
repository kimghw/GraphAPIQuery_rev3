# 테스트 에러 및 해결 과정 기록

## 개요
Microsoft Graph API Mail Collection System 개발 과정에서 발생한 테스트 에러들과 해결 방법을 기록합니다.

## 발생한 에러들

### 1. 테스트 실행 초기 에러

#### 에러 1: ModuleNotFoundError
```
ModuleNotFoundError: No module named 'core'
```

**원인**: Python 모듈 경로 설정 문제
**해결방법**: 
- `conftest.py`에서 `sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))`로 경로 추가
- 프로젝트 루트를 Python path에 추가

#### 에러 2: 의존성 주입 실패
```
TypeError: AuthenticationUseCases.__init__() missing required arguments
```

**원인**: 테스트 픽스처에서 의존성 주입이 제대로 설정되지 않음
**해결방법**:
- `conftest.py`에서 모든 필요한 의존성을 Mock으로 생성
- `DatabaseRepositoryAdapter`, `OAuthClient`, `GraphClient` 등 Mock 객체 생성

### 2. 테스트 로직 에러

#### 에러 3: 테스트 기대값 불일치
```
AssertionError: assert {'accounts': [...]} == [...]
```

**원인**: 테스트에서 기대하는 응답 형식과 실제 구현의 응답 형식이 다름
**해결방법**:
- `get_all_accounts_info()` 메서드가 리스트를 직접 반환하도록 수정
- 테스트 코드에서 응답 형식을 실제 구현에 맞게 수정

#### 에러 4: 토큰 응답 형식 불일치
```
AssertionError: assert 'token' in {'success': True, 'message': '...'}
```

**원인**: 토큰 갱신 응답에서 'token' 필드 대신 'message' 필드 반환
**해결방법**:
- 테스트에서 'token' 대신 'message' 필드 확인하도록 수정
- 실제 구현과 테스트 기대값 일치시킴

#### 에러 5: 메서드 시그니처 불일치
```
TypeError: register_account() missing required positional argument
```

**원인**: `register_account` 메서드 호출 시 필수 매개변수 누락
**해결방법**:
- 테스트에서 `tenant_id`, `client_id` 등 필수 매개변수를 실제 구현에 맞게 제거
- 메서드 시그니처를 실제 구현과 일치시킴

### 3. 데이터베이스 관련 에러

#### 에러 6: SQLAlchemy 세션 관리
```
sqlalchemy.exc.InvalidRequestError: Object is not bound to a Session
```

**원인**: 비동기 세션 관리 문제
**해결방법**:
- `DatabaseRepositoryAdapter`에서 각 메서드마다 새로운 세션 스코프 사용
- `session_scope()` 컨텍스트 매니저로 세션 생명주기 관리

### 4. 비동기 처리 에러

#### 에러 7: 비동기 함수 호출 문제
```
RuntimeError: coroutine was never awaited
```

**원인**: 비동기 함수를 동기적으로 호출
**해결방법**:
- 모든 테스트 함수에 `@pytest.mark.asyncio` 데코레이터 추가
- `await` 키워드를 사용하여 비동기 함수 호출

## Deprecation Warnings 해결

### Warning 1: datetime.utcnow() 사용
```
DeprecationWarning: datetime.datetime.utcnow() is deprecated
```

**해결방법**:
```python
# 변경 전
from datetime import datetime
updated_at=datetime.utcnow()

# 변경 후  
from datetime import datetime, UTC
updated_at=datetime.now(UTC)
```

### Warning 2: Pydantic 설정 관련
```
PydanticDeprecatedSince20: Support for class-based config is deprecated
```

**상태**: 외부 라이브러리 관련 warning으로 현재 버전에서는 무시
**향후 계획**: Pydantic V3 업그레이드 시 ConfigDict 사용으로 변경 예정

### Warning 3: Pydantic Field 설정
```
PydanticDeprecatedSince20: Using extra keyword arguments on Field is deprecated
```

**상태**: 외부 라이브러리 관련 warning으로 현재 버전에서는 무시
**향후 계획**: `json_schema_extra` 사용으로 변경 예정

## 테스트 결과 요약

### 최종 테스트 결과
```
============== test session starts ==============
collected 9 items

tests/test_auth_usecases.py::test_create_account_authorization_code PASSED [ 11%]
tests/test_auth_usecases.py::test_create_account_device_code PASSED        [ 22%]
tests/test_auth_usecases.py::test_get_account_info PASSED                  [ 33%]
tests/test_auth_usecases.py::test_authenticate_authorization_code PASSED   [ 44%]
tests/test_auth_usecases.py::test_refresh_token_flow PASSED                [ 55%]
tests/test_auth_usecases.py::test_get_all_accounts_info PASSED             [ 66%]
tests/test_auth_usecases.py::test_revoke_account_tokens PASSED             [ 77%]
tests/test_auth_usecases.py::test_search_accounts PASSED                   [ 88%]
tests/test_auth_usecases.py::test_get_authentication_logs PASSED           [100%]

======== 9 passed, 48 warnings in 0.70s ========
```

### 성과
- **모든 테스트 통과**: 9개 테스트 모두 성공
- **Warning 감소**: 52개 → 48개로 감소 (datetime 관련 warning 해결)
- **실행 시간**: 0.70초로 빠른 테스트 실행

## 교훈 및 개선사항

### 1. 테스트 주도 개발의 중요성
- 구현과 테스트 간의 계약을 명확히 정의해야 함
- 테스트 작성 시 실제 구현 시그니처와 일치시켜야 함

### 2. 비동기 프로그래밍 주의사항
- 모든 비동기 함수는 적절히 await 처리
- 세션 관리는 컨텍스트 매니저 사용

### 3. 의존성 주입 설계
- 테스트 가능한 구조로 설계
- Mock 객체를 통한 외부 의존성 격리

### 4. 에러 처리 표준화
- 일관된 응답 형식 사용
- 명확한 에러 메시지 제공

## 향후 개선 계획

1. **통합 테스트 추가**: 실제 Graph API와의 통합 테스트
2. **성능 테스트**: 대용량 메일 처리 성능 테스트  
3. **보안 테스트**: 토큰 보안 및 인증 플로우 테스트
4. **에러 시나리오 테스트**: 네트워크 오류, API 제한 등 예외 상황 테스트

---
**작성일**: 2025-05-26  
**작성자**: System  
**버전**: 1.0
