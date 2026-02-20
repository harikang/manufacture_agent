#!/bin/bash
# Backend Agent (ECS) 배포 스크립트

set -e

# 환경 변수 로드
source config/config.env 2>/dev/null || echo "config.env not found, using environment variables"

AWS_REGION=${AWS_REGION:-us-east-1}
AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}
ECR_REPO="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/diecasting-backend-agent"
ECS_CLUSTER=${ECS_CLUSTER:-diecasting-cluster}
ECS_SERVICE=${ECS_SERVICE:-backend-agent-service}

echo "=== Backend Agent 배포 시작 ==="

# ECR 로그인
echo "1. ECR 로그인..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# Docker 이미지 빌드
echo "2. Docker 이미지 빌드..."
docker build -f docker/Dockerfile.backend_agent -t ${ECR_REPO}:latest .

# ECR 푸시
echo "3. ECR 푸시..."
docker push ${ECR_REPO}:latest

# ECS 서비스 업데이트
echo "4. ECS 서비스 업데이트..."
aws ecs update-service \
    --cluster ${ECS_CLUSTER} \
    --service ${ECS_SERVICE} \
    --force-new-deployment \
    --region ${AWS_REGION}

echo "=== Backend Agent 배포 완료 ==="
echo "ECS 서비스가 새 이미지로 롤링 업데이트됩니다."
