# PoC 배포 가이드

## 📦 배포 파일 구조

```
poc-deployment/
├── lambda/
│   ├── t1_predict/
│   │   ├── lambda_function.py          # Lambda T1 코드
│   │   ├── requirements.txt
│   │   ├── Dockerfile
│   │   └── models/
│   │       ├── autoencoder_latent12.pth
│   │       ├── gradient_boosting_model.pkl
│   │       └── scaler.pkl
│   │
│   ├── t2_importance/
│   │   ├── lambda_function.py          # Lambda T2 코드
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   └── t3_rag/
│       ├── lambda_function.py          # Lambda T3 코드 (별도 구현 필요)
│       ├── requirements.txt
│       └── Dockerfile
│
├── streamlit/
│   ├── app.py                          # Streamlit UI
│   ├── requirements.txt
│   └── Dockerfile
│
└── terraform/
    ├── main.tf
    ├── alb.tf
    ├── ecs.tf
    ├── lambda.tf
    ├── api_gateway.tf
    └── s3.tf
```

---

## 🐳 Dockerfile 예시

### Lambda T1 (Predict) Dockerfile

```dockerfile
FROM public.ecr.aws/lambda/python:3.11

# 모델 파일 복사
COPY models/ /opt/ml/models/

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Lambda 함수 복사
COPY lambda_function.py ${LAMBDA_TASK_ROOT}

CMD ["lambda_function.lambda_handler"]
```

### Lambda T1 requirements.txt

```
torch==2.1.0 --index-url https://download.pytorch.org/whl/cpu
scikit-learn==1.3.2
numpy==1.24.3
pandas==2.1.3
```

### Lambda T2 (Importance) Dockerfile

```dockerfile
FROM public.ecr.aws/lambda/python:3.11

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Lambda 함수 복사
COPY lambda_function.py ${LAMBDA_TASK_ROOT}

CMD ["lambda_function.lambda_handler"]
```

### Lambda T2 requirements.txt

```
scikit-learn==1.3.2
shap==0.43.0
matplotlib==3.8.2
numpy==1.24.3
boto3==1.34.0
```

### Streamlit Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 복사
COPY app.py .

# Streamlit 포트
EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# 실행
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### Streamlit requirements.txt

```
streamlit==1.29.0
requests==2.31.0
pandas==2.1.3
plotly==5.18.0
```

---

## 🚀 배포 단계

### Step 1: 모델 파일 준비

```bash
# whiteboarding 디렉토리에서 실행
cd whiteboarding

# 모델 파일 복사
mkdir -p poc-deployment/lambda/t1_predict/models
cp autoencoder_latent12.pth poc-deployment/lambda/t1_predict/models/
cp gradient_boosting_model.pkl poc-deployment/lambda/t1_predict/models/  # 생성 필요
cp scaler.pkl poc-deployment/lambda/t1_predict/models/  # 생성 필요
```

### Step 2: Docker 이미지 빌드 및 푸시

```bash
# ECR 로그인
aws ecr get-login-password --region ap-northeast-2 | \
  docker login --username AWS --password-stdin <account-id>.dkr.ecr.ap-northeast-2.amazonaws.com

# Lambda T1 이미지 빌드
cd poc-deployment/lambda/t1_predict
docker build -t diecasting-predict:latest .
docker tag diecasting-predict:latest <account-id>.dkr.ecr.ap-northeast-2.amazonaws.com/diecasting-predict:latest
docker push <account-id>.dkr.ecr.ap-northeast-2.amazonaws.com/diecasting-predict:latest

# Lambda T2 이미지 빌드
cd ../t2_importance
docker build -t diecasting-importance:latest .
docker tag diecasting-importance:latest <account-id>.dkr.ecr.ap-northeast-2.amazonaws.com/diecasting-importance:latest
docker push <account-id>.dkr.ecr.ap-northeast-2.amazonaws.com/diecasting-importance:latest

# Streamlit 이미지 빌드
cd ../../streamlit
docker build -t diecasting-ui:latest .
docker tag diecasting-ui:latest <account-id>.dkr.ecr.ap-northeast-2.amazonaws.com/diecasting-ui:latest
docker push <account-id>.dkr.ecr.ap-northeast-2.amazonaws.com/diecasting-ui:latest
```

### Step 3: Terraform으로 인프라 배포

```bash
cd ../terraform

# 초기화
terraform init

# 계획 확인
terraform plan

# 배포
terraform apply
```

### Step 4: API Gateway URL 업데이트

```bash
# Terraform output에서 API Gateway URL 확인
terraform output api_gateway_url

# Streamlit app.py의 API_BASE_URL 업데이트
# 예: https://abc123.execute-api.ap-northeast-2.amazonaws.com/prod
```

### Step 5: 테스트

```bash
# Lambda T1 테스트
curl -X POST https://your-api-gateway-url/prod/predict \
  -H "Content-Type: application/json" \
  -d @test_payload.json

# Streamlit UI 접속
# https://your-alb-url.ap-northeast-2.elb.amazonaws.com
```

---

## 📝 Terraform 예시 (main.tf)

```hcl
terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  backend "s3" {
    bucket = "diecasting-terraform-state"
    key    = "poc/terraform.tfstate"
    region = "ap-northeast-2"
  }
}

provider "aws" {
  region = "ap-northeast-2"
  
  default_tags {
    tags = {
      Project     = "DiecastingQuality"
      Environment = "PoC"
      ManagedBy   = "Terraform"
    }
  }
}

# Variables
variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs"
  type        = list(string)
}

variable "public_subnet_ids" {
  description = "Public subnet IDs"
  type        = list(string)
}

variable "allowed_cidr_blocks" {
  description = "Allowed CIDR blocks for ALB"
  type        = list(string)
  default     = ["10.0.0.0/8"]  # 사내 IP 대역
}

# S3 Bucket for Importance Visualizations
resource "aws_s3_bucket" "importance" {
  bucket = "diecasting-quality-poc"
}

resource "aws_s3_bucket_versioning" "importance" {
  bucket = aws_s3_bucket.importance.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "importance" {
  bucket = aws_s3_bucket.importance.id
  
  rule {
    id     = "delete-old-files"
    status = "Enabled"
    
    expiration {
      days = 30
    }
  }
}

# ECR Repositories
resource "aws_ecr_repository" "predict" {
  name                 = "diecasting-predict"
  image_tag_mutability = "MUTABLE"
  
  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_repository" "importance" {
  name                 = "diecasting-importance"
  image_tag_mutability = "MUTABLE"
  
  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_repository" "ui" {
  name                 = "diecasting-ui"
  image_tag_mutability = "MUTABLE"
  
  image_scanning_configuration {
    scan_on_push = true
  }
}

# Outputs
output "api_gateway_url" {
  value = aws_api_gateway_stage.prod.invoke_url
}

output "alb_dns_name" {
  value = aws_lb.main.dns_name
}

output "s3_bucket_name" {
  value = aws_s3_bucket.importance.id
}
```

---

## 🔐 보안 체크리스트

### Lambda 함수
- [x] VPC 내 Private subnet 배치
- [x] IAM Role 최소 권한 원칙
- [x] 환경 변수 암호화 (KMS)
- [x] CloudWatch Logs 암호화

### API Gateway
- [x] IAM 인증 활성화
- [x] Throttling 설정 (1000 req/sec)
- [x] CloudWatch Logs 활성화
- [x] X-Ray Tracing 활성화

### ALB
- [x] HTTPS 리스너 (ACM 인증서)
- [x] Security Group: 사내 IP allowlist
- [x] Access Logs → S3
- [x] WAF 연동 (선택)

### ECS Fargate
- [x] Task Role 최소 권한
- [x] Secrets Manager로 API 키 관리
- [x] CloudWatch Container Insights
- [x] 자동 스케일링 설정

### S3
- [x] 버킷 암호화 (SSE-S3)
- [x] 버전 관리 활성화
- [x] Lifecycle 정책 (30일 후 삭제)
- [x] Public Access Block

---

## 📊 모니터링 설정

### CloudWatch Alarms

```hcl
# Lambda T1 에러율 알람
resource "aws_cloudwatch_metric_alarm" "lambda_t1_errors" {
  alarm_name          = "diecasting-predict-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "60"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "Lambda T1 error rate too high"
  
  dimensions = {
    FunctionName = aws_lambda_function.predict.function_name
  }
}

# Lambda T1 실행 시간 알람
resource "aws_cloudwatch_metric_alarm" "lambda_t1_duration" {
  alarm_name          = "diecasting-predict-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = "60"
  statistic           = "Average"
  threshold           = "1000"  # 1초
  alarm_description   = "Lambda T1 execution time too high"
  
  dimensions = {
    FunctionName = aws_lambda_function.predict.function_name
  }
}

# ECS CPU 사용률 알람
resource "aws_cloudwatch_metric_alarm" "ecs_cpu" {
  alarm_name          = "diecasting-ui-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "ECS CPU utilization too high"
  
  dimensions = {
    ServiceName = aws_ecs_service.ui.name
    ClusterName = aws_ecs_cluster.main.name
  }
}
```

### CloudWatch Dashboard

```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/Lambda", "Invocations", {"stat": "Sum", "label": "T1 Invocations"}],
          [".", "Errors", {"stat": "Sum", "label": "T1 Errors"}],
          [".", "Duration", {"stat": "Average", "label": "T1 Duration"}]
        ],
        "period": 300,
        "stat": "Average",
        "region": "ap-northeast-2",
        "title": "Lambda T1 Metrics"
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/ECS", "CPUUtilization", {"stat": "Average"}],
          [".", "MemoryUtilization", {"stat": "Average"}]
        ],
        "period": 300,
        "stat": "Average",
        "region": "ap-northeast-2",
        "title": "ECS Metrics"
      }
    }
  ]
}
```

---

## 🧪 테스트 시나리오

### 1. 단위 테스트

```bash
# Lambda T1 로컬 테스트
python lambda_t1_predict.py

# Lambda T2 로컬 테스트
python lambda_t2_importance.py
```

### 2. 통합 테스트

```bash
# API Gateway 테스트
./test_api_gateway.sh

# Streamlit UI 테스트
streamlit run streamlit_app.py
```

### 3. 부하 테스트

```bash
# Apache Bench
ab -n 1000 -c 10 -p test_payload.json -T application/json \
  https://your-api-gateway-url/prod/predict

# 또는 Locust
locust -f load_test.py --host=https://your-api-gateway-url
```

---

## 💰 비용 최적화

### Lambda 최적화
- Memory 크기 최적화 (2048MB → 1536MB 테스트)
- Provisioned Concurrency 사용 (Cold Start 제거)
- Reserved Concurrency 설정 (비용 예측 가능)

### ECS 최적화
- Fargate Spot 사용 (최대 70% 절감)
- Auto Scaling 정책 최적화
- 사용량 낮은 시간대 Task 수 감소

### S3 최적화
- Intelligent-Tiering 사용
- Lifecycle 정책으로 오래된 파일 삭제
- CloudFront CDN 사용 (이미지 전송)

---

## 📞 문제 해결

### Lambda Cold Start 느림
- Provisioned Concurrency 활성화
- 모델 파일 크기 최적화 (quantization)
- /tmp 디렉토리 활용

### API Gateway Timeout
- Lambda timeout 증가 (30s → 60s)
- 비동기 처리 고려
- Step Functions 사용

### ECS Task 재시작 반복
- Health check 설정 확인
- 메모리 부족 확인
- 로그 확인 (CloudWatch Logs)

---

**작성일**: 2026-01-15  
**버전**: 1.0  
**담당자**: DevOps Team
