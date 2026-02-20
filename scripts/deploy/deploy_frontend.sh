#!/bin/bash
# Frontend (S3 + CloudFront) 배포 스크립트

set -e

# 환경 변수 로드
source config/config.env 2>/dev/null || echo "config.env not found, using environment variables"

FRONTEND_BUCKET=${FRONTEND_BUCKET:-your-frontend-bucket}
CLOUDFRONT_DISTRIBUTION_ID=${CLOUDFRONT_DISTRIBUTION_ID:-}

echo "=== Frontend 배포 시작 ==="

# S3에 파일 업로드
echo "1. S3에 파일 업로드..."
aws s3 sync frontend/ s3://${FRONTEND_BUCKET}/ \
    --delete \
    --cache-control "max-age=31536000" \
    --exclude "*.html" \
    --exclude "*.js"

# HTML, JS 파일은 캐시 시간 짧게
aws s3 sync frontend/ s3://${FRONTEND_BUCKET}/ \
    --cache-control "max-age=300" \
    --include "*.html" \
    --include "*.js"

# CloudFront 캐시 무효화
if [ -n "${CLOUDFRONT_DISTRIBUTION_ID}" ]; then
    echo "2. CloudFront 캐시 무효화..."
    aws cloudfront create-invalidation \
        --distribution-id ${CLOUDFRONT_DISTRIBUTION_ID} \
        --paths "/*"
fi

echo "=== Frontend 배포 완료 ==="
