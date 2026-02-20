# AWS 인프라 배포 가이드

## 아키텍처

```
[사용자]
   ↓ HTTPS
[CloudFront]
   ├─ /* → [S3: index.html, chat.html]
   └─ /api/* → [ALB]
                 ↓
              [ECS Fargate: Backend Agent]
                 ↓ 내부 호출
              [Lambda T1/T2/T3]
```

## 배포 순서

### 1. 백엔드 에이전트 배포 (ECS Fargate)

```bash
# 실행 권한 부여
chmod +x deploy_backend_agent.sh

# 배포
./deploy_backend_agent.sh
```

**생성되는 리소스**:
- ECR 리포지토리: `diecasting-backend-agent`
- ECS Task Definition: `diecasting-backend-agent`
- CloudWatch Logs: `/ecs/diecasting-backend-agent`

**환경변수**:
- `USE_MOCK=false` (프로덕션)
- `LAMBDA_T1_URL`: Lambda T1 Function URL
- `LAMBDA_T2_URL`: Lambda T2 Function URL
- `LAMBDA_T3_URL`: Lambda T3 Function URL

### 2. ALB 설정

#### 2.1 타겟 그룹 생성
```bash
aws elbv2 create-target-group \
  --name diecasting-backend-tg \
  --protocol HTTP \
  --port 8000 \
  --vpc-id <VPC_ID> \
  --target-type ip \
  --health-check-path /health \
  --health-check-interval-seconds 30
```

#### 2.2 ECS 서비스 생성 (ALB 연결)
```bash
aws ecs create-service \
  --cluster diecasting-cluster \
  --service-name backend-agent-service \
  --task-definition diecasting-backend-agent \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[<SUBNET_IDS>],securityGroups=[<SG_ID>],assignPublicIp=ENABLED}" \
  --load-balancers "targetGroupArn=<TARGET_GROUP_ARN>,containerName=backend-agent,containerPort=8000"
```

#### 2.3 ALB 리스너 규칙 추가
```bash
aws elbv2 create-rule \
  --listener-arn <LISTENER_ARN> \
  --priority 10 \
  --conditions Field=path-pattern,Values='/api/*' \
  --actions Type=forward,TargetGroupArn=<TARGET_GROUP_ARN>
```

### 3. 프론트엔드 배포 (S3)

```bash
# 실행 권한 부여
chmod +x deploy_frontend.sh

# 배포
./deploy_frontend.sh
```

**생성되는 리소스**:
- S3 버킷: `diecasting-frontend`
- 업로드 파일: `index.html`, `chat.html`

### 4. CloudFront 설정

#### 4.1 Distribution 생성
```bash
aws cloudfront create-distribution \
  --origin-domain-name <ALB_DNS_NAME> \
  --default-root-object index.html
```

#### 4.2 Origins 설정
- **Origin 1 (S3)**: `diecasting-frontend.s3.amazonaws.com`
  - Path pattern: `/*` (기본)
  - Viewer protocol: Redirect HTTP to HTTPS
  
- **Origin 2 (ALB)**: `<ALB_DNS_NAME>`
  - Path pattern: `/api/*`
  - Viewer protocol: HTTPS only
  - Origin protocol: HTTP only

#### 4.3 Behaviors 설정
```json
{
  "PathPattern": "/api/*",
  "TargetOriginId": "ALB",
  "ViewerProtocolPolicy": "https-only",
  "AllowedMethods": ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"],
  "CachedMethods": ["GET", "HEAD"],
  "ForwardedValues": {
    "QueryString": true,
    "Headers": ["*"]
  }
}
```

### 5. 배포 확인

```bash
# 백엔드 헬스체크
curl https://<CLOUDFRONT_DOMAIN>/api/health

# 프론트엔드 접속
open https://<CLOUDFRONT_DOMAIN>
```

## 비용 예상

| 리소스 | 사양 | 월 비용 |
|--------|------|---------|
| ECS Fargate | 0.25 vCPU, 0.5GB | $15 |
| ALB | 1개 | $16 |
| Lambda T1/T2/T3 | 1,000 req/월 | $5 |
| S3 + CloudFront | 10GB 전송 | $2 |
| **총 비용** | | **$38/월** |

## 보안 설정

### 1. Security Group (ECS)
```bash
# 인바운드: ALB에서만 허용
aws ec2 authorize-security-group-ingress \
  --group-id <SG_ID> \
  --protocol tcp \
  --port 8000 \
  --source-group <ALB_SG_ID>
```

### 2. IAM Role (ECS Task Execution)
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
```

### 3. Lambda Function URL (내부 전용)
- Auth Type: `AWS_IAM` (ECS Task Role에서만 호출 가능)

## 모니터링

### CloudWatch Alarms
```bash
# ECS CPU 사용률
aws cloudwatch put-metric-alarm \
  --alarm-name backend-agent-cpu-high \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold

# ALB 5xx 에러
aws cloudwatch put-metric-alarm \
  --alarm-name alb-5xx-errors \
  --metric-name HTTPCode_Target_5XX_Count \
  --namespace AWS/ApplicationELB \
  --statistic Sum \
  --period 60 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold
```

## 롤백

```bash
# 이전 Task Definition으로 롤백
aws ecs update-service \
  --cluster diecasting-cluster \
  --service backend-agent-service \
  --task-definition diecasting-backend-agent:<REVISION>

# 프론트엔드 롤백
aws s3 sync s3://diecasting-frontend-backup/ s3://diecasting-frontend/
aws cloudfront create-invalidation --distribution-id <DIST_ID> --paths "/*"
```

## 트러블슈팅

### 1. ECS 태스크가 시작되지 않음
```bash
# 로그 확인
aws logs tail /ecs/diecasting-backend-agent --follow

# Task 상태 확인
aws ecs describe-tasks --cluster diecasting-cluster --tasks <TASK_ARN>
```

### 2. ALB 헬스체크 실패
```bash
# 타겟 상태 확인
aws elbv2 describe-target-health --target-group-arn <TG_ARN>

# Security Group 확인
aws ec2 describe-security-groups --group-ids <SG_ID>
```

### 3. CORS 에러
- ALB에서 CORS 헤더 추가 필요
- 또는 Backend Agent에서 CORS 미들웨어 설정 확인
