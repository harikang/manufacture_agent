# Draw.io 아키텍처 다이어그램 사용 가이드

## 📁 생성된 파일

**`diecasting_poc_architecture.drawio`** - AWS 아키텍처 다이어그램

---

## 🚀 사용 방법

### 방법 1: 온라인 (추천)

1. **Draw.io 웹사이트 접속**
   - https://app.diagrams.net/ 또는 https://draw.io

2. **파일 열기**
   - "Open Existing Diagram" 클릭
   - `diecasting_poc_architecture.drawio` 파일 선택

3. **편집 및 저장**
   - 자유롭게 편집 가능
   - File → Export as → PNG/PDF/SVG 등으로 내보내기

### 방법 2: VS Code Extension

1. **Extension 설치**
   ```
   Draw.io Integration (hediet.vscode-drawio)
   ```

2. **파일 열기**
   - VS Code에서 `diecasting_poc_architecture.drawio` 파일 클릭
   - 자동으로 Draw.io 에디터 실행

3. **편집**
   - 드래그 앤 드롭으로 요소 이동
   - 우클릭으로 속성 변경
   - Ctrl+S로 저장

### 방법 3: Desktop App

1. **다운로드**
   - https://github.com/jgraph/drawio-desktop/releases
   - macOS, Windows, Linux 버전 제공

2. **설치 및 실행**
   - 앱 설치 후 실행
   - File → Open → `diecasting_poc_architecture.drawio` 선택

---

## 📊 다이어그램 구성 요소

### 포함된 AWS 서비스

1. **네트워크**
   - Internet Gateway
   - VPC (10.0.0.0/16)
   - Public Subnet (10.0.1.0/24)
   - Private Subnet - ECS (10.0.2.0/24)
   - Private Subnet - Lambda (10.0.3.0/24)
   - NAT Gateway

2. **컴퓨팅**
   - Application Load Balancer (IP Allowlist)
   - ECS Fargate (Streamlit UI + Agent)
   - Lambda T1 (Predict - GB + 12D Latent)
   - Lambda T2 (Importance - SHAP)
   - Lambda T3 (RAG Query)

3. **스토리지 & AI**
   - S3 Bucket (Importance Visualizations)
   - Bedrock Knowledge Bases

4. **보안 & 모니터링**
   - IAM Roles
   - API Gateway (IAM Auth)

### 연결 (Connections)

- 🔴 빨간색 실선: HTTPS (IP Allowlist) - 사용자 → ALB
- ⚫ 검은색 실선: 내부 통신 (ALB → ECS → API Gateway → Lambda)
- 🟢 초록색 점선: S3 저장 (Lambda T2 → S3)
- 🔵 파란색 점선: Bedrock 쿼리 (Lambda T3 → Bedrock)

---

## ✏️ 편집 가이드

### 요소 추가하기

1. **AWS 아이콘 라이브러리 활성화**
   - 좌측 패널에서 "More Shapes..." 클릭
   - "AWS" 검색 후 체크
   - "AWS 19" 또는 "AWS 4" 선택

2. **아이콘 드래그**
   - 좌측 패널에서 원하는 AWS 서비스 아이콘 드래그
   - 캔버스에 드롭

3. **연결선 추가**
   - 요소 위에 마우스 오버
   - 파란색 화살표 아이콘 드래그
   - 대상 요소에 연결

### 스타일 변경

1. **색상 변경**
   - 요소 선택
   - 우측 패널에서 "Style" 탭
   - Fill Color, Stroke Color 변경

2. **텍스트 편집**
   - 요소 더블클릭
   - 텍스트 입력/수정
   - Enter로 줄바꿈

3. **크기 조정**
   - 요소 선택
   - 모서리 핸들 드래그

### 레이아웃 정렬

1. **자동 정렬**
   - 여러 요소 선택 (Shift + 클릭)
   - 상단 메뉴: Arrange → Align → Left/Center/Right

2. **균등 배치**
   - 여러 요소 선택
   - Arrange → Distribute → Horizontally/Vertically

---

## 📤 내보내기 (Export)

### PNG 이미지로 내보내기

1. File → Export as → PNG
2. 옵션 설정:
   - Zoom: 100%
   - Border Width: 10
   - Transparent Background: 체크 (선택)
3. Export 클릭

### PDF로 내보내기

1. File → Export as → PDF
2. 옵션 설정:
   - Page View: Fit to Page
   - Include a copy of my diagram: 체크 (편집 가능)
3. Export 클릭

### SVG로 내보내기 (벡터)

1. File → Export as → SVG
2. 옵션 설정:
   - Embed Images: 체크
   - Include a copy of my diagram: 체크
3. Export 클릭

---

## 🎨 커스터마이징 팁

### 1. 색상 테마 변경

**현재 색상**:
- 빨간색 (#DD3522): IP Allowlist 강조
- 초록색 (#277116): S3 관련
- 파란색 (#116D5B): Bedrock 관련
- 검은색 (#232F3E): 일반 연결

**변경 방법**:
- 연결선 선택 → Style → Line Color

### 2. 주석 박스 추가

1. 좌측 패널에서 "Rectangle" 선택
2. 캔버스에 드래그
3. 텍스트 입력
4. Style 변경:
   - Fill Color: #dae8fc (파란색)
   - Stroke Color: #6c8ebf
   - Rounded: 체크

### 3. 아이콘 크기 통일

1. 모든 AWS 아이콘 선택
2. 우측 패널 → Size
3. Width/Height 동일하게 설정 (예: 78x78)

### 4. 그리드 스냅 활성화

- View → Grid → 체크
- View → Snap to Grid → 체크
- 요소가 그리드에 자동 정렬됨

---

## 🔧 고급 기능

### 1. 레이어 사용

1. View → Layers
2. 레이어 추가/삭제
3. 레이어별로 요소 그룹화
   - 예: Network Layer, Compute Layer, Storage Layer

### 2. 템플릿 저장

1. File → Save as Template
2. 이름 입력
3. 다음 프로젝트에서 재사용

### 3. 자동 레이아웃

1. 모든 요소 선택
2. Arrange → Layout → Horizontal/Vertical Flow
3. 자동으로 정렬됨

### 4. 링크 추가

1. 요소 선택
2. Edit → Edit Link
3. URL 입력 (예: AWS Console 링크)
4. 클릭 시 링크 열림

---

## 📋 체크리스트

### 다이어그램 완성도 체크

- [ ] 모든 AWS 서비스 아이콘 표시
- [ ] 연결선 명확하게 표시
- [ ] IP Allowlist 강조 (빨간색)
- [ ] Private/Public Subnet 구분
- [ ] 보안 그룹 표시
- [ ] 성능 지표 주석
- [ ] 비용 정보 주석
- [ ] 제목 및 범례 추가

### 발표 자료용 체크

- [ ] 고해상도 PNG 내보내기 (300 DPI)
- [ ] 투명 배경 설정
- [ ] 텍스트 크기 충분히 큼 (12pt 이상)
- [ ] 색상 대비 명확
- [ ] 범례 추가

---

## 🆘 문제 해결

### 파일이 열리지 않을 때

1. **브라우저 캐시 삭제**
   - Ctrl+Shift+Delete
   - 캐시 삭제 후 재시도

2. **다른 브라우저 시도**
   - Chrome, Firefox, Edge 등

3. **파일 인코딩 확인**
   - UTF-8 인코딩 확인
   - 텍스트 에디터로 열어서 XML 구조 확인

### AWS 아이콘이 보이지 않을 때

1. **라이브러리 활성화**
   - More Shapes → AWS → 체크

2. **인터넷 연결 확인**
   - 온라인 버전은 인터넷 필요

3. **Desktop App 사용**
   - 오프라인에서도 사용 가능

---

## 📚 추가 리소스

### 공식 문서
- Draw.io 공식 문서: https://www.diagrams.net/doc/
- AWS 아키텍처 아이콘: https://aws.amazon.com/architecture/icons/

### 튜토리얼
- Draw.io 기본 사용법: https://www.youtube.com/watch?v=Z0D96ZikMkc
- AWS 아키텍처 다이어그램 그리기: https://www.youtube.com/watch?v=3XL7_Qy9KCM

### 템플릿
- AWS 아키텍처 템플릿: https://www.diagrams.net/blog/aws-diagrams

---

## 💡 활용 예시

### 1. 발표 자료
- PNG로 내보내기 (300 DPI)
- PowerPoint/Keynote에 삽입

### 2. 문서화
- PDF로 내보내기
- Confluence/Notion에 첨부

### 3. 코드 리뷰
- SVG로 내보내기
- GitHub README.md에 삽입

### 4. 인쇄물
- PDF로 내보내기 (A3 크기)
- 고해상도 설정

---

**작성일**: 2026-01-15  
**버전**: 1.0  
**파일**: diecasting_poc_architecture.drawio
