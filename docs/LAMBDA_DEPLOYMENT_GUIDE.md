# Lambda 함수 배포 가이드

## 📋 개요

3개의 Lambda 함수를 배포하여 다이캐스팅 품질 예측 시스템을 구축합니다.

- **Lambda T1**: 품질 예측 (AutoEncoder + Gradient Boosting)
- **Lambda T2**: Feature Importance 분석 (S3 + Bedrock)
- **Lambda T3**: RAG 기반 질의응답 (Knowledge Base + Bedrock)

## 🏗️ 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit UI (ECS)                        │
└─────────────────────────────────────────────────────────────┘
                          ↓
        ┌─────────────────┼─────────────────┐
        ↓                 ↓                 ↓
   [Lambda T1]       [Lambda T2]       [Lambda T3]
    Predict          Importance          RAG Query
        ↓                 ↓                 ↓
   [S3 Models]      [S3 Analysis]    [Knowledge Base]
                         ↓                 ↓
                    [Bedrock]         [Bedrock]
```

## 📦 사전 준비

### 1. S3 버킷 생성

```bash
# 모델 저장용 버킷
aws s3 mb s3://diecasting-models --region us-east-1

# Knowledge Base 문서용 버킷
aws s3 mb s3://diecasting-knowledge --region us-east-1
```

### 2. 모델 파일 업로드

```bash
# AutoEncoder 모델
aws s3 cp deployment_models/autoencoder_latent12.pth \
  s3://diecasting-models/models/autoencoder_latent12.pth

# Gradient Boosting 모델
aws s3 cp deployment_models/gradient_boosting_model.pkl \
  s3://diecasting-models/models/gradient_boosting_model.pkl

# Scaler
aws s3 cp deployment_models/scaler.pkl \
  s3://diecasting-models/models/scaler.pkl
```

### 3. Feature Importance 파일 생성 및 업로드

```bash
# feature_importance.json 생성 (Python)
python export_models_for_deployment.py

# S3 업로드
aws s3 cp feature_importance.json \
  s3://diecasting-models/analysis/feature_importance.json

aws s3 cp feature_importance.png \
  s3://diecasting-models/analysis/feature_importance.png
```

### 4. Knowledge Base 문서 업로드

```bash
# 문서 업로드
aws s3 sync knowledge_base_docs/ \
  s3://diecasting-knowledge/documents/ \
  --recursive
```

## 🚀 Lambda T1 배포 (품질 예측)

### 1. Lambda Layer 생성 (PyTorch + scikit-learn)

```bash
# Layer 디렉토리 생성
mkdir -p lambda-layer/python

# 패키지 설치
pip install \
  torch==2.1.0 \
  scikit-learn==1.3.2 \
  numpy==1.26.2 \
  -t lambda-layer/python/ \
  --platform manylinux2014_x86_64 \
  --only-binary=:all:

# ZIP 생성
cd lambda-layer
zip -r ml-layer.zip python/
cd ..

# Layer 업로드
aws lambda publish-layer-version \
  --layer-name diecasting-ml-layer \
  --zip-file fileb://lambda-layer/ml-layer.zip \
  --compatible-runtimes python3.11 \
  --region us-east-1
```

### 2. Lambda 함수 생성

```bash
# autoencoder_model.py 포함하여 ZIP 생성
zip lambda-t1.zip lambda_t1_predict.py autoencoder_model.py

# Lambda 함수 생성
aws lambda create-function \
  --function-name diecasting-predict-t1 \
  --runtime python3.11 \
  --role arn:aws:iam::ACCOUNT_ID:role/lambda-execution-role \
  --handler lambda_t1_predict.lambda_handler \
  --zip-file fileb://lambda-t1.zip \
  --timeout 30 \
  --memory-size 1024 \
  --environment Variables="{BUCKET_NAME=diecasting-models}" \
  --layers arn:aws:lambda:us-east-1:ACCOUNT_ID:layer:diecasting-ml-layer:1 \
  --region us-east-1
```

### 3. IAM 권한 설정

Lambda 실행 역할에 다음 권한 추가:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::diecasting-models/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

### 4. API Gateway 연결

```bash
# REST API 생성
aws apigateway create-rest-api \
  --name diecasting-api \
  --region us-east-1

# Lambda 통합 설정 (콘솔에서 진행 권장)
```

## 🚀 Lambda T2 배포 (Feature Importance - SHAP 기반)

### 1. SHAP Explainer 사전 생성

```bash
# SHAP explainer 생성
python create_shap_explainer.py

# S3 업로드
aws s3 cp deployment_models/shap_explainer.pkl \
  s3://diecasting-models/models/shap_explainer.pkl
```

### 2. Lambda Layer 업데이트 (SHAP 포함)

```bash
# Layer 디렉토리 생성
mkdir -p lambda-layer-t2/python

# 패키지 설치 (SHAP 포함)
pip install \
  shap==0.44.0 \
  matplotlib==3.8.2 \
  numpy==1.26.2 \
  -t lambda-layer-t2/python/ \
  --platform manylinux2014_x86_64 \
  --only-binary=:all:

# ZIP 생성
cd lambda-layer-t2
zip -r shap-layer.zip python/
cd ..

# Layer 업로드
aws lambda publish-layer-version \
  --layer-name diecasting-shap-layer \
  --zip-file fileb://lambda-layer-t2/shap-layer.zip \
  --compatible-runtimes python3.11 \
  --region us-east-1
```

### 3. Lambda 함수 생성

```bash
# ZIP 생성
zip lambda-t2.zip lambda_t2_importance.py

# Lambda 함수 생성
aws lambda create-function \
  --function-name diecasting-importance-t2 \
  --runtime python3.11 \
  --role arn:aws:iam::ACCOUNT_ID:role/lambda-execution-role \
  --handler lambda_t2_importance.lambda_handler \
  --zip-file fileb://lambda-t2.zip \
  --timeout 60 \
  --memory-size 1024 \
  --environment Variables="{BUCKET_NAME=diecasting-models}" \
  --layers \
    arn:aws:lambda:us-east-1:ACCOUNT_ID:layer:diecasting-ml-layer:1 \
    arn:aws:lambda:us-east-1:ACCOUNT_ID:layer:diecasting-shap-layer:1 \
  --region us-east-1
```

### 4. Bedrock 권한 추가

```json
{
  "Effect": "Allow",
  "Action": [
    "bedrock:InvokeModel",
    "s3:PutObject"
  ],
  "Resource": [
    "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-haiku-20240307-v1:0",
    "arn:aws:s3:::diecasting-models/analysis/*"
  ]
}
```

### 5. 테스트

```bash
# 예측 결과와 함께 테스트
aws lambda invoke \
  --function-name diecasting-importance-t2 \
  --payload file://test_importance_payload.json \
  response.json

cat response.json
```

test_importance_payload.json:
```json
{
  "body": {
    "features": {
      "Process_Temperature": 690.0,
      "Process_Pressure": 145.0,
      ...
    },
    "latent_features": [0.12, -0.45, 0.33, 0.67, -0.23, 0.89, -0.12, 0.45, -0.67, 0.23, -0.89, 0.34],
    "top_n": 10,
    "use_bedrock": true,
    "generate_chart": true
  }
}
```

**주요 기능:**
- SHAP TreeExplainer로 실시간 feature importance 계산
- 개별 예측에 대한 SHAP values 분석
- 영향을 미친 장비/센서에 대한 상세 설명 제공
- SHAP waterfall chart 자동 생성 및 S3 업로드
- Bedrock Claude로 자연어 요약 생성

## 🚀 Lambda T3 배포 (RAG)

### 1. Bedrock Knowledge Base 생성

```bash
# Knowledge Base 생성 (콘솔에서 진행)
# 1. Bedrock 콘솔 접속
# 2. Knowledge Bases 메뉴
# 3. Create knowledge base
# 4. S3 데이터 소스: s3://diecasting-knowledge/documents/
# 5. Embedding 모델: Titan Embeddings G1
# 6. Vector DB: OpenSearch Serverless (자동 생성)
```

### 2. Lambda 함수 생성

```bash
# ZIP 생성
zip lambda-t3.zip lambda_t3_rag.py

# Lambda 함수 생성
aws lambda create-function \
  --function-name diecasting-rag-t3 \
  --runtime python3.11 \
  --role arn:aws:iam::ACCOUNT_ID:role/lambda-execution-role \
  --handler lambda_t3_rag.lambda_handler \
  --zip-file fileb://lambda-t3.zip \
  --timeout 30 \
  --memory-size 512 \
  --environment Variables="{BUCKET_NAME=diecasting-knowledge,KNOWLEDGE_BASE_ID=YOUR_KB_ID}" \
  --region us-east-1
```

### 3. Bedrock 권한 추가

```json
{
  "Effect": "Allow",
  "Action": [
    "bedrock:InvokeModel",
    "bedrock:Retrieve"
  ],
  "Resource": [
    "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-haiku-20240307-v1:0",
    "arn:aws:bedrock:us-east-1:ACCOUNT_ID:knowledge-base/YOUR_KB_ID"
  ]
}
```

## 🧪 테스트

### Lambda T1 테스트

```bash
aws lambda invoke \
  --function-name diecasting-predict-t1 \
  --payload file://test_payload.json \
  response.json

cat response.json
```

test_payload.json:
```json
{
  "body": {
    "features": {
      "Process_Temperature": 650.0,
      "Process_Pressure": 120.0,
      ...
    }
  }
}
```

### Lambda T2 테스트

```bash
aws lambda invoke \
  --function-name diecasting-importance-t2 \
  --payload '{"body":{"top_n":10,"use_bedrock":true}}' \
  response.json
```

### Lambda T3 테스트

```bash
aws lambda invoke \
  --function-name diecasting-rag-t3 \
  --payload '{"body":{"query":"불량의 주요 원인은?"}}' \
  response.json
```

## 📊 모니터링

### CloudWatch Logs

```bash
# Lambda T1 로그
aws logs tail /aws/lambda/diecasting-predict-t1 --follow

# Lambda T2 로그
aws logs tail /aws/lambda/diecasting-importance-t2 --follow

# Lambda T3 로그
aws logs tail /aws/lambda/diecasting-rag-t3 --follow
```

### CloudWatch Metrics

- Invocations
- Duration
- Errors
- Throttles
- ConcurrentExecutions

### X-Ray Tracing

Lambda 함수에 X-Ray 활성화:

```bash
aws lambda update-function-configuration \
  --function-name diecasting-predict-t1 \
  --tracing-config Mode=Active
```

## 💰 비용 최적화

### 1. Lambda 설정
- **메모리**: 필요한 최소 메모리 사용
  - T1: 1024 MB (모델 로딩)
  - T2: 512 MB
  - T3: 512 MB
- **타임아웃**: 30초 (충분한 시간)
- **Provisioned Concurrency**: 프로덕션 환경에서만 사용

### 2. S3 비용
- **Intelligent-Tiering**: 자주 사용하지 않는 파일
- **Lifecycle Policy**: 오래된 로그 삭제

### 3. Bedrock 비용
- **모델 선택**: Claude 3 Haiku (가장 저렴)
- **토큰 최적화**: 프롬프트 길이 최소화

## 🔒 보안

### 1. IAM 최소 권한 원칙
- 각 Lambda에 필요한 권한만 부여
- S3 버킷별 세분화된 권한

### 2. VPC 설정 (선택)
- 민감한 데이터 처리 시 VPC 내 배포
- NAT Gateway 또는 VPC Endpoint 사용

### 3. 환경 변수 암호화
- Secrets Manager 사용
- KMS 키로 암호화

## 📝 업데이트

### Lambda 코드 업데이트

```bash
# 코드 수정 후 ZIP 재생성
zip lambda-t1.zip lambda_t1_predict.py autoencoder_model.py

# 업데이트
aws lambda update-function-code \
  --function-name diecasting-predict-t1 \
  --zip-file fileb://lambda-t1.zip
```

### 모델 업데이트

```bash
# 새 모델 S3 업로드
aws s3 cp new_model.pth s3://diecasting-models/models/autoencoder_latent12.pth

# Lambda 재시작 (Cold start로 새 모델 로드)
aws lambda update-function-configuration \
  --function-name diecasting-predict-t1 \
  --environment Variables="{BUCKET_NAME=diecasting-models,MODEL_VERSION=v2}"
```

## 🆘 트러블슈팅

### 1. Lambda 타임아웃
- 메모리 증가
- 타임아웃 시간 증가
- 모델 로딩 최적화

### 2. Cold Start 지연
- Provisioned Concurrency 사용
- Lambda Layer 최적화
- 모델 크기 감소

### 3. S3 접근 오류
- IAM 권한 확인
- 버킷 정책 확인
- 리전 일치 확인

## 📞 문의

- 기술 지원: tech-support@company.com
- AWS 관련: aws-admin@company.com

---

**작성일**: 2026-01-19  
**버전**: 1.0.0
