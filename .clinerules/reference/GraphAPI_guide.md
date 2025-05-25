# 📘 Microsoft Graph API 이메일 조회 완벽 가이드

이 문서는 Microsoft Graph API를 활용하여 특정 사용자 또는 모든 사용자의 메일을 효과적으로 조회하는 방법을 체계적으로 안내합니다. OData 쿼리 매개변수를 활용한 기본 및 고급 필터링 예제를 포함하고 있습니다.

### 1. 기본 API 엔드포인트

- **내 메일 조회 (위임된 권한):**
  ```http
  GET [https://graph.microsoft.com/v1.0/me/messages](https://graph.microsoft.com/v1.0/me/messages)
  ```
- **특정 사용자 메일 조회 (위임된/애플리케이션 권한):**
  ```http
  GET [https://graph.microsoft.com/v1.0/users/](https://graph.microsoft.com/v1.0/users/){사용자 ID 또는 UPN}/messages
  ```

---

### 2. 핵심 OData 쿼리 매개변수

| 매개변수      | 설명                                                               | 사용 예시                                   |
| :---------- | :----------------------------------------------------------------- | :------------------------------------------ |
| **`$select`** | 응답에 포함할 특정 필드만 선택하여 데이터 크기를 최적화합니다.     | `$select=subject,from,receivedDateTime`     |
| **`$filter`** | 특정 조건에 맞는 데이터만 필터링합니다.                            | `$filter=isRead eq false` (읽지 않은 메일만) |
| **`$orderby`** | 결과를 특정 필드를 기준으로 정렬합니다. (`asc`/`desc`)             | `$orderby=receivedDateTime desc` (최신순)    |
| **`$top`** | 결과의 개수를 상위 N개로 제한합니다.                               | `$top=10` (최대 10개)                      |
| **`$search`** | 키워드로 메시지를 검색합니다. (인덱싱된 모든 필드에서 검색)        | `$search="회의록"`                          |

---

### 3. 주요 조회 시나리오별 API 요청 예시

*아래 모든 예시는 `https://graph.microsoft.com/v1.0` 뒤에 붙여서 사용하시면 됩니다.*

#### 📈 **A. 기간 및 개수 필터링**

**1. 최근 메일 10개 조회**
> `orderby`로 최신순 정렬 후 `top`으로 개수를 제한합니다.
```http
GET /me/messages?$orderby=receivedDateTime desc&$top=10
```

**2. 특정 기간의 메일 조회 (예: 2025년 5월)**
> `filter`를 사용하여 `receivedDateTime`이 특정 범위에 있는지 확인합니다.
```http
GET /me/messages?$filter=receivedDateTime ge 2025-05-01T00:00:00Z and receivedDateTime lt 2025-06-01T00:00:00Z
```

#### 📂 **B. 상태 및 속성 필터링**

**1. 읽지 않은 메일만 조회**
> `isRead` 속성을 `false`로 필터링합니다.
```http
GET /me/messages?$filter=isRead eq false
```

**2. 특정인에게서 온 메일 조회**
> `from` 주소의 `emailAddress` 객체를 필터링합니다.
```http
GET /me/messages?$filter=from/emailAddress/address eq 'noreply@google.com'
```

**3. '중요' 표시가 있는 메일만 조회**
> `importance` 속성을 필터링합니다. (`low`, `normal`, `high`)
```http
GET /me/messages?$filter=importance eq 'high'
```

#### 🔍 **C. 내용 검색 및 필드 선택**

**1. 제목, 본문 등에서 키워드 검색**
> `search`를 사용하여 자유로운 텍스트 검색을 수행합니다. (가장 편리함)
```http
GET /me/messages?$search="프로젝트 제안서"
```

**2. 특정 필드만 선택하여 조회 (성능 최적화)**
> `select`를 사용하여 제목, 보낸 사람, 받은 날짜만 가져옵니다.
```http
GET /me/messages?$select=subject,from,receivedDateTime
```

**3. 본문을 일반 텍스트(TEXT) 형식으로 받기**
> `Prefer` 헤더를 추가하여 HTML이 아닌 TEXT 형식의 본문을 요청합니다.
```http
GET /me/messages?$select=subject,body
Prefer: outlook.body-content-type="text"
```

---

### 4. 고급 조합 예시

> **"2025년 5월 한 달간 '김민준'에게서 온 읽지 않은 메일을 최신순으로 5개 조회하되, 제목과 받은 날짜만 가져오기"**

```http
GET /me/messages?$filter=receivedDateTime ge 2025-05-01T00:00:00Z and receivedDateTime lt 2025-06-01T00:00:00Z and from/emailAddress/address eq 'minjun.kim@example.com' and isRead eq false&$orderby=receivedDateTime desc&$top=5&$select=subject,receivedDateTime
```
다음 표·가이드를 프로젝트 요구사항 문서에 그대로 삽입해도 될 수준으로 정리했습니다.

---

## 1. 공통 전제 & 세팅

| 구분                           | 내용                                                                                                                                                                                                                     |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **엔드포인트 도메인**                | `https://graph.microsoft.com/v1.0` (베타 기능이 필요하면 `/beta`, 단 프로덕션 전에는 `/v1.0`으로 교체)                                                                                                                                      |
| **AAP 등록 시 필수 Redirect URI** | Web : `https://{YOUR_DOMAIN}/auth/callback`<br>Native/CLI : `http://localhost:{PORT}`                                                                                                                                  |
| **권장 권한 스코프**                | `offline_access` (리프레시 토큰)<br>`User.Read`, `Mail.Read`, `Mail.ReadWrite`, `Mail.Send`<br>`MailboxSettings.ReadWrite` (타임존·언어),<br>`Directory.Read.All` (AUTH005/006에서 사용자·스코프 점검)<br>`Policy.Read.All` (조직 정책 점검 필요 시) |
| **토큰 획득 흐름**                 | • **Authorization Code Flow** : 표준 3-leg OAuth2 (AUTH001 기본)<br>• **Device Code Flow** : CLI·머신 계정용 (AUTH001 선택)                                                                                                       |
| **Rate-Limit 가이드**           | 10 000 req/10 min 앱 한도, 1 000 req/10 min × 사용자 한도·컨커런시 ≤ 4 요청 / 사용자·메일박스                                                                                                                                               |

---

## 2. 유즈케이스별 Graph API 매핑

| 코드                         | Graph API Endpoint                                                                                                              | HTTP Verb                                                                 | 권한 스코프                                    | 비고 / 가이드라인                                                                                       |                                                              |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- | ----------------------------------------- | ------------------------------------------------------------------------------------------------ | ------------------------------------------------------------ |
| **AUTH001**<br>계정 등록       | n/a (토큰 엔드포인트 `/oauth2/v2.0/token`)                                                                                             | `POST`                                                                    | `offline_access` + 등록 스코프                 | 성공 후 **`GET /me`** 로 토큰 유효성 1차 검사                                                                |                                                              |
| **AUTH002**<br>사용자 CRUD 조회 | • \`GET /users/{id                                                                                                              | userPrincipalName}`<br>• `PATCH /users/{id}`<br>• `DELETE /users/{id}\`   | `GET /PATCH /DELETE`                      | `Directory.Read.All` (+ `Directory.AccessAsUser.All` 수정·삭제)                                      | 삭제 대신 `"accountEnabled": false` 소프트-삭제 권장                    |
| **AUTH003**<br>사용자 인증 재실행  | n/a (다시 인증 URL 발급)                                                                                                              | –                                                                         | –                                         | 로그인 URL :`https://login.microsoftonline.com/{TENANT}/oauth2/v2.0/authorize?...`                  |                                                              |
| **AUTH004**<br>토큰 갱신       | `/oauth2/v2.0/token` (grant type = refresh\_token)                                                                              | `POST`                                                                    | –                                         | 토큰 만료 5 분 전 미리 갱신, 실패 시 즉시 AUTH003 재시도                                                           |                                                              |
| **AUTH005**<br>스코프 점검      | `GET /oauth2PermissionGrants?$filter=clientId eq '{APP_ID}'`                                                                    | `GET`                                                                     | `Directory.Read.All`                      | 반환 스코프와 필요 스코프 diff → 부족 시 재동의                                                                   |                                                              |
| **AUTH006**<br>토큰 폐기       | `POST /users/{id}/revokeSignInSessions`                                                                                         | `POST`                                                                    | `User.ReadWrite.All`                      | AzureAD에 캐시된 Refresh Token까지 모두 폐기                                                               |                                                              |
| **AUTH007**<br>감사 로그       | • Azure AD Sign-in logs (Microsoft Graph `/auditLogs/signIns`)<br>• `GET /auditLogs/directoryAudits`                            | `GET`                                                                     | `AuditLog.Read.All`                       | 30일 보관, 4 MB 넘는 경우 페이지네이션                                                                        |                                                              |
| **MAIL001**<br>메일 조회       | \`GET /users/{id                                                                                                                | me}/messages?\$filter=...&\$select=id,subject,bodyPreview,...&\$top={N}\` | `GET`                                     | `Mail.Read`                                                                                      | 기간 필터 예: `receivedDateTime ge 2024-05-01T00:00:00Z`          |
| **MAIL002**<br>조회 기록 관리    | – (내부 DB)                                                                                                                       | –                                                                         | –                                         | 응답 필드 `id`, `internetMessageId` 고유값 저장                                                           |                                                              |
| **MAIL003**<br>메일 송신       | \`POST /users/{id                                                                                                               | me}/sendMail\`                                                            | `POST`                                    | `Mail.Send`                                                                                      | JSON body :`{ "message": {...}, "saveToSentItems": "true" }` |
| **MAIL004**<br>증분 모니터      | `GET /users/{id}/mailFolders('Inbox')/messages/delta?$deltaToken=...`                                                           | `GET`                                                                     | `Mail.Read`                               | deltaToken 사용 → 새 토큰은 응답 `@odata.deltaLink` 에서 추출                                                |                                                              |
| **MAIL005**<br>첨부파일        | • 소형 `GET /messages/{mid}/attachments/{aid}/$value`<br>• 대용량 `POST /messages/{mid}/attachments/createUploadSession` → PUT chunk | `GET /POST` → `PUT`                                                       | `Mail.Read` (대용량도 동일)                     | 3 MB 초과 시 uploadSession 필수                                                                       |                                                              |
| **MAIL006**<br>PII 마스킹     | –                                                                                                                               | –                                                                         | –                                         | 본문(HTML)/헤더 를 받아 사내 Regex 룰 적용                                                                   |                                                              |
| **MAIL007**<br>전송 상태 추적    | – (외부 API + 내부 DB)                                                                                                              | –                                                                         | –                                         | 실패 시 DLQ → 재시도 지수백오프(1-2-4-8 min…)                                                               |                                                              |
| **MAIL008**<br>Webhook 구독  | `POST /subscriptions`                                                                                                           | `POST`                                                                    | `MailboxSettings.Read` **또는** `Mail.Read` | `resource` : `/users/{id}/mailFolders('Inbox')/messages`<br>`expirationDateTime` 최대 423 분 (v1.0) |                                                              |
|                            | **갱신** `PATCH /subscriptions/{sid}`                                                                                             | `PATCH`                                                                   | 동일                                        | 갱신 주기 5 min \~ 3 days; 실패하면 폴링으로 폴백                                                              |                                                              |
| **MAIL009**<br>임베딩 저장      | – (Embedding API → Qdrant / Pinecone)                                                                                           | –                                                                         | –                                         | Graph API 호출 없음.                                                                                 |                                                              |
| **MAIL010**<br>사용자 알림      | – (Slack / Discord / SMS Webhook)                                                                                               | –                                                                         | –                                         | 트리거 조건은 MAIL002 로그 + 키워드 매칭                                                                      |                                                              |
| **MAIL011**<br>레이트-리밋 보호   | 모든 메일 호출 라우트                                                                                                                    | –                                                                         | –                                         | 429 응답일 때 `Retry-After` 헤더 값(sec) 만큼 대기                                                          |                                                              |
| **MAIL012**<br>대량 Export   | `GET /users/{id}/mailFolders('Inbox')/messages?$top=1000&$select=…&$skiptoken=…`                                                | `GET`                                                                     | `Mail.Read`                               | 최대 1000 건/page, `@odata.nextLink` 로 페이지네이션                                                       |                                                              |

---

## 3. 구현‧운용 가이드라인

1. **동시성 & 페이지네이션**

   * `Prefer: outlook.body-content-type="text"` 헤더로 불필요한 HTML → 텍스트 변환 비용 최소화
   * 대량 조회 시 *페이지 완료* 후 200 ms sleep → 서비스 지연 없이 레이트-리밋 완화
2. **Delta Link 수명**

   * 토큰이 오래되면 410 Gone 반환 → **`GET .../delta`** 를 파라미터 없이 재호출해 새 delta-link 로 초기화
3. **Webhook 서명 검증**

   * 응답 헤더 `validationToken` → 200/OK 즉시 echo, 5 sec 이내 완료
   * 서명(request body `clientState`)을 UUID v4 랜덤으로 지정 후 요청과 비교
4. **대용량 첨부 세션**

   * 업로드 세션 URL `@odata.uploadUrl` 은 15 분 유효, 4 MiB 블록 크기 권장
   * PUT chunk 요청 성공 시 `202 Accepted` + `nextExpectedRanges` 확인
5. **보안 & 컴플라이언스**

   * PII 마스킹(메일 주소, 전화번호, 주민번호 등) 완료 후 **Encryption-At-Rest** 스토리지로 이동
   * 감사 로그(AUTH007)와 사용자 메일 로그는 최소 1년 보관 (ISMS-P 권장)
6. **에러 코드 표준화**

   * Graph API 오류 body `error.code` → 내부 코드 매핑(예: `ErrorMailboxNotEnabledForRESTAPI` → “E1103”) 후 공유 lib export
   * 외부 API 호출 실패도 동일 매핑 테이블 사용
7. **CI/CD 테스트**

   * **microsoftgraph/msgraph-mock-service** Docker 이미지로 통합 테스트; delta, attachment, webhook 시나리오 포함
   * 스코프 변경(PR) 시 AUTH005 유닛 테스트 자동 실행 → 부족 스코프 PR block

---

### ✅ 다음 단계 제안

1. **ERD & 마이그레이션 스크립트**

   * 위 테이블 A/B/C + Mail Log + Token Cache + Webhook Subscription 저장 테이블 설계
2. **샘플 코드 Spike**

   * `msal` + `httpx.AsyncClient` 조합으로 AUTH001/AUTH004/AUTH006 end-to-end 확인
3. **작업 분할**

   * “인증 서비스” vs “메일 서비스” 마이크로서비스 분리 후 **공통 라이브러리(v0.1.0)** 로 유즈케이스 코드 공유

이 가이드라인과 엔드포인트 매핑을 바탕으로 **스펙 문서 / OpenAPI 정의**를 작성하면 구현 단계에서 누락 없이 바로 착수할 수 있습니다.



---
*이 가이드가 Graph API를 활용한 메일 기능 개발에 도움이 되기를 바랍니다.*