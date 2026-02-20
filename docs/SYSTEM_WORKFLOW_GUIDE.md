# 다이캐스팅 품질 예측 시스템 - 사용자 워크플로우 가이드

## 📋 목차
1. [시스템 개요](#시스템-개요)
2. [전체 워크플로우](#전체-워크플로우)
3. [Lambda 함수 상세](#lambda-함수-상세)
4. [Streamlit UI 사용법](#streamlit-ui-사용법)
5. [배포 정보](#배포-정보)

---

## 시스템 개요

**다이캐스팅 품질 예측 시스템**은 AI 기반 실시간 불량 예측 및 분석 플랫폼입니다.

### 주요 기능
- ✅ **실시간 품질 예측**: 30개 공정/센서 데이터 → 불량/정상 판정
- 🔍 **Feature Importance 분석**: SHAP 기반 상세 분석
- 💬 **AI 어시스턴트**: RAG 기반 공정 질의응답

### 기술 스택
- **Frontend**: Streamlit
- **Backend**: AWS Lambda (Container Image)
- **ML Models**: AutoEncoder (30D→12D) + Gradient Boosting
- **AI**: Amazon Bedrock (Claude 3.5 Sonnet)
- **Vector DB**: S3 Vectors (Knowledge Base)

---

## 전체 워크플로우

```
┌─────────────────────────────────────────────────────────────────┐
│                    사용자 워크플로우                              │
└─────────────────────────────────────────────────────────────────┘

1. 사용자가 Streamlit UI 접속
   ↓
2. 공정 파라미터 및 센서 데이터 입력 (30개 features)
   - Process Parameters: 16개 (온도, 압력, 속도 등)
   - Sensor Data: 14개 (진동, 소음, 온도, 압력 등)
   ↓
3. "예측 실행" 버튼 클릭
   ↓
4. Streamlit → Lambda T1 호출 (HTTP POST)
   ├─ AutoEncoder: 30D → 12D 압축
   ├─ Gradient Boosting: 42D (30+12) → 불량 예측
   └─ 결과 반환: 불량/정상 + 확률 + 12D latent
   ↓
5. 예측 결과 표시
   ├─ 불량/정상 분류
   ├─ 불량 확률 (0-100%)
   ├─ 신뢰도 (high/medium/low)
   ├─ 처리 시간
   └─ Latent Features 시각화 (12D 바 차트)
   ↓
6. (선택) "상세 분석" 버튼 클릭
   ↓
7. Streamlit → Lambda T2 호출 (HTTP POST)
   ├─ Feature Importance 계산 (GradientBoosting)
   ├─ 시각화 생성 (PNG)
   └─ S3에 저장 후 Presigned URL 반환
   ↓
8. Feature Importance 시각화 표시
   ├─ Top 15 features
   ├─ Importance values
   ├─ 장비/센서 설명
   └─ 조치 방안 가이드
   ↓
9. (선택) AI 어시스턴트 탭에서 질문 입력
   ↓
10. Streamlit → Lambda T3 호출 (HTTP POST)
    ├─ Knowledge Base 검색 (S3 Vectors)
    ├─ 관련 문서 검색 (Top 5)
    ├─ Claude 3.5 Sonnet 답변 생성
    └─ 자연어 답변 + 출처 반환
    ↓
11. AI 답변 표시
    ├─ 자연어 답변
    ├─ 참고 문서 (출처)
    └─ 관련도 점수
```

---

## Lambda 함수 상세

### Lambda T1: 품질 예측 (Prediction)

**Function Name**: `diecasting-predict-t1`  
**URL**: `https://your-lambda-t1.lambda-url.us-east-1.on.aws/`

#### 입력 형식
```json
{
  "body": {
    "features": {
      "Process_Temperature": 1.515671,
      "Process_Pressure": 440.549188,
      "Process_InjectionSpeed": 0.149605,
      ...
      "Sensor_Voltage": 21.912492
    }
  }
}
```

#### 출력 형식
```json
{
  "statusCode": 200,
  "body": {
    "prediction": {
      "class": "normal",
      "probability": 0.1391,
      "confidence": "high",
      "confidence_score": 0.8609,
      "class_probabilities": {
        "normal": 0.8609,
        "defect": 0.1391
      }
    },
    "latent_features": [0.23, -0.18, ...],
    "processing_time_ms": 7.0,
    "model_version": "v1.0_12D_GB",
    "model_performance": {
      "f1_score": 0.7027,
      "roc_auc": 0.9175,
      "accuracy": 0.8832
    }
  }
}
```

#### 처리 과정
1. **Feature Scaling**: StandardScaler로 정규화
2. **AutoEncoder**: 30D → 12D 압축 (SwiGLU + Attention)
3. **Feature Combination**: 30D + 12D = 42D
4. **Prediction**: Gradient Boosting Classifier
5. **Confidence Calculation**: 확률 기반 신뢰도 산출

#### 성능
- **처리 시간**: ~7-10ms (Warm start)
- **Cold start**: ~2-3초
- **메모리**: 1024 MB
- **Timeout**: 30초

---

### Lambda T2: Feature Importance 분석 (Analysis)

**Function Name**: `diecasting-importance-t2`  
**URL**: `https://your-lambda-t2.lambda-url.us-east-1.on.aws/`

#### 입력 형식
```json
{
  "body": {
    "features": { ... },
    "latent_features": [0.23, -0.18, ...],
    "top_n": 15,
    "generate_chart": true
  }
}
```

#### 출력 형식
```json
{
  "statusCode": 200,
  "body": {
    "feature_importance": {
      "Process_Temperature": 0.1234,
      "Process_Pressure": 0.0987,
      ...
    },
    "top_features": [
      ["Process_Temperature", 0.1234],
      ["Process_Pressure", 0.0987],
      ...
    ],
    "equipment_descriptions": [
      {
        "feature_name": "Process_Temperature",
        "name": "용탕 온도",
        "equipment": "용탕로 (Melting Furnace)",
        "description": "...",
        "importance": 0.1234
      }
    ],
    "plot_url": "https://...",
    "processing_time_ms": 1800.0
  }
}
```

#### 처리 과정
1. **Feature Importance 계산**: GradientBoosting의 `feature_importances_` 사용
2. **Top N 추출**: 상위 N개 feature 선택
3. **장비 매핑**: S3에서 equipment_sensor_mapping.json 로드
4. **시각화 생성**: matplotlib로 바 차트 생성
5. **S3 업로드**: PNG 파일 업로드 및 Presigned URL 생성

#### 성능
- **처리 시간**: ~1.8-2초
- **메모리**: 2048 MB
- **Timeout**: 60초

---

### Lambda T3: AI 어시스턴트 (RAG)

**Function Name**: `diecasting-rag-t3`  
**URL**: `https://your-lambda-t3.lambda-url.us-east-1.on.aws/`

#### 입력 형식
```json
{
  "body": {
    "query": "기공 불량의 주요 원인은 무엇인가요?"
  }
}
```

#### 출력 형식
```json
{
  "statusCode": 200,
  "body": {
    "answer": "기공 불량의 주요 원인은...",
    "sources": [
      {
        "title": "기공 불량 분석 가이드",
        "uri": "s3://diecasting-knowledge-base/...",
        "score": 0.85
      }
    ],
    "processing_time_ms": 1500.0
  }
}
```

#### 처리 과정
1. **Knowledge Base 검색**: S3 Vectors에서 관련 문서 검색
2. **Context 구성**: Top 5 문서 추출
3. **LLM 호출**: Claude 3.5 Sonnet으로 답변 생성
4. **출처 반환**: 참고 문서 정보 포함

#### 성능
- **처리 시간**: ~1.5-2초
- **메모리**: 512 MB
- **Timeout**: 60초

---

## Streamlit UI 사용법

### 접속 방법
```bash
# 로컬 실행
streamlit run streamlit_app.py

# 배포된 URL
http://18.234.101.63:8501
```

### 탭 구성

#### 1️⃣ 품질 예측 탭
- **공정 파라미터 입력**: 16개 필드
- **센서 데이터 입력**: 14개 필드
- **예측 실행**: Lambda T1 호출
- **결과 표시**:
  - 판정 카드 (불량/정상)
  - 불량 확률 게이지
  - Latent Features 바 차트
  - 모델 성능 정보

#### 2️⃣ 상세 분석 탭
- **전제 조건**: 먼저 예측 실행 필요
- **상세 분석 실행**: Lambda T2 호출
- **결과 표시**:
  - SHAP Waterfall Plot (이미지)
  - Top 15 Feature Importance 바 차트
  - Feature Importance 테이블
  - 장비/센서 설명
  - 해석 가이드

#### 3️⃣ AI 어시스턴트 탭
- **질문 입력**: 채팅 인터페이스
- **답변 생성**: Lambda T3 호출
- **결과 표시**:
  - 자연어 답변
  - 참고 문서 (출처)
  - 관련도 점수
- **채팅 히스토리**: 세션 내 대화 기록

### 사이드바
- **시스템 정보**: Lambda 함수 상태
- **모델 정보**: 성능 지표
- **사용 가이드**: 간단한 사용법

---

## 배포 정보

### AWS 리소스

#### S3 Buckets
- **diecasting-models**: 모델 파일 저장
  - `models/autoencoder_latent12.pth`
  - `models/gradient_boosting_model.pkl`
  - `models/scaler.pkl`
  - `config/equipment_sensor_mapping.json`
  - `analysis/importance_chart_*.png`

#### Lambda Functions
| Function | Memory | Timeout | Package Type |
|----------|--------|---------|--------------|
| diecasting-predict-t1 | 1024 MB | 30s | Image |
| diecasting-importance-t2 | 2048 MB | 60s | Image |
| diecasting-rag-t3 | 512 MB | 60s | Zip |

#### Bedrock
- **Knowledge Base ID**: `4GOU8MFELR`
- **Data Source ID**: `85CWXCHZLJ`
- **Embedding Model**: Titan Embeddings G1 - Text v2
- **LLM**: Claude 3.5 Sonnet v2

#### ECR Repositories
- `diecasting-lambda-t1`
- `diecasting-lambda-t2`

### 비용 추정 (월간, 1000 requests 기준)

| 서비스 | 비용 |
|--------|------|
| Lambda T1 | $0.20 |
| Lambda T2 | $0.40 |
| Lambda T3 | $0.10 |
| Bedrock (Claude) | $12.00 |
| S3 | $0.50 |
| Knowledge Base | $3.00 |
| **총계** | **$16.20** |

### 보안

#### IAM Role
- **Role Name**: `lambda-diecasting-execution-role`
- **Policies**:
  - `AWSLambdaBasicExecutionRole`
  - `S3AccessPolicy` (diecasting-models)
  - `BedrockAccessPolicy` (Claude 3.5 Sonnet)

#### Network
- **Lambda**: Public subnet (Function URL)
- **S3**: Private (IAM 인증)
- **Bedrock**: AWS PrivateLink

---

## 테스트 방법

### 전체 워크플로우 테스트
```bash
python test_full_workflow.py
```

### 개별 Lambda 테스트

#### Lambda T1
```bash
curl -X POST https://your-lambda-t1.lambda-url.us-east-1.on.aws/ \
  -H 'Content-Type: application/json' \
  -d @test_payload_t1.json
```

#### Lambda T2
```bash
curl -X POST https://your-lambda-t2.lambda-url.us-east-1.on.aws/ \
  -H 'Content-Type: application/json' \
  -d @test_payload_t2.json
```

#### Lambda T3
```bash
curl -X POST https://your-lambda-t3.lambda-url.us-east-1.on.aws/ \
  -H 'Content-Type: application/json' \
  -d '{"body":{"query":"기공 불량의 주요 원인은?"}}'
```

---

## 문제 해결

### Lambda T1 NaN 오류
- **원인**: 입력 값이 학습 데이터 분포를 벗어남
- **해결**: 현실적인 값 사용 (scaler 통계 기반)

### Lambda T2 numpy 오류
- **원인**: numpy 버전 불일치
- **해결**: numpy 2.2.1 사용

### Lambda T3 Query 오류
- **원인**: 페이로드 형식 불일치
- **해결**: `question` → `query`로 변경

### Streamlit 연결 오류
- **원인**: Lambda URL 파일 없음
- **해결**: `lambda_t*_url.txt` 파일 확인

---

## 유지보수

### 모델 업데이트
1. 새 모델 학습
2. S3에 업로드
3. Lambda 환경 변수 업데이트 (캐시 무효화)

### Knowledge Base 업데이트
1. 문서 추가/수정
2. S3에 업로드
3. Data Source 동기화

### Lambda 재배포
```bash
# Lambda T1
bash deploy_lambda_t1_docker.sh

# Lambda T2
bash deploy_lambda_t2_docker.sh

# Lambda T3
bash deploy_lambda_t3.sh
```

---

## 참고 문서
- [FINAL_SYSTEM_DOCUMENTATION.md](FINAL_SYSTEM_DOCUMENTATION.md)
- [LAMBDA_T3_RAG_DESIGN.md](LAMBDA_T3_RAG_DESIGN.md)
- [SYSTEM_SUMMARY.md](SYSTEM_SUMMARY.md)

---

**Version**: 1.0.0  
**Last Updated**: 2026-01-26  
**Author**: AI Development Team
