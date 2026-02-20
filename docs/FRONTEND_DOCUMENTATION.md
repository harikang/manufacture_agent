# 프론트엔드 문서 (Frontend Documentation)

다이캐스팅 품질 예측 AI 시스템의 프론트엔드 구성 및 기능을 설명합니다.

## 📁 파일 구조

```
withoutstreamlit/
├── index.html      # 랜딩 페이지 (메인 홈)
├── index.css       # 랜딩 페이지 스타일
├── index.js        # 랜딩 페이지 인터랙션
├── chat.html       # AI 챗봇 인터페이스
├── chat.css        # 챗봇 스타일
└── chat.js         # 챗봇 핵심 로직
```

---

## 1. 랜딩 페이지 (index.html, index.css, index.js)

### 1.1 index.html - 메인 페이지 구조

다이캐스팅 품질 예측 AI 서비스의 소개 페이지입니다.

#### 주요 섹션

| 섹션 | 설명 |
|------|------|
| `nav` | 고정 네비게이션 바 (로고, 메뉴, CTA 버튼) |
| `.hero` | 히어로 섹션 - 서비스 소개 및 공정 시각화 |
| `.services` | 서비스 카드 (품질 예측, 원인 분석) |
| `.engineering` | 기술력 소개 섹션 |
| `.gallery` | 갤러리 아이템 |
| `.stats` | 통계 카드 (성과 지표) |
| `.cta-section` | Call-to-Action 섹션 |
| `footer` | 푸터 |

#### 공정 시각화 (Process Visualization)

```html
<div class="process-visualization">
  <div class="process-flow">
    <div class="process-stage" data-stage="melting">용해</div>
    <div class="process-arrow"></div>
    <div class="process-stage" data-stage="injection">사출</div>
    <div class="process-arrow"></div>
    <div class="process-stage" data-stage="cooling">냉각</div>
  </div>
</div>
```

다이캐스팅 3단계 공정(용해 → 사출 → 냉각)을 시각적으로 표현합니다.

### 1.2 index.css - 스타일 시스템

#### CSS 변수 (Design Tokens)

```css
:root {
  --bg-deep: #060a1a;        /* 배경 (가장 어두운) */
  --bg-section: #0a1029;     /* 섹션 배경 */
  --bg-card: #0d1433;        /* 카드 배경 */
  --blue-primary: #2563eb;   /* 주요 파란색 */
  --blue-accent: #60a5fa;    /* 강조 파란색 */
  --text-white: #f1f5f9;     /* 기본 텍스트 */
  --text-secondary: #94a3b8; /* 보조 텍스트 */
  --border-card: rgba(59, 130, 246, 0.18);
}
```

#### 주요 애니메이션

| 애니메이션 | 용도 |
|-----------|------|
| `fadeInUp` | 요소 등장 (아래→위) |
| `slideInLeft/Right` | 좌우 슬라이드 |
| `pulse` | 맥박 효과 (상태 표시) |
| `float` | 부유 효과 (아이콘) |
| `glow` | 발광 효과 (품질 지표) |
| `rotate` | 회전 (로딩, 게이지) |
| `moltenFlow` | 용탕 흐름 시뮬레이션 |

### 1.3 index.js - 인터랙션 로직

#### 주요 기능

```javascript
// 1. 실시간 공정 데이터 시뮬레이션
function updateProcessData() {
  // 온도, 압력, 냉각시간 랜덤 변동
  // 품질 예측 상태 업데이트
}
setInterval(updateProcessData, 3000);

// 2. 공정 단계 인터랙션
processStages.forEach(stage => {
  stage.addEventListener('mouseenter', ...);  // 호버 효과
  stage.addEventListener('click', ...);       // 클릭 애니메이션
});

// 3. 스크롤 애니메이션 (Intersection Observer)
const observer = new IntersectionObserver((entries) => {
  // 요소가 뷰포트에 들어오면 애니메이션 실행
});
```

---

## 2. 챗봇 인터페이스 (chat.html, chat.css, chat.js)

### 2.1 chat.html - 챗봇 UI 구조

#### 레이아웃

```
┌─────────────────────────────────────────────────────┐
│                    TOPBAR                           │
├──────────┬──────────────────────────┬───────────────┤
│          │                          │               │
│ SIDEBAR  │      CHAT COLUMN         │ INSIGHT PANEL │
│          │                          │               │
│ - 새대화 │  - 메시지 영역           │ - 품질 예측   │
│ - KB업뎃 │  - 데이터 패널           │ - Feature     │
│          │  - 입력 영역             │   Importance  │
│          │                          │ - KB 결과     │
│          │                          │               │
└──────────┴──────────────────────────┴───────────────┘
```

#### 주요 컴포넌트

| 컴포넌트 | ID/Class | 설명 |
|---------|----------|------|
| 사이드바 | `#sidebar` | 대화 세션 목록 (세션 히스토리 제거됨) |
| 채팅 영역 | `#chatMessages` | 메시지 표시 영역 |
| 데이터 패널 | `#dataPanel` | 30개 공정 변수 입력 |
| 입력창 | `#chatInput` | 사용자 질문 입력 |
| 인사이트 패널 | `#insightPanel` | 품질 예측, Feature Importance, KB 결과 표시 (context-panel에서 변경) |
| KB 모달 | `#kbModal` | Knowledge Base 업데이트 모달 |

### 2.2 chat.css - 챗봇 스타일

#### CSS 변수

```css
:root {
  --bg-base: #0B1220;
  --bg-surface: #111827;
  --bg-elevated: #0F172A;
  --accent: #38BDF8;
  --status-good: #22C55E;   /* 양품 */
  --status-warn: #F59E0B;   /* 경고 */
  --status-bad: #EF4444;    /* 불량 */
}
```

#### 주요 UI 컴포넌트 스타일

| 컴포넌트 | 클래스 | 설명 |
|---------|--------|------|
| 메시지 버블 | `.msg.user`, `.msg.ai` | 사용자/AI 메시지 (호버 효과, 애니메이션 추가) |
| 예측 카드 | `.prediction-card` | 품질 예측 결과 표시 |
| XAI 차트 | `.xai-card`, `.xai-bar-*` | Feature Importance 바 차트 (24개 표시) |
| 장비 카드 | `.equipment-card` | 관련 장비 정보 |
| RAG 답변 | `.rag-answer`, `.rag-sources` | Knowledge Base 검색 결과 (채팅에서 제거, 인사이트 패널에만 표시) |
| 에이전트 스텝 | `.agent-steps`, `.agent-step` | Lambda 호출 진행 상태 (완료 후 자동 숨김) |
| 라이브 인디케이터 | `.live-indicator` | 실시간 처리 표시 |
| 인사이트 패널 | `.insight-panel` | 우측 패널 (320px → 400px로 확장) |

#### 에이전트 스텝 인디케이터 (Lambda 호출 시각화)

```css
.agent-step.active .step-icon {
  border-color: var(--accent);
  animation: stepPulse 1.5s ease-in-out infinite;
}

.agent-step.completed .step-icon {
  background: var(--status-good);
}
```

**이 부분이 "~~호출중" 메시지와 로딩 아이콘을 표시하는 핵심 스타일입니다.**

### 2.3 chat.js - 챗봇 핵심 로직

#### API 엔드포인트

```javascript
// Backend Agent (CloudFront → ALB → ECS)
const BACKEND_BASE = 'https://your-distribution.cloudfront.net';
const BACKEND_CHAT = BACKEND_BASE + '/api/chat';

// Lambda 직접 호출 (Fallback)
const API_BASE = 'https://your-api-gateway.execute-api.us-east-1.amazonaws.com/prod';
const LAMBDA_T1 = API_BASE + '/t1';  // 품질 예측
const LAMBDA_T2 = API_BASE + '/t2';  // Feature Importance
const LAMBDA_T3 = API_BASE + '/t3';  // Knowledge Base
```

#### 공정 데이터 (30개 변수)

```javascript
const SAMPLE_FEATURES = {
  Process_Temperature: 670.0,    // 용탕 온도
  Process_Pressure: 145.0,       // 사출 압력
  Process_InjectionSpeed: 4.2,   // 사출 속도
  Process_CoolingTime: 10.5,     // 냉각 시간
  // ... 총 30개 변수
};

const FEATURE_LABELS = {
  Process_Temperature: '용탕 온도',
  Process_Pressure: '사출 압력',
  // ... 한글 라벨 매핑
};
```

#### 핵심 함수

| 함수 | 설명 |
|------|------|
| `sendMessage()` | 메시지 전송 및 Backend Agent 호출 |
| `handleBackendAgentSSE()` | SSE 스트리밍 응답 처리 |
| `classifyIntent()` | 의도 분류 (prediction/xai/knowledge) |
| `callLambdaT1/T2/T3()` | Lambda 직접 호출 (Fallback) |

#### SSE 이벤트 처리 (실시간 Lambda 호출 표시)

```javascript
async function handleBackendAgentSSE(question, container) {
  // SSE 스트림 연결
  const response = await fetch(BACKEND_CHAT, { ... });
  const reader = response.body.getReader();

  // 중복 렌더링 방지
  const renderedCards = {};
  renderedCards[msgId] = { t1: false, t2: false, t3: false };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    // 이벤트 타입별 처리
    if (data.type === 'tool_start') {
      // "Lambda T1 호출 중..." 표시
      handleToolStart(data.tool, data.input, elapsed, msgId);
    } else if (data.type === 'tool_end') {
      // "Lambda T1 완료" 표시
      handleToolEnd(data.tool, data.result, elapsed, msgId);
    } else if (data.type === 't1_result') {
      // 예측 결과 즉시 렌더링
      t1Result = data.data;
      renderLiveT1Result(t1Result, msgId);
    } else if (data.type === 't2_result') {
      // Feature Importance 즉시 렌더링 (중복 방지)
      if (!renderedCards[msgId]?.t2) {
        t2Result = data.data;
        renderLiveT2Result(t2Result, msgId);
      }
    } else if (data.type === 't3_result') {
      // KB 결과는 인사이트 패널에만 표시
      t3Result = data.data;
    } else if (data.type === 'ai_response') {
      // AI 최종 답변 렌더링
      aiSummary = data.data?.answer || '';
      renderLiveAIResponse(aiSummary, msgId);
    } else if (data.type === 'done') {
      // 스트림 완료 - 명시적 종료
      finalizeLiveResponse(t1Result, t2Result, t3Result, aiSummary, elapsed, msgId);
      reader.cancel();  // 스트림 명시적 종료
      return;  // 함수 종료
    }
  }
}
```

**주요 개선사항:**
- **중복 방지**: `renderedCards` 객체로 T1/T2/T3 중복 렌더링 방지
- **즉시 렌더링**: T2 결과를 debounce 없이 즉시 표시 (이전에는 100ms 지연)
- **명시적 종료**: `done` 이벤트 시 `reader.cancel()` + `return`으로 스트림 완전 종료
- **재연결 방지**: 스트림 종료 후 재연결되지 않도록 개선

#### Step Indicator 동적 생성

```javascript
// Tool 정보 매핑
const TOOL_INFO = {
  'predict_quality': {
    id: 'predict',
    title: '품질 예측 (Lambda T1)',
    desc: 'ML 모델로 품질을 예측합니다'
  },
  'analyze_feature_importance': {
    id: 'analyze',
    title: '원인 분석 (Lambda T2)',
    desc: 'Feature Importance를 분석합니다'
  },
  'search_knowledge_base': {
    id: 'search',
    title: '지식 검색 (Lambda T3)',
    desc: 'Knowledge Base에서 관련 문서를 검색합니다'
  }
};

// Tool 단계 동적 추가
function addToolStep(toolName, input, elapsed, msgId) {
  const stepHtml = `
    <div class="agent-step active" id="step-${toolInfo.id}_${msgId}">
      <div class="step-icon">${toolInfo.icon}</div>
      <div class="step-content">
        <div class="step-title">${toolInfo.title}</div>
        <div class="step-desc">${toolInfo.desc}</div>
        <div class="step-result">
          <span class="tool-badge">⏳ 실행 중...</span>
        </div>
      </div>
    </div>
  `;
  stepsContainer.insertAdjacentHTML('beforeend', stepHtml);
}
```

#### 결과 렌더링 함수

| 함수 | 설명 |
|------|------|
| `renderPredictionCard()` | 품질 예측 결과 (게이지 차트) |
| `renderXaiCard()` | Feature Importance 바 차트 |
| `renderEquipmentDescriptions()` | 관련 장비 카드 |
| `renderKbAnswer()` | RAG 답변 + 참고 문서 |

#### 장비/센서 매핑

```javascript
const EQUIPMENT_MAP = {
  "melting_furnace": {
    name: "용탕로",
    name_en: "Melting Furnace",
    description: "알루미늄 합금을 용융시키는 핵심 장비",
    action: "온도 편차가 클 경우 버너 상태 확인"
  },
  // ...
};

const FEATURE_TO_EQUIPMENT = {
  Process_Temperature: "melting_furnace",
  Process_Pressure: "injection_unit",
  // ...
};
```

---

## 3. 데이터 흐름

```
사용자 질문 입력
       ↓
┌──────────────────────────────────────────────────────┐
│  chat.js: sendMessage()                              │
│     ↓                                                │
│  handleBackendAgentSSE() - SSE 스트림 연결           │
│     ↓                                                │
│  Backend Agent (ECS) - 의도 분류                     │
│     ↓                                                │
│  ┌─────────────────────────────────────────────────┐ │
│  │ SSE Events:                                     │ │
│  │  • tool_start → addToolStep() (로딩 표시)      │ │
│  │  • tool_end → handleToolEnd() (완료 표시)      │ │
│  │  • t1_result → renderLiveT1Result()            │ │
│  │  • t2_result → renderLiveT2Result()            │ │
│  │  • t3_result → renderLiveT3Result()            │ │
│  │  • done → finalizeLiveResponse()               │ │
│  └─────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
       ↓
화면에 결과 표시
```

---

## 4. 반응형 디자인

| 브레이크포인트 | 변경 사항 |
|---------------|----------|
| `≤1280px` | Insight Panel 숨김 |
| `≤1024px` | 2컬럼 → 1컬럼 레이아웃 |
| `≤960px` | Sidebar 오버레이 모드 |
| `≤640px` | 모바일 최적화 (패딩 축소) |

---

## 5. 외부 라이브러리

| 라이브러리 | 용도 |
|-----------|------|
| `marked.js` | Markdown → HTML 변환 |
| `DOMPurify` | XSS 방지 (HTML 정화) |
| `Inter`, `Noto Sans KR` | 웹 폰트 |

---

## 6. 주요 UX 기능

1. **실시간 Lambda 호출 표시**: SSE를 통해 각 Lambda 호출 단계를 실시간으로 표시
2. **중복 렌더링 방지**: `renderedCards` 객체로 T1/T2/T3 결과 중복 표시 방지
3. **공정 데이터 편집**: 30개 변수를 직접 수정하여 예측 테스트 가능
4. **마크다운 렌더링**: AI 응답의 마크다운 형식 지원
5. **인사이트 패널**: 품질 예측, Feature Importance, KB 결과를 우측 패널에 동적 표시
6. **세션 관리**: 새 대화 시작 기능 (세션 히스토리는 제거됨)
7. **KB 업데이트**: Knowledge Base 인제스트 트리거
8. **처리 단계 숨김**: 완료 후 에이전트 스텝 인디케이터 자동 숨김
9. **Latent Features 확장**: 12개 → 24개로 증가하여 더 많은 잠재 변수 표시
10. **폰트 크기 증가**: 모든 텍스트 1pt 증가로 가독성 향상
