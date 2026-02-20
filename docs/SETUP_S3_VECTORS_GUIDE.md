# S3 Vectors + Bedrock Knowledge Base 설정 가이드

## 현재 상태
✅ S3 Vector 버킷 생성 완료

## 다음 단계

---

## Step 1: S3 Vector Index 생성

S3 Vector 버킷에 Vector Index를 생성해야 합니다.

### 1.1 S3 Console에서 Vector Index 생성

1. **AWS Console > S3** 이동
2. 버킷 목록에서 생성한 S3 Vector 버킷 선택
3. **Properties** 탭 클릭
4. 아래로 스크롤하여 **Vector configuration** 섹션 찾기
5. **Create vector index** 버튼 클릭

### 1.2 Vector Index 설정

다음 정보 입력:

```
Vector index name: diecasting-vector-index
Dimensions: 1024
Distance metric: Cosine
```

**설명:**
- **Vector index name**: Knowledge Base에서 참조할 인덱스 이름
- **Dimensions**: `1024` (Titan Embeddings v2 모델의 벡터 차원)
- **Distance metric**: `Cosine` (코사인 유사도 - 가장 일반적)

6. **Create vector index** 버튼 클릭

⏳ Vector Index 생성 중... (약 30초 소요)

✅ Status가 **Active**로 변경되면 완료!

---

## Step 2: 문서 업로드

이미 로컬에 샘플 문서가 준비되어 있습니다. S3에 업로드하겠습니다.

### 2.1 터미널에서 문서 업로드

```bash
# 트러블슈팅 문서
aws s3 cp knowledge_base_docs/troubleshooting/porosity_troubleshooting_guide.md \
  s3://YOUR_VECTOR_BUCKET_NAME/documents/troubleshooting/

# 공정 매뉴얼
aws s3 cp knowledge_base_docs/process_manual/injection_process_sop.md \
  s3://YOUR_VECTOR_BUCKET_NAME/documents/process_manual/

# 안전 규정
aws s3 cp knowledge_base_docs/regulations/safety_regulations.md \
  s3://YOUR_VECTOR_BUCKET_NAME/documents/regulations/

# SOP 문서
aws s3 cp knowledge_base_docs/sop/diecasting_process_sop.md \
  s3://YOUR_VECTOR_BUCKET_NAME/documents/process_manual/

# 센서 사양서
aws s3 cp knowledge_base_docs/sensors/sensor_specifications.md \
  s3://YOUR_VECTOR_BUCKET_NAME/documents/sensor_manual/

# 불량 분석
aws s3 cp knowledge_base_docs/troubleshooting/defect_analysis.md \
  s3://YOUR_VECTOR_BUCKET_NAME/documents/troubleshooting/
```

**YOUR_VECTOR_BUCKET_NAME**을 실제 버킷 이름으로 교체하세요!

### 2.2 업로드 확인

```bash
aws s3 ls s3://YOUR_VECTOR_BUCKET_NAME/documents/ --recursive
```

6개 파일이 표시되어야 합니다.

---

## Step 3: IAM 역할 생성 (Bedrock용)

Bedrock Knowledge Base가 S3 Vector 버킷에 접근할 수 있도록 IAM 역할을 생성합니다.

### 3.1 Trust Policy 생성

```bash
cat > /tmp/kb-trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "bedrock.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
```

### 3.2 IAM 역할 생성

```bash
aws iam create-role \
  --role-name BedrockKnowledgeBaseRole-S3Vectors \
  --assume-role-policy-document file:///tmp/kb-trust-policy.json \
  --description "Bedrock Knowledge Base role for S3 Vectors"
```

### 3.3 S3 접근 정책 생성

```bash
cat > /tmp/kb-s3-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket",
        "s3:PutObject",
        "s3:GetBucketVectorConfiguration",
        "s3:ListBucketVectorIndexes",
        "s3:GetVectorIndex",
        "s3:PutVectorIndex",
        "s3:QueryVectorIndex"
      ],
      "Resource": [
        "arn:aws:s3:::YOUR_VECTOR_BUCKET_NAME",
        "arn:aws:s3:::YOUR_VECTOR_BUCKET_NAME/*"
      ]
    }
  ]
}
EOF
```

**YOUR_VECTOR_BUCKET_NAME**을 실제 버킷 이름으로 교체하세요!

### 3.4 정책 연결

```bash
aws iam put-role-policy \
  --role-name BedrockKnowledgeBaseRole-S3Vectors \
  --policy-name S3VectorAccessPolicy \
  --policy-document file:///tmp/kb-s3-policy.json
```

### 3.5 Bedrock 모델 접근 정책 추가

```bash
cat > /tmp/kb-bedrock-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/amazon.titan-embed-text-v2:0"
      ]
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name BedrockKnowledgeBaseRole-S3Vectors \
  --policy-name BedrockModelAccessPolicy \
  --policy-document file:///tmp/kb-bedrock-policy.json
```

✅ IAM 역할 생성 완료!

---

## Step 4: Bedrock Knowledge Base 생성

이제 AWS Console에서 Knowledge Base를 생성합니다.

### 4.1 Bedrock Console 접속

1. **AWS Console > Amazon Bedrock** 이동
2. 왼쪽 메뉴에서 **Knowledge bases** 선택
3. **Create knowledge base** 버튼 클릭

### 4.2 Knowledge Base 기본 설정

**페이지: "Provide knowledge base details"**

```
Knowledge base name: diecasting-kb
Description: 다이캐스팅 공정 지식 베이스
```

**IAM permissions:**
- **Use an existing service role** 선택
- 드롭다운에서: `BedrockKnowledgeBaseRole-S3Vectors` 선택

➡️ **Next** 클릭

### 4.3 Data Source 설정

**페이지: "Set up data source"**

```
Data source name: diecasting-docs
S3 URI: s3://YOUR_VECTOR_BUCKET_NAME/documents/
```

**Chunking strategy:**
- **Fixed-size chunking** 선택
- Max tokens: `300`
- Overlap percentage: `20`

➡️ **Next** 클릭

### 4.4 Embeddings Model 선택

**페이지: "Select embeddings model"**

- **Titan Embeddings G1 - Text v2** 선택
- Dimensions: `1024` (자동)

➡️ **Next** 클릭

### 4.5 Vector Store 설정

**페이지: "Configure vector store"**

**Vector database:**
- **S3 vector bucket** 선택 (라디오 버튼)

**S3 vector bucket configuration:**
- S3 bucket: `YOUR_VECTOR_BUCKET_NAME` (드롭다운에서 선택)
- Vector index: `diecasting-vector-index` (드롭다운에서 선택)

➡️ **Next** 클릭

### 4.6 Review and Create

모든 설정 확인 후:

➡️ **Create knowledge base** 클릭

⏳ Knowledge Base 생성 중... (약 1-2분)

---

## Step 5: Data Source 동기화

Knowledge Base가 생성되면:

1. **Data sources** 탭에서 `diecasting-docs` 확인
2. **Sync** 버튼 클릭
3. 확인 팝업에서 **Sync** 클릭

⏳ 동기화 진행 중... (약 5-10분)

**진행 상황:**
- Status: **Syncing** → **Available**
- Documents: 6개 인덱싱

✅ Status가 **Available**로 변경되면 완료!

---

## Step 6: Knowledge Base ID 저장

1. Knowledge Base 상세 페이지에서 **Knowledge base ID** 복사
2. 터미널에서 저장:

```bash
echo "YOUR_KB_ID" > knowledge_base_id.txt
```

예: `echo "A1B2C3D4E5" > knowledge_base_id.txt`

3. 확인:
```bash
cat knowledge_base_id.txt
```

---

## Step 7: Knowledge Base 테스트

Console에서 테스트:

1. **Test** 탭 클릭
2. 질문 입력:
   ```
   포로시티 불량이 발생했을 때 어떻게 해결하나요?
   ```
3. **Run** 클릭
4. 답변 확인

✅ 답변이 생성되면 Knowledge Base 설정 완료!

---

## Step 8: Lambda T3 배포

Knowledge Base가 준비되었으니 Lambda T3를 배포합니다.

```bash
chmod +x deploy_lambda_t3.sh
./deploy_lambda_t3.sh
```

⏳ 배포 진행 중... (약 3-5분)

---

## Step 9: 전체 시스템 테스트

```bash
python3 test_lambda_t3.py
```

✅ 모든 테스트가 통과하면 완료!

---

## 요약

완료해야 할 단계:

1. ✅ S3 Vector 버킷 생성 (완료)
2. ⏳ Vector Index 생성
3. ⏳ 문서 업로드
4. ⏳ IAM 역할 생성
5. ⏳ Knowledge Base 생성
6. ⏳ Data Source 동기화
7. ⏳ Knowledge Base ID 저장
8. ⏳ Lambda T3 배포
9. ⏳ 테스트

**예상 소요 시간:** 약 20-30분

---

## 트러블슈팅

### Vector Index가 드롭다운에 없는 경우
- S3 Console > 버킷 > Properties > Vector configuration 확인
- Status가 **Active**인지 확인

### IAM 권한 오류
- IAM 역할에 S3 Vector 관련 권한 추가 확인
- Trust Policy에 bedrock.amazonaws.com 추가 확인

### 동기화 실패
- S3 URI 경로 확인: `s3://버킷이름/documents/`
- 문서가 실제로 업로드되었는지 확인
- CloudWatch Logs에서 에러 확인

---

## 다음 단계

Knowledge Base 설정이 완료되면:
1. Lambda T3 배포
2. Agent 통합
3. Streamlit UI 연결
