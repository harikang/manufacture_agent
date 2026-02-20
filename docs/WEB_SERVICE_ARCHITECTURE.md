# 다이캐스팅 품질 예측 AI 웹 서비스 아키텍처

## 📋 서비스 개요

다이캐스팅 공정의 품질 예측, 원인 분석, 공정 지식 검색을 제공하는 AI 기반 웹 서비스

### 주요 기능
- **품질 예측 (T1)**: ML 모델 기반 양품/불량 판정 및 확률 산출
- **원인 분석 (T2)**: XAI 기반 Feature Importance 시각화
- **지식 검색 (T3)**: Bedrock RAG 기반 공정 Knowledge Base 질의응답

---

## 🏗️ 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              사용자 브라우저                              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     CloudFront (HTTPS)                                   │
│                 dspu51cezno9b.cloudfront.net                            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
┌──────────────────────────────┐    ┌──────────────────────────────────────┐
│      S3 (정적 웹 호스팅)       │    │         API Gateway (HTTP API)        │
│   diecasting-frontend        │    │  your-api-gateway.execute-api.us-east-1    │
│   - index.html               │    │                                      │
│   - chat.html                │    │   POST /t1 → Lambda T1 (예측)        │
│   - ref2.jpg                 │    │   POST /t2 → Lambda T2 (분석)        │
└──────────────────────────────┘    │   POST /t3 → Lambda T3 (RAG)         │
                                    └──────────────────────────────────────┘
                                                    │
                    ┌───────────────┬───────────────┼───────────────┐
                    ▼               ▼               ▼               ▼
            ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
            │  Lambda T1  │ │  Lambda T2  │ │  Lambda T3  │ │   Bedrock   │
            │  품질 예측   │ │  원인 분석   │ │  RAG 검색   │ │ Claude 3.5  │
            └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
                    │               │               │
                    ▼               ▼               ▼
            ┌─────────────────────────────────────────────────────────────┐
            │                        S3 Buckets                           │
            │  diecasting-models (ML 모델)  │  diecasting-knowledge-base  │
            └─────────────────────────────────────────────────────────────┘
```

---

## 🖥️ 프론트엔드

### 기술 스택
- **HTML5 / CSS3 / Vanilla JavaScript**
- **호스팅**: S3 정적 웹사이트 + CloudFront CDN

### 파일 구조
```
withoutstreamlit/
├── index.html          # 랜딩 페이지
├── chat.html           # AI 채팅 인터페이스
└── equipment_sensor_mapping.json  # 장비/센서 매핑 데이터
```

### 주요 컴포넌트

| 파일 | 설명 |
|------|------|
| `index.html` | 서비스 소개 랜딩 페이지, 주요 기능 안내 |
| `chat.html` | AI 채팅 UI, 공정 데이터 입력 패널, 결과 시각화 |

### 접속 URL
- **CloudFront**: `https://dspu51cezno9b.cloudfront.net`
- **S3 직접**: `http://diecasting-frontend.s3-website-us-east-1.amazonaws.com`

---

## ⚙️ 백엔드

### API Gateway
- **Type**: HTTP API
- **Endpoint**: `https://your-api-gateway.execute-api.us-east-1.amazonaws.com/prod`
- **CORS**: 모든 Origin 허용

### Lambda 함수

| 함수명 | 경로 | 기능 | 런타임 |
|--------|------|------|--------|
| `diecasting-predict-t1` | POST /t1 | 품질 예측 (AutoEncoder + Gradient Boosting) | Docker (Python) |
| `diecasting-importance-t2` | POST /t2 | Feature Importance 분석 | Docker (Python) |
| `diecasting-rag-t3` | POST /t3 | Knowledge Base RAG 검색 | Docker (Python) |

### API 명세

#### POST /t1 - 품질 예측
```json
// Request
{
  "features": {
    "Process_Temperature": 670.0,
    "Process_Pressure": 145.0,
    // ... 30개 공정 변수
  }
}

// Response
{
  "prediction": {
    "class": "normal",
    "probability": 0.85,
    "class_probabilities": { "normal": 0.85, "defect": 0.15 }
  },
  "latent_features": [0.12, -0.34, ...],
  "processing_time_ms": 45.2
}
```

#### POST /t2 - 원인 분석
```json
// Request
{
  "features": { ... },
  "latent_features": [...],
  "top_n": 10
}

// Response
{
  "top_features": [
    ["Process_Temperature", 0.152],
    ["Sensor_Pressure1", 0.098],
    // ...
  ]
}
```

#### POST /t3 - 지식 검색
```json
// Request
{
  "query": "사출 압력 권장 범위"
}

// Response
{
  "answer": "다이캐스팅 공정의 권장 사출 압력은 120-130 MPa입니다...",
  "sources": [
    { "title": "defect_analysis.md", "uri": "s3://...", "score": 0.69 }
  ]
}
```

---

## ☁️ AWS 인프라

### 사용 서비스

| 서비스 | 용도 | 리소스명 |
|--------|------|----------|
| **S3** | 정적 웹 호스팅 | `diecasting-frontend` |
| **S3** | ML 모델 저장 | `diecasting-models` |
| **S3** | Knowledge Base 문서 | `diecasting-knowledge-base` |
| **CloudFront** | CDN / HTTPS | `E3AC6CCXVU3ILB` |
| **API Gateway** | REST API | `your-api-gateway` |
| **Lambda** | 서버리스 컴퓨팅 | T1, T2, T3 함수 |
| **Bedrock** | LLM (Claude 3.5) | Knowledge Base RAG |
| **ECR** | Docker 이미지 저장소 | Lambda 컨테이너 이미지 |

### 리전
- **us-east-1** (N. Virginia)

### 주요 엔드포인트

```
# CloudFront (프론트엔드)
https://dspu51cezno9b.cloudfront.net

# API Gateway (백엔드)
https://your-api-gateway.execute-api.us-east-1.amazonaws.com/prod/t1
https://your-api-gateway.execute-api.us-east-1.amazonaws.com/prod/t2
https://your-api-gateway.execute-api.us-east-1.amazonaws.com/prod/t3
```

---

## 🔄 데이터 흐름

### 1. 품질 예측 플로우
```
사용자 질문 ("현재 조건에서 불량 가능성은?")
    ↓
Intent 분류 (prediction)
    ↓
Lambda T1 호출 (30개 공정 변수)
    ↓
AutoEncoder → Latent Features (12D)
    ↓
Gradient Boosting → 예측 결과
    ↓
Lambda T2 호출 (Feature Importance)
    ↓
UI 렌더링 (게이지 차트 + 막대 그래프 + 장비 카드)
```

### 2. 지식 검색 플로우
```
사용자 질문 ("사출 압력 권장 범위")
    ↓
Intent 분류 (knowledge)
    ↓
Lambda T3 호출
    ↓
Bedrock Knowledge Base 검색
    ↓
Claude 3.5 답변 생성
    ↓
UI 렌더링 (답변 + 참고 문서)
```

---

## 📁 관련 파일

### 프론트엔드
- `withoutstreamlit/index.html` - 랜딩 페이지
- `withoutstreamlit/chat.html` - 채팅 UI
- `withoutstreamlit/equipment_sensor_mapping.json` - 장비/센서 정보

### 백엔드 (Lambda)
- `lambda_t1_predict.py` - 품질 예측 Lambda
- `lambda_t2_importance.py` - Feature Importance Lambda
- `lambda_t3_rag.py` - RAG 검색 Lambda

### 배포 스크립트
- `deploy_lambda_t1_docker.sh` - T1 Docker 배포
- `deploy_lambda_t2_docker.sh` - T2 Docker 배포
- `deploy_lambda_t3.sh` - T3 배포

### ML 모델
- `deployment_models/autoencoder_latent12.pth` - AutoEncoder
- `deployment_models/gradient_boosting_model.pkl` - GB 분류기
- `deployment_models/scaler.pkl` - Feature Scaler

---

## 🚀 배포 방법

### 프론트엔드 배포
```bash
# S3 업로드
aws s3 cp withoutstreamlit/index.html s3://diecasting-frontend/
aws s3 cp withoutstreamlit/chat.html s3://diecasting-frontend/

# CloudFront 캐시 무효화
aws cloudfront create-invalidation --distribution-id E3AC6CCXVU3ILB --paths "/*"
```

### Lambda 배포 (Docker)
```bash
# ECR 로그인
aws ecr get-login-password | docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# 이미지 빌드 & 푸시
docker build -t diecasting-lambda-t3 -f Dockerfile.lambda_t3 .
docker tag diecasting-lambda-t3:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/diecasting-lambda-t3:latest
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/diecasting-lambda-t3:latest

# Lambda 업데이트
aws lambda update-function-code --function-name diecasting-rag-t3 --image-uri ...
```

---

## 📊 성능 지표

| 지표 | 값 |
|------|-----|
| 예측 정확도 | 99.2% |
| 평균 응답 시간 | < 1초 |
| 분석 가능 변수 | 30개 |
| Knowledge Base 문서 | 10+ |

---

*최종 업데이트: 2026-01-31*
