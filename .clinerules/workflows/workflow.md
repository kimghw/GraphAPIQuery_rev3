2. 단계별 작업 순서(예시)
2.1 초기 세팅 단계
가상환경 & 패키지 설치

python 3.11(or 3.10) 환경 준비

Poetry, Pipenv, 또는 venv 사용. 의존성 패키지( FastAPI, SQLAlchemy, Pydantic, Typer 등 )를 설치

pyproject.toml이나 requirements.txt에 버전 명시

프로젝트 기본 구조 생성

위와 같은 폴더 구조를 대략 잡아두기(아직 폴더가 비어 있어도 무방)

core/, adapters/, tests/ 디렉터리 및 main.py, cli_app.py(혹은 cli.py) 파일 생성

Pydantic-Settings 기반 설정 어댑터 초안

adapters/config 폴더 아래에서 ConfigPort (추상화)와 ConfigAdapter (Pydantic Settings) 구상

.env 파일 예시를 만들고, Pydantic Settings로 로드해보는 예제 코드 작성

FastAPI와 CLI 공통으로 사용할 설정 객체를 생성(예: get_settings() 함수)

기본 main.py & CLI 스켈레톤

main.py(FastAPI):

python
복사
from fastapi import FastAPI
from adapters.api import router as api_router
from adapters.config import get_settings

def create_app() -> FastAPI:
    app = FastAPI()
    settings = get_settings()
    # 라우터 등록
    app.include_router(api_router)
    # 기타 startup/shutdown 이벤트
    return app

app = create_app()
cli_app.py(Typer):

python
복사
import typer
from adapters.config import get_settings

app = typer.Typer()

@app.command("hello")
def hello_command():
    settings = get_settings()
    typer.echo("Hello from CLI with env: " + settings.ENVIRONMENT)

if __name__ == "__main__":
    app()
2.2 도메인(Entity) 및 유즈케이스(UseCase) 설계/구현 단계
도메인 엔티티 정의(core/domain)

예) UserAccount, AuthToken, EmailMessage, MailAttachment 등

비즈니스 규칙(예: 유효한 메일 주소인지, 토큰 만료시간 계산 등)을 담을 수 있는 메서드 or ValueObject를 정의

Graph API와 상관없이 “우리 시스템에서 다뤄야 하는 이메일/사용자”의 핵심 속성을 우선 정의

유즈케이스 초안(core/usecases)

예: RegisterAccountUseCase, RenewTokenUseCase, FetchMailUseCase, SendMailUseCase 등

단일 진입점(메서드 or 함수)으로 하고, Input/Output DTO(또는 Pydantic 모델)를 명세

포트(Ports) 인터페이스: 유즈케이스가 필요한 외부 리소스(API, DB, Cache 등)를 메서드 시그니처만 있는 추상 클래스로 정의

python
복사
class AuthRepositoryPort(Protocol):
    def save_account(self, account: UserAccount): ...
    def find_account_by_email(self, email: str) -> UserAccount | None: ...
    # ...
서비스(core/services)

내부적으로 “메일 본문 전처리”나 “스팸 필터링” 같은 독립 로직이 있다면 서비스 레이어로 분리

“비즈니스 로직, 규칙을 표현하는 메서드”가 주로 위치

유즈케이스와 달리 “어떤 의도된 사용자 시나리오인지” 보다는 “도메인 동작 로직”에 집중

단위 테스트(tests/unit)

도메인 엔티티 / 유즈케이스 / 서비스에 대한 “순수 파이썬” 단위 테스트를 작성

아직 DB나 Graph API 연동이 구현되지 않았으므로, 포트들을 Mock 또는 Fake로 대체

결과물:
- “내부 로직”은 대부분 완성된 상태.
- “외부 어댑터” 없이도 코어 레벨 단위 테스트가 통과.

2.3 어댑터(포트 구현) 및 통합 단계
DB Adapter(adapters/db)

SQLAlchemy(Alembic) 설정 & RepositoryPort 인터페이스 구현

예: AuthRepositoryImpl, MailRepositoryImpl 등이 Core에 선언된 Port(Protocol/ABC)를 실제 DB CRUD로 구현

Alembic 설정 폴더(alembic/)에서 마이그레이션 스크립트 생성(테이블 스키마 UserAccounts, MailHistories 등)

DB 세션 주입: FastAPI Depends 또는 함수 인자로 주입, CLI에서도 asyncio.run() 혹은 DB Connection context를 사용

MS Graph Adapter(adapters/msgraph)

인증/토큰: MSAL 라이브러리 이용, AuthFlowPort(Core에서 정의) 구현체

Authorization Code Flow(로그인 URL 생성, 콜백 처리)

Device Code Flow(콘솔 환경에서 입력)

토큰 저장/조회는 DB Adapter와 연동

메일 조회/전송: Graph API(HTTP) 호출 로직

MailServicePort(Core에서 정의)를 구현

delta link, webhook 등록/갱신, 증분 메일 조회 등

API Adapter(adapters/api)

FastAPI 라우터로, 유즈케이스 별 HTTP Endpoint 구성

Request/Response DTO(Pydantic model)를 정의해 @router.post 등으로 매핑

비즈니스 로직은 호출만 하고, “Request 파싱 → UseCase 호출 → Response 변환” 정도만 담당(얇은 레이어)

CLI Adapter(adapters/cli)

Typer 기반으로, @app.command를 통해 “계정 등록” register_account, “토큰 갱신” renew_token 등 명령어 제공

역시 “입력 파싱 → UseCase 호출 → 결과 출력” 으로 얇게 처리

테스트 - 통합/엔드투엔드(tests/integration, e2e)

DB 연결 + MS Graph Mock or 실 API Key(개발 계정)와 연동 테스트

Docker-compose로 테스트 환경 구축(필요 시)

FastAPI TestClient/pytest-asyncio로 E2E(HTTP 요청 → DB/외부 API → 응답) 시나리오 확인

CLI E2E는 “click.testing.CliRunner” 혹은 Typer 자체 test runner로 검증

결과물:
- 모든 어댑터(DB, Graph, API, CLI)가 연결되어 “실제 동작” 가능한 상태.

2.4 고급 기능(Worker, Webhook, 모니터링 등)
증분 메일 모니터링

delta link & subscription webhook

FastAPI 내에 Webhook 수신 Endpoint 마련( POST /graph-webhook/notify 등 )

webhook이 실패하거나 만료될 경우 fallback(폴링)

Scheduler/Worker: Celery, RQ, 혹은 AsyncIO 주기 실행 등 구현

Core 유즈케이스 호출 → DB에 기록 → 외부 API 전송

PII 마스킹, 첨부파일 업로드

HTML → 텍스트 변환, 정규식 마스킹 로직(core/services 폴더)에 추가

첨부파일은 /attachments API → S3/Blob 등으로 업로드 → DB에 메타데이터 저장

알림(Slack, SMS, Discord)

Core에서 “특정 키워드 감지 시 알림” 유즈케이스/서비스

실제 전송은 adapters/notifications(또는 worker) 형태로 구현

로깅 & 모니터링

structlog/JSON 포맷 로거 통일 → logging_config.py 등으로 공통 설정

Sentry / NewRelic 등 연동(옵션)

FastAPI middleware / exception_handler로 예외 포맷 통일

2.5 운영/릴리스(Deployment) 준비
Docker 컨테이너(선택)

Dockerfile + docker-compose.yml 작성

production/staging/dev 모드별 환경변수 세팅

CI/CD 파이프라인

린트(black/isort), 타입체크(mypy), 테스트(pytest), 빌드(Docker) 단계 설정

GitHub Actions, GitLab CI, Jenkins 등 선택

운영 환경 설정 & 문서화

.env.prod, .env.staging 분리

API Usage 문서(Swagger + 추가 설명), CLI 사용 가이드

DB 마이그레이션 방법 정리(알림, 실행 순서 등)

실 서버/테넌트 연결 테스트

실제 Microsoft 365 Test Tenant(개발자용)로 연결, O365 Admin 설정

Token Refresh, Webhook Subscription 만료 주기(최대 4230분) 자동 갱신 등

3. 작업 단계별 유의사항
Domain-Driven:

DB 스키마보다 먼저 Core 도메인을 정의해, “업무상 필요한 개념”이 잘 표현되도록.

Ports/Interfaces:

“Core가 필요로 하는 메서드”를 먼저 설계(Port), 어댑터는 그에 맞춰 구현.

의존성 방향: Core ←(Interface)→ Adapters.

Pydantic 모델 분리:

Core 엔티티 vs. Adapters용 DTO(입출력) 구분.

규모 작으면 동일 모델 재사용 가능하지만, “Graph API Response” 그대로 Core에 침투하지 않도록 주의.

애플리케이션 계층의 ‘얇은 어댑터’

Router나 CLI는 “입력 파싱 + UseCase 호출 + 결과 반환” 정도로만 유지.

테스트 우선(단위 → 통합 → E2E)

핵심 유즈케이스 로직을 먼저 단위 테스트로 검증 → DB나 Graph 연결(통합 테스트) → 실제(혹은 mock) 환경으로 E2E.

MS Graph는 네트워크/계정 상태에 따라 불안정할 수 있으니, mock server나 VCR.py(HTTP mocking) 활용을 검토.

점진적 완성

초기엔 “인증(Authorize) → 토큰발급 → 메일 조회” 같이 핵심 플로우 1~2개만 완성 → 이후 확장(증분조회, webhook, 첨부, 알림 등).

너무 많은 기능을 동시에 붙이면 복잡도가 급상승.

배포 전 종합 리팩토링

첫 MVP 완료 뒤, 필요 없는 중복 로직/명칭/폴더 구조를 정리하여 “가독성과 유지보수성”을 보장.

4. 최종 요약
아래 순서로 진행하면 핵심 로직을 빠르게 확보하고, 외부 연동/어댑터는 단계별로 안전하게 붙일 수 있습니다.

프로젝트 골격 구성:

폴더 구조, Pydantic Settings, FastAPI/CLI 스켈레톤, Alembic 초기화

도메인 & 유즈케이스 구현 + 단위 테스트:

DB나 외부 API 없이도 동작·테스트 가능

DB/Graph Adapter:

Repository/Service 포트 구현, 통합 테스트

API/CLI 라우터/커맨드:

Core 호출(비즈니스 로직) → 어댑터로 결과 확인

Webhook/증분조회/알림 등 고급 기능:

Worker, Webhook Subscription, PII마스킹, 첨부파일 처리

운영 준비:

Docker/CI/CD, 문서화, 설정 분리, 모니터링(로깅/Sentry)

이 순서를 따르면, 코어 로직의 독립성을 가장 먼저 확보하고, 이후에 필요한 외부 연동 기능을 “포트/어댑터” 구조로 점차 안정적으로 연결할 수 있습니다.
이를 통해 클린 아키텍처 원칙, 얇은 어댑터 구현 그리고 FastAPI + Typer 공존 구조를 유지하면서, “Microsoft 365 메일 수집/동기화” 시스템을 안전하게 완성할 수 있을 것입니다.