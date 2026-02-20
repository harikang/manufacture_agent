# 개선된 아키텍처 구성

## 구조 변경 요약

### Before (기존)
```
[Frontend: chat.html]
  ↓ 직접 호출
[Lambda T1/T2/T3]  ❌ Lambda URL이 프론트에 노출
```

### After (개선)
```
[Frontend: S3+CloudFront]
  ↓ POST /api/chat, /t0, /t1, /t2, /t3
[API Gateway]
  ├─ /t0 → Lambda T0 (KB Ingest)
  ├─ /t1 → Lambda T1 (Prediction)
  ├─ /t2 → Lambda T2 (XAI)
  ├─ /t3 → Lambda T3 (RAG)
  └─ /api/* → ALB → ECS Fargate (Backend Agent)
[Backend Agent: FastAPI on ECS Fargate]
  ├─ 의도 분류 (prediction/xai/knowledge)
  ├─ Lambda T1 호출 (내부 URL)
  ├─ Lambda T2 호출 (내부 URL)
  └─ Lambda T3 호출 (내부 URL)
  ↓ SSE 스트리밍
[Frontend: 렌더링만]
```

## Lambda 함수 구성

| Lambda | 역할 | 트리거 |
|--------|------|--------|
| T0 | KB 인제스트 (문서 청킹/임베딩) | API Gateway /t0 |
| T1 | 품질 예측 (Autoencoder + GB) | API Gateway /t1 또는 Backend Agent |
| T2 | Feature Importance (XAI) | API Gateway /t2 또는 Backend Agent |
| T3 | Knowledge Base RAG | API Gateway /t3 또는 Backend Agent |

## 핵심 변경사항

### 1. 백엔드 에이전트 (backend_agent.py)
- **역할**: 의도 분류 + Lambda 오케스트레이션
- **기술**: FastAPI + SSE 스트리밍
- **엔드포인트**:
  - `POST /api/sessions`: 세션 생성
  - `POST /api/chat`: 메인 채팅 (SSE)
  - `POST /api/kb-ingest`: KB 인제스트 (T0 프록시)
  - `GET /health`: 헬스체크

### 1-1. Lambda T0 (KB Ingest)
- **역할**: Bedrock Knowledge Base 인제스트 워크플로우
- **파일**: `appservice/lambda_t0_ingest.py`
- **기능**:
  - `start_ingestion`: Data Source 동기화 시작
  - `check_status`: Job 상태 확인
  - `list_jobs`: 최근 Job 목록 조회
- **환경변수**:
  - `KNOWLEDGE_BASE_ID`: 4GOU8MFELR
  - `DATA_SOURCE_ID`: 85CWXCHZLJ

### 2. 프론트엔드 (chat_v2.html)
- **변경**: Lambda URL 완전 제거
- **호출**: 백엔드 API만 사용 (`http://localhost:8000/api`)
- **렌더링**: SSE 이벤트 수신 후 UI 업데이트만

### 3. 보안 강화
- ✅ Lambda URL 은닉 (백엔드만 알고 있음)
- ✅ API Gateway에서 인증 중앙화
- ✅ ALB에서 IP allowlist 적용
- ✅ VPC 내부 통신

## 배포 방법

### 1. 로컬 테스트
```bash
# 백엔드 실행
cd /Users/kang/whiteboarding
python backend_agent.py

# 프론트엔드 (별도 터미널)
python -m http.server 8080
# 브라우저: http://localhost:8080/withoutstreamlit/chat_v2.html
```

### 2. Docker 빌드
```bash
# 백엔드 이미지
docker build -f Dockerfile.backend -t diecasting-backend:latest .

# 실행
docker run -p 8000:8000 \
  -e LAMBDA_T1_URL=https://lambda-t1.execute-api.ap-northeast-2.amazonaws.com/prod \
  -e LAMBDA_T2_URL=https://lambda-t2.execute-api.ap-northeast-2.amazonaws.com/prod \
  -e LAMBDA_T3_URL=https://lambda-t3.execute-api.ap-northeast-2.amazonaws.com/prod \
  diecasting-backend:latest
```

### 3. ECS Fargate 배포
```bash
# ECR 푸시
aws ecr get-login-password --region ap-northeast-2 | docker login --username AWS --password-stdin <account>.dkr.ecr.ap-northeast-2.amazonaws.com
docker tag diecasting-backend:latest <account>.dkr.ecr.ap-northeast-2.amazonaws.com/diecasting-backend:latest
docker push <account>.dkr.ecr.ap-northeast-2.amazonaws.com/diecasting-backend:latest

# ECS 태스크 정의 업데이트
aws ecs update-service --cluster diecasting-cluster --service backend-agent --force-new-deployment
```

### 4. 프론트엔드 배포 (S3+CloudFront)
```bash
# S3 업로드
aws s3 sync withoutstreamlit/ s3://diecasting-frontend/ --exclude "*.py"

# CloudFront 무효화
aws cloudfront create-invalidation --distribution-id E1234567890ABC --paths "/*"
```

## 비용 영향

| 항목 | 기존 | 개선 | 변화 |
|------|------|------|------|
| Lambda | $20/월 | $20/월 | - |
| ECS Fargate | - | $15/월 | +$15 |
| API Gateway | - | $3/월 | +$3 |
| **총 비용** | **$20/월** | **$38/월** | **+90%** |
| **ROI** | 722% | 650% | -10% |

**결론**: 보안 강화 대비 비용 증가는 합리적 (월 $18 추가)

## 장점

1. **보안**: Lambda URL 완전 은닉
2. **유지보수**: 백엔드에서 로직 중앙 관리
3. **확장성**: 백엔드에서 캐싱/로깅/모니터링 추가 용이
4. **사용자 경험**: SSE 스트리밍으로 실시간 피드백

## 다음 단계

1. ✅ 로컬 테스트 완료
2. ⏳ Docker 이미지 빌드 및 테스트
3. ⏳ ECS Fargate 배포
4. ⏳ API Gateway + ALB 연동
5. ⏳ CloudFront + S3 프론트엔드 배포
6. ⏳ 통합 테스트 및 성능 검증

## Lambda T0 배포 가이드

### 1. Lambda 함수 배포
```bash
./scripts/deploy/deploy_lambda_t0.sh
```

### 2. API Gateway에 /t0 경로 추가
```bash
# API Gateway ID 확인
API_ID="your-api-gateway"
REGION="us-east-1"

# /t0 리소스 생성
PARENT_ID=$(aws apigateway get-resources --rest-api-id $API_ID --region $REGION \
  --query "items[?path=='/'].id" --output text)

RESOURCE_ID=$(aws apigateway create-resource \
  --rest-api-id $API_ID \
  --parent-id $PARENT_ID \
  --path-part "t0" \
  --region $REGION \
  --query 'id' --output text)

# POST 메서드 생성
aws apigateway put-method \
  --rest-api-id $API_ID \
  --resource-id $RESOURCE_ID \
  --http-method POST \
  --authorization-type NONE \
  --region $REGION

# Lambda 통합 설정
LAMBDA_ARN="arn:aws:lambda:${REGION}:$(aws sts get-caller-identity --query Account --output text):function:diecasting-lambda-t0-ingest"

aws apigateway put-integration \
  --rest-api-id $API_ID \
  --resource-id $RESOURCE_ID \
  --http-method POST \
  --type AWS_PROXY \
  --integration-http-method POST \
  --uri "arn:aws:apigateway:${REGION}:lambda:path/2015-03-31/functions/${LAMBDA_ARN}/invocations" \
  --region $REGION

# Lambda 권한 추가
aws lambda add-permission \
  --function-name diecasting-lambda-t0-ingest \
  --statement-id apigateway-t0 \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:${REGION}:*:${API_ID}/*/POST/t0" \
  --region $REGION

# API 배포
aws apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name prod \
  --region $REGION
```

### 3. 테스트
```bash
# 최근 Job 목록 조회
curl -X POST https://your-api-gateway.execute-api.us-east-1.amazonaws.com/prod/t0 \
  -H 'Content-Type: application/json' \
  -d '{"action": "list_jobs"}'

# 인제스트 시작
curl -X POST https://your-api-gateway.execute-api.us-east-1.amazonaws.com/prod/t0 \
  -H 'Content-Type: application/json' \
  -d '{"action": "start_ingestion"}'
```
