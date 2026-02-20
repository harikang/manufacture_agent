# Lambda T3: RAG 기반 지식 검색 시스템 설계

## 1. 시스템 개요

Lambda T3는 AWS Bedrock Knowledge Base와 S3를 활용한 RAG(Retrieval-Augmented Generation) 시스템으로, 다이캐스팅 공정 관련 문서를 검색하고 자연어로 답변을 생성합니다.

## 2. 아키텍처

```
User Query → Lambda T3 → Bedrock Knowledge Base → S3 Vector Store
                ↓
         Bedrock LLM (Claude 3.5 Sonnet)
                ↓
         Natural Language Response
```

## 3. 문서 분류 및 메타데이터 구조

### 3.1 문서 카테고리

| 카테고리 | 설명 | 메타데이터 키 |
|---------|------|--------------|
| **troubleshooting** | 트러블슈팅 기록, 불량 원인 분석 | `category`, `defect_type`, `severity`, `date` |
| **meeting_notes** | 과거 회의록, 의사결정 기록 | `category`, `meeting_type`, `date`, `participants` |
| **regulations** | 안전 법규, 품질 기준 | `category`, `regulation_type`, `effective_date`, `authority` |
| **process_manual** | 공정 메뉴얼, SOP | `category`, `process_type`, `version`, `last_updated` |
| **equipment_manual** | 장비 설명서, 유지보수 가이드 | `category`, `equipment_type`, `manufacturer`, `model` |
| **sensor_manual** | 센서 설명서, 캘리브레이션 가이드 | `category`, `sensor_type`, `measurement_range`, `accuracy` |

### 3.2 공통 메타데이터

```json
{
  "category": "string",           // 문서 카테고리
  "title": "string",              // 문서 제목
  "language": "ko",               // 언어 (한국어)
  "created_date": "YYYY-MM-DD",   // 생성일
  "last_updated": "YYYY-MM-DD",   // 최종 수정일
  "author": "string",             // 작성자
  "version": "string",            // 버전
  "tags": ["tag1", "tag2"],       // 태그
  "priority": "high|medium|low"   // 우선순위
}
```

## 4. 청킹 전략 (Chunking Strategy)

### 4.1 문서별 최적 청킹 설정

#### A. 트러블슈팅 기록 (troubleshooting)
- **청크 크기**: 500-800 토큰
- **오버랩**: 100 토큰
- **분할 기준**: 
  - 문제 발생 → 원인 분석 → 해결 방법 단위로 분할
  - 각 케이스를 독립적인 청크로 유지
- **메타데이터 추가**:
  ```json
  {
    "defect_type": "porosity|crack|dimension|surface",
    "root_cause": "string",
    "solution": "string",
    "severity": "critical|major|minor",
    "resolution_time": "hours"
  }
  ```

#### B. 회의록 (meeting_notes)
- **청크 크기**: 600-1000 토큰
- **오버랩**: 150 토큰
- **분할 기준**:
  - 안건별로 분할
  - 의사결정 내용과 배경을 함께 유지
- **메타데이터 추가**:
  ```json
  {
    "meeting_type": "quality_review|production_planning|safety",
    "agenda_item": "string",
    "decision": "string",
    "action_items": ["item1", "item2"]
  }
  ```

#### C. 안전 법규 (regulations)
- **청크 크기**: 400-600 토큰
- **오버랩**: 80 토큰
- **분할 기준**:
  - 조항별로 분할
  - 관련 조항 참조를 메타데이터에 포함
- **메타데이터 추가**:
  ```json
  {
    "regulation_type": "safety|quality|environmental",
    "article_number": "string",
    "effective_date": "YYYY-MM-DD",
    "authority": "KOSHA|ISO|internal",
    "compliance_level": "mandatory|recommended"
  }
  ```

#### D. 공정 메뉴얼 (process_manual)
- **청크 크기**: 700-1000 토큰
- **오버랩**: 150 토큰
- **분할 기준**:
  - 공정 단계별로 분할
  - 파라미터 설정과 주의사항을 함께 유지
- **메타데이터 추가**:
  ```json
  {
    "process_type": "injection|cooling|ejection|trimming",
    "process_step": "string",
    "parameters": {
      "temperature_range": "string",
      "pressure_range": "string",
      "time_range": "string"
    },
    "quality_checkpoints": ["checkpoint1", "checkpoint2"]
  }
  ```

#### E. 장비 설명서 (equipment_manual)
- **청크 크기**: 600-900 토큰
- **오버랩**: 120 토큰
- **분할 기준**:
  - 기능별, 유지보수 항목별로 분할
  - 트러블슈팅 섹션은 독립적으로 유지
- **메타데이터 추가**:
  ```json
  {
    "equipment_type": "injection_machine|mold|cooling_system",
    "manufacturer": "string",
    "model": "string",
    "section_type": "operation|maintenance|troubleshooting|specs",
    "maintenance_interval": "daily|weekly|monthly|yearly"
  }
  ```

#### F. 센서 설명서 (sensor_manual)
- **청크 크기**: 400-600 토큰
- **오버랩**: 80 토큰
- **분할 기준**:
  - 센서별, 측정 항목별로 분할
  - 캘리브레이션 절차는 완전하게 유지
- **메타데이터 추가**:
  ```json
  {
    "sensor_type": "temperature|pressure|vibration|flow",
    "measurement_range": "string",
    "accuracy": "string",
    "calibration_frequency": "string",
    "installation_location": "string"
  }
  ```

## 5. S3 버킷 구조

```
s3://diecasting-knowledge-base/
├── documents/
│   ├── troubleshooting/
│   │   ├── 2024/
│   │   │   ├── porosity_case_001.md
│   │   │   └── crack_case_002.md
│   │   └── 2025/
│   ├── meeting_notes/
│   │   ├── 2024/
│   │   └── 2025/
│   ├── regulations/
│   │   ├── safety/
│   │   ├── quality/
│   │   └── environmental/
│   ├── process_manual/
│   │   ├── injection/
│   │   ├── cooling/
│   │   └── ejection/
│   ├── equipment_manual/
│   │   ├── injection_machines/
│   │   ├── molds/
│   │   └── cooling_systems/
│   └── sensor_manual/
│       ├── temperature/
│       ├── pressure/
│       └── vibration/
└── metadata/
    └── document_index.json
```

## 6. Bedrock Knowledge Base 설정

### 6.1 임베딩 모델
- **모델**: Amazon Titan Embeddings G1 - Text v1.2
- **차원**: 1024
- **언어**: 한국어 지원

### 6.2 벡터 스토어
- **타입**: Amazon S3 (Vector Engine)
- **버킷 구조**:
  ```
  s3://diecasting-knowledge-base/
  ├── documents/          # 원본 문서
  ├── vectors/            # 벡터 임베딩 (자동 생성)
  └── metadata/           # 메타데이터 인덱스
  ```
- **벡터 설정**:
  ```json
  {
    "dimension": 1024,
    "distance_metric": "cosine",
    "storage_format": "parquet"
  }
  ```

### 6.3 검색 설정
- **검색 타입**: Semantic search (벡터 유사도 기반)
- **Top K**: 5-10 문서
- **최소 유사도 점수**: 0.7
- **메타데이터 필터링**: 활성화 (S3 Select 활용)

## 7. Lambda T3 기능 명세

### 7.1 입력 형식

```json
{
  "query": "포로시티 불량이 발생했을 때 어떻게 해결하나요?",
  "filters": {
    "category": ["troubleshooting", "process_manual"],
    "date_range": {
      "start": "2024-01-01",
      "end": "2025-12-31"
    },
    "priority": ["high", "medium"]
  },
  "max_results": 5,
  "include_sources": true
}
```

### 7.2 출력 형식

```json
{
  "statusCode": 200,
  "body": {
    "answer": "포로시티 불량 해결 방법...",
    "sources": [
      {
        "document_title": "포로시티 불량 트러블슈팅 가이드",
        "category": "troubleshooting",
        "excerpt": "...",
        "relevance_score": 0.92,
        "metadata": {
          "defect_type": "porosity",
          "severity": "major",
          "date": "2024-11-15"
        },
        "s3_uri": "s3://diecasting-knowledge-base/documents/troubleshooting/2024/porosity_case_001.md"
      }
    ],
    "query_metadata": {
      "total_documents_searched": 1250,
      "documents_retrieved": 5,
      "processing_time_ms": 850,
      "model_used": "anthropic.claude-3-5-sonnet-20241022-v2:0"
    }
  }
}
```

### 7.3 주요 기능

1. **자연어 질의 처리**
   - 한국어 질문을 이해하고 관련 문서 검색
   - 의도 파악 (트러블슈팅, 절차 문의, 규정 확인 등)

2. **메타데이터 기반 필터링**
   - 카테고리별 검색
   - 날짜 범위 필터
   - 우선순위 필터
   - 장비/센서 타입 필터

3. **컨텍스트 기반 답변 생성**
   - 검색된 문서를 기반으로 정확한 답변 생성
   - 출처 명시
   - 관련 문서 추천

4. **다중 문서 통합**
   - 여러 문서에서 정보를 종합하여 답변
   - 모순되는 정보 처리
   - 최신 정보 우선

## 8. 프롬프트 엔지니어링

### 8.1 시스템 프롬프트

```
당신은 다이캐스팅 공정 전문가입니다. 제공된 문서를 기반으로 정확하고 실용적인 답변을 제공하세요.

답변 규칙:
1. 반드시 제공된 문서의 정보만 사용하세요
2. 출처를 명확히 밝히세요
3. 안전과 관련된 내용은 특히 신중하게 답변하세요
4. 불확실한 경우 "문서에서 해당 정보를 찾을 수 없습니다"라고 답하세요
5. 단계별 절차는 번호를 매겨 명확하게 설명하세요
6. 중요한 파라미터나 수치는 정확하게 인용하세요
```

### 8.2 쿼리 증강 (Query Augmentation)

사용자 질문을 확장하여 검색 정확도 향상:
- 동의어 추가 (예: "불량" → "결함", "defect")
- 관련 용어 추가 (예: "포로시티" → "기공", "porosity")
- 컨텍스트 추가 (예: 이전 대화 내용 참조)

## 9. 성능 최적화

### 9.1 캐싱 전략
- 자주 묻는 질문(FAQ) 캐싱
- 검색 결과 캐싱 (1시간 TTL)
- 임베딩 캐싱

### 9.2 비용 최적화
- 청크 크기 최적화로 토큰 사용량 감소
- 하이브리드 검색으로 정확도 향상
- 배치 처리 지원

## 10. 모니터링 및 평가

### 10.1 메트릭
- 검색 정확도 (Precision@K, Recall@K)
- 답변 품질 (사용자 피드백)
- 응답 시간
- 비용 (토큰 사용량)

### 10.2 로깅
- 모든 쿼리 및 응답 로깅
- 검색된 문서 및 점수 로깅
- 에러 및 예외 로깅

## 11. 보안 및 규정 준수

- S3 버킷 암호화 (SSE-S3)
- IAM 역할 기반 접근 제어
- VPC 엔드포인트 사용
- 민감 정보 마스킹
- 감사 로그 유지

## 12. 구현 단계

### Phase 1: 인프라 구축
1. S3 버킷 생성 및 구조 설정
2. IAM 역할 생성 (Bedrock Knowledge Base용)
3. Bedrock Knowledge Base 생성 (S3 Vector Store 연결)
4. Data Source 생성 및 동기화
5. Lambda 함수 생성 및 배포

**실행 스크립트:**
```bash
./setup_knowledge_base_s3.sh      # S3 및 IAM 설정
python3 create_knowledge_base.py  # Knowledge Base 생성
./deploy_lambda_t3.sh             # Lambda 배포
```

### Phase 2: 문서 준비 및 인제스트
1. 샘플 문서 작성 (각 카테고리별)
2. 메타데이터 스키마 정의
3. S3에 문서 업로드
4. 자동 벡터화 및 인덱싱

**문서 업로드:**
```bash
aws s3 cp document.md s3://diecasting-knowledge-base/documents/category/
aws bedrock-agent start-ingestion-job --knowledge-base-id ${KB_ID} --data-source-id ${DS_ID}
```

### Phase 3: Lambda T3 개발
1. 기본 RAG 파이프라인 구현
2. 메타데이터 필터링 구현
3. 프롬프트 엔지니어링
4. 에러 핸들링
5. Docker 이미지 빌드 및 ECR 푸시

**개발 완료:** `lambda_t3_rag.py` 구현 완료

### Phase 4: 통합 및 테스트
1. Lambda T3 단독 테스트
2. Agent와 통합
3. Streamlit UI 연결
4. 성능 테스트
5. 사용자 테스트

**테스트:**
```bash
python3 test_lambda_t3.py
```

## 13. 예상 비용

### 월간 예상 비용 (1000 쿼리 기준)

#### Bedrock 비용
- **Knowledge Base**: 무료 (검색 API 호출만 과금)
- **Titan Embeddings**: 
  - 입력 토큰: 1000 쿼리 × 평균 50 토큰 = 50K 토큰
  - 비용: $0.0001/1K 토큰 × 50 = $0.005
- **Claude 3.5 Sonnet**:
  - 입력 토큰: 1000 쿼리 × 평균 2000 토큰 (컨텍스트) = 2M 토큰
  - 출력 토큰: 1000 쿼리 × 평균 500 토큰 = 500K 토큰
  - 입력 비용: $0.003/1K 토큰 × 2000 = $6.00
  - 출력 비용: $0.015/1K 토큰 × 500 = $7.50
  - 소계: $13.50

#### S3 비용
- **스토리지**: 
  - 문서: 100MB (원본 + 청크)
  - 벡터: 200MB (임베딩)
  - 메타데이터: 10MB
  - 총 310MB × $0.023/GB = $0.007
- **요청**:
  - GET 요청: 1000 쿼리 × 5 문서 = 5000 요청
  - 비용: $0.0004/1K 요청 × 5 = $0.002
- **데이터 전송**: 
  - 1000 쿼리 × 5 문서 × 10KB = 50MB
  - 비용: 무료 (1GB 미만)
- **소계**: $0.009

#### Lambda 비용
- **실행 시간**: 1000 쿼리 × 2초 × 1024MB = 2000 GB-초
- **요청**: 1000 요청
- 실행 비용: $0.0000166667/GB-초 × 2000 = $0.033
- 요청 비용: $0.20/1M 요청 × 0.001 = $0.0002
- **소계**: $0.033

#### 총 예상 비용
- **Bedrock**: $13.505
- **S3**: $0.009
- **Lambda**: $0.033
- **총계**: **$13.55/월** (1000 쿼리 기준)

#### 비용 절감 효과
- **OpenSearch Serverless 대비**: $86.45/월 절감 (86% 절감)
- S3 벡터 스토어 사용으로 인프라 비용 최소화
- 사용량 기반 과금으로 유연한 비용 관리

#### 확장 시나리오
| 월간 쿼리 수 | Bedrock | S3 | Lambda | 총 비용 |
|------------|---------|-----|--------|---------|
| 1,000 | $13.51 | $0.01 | $0.03 | $13.55 |
| 5,000 | $67.53 | $0.02 | $0.17 | $67.72 |
| 10,000 | $135.05 | $0.03 | $0.33 | $135.41 |
| 50,000 | $675.25 | $0.10 | $1.67 | $677.02 |

#### 비용 최적화 팁
1. **캐싱 활용**: 자주 묻는 질문 캐싱으로 Bedrock 호출 감소
2. **필터 사용**: 메타데이터 필터로 불필요한 문서 검색 방지
3. **청크 크기 최적화**: 적절한 청크 크기로 토큰 사용량 감소
4. **배치 처리**: 여러 질문을 한 번에 처리하여 효율성 향상

## 14. 향후 개선 사항

1. **멀티모달 지원**: 이미지, 도표 포함 문서 처리
2. **실시간 업데이트**: 새 문서 자동 인덱싱
3. **대화 기록 관리**: 컨텍스트 유지
4. **개인화**: 사용자별 맞춤 답변
5. **다국어 지원**: 영어, 중국어 추가
