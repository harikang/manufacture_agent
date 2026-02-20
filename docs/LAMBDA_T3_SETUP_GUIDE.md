# Lambda T3 RAG 시스템 설정 가이드

## 개요

Lambda T3는 AWS Bedrock Knowledge Base와 S3 Vector Store를 활용한 RAG(Retrieval-Augmented Generation) 시스템입니다.

## 아키텍처

```
User Query → Lambda T3 → Bedrock Knowledge Base (S3 Vector Store)
                ↓
         Bedrock Agent Runtime (검색)
                ↓
         Claude 3.5 Sonnet (답변 생성)
                ↓
         Natural Language Response
```

## 사전 요구사항

1. **AWS CLI 설치 및 구성**
   ```bash
   aws --version
   aws configure
   ```

2. **Docker 설치**
   ```bash
   docker --version
   ```

3. **Python 3.11+ 설치**
   ```bash
   python3 --version
   ```

4. **필요한 AWS 권한**
   - Bedrock 모델 접근 권한
   - S3 버킷 생성 및 관리
   - IAM 역할 생성
   - Lambda 함수 생성 및 관리
   - ECR 리포지토리 관리

## 설정 단계

### Step 1: S3 버킷 및 IAM 역할 생성

```bash
# 실행 권한 부여
chmod +x setup_knowledge_base_s3.sh

# 스크립트 실행
./setup_knowledge_base_s3.sh
```

**생성되는 리소스:**
- S3 버킷: `diecasting-knowledge-base`
- IAM 역할: `AmazonBedrockExecutionRoleForKnowledgeBase_diecasting`
- 샘플 문서 업로드

### Step 2: Knowledge Base 생성

```bash
# Python 스크립트 실행
python3 create_knowledge_base.py
```

**생성되는 리소스:**
- Bedrock Knowledge Base
- Data Source (S3 연결)
- 자동 데이터 동기화

**출력:**
- Knowledge Base ID가 `knowledge_base_id.txt`에 저장됨

**예상 소요 시간:** 5-10분 (데이터 동기화 포함)

### Step 3: Lambda T3 배포

```bash
# 실행 권한 부여
chmod +x deploy_lambda_t3.sh

# 스크립트 실행
./deploy_lambda_t3.sh
```

**생성되는 리소스:**
- ECR 리포지토리: `diecasting-lambda-t3`
- Docker 이미지 빌드 및 푸시
- IAM 역할: `lambda-diecasting-rag-execution-role`
- Lambda 함수: `diecasting-rag-t3`
- Function URL (Public 접근)

**출력:**
- Function URL이 `lambda_t3_url.txt`에 저장됨

**예상 소요 시간:** 3-5분

### Step 4: 테스트

```bash
# Python 테스트 스크립트 실행
python3 test_lambda_t3.py
```

**테스트 케이스:**
1. 트러블슈팅 질문
2. 공정 파라미터 질문
3. 안전 규정 질문
4. 필터 없는 일반 질문

**또는 curl로 직접 테스트:**

```bash
# Lambda T3 URL 읽기
LAMBDA_URL=$(cat lambda_t3_url.txt)

# 테스트 요청
curl -X POST ${LAMBDA_URL} \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "포로시티 불량이 발생했을 때 어떻게 해결하나요?",
    "filters": {
      "category": ["troubleshooting", "process_manual"]
    },
    "max_results": 3,
    "include_sources": true
  }'
```

## API 사용법

### 요청 형식

```json
{
  "query": "질문 내용",
  "filters": {
    "category": ["troubleshooting", "process_manual"],
    "date_range": {
      "start": "2024-01-01",
      "end": "2025-12-31"
    },
    "priority": ["high", "medium"],
    "defect_type": "porosity",
    "process_type": "injection"
  },
  "max_results": 5,
  "include_sources": true
}
```

### 응답 형식

```json
{
  "answer": "답변 내용...",
  "sources": [
    {
      "document_title": "문서 제목",
      "category": "troubleshooting",
      "excerpt": "발췌 내용...",
      "relevance_score": 0.92,
      "metadata": {
        "created_date": "2024-11-15",
        "author": "품질관리팀",
        "version": "2.1"
      },
      "s3_uri": "s3://..."
    }
  ],
  "query_metadata": {
    "total_documents_retrieved": 3,
    "processing_time_ms": 850.23,
    "model_used": "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "timestamp": "2024-01-22T10:30:00.000Z"
  }
}
```

## 문서 추가 방법

### 1. S3에 직접 업로드

```bash
# 트러블슈팅 문서
aws s3 cp my_document.md s3://diecasting-knowledge-base/documents/troubleshooting/

# 공정 매뉴얼
aws s3 cp my_manual.md s3://diecasting-knowledge-base/documents/process_manual/

# 안전 규정
aws s3 cp my_regulation.md s3://diecasting-knowledge-base/documents/regulations/
```

### 2. 데이터 동기화

```bash
# Knowledge Base ID 읽기
KB_ID=$(cat knowledge_base_id.txt)

# Data Source ID 조회
DS_ID=$(aws bedrock-agent list-data-sources \
  --knowledge-base-id ${KB_ID} \
  --query 'dataSourceSummaries[0].dataSourceId' \
  --output text)

# 동기화 시작
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id ${KB_ID} \
  --data-source-id ${DS_ID}

# 동기화 상태 확인
aws bedrock-agent list-ingestion-jobs \
  --knowledge-base-id ${KB_ID} \
  --data-source-id ${DS_ID} \
  --max-results 1
```

### 3. 문서 메타데이터 형식

문서 상단에 메타데이터 추가:

```markdown
**문서 메타데이터:**
- Category: troubleshooting
- Defect Type: porosity
- Severity: major
- Last Updated: 2024-11-15
- Author: 품질관리팀
- Version: 2.1
- Priority: high

# 문서 제목

문서 내용...
```

## 청킹 전략 커스터마이징

현재 설정: 300 토큰, 20% 오버랩

변경하려면 `create_knowledge_base.py` 수정:

```python
'fixedSizeChunkingConfiguration': {
    'maxTokens': 500,        # 청크 크기 변경
    'overlapPercentage': 15  # 오버랩 비율 변경
}
```

## 비용 최적화

### 1. 캐싱 활용

자주 묻는 질문은 캐싱하여 Bedrock 호출 감소:

```python
# Lambda 함수에 캐싱 레이어 추가
import functools
from datetime import datetime, timedelta

@functools.lru_cache(maxsize=100)
def cached_query(query: str, filters_json: str):
    # 검색 및 답변 생성
    pass
```

### 2. 배치 처리

여러 질문을 한 번에 처리:

```json
{
  "queries": [
    "질문 1",
    "질문 2",
    "질문 3"
  ],
  "filters": {...}
}
```

### 3. 필터 활용

불필요한 문서 검색 방지:

```json
{
  "query": "...",
  "filters": {
    "category": ["troubleshooting"],  // 특정 카테고리만
    "priority": ["high"]               // 우선순위 높은 것만
  }
}
```

## 모니터링

### CloudWatch Logs

```bash
# Lambda 로그 확인
aws logs tail /aws/lambda/diecasting-rag-t3 --follow

# 최근 10분 로그
aws logs tail /aws/lambda/diecasting-rag-t3 --since 10m
```

### 메트릭 확인

```bash
# Lambda 메트릭
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=diecasting-rag-t3 \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum
```

## 트러블슈팅

### 문제: Knowledge Base 생성 실패

**원인:** IAM 역할 권한 부족

**해결:**
```bash
# IAM 역할 정책 확인
aws iam list-role-policies --role-name AmazonBedrockExecutionRoleForKnowledgeBase_diecasting

# 정책 재적용
./setup_knowledge_base_s3.sh
```

### 문제: 데이터 동기화 실패

**원인:** S3 버킷 권한 또는 문서 형식 오류

**해결:**
```bash
# 동기화 작업 상태 확인
aws bedrock-agent get-ingestion-job \
  --knowledge-base-id ${KB_ID} \
  --data-source-id ${DS_ID} \
  --ingestion-job-id ${JOB_ID}

# 실패 원인 확인
# failureReasons 필드 확인
```

### 문제: Lambda 함수 타임아웃

**원인:** 복잡한 질문 또는 많은 문서 검색

**해결:**
```bash
# 타임아웃 증가 (60초 → 120초)
aws lambda update-function-configuration \
  --function-name diecasting-rag-t3 \
  --timeout 120
```

### 문제: 답변 품질 낮음

**원인:** 청킹 전략 또는 검색 설정 부적절

**해결:**
1. 청크 크기 조정 (300 → 500 토큰)
2. max_results 증가 (5 → 10)
3. 문서 메타데이터 개선
4. 프롬프트 엔지니어링 개선

## Agent 통합

Lambda T3를 Agent에 통합:

```python
# prototype/agent.py 수정

LAMBDA_T3_URL = "https://your-lambda-url.lambda-url.us-east-1.on.aws/"

def search_knowledge_base(self, query: str, filters: dict = None):
    """Knowledge Base 검색"""
    payload = {
        "query": query,
        "filters": filters or {},
        "max_results": 5,
        "include_sources": True
    }
    
    response = requests.post(LAMBDA_T3_URL, json=payload)
    return response.json()
```

## 다음 단계

1. **문서 추가**: 실제 트러블슈팅 기록, 회의록 등 추가
2. **메타데이터 최적화**: 검색 정확도 향상
3. **Agent 통합**: Streamlit UI에서 사용
4. **성능 튜닝**: 청킹 전략 및 프롬프트 최적화
5. **모니터링 설정**: CloudWatch 대시보드 구성

## 참고 자료

- [AWS Bedrock Knowledge Bases](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html)
- [S3 as Vector Store](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-setup.html)
- [Bedrock Agent Runtime API](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_agent-runtime_Retrieve.html)
- [Lambda Container Images](https://docs.aws.amazon.com/lambda/latest/dg/images-create.html)
