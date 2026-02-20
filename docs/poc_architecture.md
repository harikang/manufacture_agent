# 다이캐스팅 품질 예측 PoC 아키텍처

## 시스템 구조

```
(사내 사용자)
     |
     | HTTPS (사내 IP allowlist)
     v
[Public ALB]
     |
     | Forward to ECS
     v
[ECS Fargate: Streamlit UI + Agent(오케스트레이터)]
     |
     | HTTPS (API 호출)
     v
[API Gateway]
     |
     +----------------+----------------+
     |                |                |
     v                v                v
[Lambda T1]      [Lambda T2]      [Lambda T3]
Predict          Importance       RAG/KB Query
     |                |                |
     |                v                v
     |           [S3 Bucket]    [Bedrock Knowledge Bases]
     |           (importance     (S3 문서 기반)
     |            JSON/PNG)
     v
[결과 반환]
```

## 최적 모델 구성

### Lambda T1: Predict
- **Model**: Gradient Boosting + 12D Latent AutoEncoder
- **Input**: 30D features (Process 16개 + Sensor 14개)
- **Output**: 불량 예측 (확률, 클래스, 신뢰도)
- **Performance**: F1=0.7027, ROC-AUC=0.9175

### Lambda T2: Feature Importance
- **기능**: SHAP values 계산 및 시각화
- **Output**: Feature importance JSON + PNG
- **저장**: S3 bucket

### Lambda T3: RAG/KB Query
- **기능**: Bedrock Knowledge Bases 연동
- **목적**: 불량 원인 분석, 개선 방안 제시
- **데이터**: 과거 불량 사례, 공정 매뉴얼

---

## 배포 파일 구조

```
poc-deployment/
├── lambda/
│   ├── t1_predict/
│   │   ├── lambda_function.py
│   │   ├── requirements.txt
│   │   ├── models/
│   │   │   ├── autoencoder_latent12.pth
│   │   │   ├── gradient_boosting_model.pkl
│   │   │   └── scaler.pkl
│   │   └── Dockerfile
│   │
│   ├── t2_importance/
│   │   ├── lambda_function.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   └── t3_rag/
│       ├── lambda_function.py
│       ├── requirements.txt
│       └── Dockerfile
│
├── streamlit/
│   ├── app.py
│   ├── agent.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── terraform/
│   ├── main.tf
│   ├── alb.tf
│   ├── ecs.tf
│   ├── lambda.tf
│   ├── api_gateway.tf
│   └── s3.tf
│
└── README.md
```

---

## 기술 스택

### Lambda T1 (Predict)
- **Runtime**: Python 3.11
- **Memory**: 2048 MB
- **Timeout**: 30s
- **Dependencies**:
  - torch (CPU-only)
  - scikit-learn
  - numpy
  - pandas

### Lambda T2 (Importance)
- **Runtime**: Python 3.11
- **Memory**: 3008 MB
- **Timeout**: 60s
- **Dependencies**:
  - shap
  - matplotlib
  - boto3 (S3 upload)

### Lambda T3 (RAG)
- **Runtime**: Python 3.11
- **Memory**: 1024 MB
- **Timeout**: 30s
- **Dependencies**:
  - boto3 (Bedrock)
  - langchain

### ECS Fargate (Streamlit)
- **vCPU**: 0.5
- **Memory**: 1 GB
- **Port**: 8501
- **Dependencies**:
  - streamlit
  - requests
  - plotly

---

## API 스펙

### 1. POST /predict (Lambda T1)

**Request**:
```json
{
  "features": {
    "Process_Temperature": 650.5,
    "Process_Pressure": 120.3,
    "Process_InjectionSpeed": 2.5,
    ...
    "Sensor_Vibration": 0.15
  }
}
```

**Response**:
```json
{
  "prediction": {
    "class": "defect",
    "probability": 0.78,
    "confidence": "high"
  },
  "latent_features": [0.12, -0.45, 0.89, ...],
  "processing_time_ms": 15,
  "model_version": "v1.0_12D_GB"
}
```

### 2. POST /importance (Lambda T2)

**Request**:
```json
{
  "features": { ... },
  "prediction_id": "pred_20260115_001"
}
```

**Response**:
```json
{
  "importance": {
    "Process_Temperature": 0.25,
    "Sensor_Vibration": 0.18,
    ...
  },
  "visualization_url": "s3://bucket/importance/pred_20260115_001.png",
  "top_features": [
    {"name": "Process_Temperature", "value": 0.25},
    {"name": "Sensor_Vibration", "value": 0.18},
    {"name": "Process_Pressure", "value": 0.15}
  ]
}
```

### 3. POST /rag-query (Lambda T3)

**Request**:
```json
{
  "query": "온도 650도에서 진동 0.15일 때 불량 원인은?",
  "context": {
    "prediction": "defect",
    "top_features": ["Process_Temperature", "Sensor_Vibration"]
  }
}
```

**Response**:
```json
{
  "answer": "온도 650도는 권장 범위(620-640도)를 초과하여...",
  "sources": [
    {
      "document": "공정_매뉴얼_v2.pdf",
      "page": 15,
      "relevance": 0.92
    }
  ],
  "recommendations": [
    "온도를 630도로 낮추세요",
    "냉각 시스템을 점검하세요"
  ]
}
```

---

## 보안 및 네트워크

### ALB 설정
- **Listener**: HTTPS (443)
- **SSL Certificate**: ACM
- **Security Group**: 사내 IP allowlist
- **Health Check**: /health

### API Gateway 설정
- **Type**: REST API
- **Authorization**: IAM (ECS Task Role)
- **Throttling**: 1000 req/sec
- **CORS**: Enabled

### Lambda 설정
- **VPC**: Private subnet (NAT Gateway 경유)
- **Security Group**: Outbound only
- **IAM Role**: 최소 권한 원칙

---

## 모니터링 및 로깅

### CloudWatch Metrics
- Lambda 실행 시간
- Lambda 에러율
- API Gateway 요청 수
- ECS CPU/Memory 사용률

### CloudWatch Logs
- Lambda 실행 로그
- Streamlit 애플리케이션 로그
- API Gateway 액세스 로그

### X-Ray Tracing
- End-to-end 요청 추적
- 병목 구간 식별

---

## 비용 추정 (월간)

### Lambda T1 (Predict)
- 요청: 100,000회/월
- 실행 시간: 평균 15ms
- 메모리: 2048 MB
- **비용**: ~$5

### Lambda T2 (Importance)
- 요청: 10,000회/월 (선택적)
- 실행 시간: 평균 500ms
- 메모리: 3008 MB
- **비용**: ~$8

### Lambda T3 (RAG)
- 요청: 5,000회/월
- 실행 시간: 평균 200ms
- 메모리: 1024 MB
- **비용**: ~$2

### ECS Fargate
- vCPU: 0.5, Memory: 1 GB
- 24/7 운영
- **비용**: ~$15

### API Gateway
- 요청: 115,000회/월
- **비용**: ~$0.40

### S3 + CloudWatch
- **비용**: ~$5

### **총 예상 비용**: ~$35/월

---

## 성능 목표

### Lambda T1 (Predict)
- **Cold Start**: < 2s
- **Warm Execution**: < 20ms
- **Throughput**: 1000 req/sec
- **Availability**: 99.9%

### End-to-End
- **P50 Latency**: < 100ms
- **P99 Latency**: < 500ms
- **Error Rate**: < 0.1%

---

## 배포 전략

### Phase 1: 개발 환경 (1주)
- Lambda 함수 개발 및 테스트
- Streamlit UI 개발
- 로컬 통합 테스트

### Phase 2: 스테이징 환경 (1주)
- Terraform으로 인프라 구축
- CI/CD 파이프라인 설정
- 부하 테스트

### Phase 3: 프로덕션 배포 (1주)
- Blue/Green 배포
- 모니터링 설정
- 사용자 교육

### Phase 4: 운영 및 최적화 (지속)
- 성능 모니터링
- 모델 재학습 (월 1회)
- 피드백 수집 및 개선
