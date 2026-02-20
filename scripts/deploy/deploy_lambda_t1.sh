#!/bin/bash
# Lambda T1 (품질 예측) 배포 스크립트

set -e

# 환경 변수 로드
source config/config.env 2>/dev/null || echo "config.env not found, using environment variables"

AWS_REGION=${AWS_REGION:-us-east-1}
AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}
ECR_REPO="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/diecasting-lambda-t1"
LAMBDA_FUNCTION_NAME="diecasting-predict-quality"

echo "=== Lambda T1 배포 시작 ==="

# ECR 로그인
echo "1. ECR 로그인..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# Docker 이미지 빌드
echo "2. Docker 이미지 빌드..."
docker build -f docker/Dockerfile.lambda -t ${ECR_REPO}:latest .

# ECR 푸시
echo "3. ECR 푸시..."
docker push ${ECR_REPO}:latest

# Lambda 함수 업데이트
echo "4. Lambda 함수 업데이트..."
aws lambda update-function-code \
    --function-name ${LAMBDA_FUNCTION_NAME} \
    --image-uri ${ECR_REPO}:latest \
    --region ${AWS_REGION}

echo "=== Lambda T1 배포 완료 ==="
