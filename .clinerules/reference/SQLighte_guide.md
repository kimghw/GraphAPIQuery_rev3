# SQLite 사용자 가이드

## 📋 개요
이 프로젝트에서 SQLite는 개발 및 테스트 환경의 기본 데이터베이스로 사용됩니다. 사용자가 기술스택 단계에서 알아야 하는 SQLite 관련 핵심 정보를 정리했습니다.

---

## 🎯 SQLite 역할 및 용도

### 주요 사용 목적
- **개발환경**: 로컬 개발 시 기본 데이터베이스
- **테스트환경**: 단위/통합 테스트용 임시 데이터베이스  
- **프로토타이핑**: 빠른 개발 및 검증용
- **단일 사용자**: 개인용 또는 소규모 애플리케이션

### 환경별 데이터베이스 전략
```
개발환경: SQLite (로컬 파일)
테스트환경: SQLite (임시 파일)
운영환경: PostgreSQL (서버 기반)
```

---

## 🔧 SQLite 특징 및 제약사항

### ✅ 장점
- **파일 기반**: 단일 파일로 전체 데이터베이스 저장
- **서버리스**: 별도 데이터베이스 서버 불필요
- **경량**: 설치 및 설정이 간단
- **이식성**: 파일 복사만으로 데이터베이스 이동 가능
- **ACID 준수**: 트랜잭션 안전성 보장
- **SQL 표준**: 표준 SQL 문법 지원

### ⚠️ 제약사항
- **동시성 제한**: 다중 사용자 환경에서 성능 제약
- **확장성 한계**: 대용량 데이터 처리에 부적합
- **네트워크 접근 불가**: 원격 접근 지원 안함
- **사용자 관리 없음**: 권한 관리 기능 제한적
- **데이터 타입 제한**: 일부 고급 데이터 타입 미지원

---

## ⚙️ 프로젝트 내 SQLite 설정

### 기본 설정 (config/settings.py)
```python
# 개발환경
DATABASE_URL: str = "sqlite:///./graphapi.db"

# 테스트환경  
DATABASE_URL: str = "sqlite:///./test_graphapi.db"

# 비동기 변환 (자동)
sqlite:///./graphapi.db → sqlite+aiosqlite:///./graphapi.db
```

### 환경별 설정
```python
class DevelopmentSettings(Settings):
    DATABASE_URL = "sqlite:///./graphapi.db"

class TestSettings(Settings):
    DATABASE_URL = "sqlite:///./test_graphapi.db"

class ProductionSettings(Settings):
    DATABASE_URL = "postgresql://user:pass@host:port/db"
```

---

## 🚀 SQLite 성능 최적화 (자동 적용)

### 프로젝트에서 자동 설정되는 최적화
```python
# adapters/db/database.py에서 자동 적용
cursor.execute("PRAGMA foreign_keys=ON")        # 참조 무결성
cursor.execute("PRAGMA journal_mode=WAL")        # 동시 읽기/쓰기
cursor.execute("PRAGMA synchronous=NORMAL")      # 성능 향상
cursor.execute("PRAGMA temp_store=MEMORY")       # 메모리 임시 저장
cursor.execute("PRAGMA mmap_size=268435456")     # 256MB 메모리 매핑
```

### 각 설정의 효과
- **WAL 모드**: 읽기와 쓰기 동시 실행 가능
- **Foreign Keys**: 데이터 무결성 강화
- **Memory Temp Store**: 임시 데이터 처리 속도 향상
- **MMAP**: 파일 I/O 성능 대폭 개선

---

## 📁 데이터베이스 파일 관리

### 파일 위치
```
프로젝트 루트/
├── graphapi.db          # 개발용 데이터베이스
├── test_graphapi.db     # 테스트용 데이터베이스
└── .token_cache.json    # OAuth 토큰 캐시
```

### 파일 관리 명령어
```bash
# 데이터베이스 파일 확인
ls -la *.db

# 데이터베이스 크기 확인
du -h graphapi.db

# 데이터베이스 백업
cp graphapi.db graphapi_backup_$(date +%Y%m%d).db

# 데이터베이스 초기화 (주의!)
rm graphapi.db
python -c "from adapters.db.database import migrate_database_sync; from config.settings import get_settings; migrate_database_sync(get_settings())"
```

---

## 🔄 운영환경 전환 가이드

### SQLite → PostgreSQL 전환 절차

#### 1. 환경변수 설정
```bash
# .env 파일 수정
DATABASE_URL=postgresql://username:password@localhost:5432/graphapi_prod
```

#### 2. PostgreSQL 설치 및 설정
```bash
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# macOS
brew install postgresql

# 데이터베이스 생성
createdb graphapi_prod
```

#### 3. 의존성 확인
```bash
# requirements.txt에 이미 포함됨
psycopg2-binary==2.9.9
```

#### 4. 마이그레이션 실행
```bash
# 테이블 생성
python -c "from adapters.db.database import migrate_database_sync; from config.settings import get_settings; migrate_database_sync(get_settings())"
```

#### 5. 데이터 이전 (필요시)
```python
# 데이터 이전 스크립트 예시
import sqlite3
import psycopg2
from config.settings import get_settings

def migrate_data():
    # SQLite에서 데이터 읽기
    sqlite_conn = sqlite3.connect('graphapi.db')
    
    # PostgreSQL에 데이터 쓰기
    settings = get_settings()
    pg_conn = psycopg2.connect(settings.DATABASE_URL)
    
    # 데이터 이전 로직 구현
    # ...
```

---

## 🛠️ 개발자 도구 및 팁

### SQLite 명령줄 도구
```bash
# SQLite CLI 접속
sqlite3 graphapi.db

# 테이블 목록 확인
.tables

# 스키마 확인
.schema accounts

# 데이터 조회
SELECT * FROM accounts LIMIT 5;

# 종료
.quit
```

### GUI 도구 추천
- **DB Browser for SQLite**: 무료 GUI 도구
- **SQLiteStudio**: 크로스 플랫폼 GUI
- **DBeaver**: 범용 데이터베이스 도구
- **VSCode SQLite Extension**: 에디터 내 통합

### 디버깅 팁
```python
# 쿼리 로깅 활성화 (개발환경에서 자동)
DATABASE_ECHO = True  # config/settings.py

# 수동 쿼리 실행
from adapters.db.database import get_database_adapter
db = get_database_adapter()
with db.session_scope() as session:
    result = session.execute("SELECT COUNT(*) FROM accounts")
    print(result.scalar())
```

---

## ⚠️ 주의사항 및 모범 사례

### 운영환경 사용 금지
```python
# ❌ 운영환경에서 SQLite 사용 금지
if settings.ENVIRONMENT == "production" and "sqlite" in settings.DATABASE_URL:
    raise ValueError("SQLite는 운영환경에서 사용할 수 없습니다")
```

### 파일 권한 관리
```bash
# 데이터베이스 파일 권한 확인
ls -la graphapi.db

# 권한 설정 (필요시)
chmod 644 graphapi.db
```

### 백업 전략
```bash
# 정기 백업 스크립트
#!/bin/bash
BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
cp graphapi.db "$BACKUP_DIR/graphapi_$DATE.db"

# 7일 이상 된 백업 파일 삭제
find $BACKUP_DIR -name "graphapi_*.db" -mtime +7 -delete
```

### 동시성 고려사항
```python
# 높은 동시성이 필요한 경우 PostgreSQL 사용
if concurrent_users > 10:
    print("PostgreSQL 사용을 권장합니다")
    
# SQLite 사용 시 연결 풀 설정
engine = create_engine(
    "sqlite:///./graphapi.db",
    poolclass=StaticPool,
    connect_args={"check_same_thread": False}
)
```

---

## 🔍 트러블슈팅

### 자주 발생하는 문제

#### 1. 데이터베이스 잠금 오류
```
sqlite3.OperationalError: database is locked
```
**해결방법**:
```bash
# 프로세스 종료 후 재시도
pkill -f python
rm -f graphapi.db-wal graphapi.db-shm
```

#### 2. 파일 권한 오류
```
sqlite3.OperationalError: unable to open database file
```
**해결방법**:
```bash
# 권한 확인 및 수정
ls -la graphapi.db
chmod 644 graphapi.db
```

#### 3. 디스크 공간 부족
```
sqlite3.OperationalError: disk I/O error
```
**해결방법**:
```bash
# 디스크 공간 확인
df -h
# 불필요한 파일 정리
rm -f *.db-wal *.db-shm
```

### 성능 문제 해결
```python
# 연결 풀 크기 조정
engine = create_engine(
    database_url,
    pool_size=1,        # SQLite는 단일 연결 권장
    max_overflow=0,
    pool_timeout=30
)

# 트랜잭션 최적화
with db.session_scope() as session:
    # 여러 작업을 하나의 트랜잭션으로 묶기
    session.add_all([obj1, obj2, obj3])
    # 자동 커밋됨
```

---

## 📚 추가 학습 자료

### 공식 문서
- [SQLite 공식 문서](https://sqlite.org/docs.html)
- [SQLAlchemy SQLite 가이드](https://docs.sqlalchemy.org/en/14/dialects/sqlite.html)
- [aiosqlite 문서](https://aiosqlite.omnilib.dev/)

### 모범 사례
- SQLite 성능 최적화 가이드
- 데이터베이스 마이그레이션 전략
- 백업 및 복구 절차

이 가이드를 통해 프로젝트에서 SQLite를 효과적으로 활용하고, 필요시 운영환경으로 원활하게 전환할 수 있습니다.
