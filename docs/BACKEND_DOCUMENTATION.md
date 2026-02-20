# 백엔드 문서 (Backend Documentation)

다이캐스팅 품질 예측 AI 시스템의 백엔드 아키텍처 및 구현을 설명합니다.

## 📁 파일 구조

```
backend_agent.py        # FastAPI 서버 + Bedrock Claude Tool Use
docker/
├── Dockerfile.backend_agent  # Docker 이미지 빌드 파일
config/
└── requirements_backend.txt  # Python 의존성
```

---

## 1. 아키텍처 개요

### 1.1 시스템 구성

```
Frontend (S3/CloudFront)
       ↓
   ALB (Application Load Balancer)
       ↓
ECS Fargate (backend_agent.py)
       ↓
   ┌─────────────────────────────────┐
   │  Bedrock Claude Sonnet 4.5      │
   │  (Tool Use / Agentic AI)        │
   └─────────────────────────────────┘
       ↓
   ┌──────────┬──────────┬──────────┐
   │ Lambda   │ Lambda   │ Lambda   │
   │ T1       │ T2       │ T3       │
   │ (품질예측)│ (원인분석)│ (KB검색) │
   └──────────┴──────────┴──────────┘
```

### 1.2 핵심 기술 스택

| 기술 | 용도 |
|------|------|
| **FastAPI** | 비동기 웹 프레임워크 |
| **Bedrock Claude Sonnet 4.5** | LLM 기반 의도 분류 및 도구 선택 |
| **SSE (Server-Sent Events)** | 실시간 스트리밍 응답 |
| **SigV4 인증** | Lambda Function URL IAM 인증 |
| **boto3** | AWS SDK (Bedrock, Lambda 호출) |

---

## 2. 환경 변수

```bash
# Lambda Function URLs
LAMBDA_T0_URL=https://...  # KB Ingest
LAMBDA_T1_URL=https://...  # 품질 예측
LAMBDA_T2_URL=https://...  # Feature Importance
LAMBDA_T3_URL=https://...  # Knowledge Base 검색

# Bedrock 모델
MODEL_ID=us.anthropic.claude-sonnet-4-5-20250929-v1:0

# Mock 모드 (개발용)
USE_MOCK=false
```

---

## 3. API 엔드포인트

### 3.1 POST /api/chat (SSE 스트리밍)

사용자 질문을 받아 Bedrock Claude가 도구를 선택하고 실행한 후 최종 답변을 스트리밍으로 반환합니다.

#### Request Body

```json
{
  "question": "불량 원인이 뭐야?",
  "features": {
    "Process_Temperature": 670.0,
    "Process_Pressure": 145.0,
    ...
  },
  "session_id": "session_123"
}
```

#### SSE Event Types

| Event Type | 설명 | 데이터 예시 |
|-----------|------|------------|
| `status` | 진행 상황 메시지 | `{"type": "status", "message": "도구 선택 중..."}` |
| `tool_start` | Lambda 호출 시작 | `{"type": "tool_start", "tool": "predict_quality"}` |
| `tool_end` | Lambda 호출 완료 | `{"type": "tool_end", "tool": "predict_quality", "result": {...}}` |
| `t1_result` | 품질 예측 결과 | `{"type": "t1_result", "data": {"prediction": {...}}}` |
| `t2_result` | Feature Importance 결과 | `{"type": "t2_result", "data": {"top_features": [...]}}` |
| `t3_result` | KB 검색 결과 | `{"type": "t3_result", "data": {"results": [...]}}` |
| `ai_response` | LLM 최종 답변 | `{"type": "ai_response", "data": {"answer": "..."}}` |
| `done` | 스트림 종료 | `{"type": "done", "elapsed": 5.2}` |
| `error` | 에러 발생 | `{"type": "error", "message": "..."}` |

#### Response Example (SSE Stream)

```
data: {"type":"status","message":"도구 선택 중...","elapsed":0.1}

data: {"type":"tool_start","tool":"predict_quality","elapsed":0.2}

data: {"type":"tool_end","tool":"predict_quality","result":{...},"elapsed":1.5}

data: {"type":"t1_result","data":{"prediction":{...}},"elapsed":1.5}

data: {"type":"tool_start","tool":"analyze_feature_importance","elapsed":1.6}

data: {"type":"tool_end","tool":"analyze_feature_importance","result":{...},"elapsed":3.2}

data: {"type":"t2_result","data":{"top_features":[...]},"elapsed":3.2}

data: {"type":"ai_response","data":{"answer":"현재 조건에서..."},"elapsed":4.8}

data: {"type":"done","elapsed":5.0}
```

### 3.2 POST /api/session/create

새 세션 생성 (현재는 메모리 기반, 추후 DB 연동 가능)

#### Request Body

```json
{
  "user_id": "user_123"
}
```

#### Response

```json
{
  "session_id": "session_1707552000_abc123",
  "created_at": "2024-02-10T10:00:00Z"
}
```

### 3.3 POST /api/kb/ingest

Knowledge Base 인제스트 트리거

#### Request Body

```json
{
  "action": "start"
}
```

또는

```json
{
  "action": "status",
  "job_id": "job_123"
}
```

#### Response

```json
{
  "status": "success",
  "job_id": "job_123",
  "message": "Ingestion started"
}
```

### 3.4 GET /health

헬스체크 엔드포인트

#### Response

```json
{
  "status": "healthy"
}
```

---

## 4. Bedrock Claude Tool Use

### 4.1 시스템 프롬프트

```python
SYSTEM_PROMPT = """당신은 다이캐스팅 제조 공정 AI 어시스턴트입니다.
사용자의 질문을 분석하고, 적절한 도구를 호출하여 답변을 생성하세요.

## 도구 사용 가이드

1. **품질 예측 질문** → predict_quality 호출
2. **원인 분석 질문** → predict_quality 먼저 호출 → analyze_feature_importance 호출
3. **공정 지식 질문** → search_knowledge_base 호출

## 중요 규칙
- 각 도구는 한 번만 호출
- analyze_feature_importance는 predict_quality 후에만 사용
- 도구 결과를 받으면 즉시 최종 답변 생성하고 종료
"""
```

### 4.2 도구 정의 (Tools)

#### Tool 1: predict_quality

```python
{
  "name": "predict_quality",
  "description": "품질 예측 도구. 현재 공정 파라미터를 기반으로 양품/불량 예측",
  "inputSchema": {
    "json": {
      "type": "object",
      "properties": {
        "features": {
          "type": "object",
          "description": "공정 파라미터 딕셔너리"
        }
      },
      "required": ["features"]
    }
  }
}
```

**Lambda T1 호출** → 품질 예측 결과 + latent_features 반환

#### Tool 2: analyze_feature_importance

```python
{
  "name": "analyze_feature_importance",
  "description": "Feature Importance 분석 도구. 품질에 영향을 미치는 주요 변수 분석",
  "inputSchema": {
    "json": {
      "type": "object",
      "properties": {
        "features": {"type": "object"},
        "latent_features": {
          "type": "array",
          "items": {"type": "number"}
        }
      },
      "required": ["features", "latent_features"]
    }
  }
}
```

**Lambda T2 호출** → Feature Importance 순위 반환

#### Tool 3: search_knowledge_base

```python
{
  "name": "search_knowledge_base",
  "description": "공정 지식 검색 도구. Knowledge Base에서 관련 문서 검색",
  "inputSchema": {
    "json": {
      "type": "object",
      "properties": {
        "query": {
          "type": "string",
          "description": "검색할 질문 또는 키워드"
        }
      },
      "required": ["query"]
    }
  }
}
```

**Lambda T3 호출** → RAG 답변 + 참고 문서 반환

### 4.3 Agent Loop 흐름

```
1. 사용자 질문 수신
   ↓
2. Bedrock Claude에 질문 전달 (Tool Config 포함)
   ↓
3. Claude가 도구 선택 (tool_use)
   ↓
4. 선택된 도구 실행 (Lambda 호출)
   ↓
5. 도구 결과를 Claude에 전달
   ↓
6. Claude가 최종 답변 생성 (end_turn)
   ↓
7. 답변을 SSE로 스트리밍
```

**최대 반복 횟수**: 3회 (무한 루프 방지)

---

## 5. Lambda 호출 (SigV4 인증)

### 5.1 SigV4 서명 함수

```python
def sign_request(url: str, method: str, payload: dict) -> dict:
    """Lambda Function URL IAM 인증을 위한 SigV4 서명"""
    body = json.dumps(payload)
    request = AWSRequest(method=method, url=url, data=body, headers={
        'Content-Type': 'application/json'
    })
    SigV4Auth(credentials, 'lambda', 'us-east-1').add_auth(request)
    return dict(request.headers)
```

### 5.2 Lambda 호출 함수

| 함수 | Lambda | 설명 |
|------|--------|------|
| `call_lambda_t1_sync()` | T1 | 품질 예측 (동기 호출) |
| `call_lambda_t2_sync()` | T2 | Feature Importance (동기 호출) |
| `call_lambda_t3_sync()` | T3 | Knowledge Base 검색 (동기 호출) |

**타임아웃**: 30초

---

## 6. 도구 결과 요약 (토큰 최적화)

LLM에 전달할 때 불필요한 데이터를 제거하여 토큰 수를 줄입니다.

```python
def summarize_tool_result(tool_name: str, result: Dict[str, Any]) -> Dict[str, Any]:
    if tool_name == "predict_quality":
        # latent_features는 상위 24개만 전달
        latent = result.get("latent_features", [])[:24]
        return {
            "prediction": result.get("prediction"),
            "latent_features": latent
        }
    elif tool_name == "analyze_feature_importance":
        # 상위 10개 feature만 전달, equipment_descriptions 제거
        top_features = result.get("top_features", [])[:10]
        return {
            "top_features": top_features,
            "top_features_percent": result.get("top_features_percent", [])[:10]
        }
    elif tool_name == "search_knowledge_base":
        # 상위 3개 결과만 전달
        results = result.get("results", [])[:3]
        return {"results": results}
```

**효과**: LLM 응답 시간 단축 (토큰 수 감소)

---

## 7. 세션 관리 (In-Memory)

```python
# 메모리 기반 대화 저장
conversation_memory: Dict[str, List[Dict[str, Any]]] = {}
MAX_HISTORY_LENGTH = 10  # 최근 10개 메시지만 유지
```

**특징:**
- 세션별로 대화 기록 저장
- 최근 10개 메시지만 유지 (메모리 절약)
- 컨테이너 재시작 시 초기화됨 (추후 DynamoDB 연동 가능)

---

## 8. SSE 스트리밍 구현

### 8.1 agent_event_stream() 함수

```python
async def agent_event_stream(question: str, features: Dict[str, float], session_id: str):
    """SSE 스트리밍으로 실시간 진행 상황 전송"""
    
    # 시작 시간 기록
    start_time = time.time()
    
    # Agent Loop - 최대 3회 반복
    for iteration in range(3):
        # 상태 메시지 전송
        if iteration > 0 and tool_use_results:
            yield f"data: {json.dumps({'type': 'status', 'message': '분석 결과를 통합하여 최종 답변 생성 중...'})}\n\n"
        
        # Bedrock Converse API 호출
        response = await loop.run_in_executor(
            None,
            lambda: bedrock_runtime.converse(...)
        )
        
        # Tool Use 처리
        if stop_reason == "tool_use":
            for content in message.get("content", []):
                if "toolUse" in content:
                    # tool_start 이벤트 전송
                    yield f"data: {json.dumps({'type': 'tool_start', 'tool': tool_name})}\n\n"
                    
                    # 도구 실행
                    result = await loop.run_in_executor(None, execute_tool, ...)
                    
                    # tool_end 이벤트 전송
                    yield f"data: {json.dumps({'type': 'tool_end', 'tool': tool_name, 'result': result})}\n\n"
                    
                    # 결과 타입별 이벤트 전송
                    if tool_name == "predict_quality":
                        yield f"data: {json.dumps({'type': 't1_result', 'data': result})}\n\n"
                    elif tool_name == "analyze_feature_importance":
                        yield f"data: {json.dumps({'type': 't2_result', 'data': result})}\n\n"
        
        # 최종 답변 전송
        if stop_reason == "end_turn":
            yield f"data: {json.dumps({'type': 'ai_response', 'data': {'answer': final_text}})}\n\n"
            await asyncio.sleep(0.2)  # 버퍼 플러시 대기
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            await asyncio.sleep(0.1)  # 완전 전송 보장
            return
```

### 8.2 대기 시간 최적화

```python
# ai_response 후 대기 (0.05s → 0.2s로 증가)
await asyncio.sleep(0.2)

# done 이벤트 후 대기 (추가)
await asyncio.sleep(0.1)
```

**목적**: SSE 연결 조기 종료 방지 (ERR_HTTP2_PROTOCOL_ERROR 해결)

---

## 9. 에러 처리

### 9.1 Lambda 호출 실패

```python
try:
    response = requests.post(LAMBDA_URL, json=payload, headers=headers, timeout=30)
    data = response.json()
    return data
except Exception as e:
    return {"error": str(e)}
```

### 9.2 SSE 스트림 에러

```python
try:
    async for event in agent_event_stream(...):
        yield event
except Exception as e:
    yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
```

---

## 10. 배포 (ECS Fargate)

### 10.1 Docker 이미지 빌드

```bash
docker build --platform linux/amd64 \
  -f docker/Dockerfile.backend_agent \
  -t diecasting-backend-agent:latest .
```

### 10.2 ECR 푸시

```bash
# ECR 로그인
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# 태그 및 푸시
docker tag diecasting-backend-agent:latest \
  YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/diecasting-backend-agent:latest

docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/diecasting-backend-agent:latest
```

### 10.3 ECS 서비스 업데이트

```bash
aws ecs update-service \
  --cluster diecasting-cluster \
  --service backend-agent-service \
  --force-new-deployment \
  --region us-east-1
```

---

## 11. 모니터링 및 로깅

### 11.1 로그 출력

```python
print(f"⏱️ LLM 호출 시간: {llm_duration:.2f}초 (iteration {iteration + 1})")
```

**CloudWatch Logs**에서 확인 가능:
- `/ecs/diecasting-backend-agent`

### 11.2 주요 메트릭

| 메트릭 | 설명 |
|--------|------|
| LLM 호출 시간 | Bedrock Converse API 응답 시간 |
| Lambda 호출 시간 | T1/T2/T3 Lambda 실행 시간 |
| 전체 처리 시간 | 질문 수신 → 최종 답변 전송 |

---

## 12. 성능 최적화

### 12.1 적용된 최적화

1. **도구 결과 요약**: LLM에 전달할 데이터 최소화 (토큰 절약)
2. **Agent Loop 축소**: 5회 → 3회로 감소
3. **비동기 처리**: `asyncio.run_in_executor`로 동기 Lambda 호출을 비동기로 실행
4. **SSE 버퍼 플러시**: `asyncio.sleep`으로 이벤트 전송 보장

### 12.2 향후 개선 방향

1. **Lambda 병렬 호출**: 독립적인 도구는 동시 실행 (현재는 순차)
2. **캐싱**: 동일 질문에 대한 응답 캐싱
3. **DB 연동**: DynamoDB로 세션 영구 저장
4. **스트리밍 LLM 응답**: Bedrock Converse Stream API 사용

---

## 13. 보안

### 13.1 IAM 인증

- Lambda Function URL 호출 시 **SigV4 서명** 사용
- ECS Task Role로 Bedrock 및 Lambda 호출 권한 부여

### 13.2 CORS 설정

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한 권장
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 14. 트러블슈팅

### 14.1 SSE 연결 끊김 (ERR_HTTP2_PROTOCOL_ERROR)

**원인**: `done` 이벤트 전송 후 스트림이 즉시 종료되어 클라이언트가 수신하지 못함

**해결**:
```python
yield f"data: {json.dumps({'type': 'done'})}\n\n"
await asyncio.sleep(0.1)  # 전송 완료 대기
```

### 14.2 T2 결과 중복 표시

**원인**: 프론트엔드에서 중복 렌더링

**해결**: 백엔드는 정상, 프론트엔드에서 `renderedCards` 객체로 중복 방지

### 14.3 LLM 응답 지연

**원인**: 도구 결과에 불필요한 데이터가 많아 토큰 수 증가

**해결**: `summarize_tool_result()` 함수로 데이터 요약

---

## 15. 참고 자료

- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [Bedrock Converse API](https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html)
- [SSE (Server-Sent Events)](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- [AWS SigV4 인증](https://docs.aws.amazon.com/general/latest/gr/signature-version-4.html)
