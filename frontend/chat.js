    // ========== BACKEND API ENDPOINTS ==========
    // Backend Agent (CloudFront → ALB → ECS) 엔드포인트 - LLM 기반 의도 분류
    // 실제 배포 시 아래 URL을 본인의 CloudFront/API Gateway URL로 변경하세요
    const BACKEND_BASE = 'https://your-cloudfront-distribution.cloudfront.net';
    const BACKEND_CHAT = BACKEND_BASE + '/api/chat';
    const BACKEND_KB_INGEST = BACKEND_BASE + '/api/kb-ingest';
    
    // API Gateway 엔드포인트 (직접 Lambda 호출용 - fallback)
    const API_BASE = 'https://your-api-gateway.execute-api.us-east-1.amazonaws.com/prod';
    const LAMBDA_T0 = API_BASE + '/t0';  // KB Ingest (fallback)
    const LAMBDA_T1 = API_BASE + '/t1';
    const LAMBDA_T2 = API_BASE + '/t2';
    const LAMBDA_T3 = API_BASE + '/t3';

    // ========== SAMPLE PROCESS DATA (30 features) ==========
    const SAMPLE_FEATURES = {
      Process_Temperature: 670.0,
      Process_Pressure: 145.0,
      Process_InjectionSpeed: 4.2,
      Process_InjectionTime: 0.85,
      Process_CoolingTime: 10.5,
      Process_ClampForce: 720.0,
      Process_MoldTemperature: 195.0,
      Process_MeltTemperature: 685.0,
      Process_CycleTime: 34.0,
      Process_ShotSize: 275.0,
      Process_BackPressure: 62.0,
      Process_ScrewSpeed: 110.0,
      Process_HoldPressure: 100.0,
      Process_HoldTime: 2.2,
      Process_CushionPosition: 3.8,
      Process_PlasticizingTime: 5.8,
      Sensor_Vibration: 0.25,
      Sensor_Noise: 76.0,
      Sensor_Temperature1: 680.0,
      Sensor_Temperature2: 190.0,
      Sensor_Temperature3: 182.0,
      Sensor_Pressure1: 142.0,
      Sensor_Pressure2: 102.0,
      Sensor_Pressure3: 63.0,
      Sensor_Flow: 26.5,
      Sensor_Position: 112.0,
      Sensor_Speed: 2.6,
      Sensor_Torque: 175.0,
      Sensor_Current: 52.0,
      Sensor_Voltage: 390.0
    };

    // Feature name -> Korean label mapping
    const FEATURE_LABELS = {
      Process_Temperature: '용탕 온도',
      Process_Pressure: '사출 압력',
      Process_InjectionSpeed: '사출 속도',
      Process_InjectionTime: '사출 시간',
      Process_CoolingTime: '냉각 시간',
      Process_ClampForce: '클램프 힘',
      Process_MoldTemperature: '금형 온도',
      Process_MeltTemperature: '용융 온도',
      Process_CycleTime: '사이클 타임',
      Process_ShotSize: '샷 사이즈',
      Process_BackPressure: '배압',
      Process_ScrewSpeed: '스크류 속도',
      Process_HoldPressure: '보압',
      Process_HoldTime: '보압 시간',
      Process_CushionPosition: '쿠션 위치',
      Process_PlasticizingTime: '가소화 시간',
      Sensor_Vibration: '진동 센서',
      Sensor_Noise: '소음 센서',
      Sensor_Temperature1: '온도 센서 1',
      Sensor_Temperature2: '온도 센서 2',
      Sensor_Temperature3: '온도 센서 3',
      Sensor_Pressure1: '압력 센서 1',
      Sensor_Pressure2: '압력 센서 2',
      Sensor_Pressure3: '압력 센서 3',
      Sensor_Flow: '유량 센서',
      Sensor_Position: '위치 센서',
      Sensor_Speed: '속도 센서',
      Sensor_Torque: '토크 센서',
      Sensor_Current: '전류 센서',
      Sensor_Voltage: '전압 센서'
    };

    // Last T1 result for chaining to T2
    let lastT1Result = null;

    // ========== EDITABLE FEATURES (copy of sample) ==========
    let currentFeatures = { ...SAMPLE_FEATURES };
    
    // 초기화 확인
    console.log('Features initialized:', Object.keys(currentFeatures).length, 'features');
    console.log('Sample feature values:', {
      Process_Temperature: currentFeatures.Process_Temperature,
      Process_Pressure: currentFeatures.Process_Pressure
    });

    function initDataPanel() {
      const grid = document.getElementById('dataPanelGrid');
      let html = '';
      for (const [key, val] of Object.entries(SAMPLE_FEATURES)) {
        const label = FEATURE_LABELS[key] || key;
        html += `
          <div class="data-field">
            <label title="${key}">${label}</label>
            <input type="number" step="any" id="feat_${key}" value="${val}" onchange="updateFeature('${key}', this.value)" />
          </div>
        `;
      }
      grid.innerHTML = html;
      console.log('Data panel initialized with', Object.keys(SAMPLE_FEATURES).length, 'features');
    }

    function updateFeature(key, val) {
      currentFeatures[key] = parseFloat(val) || 0;
    }

    function resetFeatures() {
      currentFeatures = { ...SAMPLE_FEATURES };
      for (const [key, val] of Object.entries(SAMPLE_FEATURES)) {
        const el = document.getElementById('feat_' + key);
        if (el) el.value = val;
      }
    }

    function toggleDataPanel() {
      const panel = document.getElementById('dataPanel');
      const btn = document.getElementById('dataPanelToggle');
      panel.classList.toggle('open');
      btn.classList.toggle('active');
    }

    // Init on load
    initDataPanel();

    // ========== INTENT CLASSIFICATION ==========
    function classifyIntent(question) {
      const q = question.toLowerCase();
      const t1Keywords = ['불량', '양품', '예측', '가능성', '판정', '품질', 'prediction'];
      const t2Keywords = ['영향', '원인', '중요도', '기여', 'feature', '분석', '왜'];
      const t3Keywords = ['범위', '스펙', '권장', '장비', '공정', '해결', '방법', '어떻게', '무엇', '설명', '가이드', '매뉴얼', '트러블', '포로시티', '법규', '안전', '트러블슈팅'];

      const isT1 = t1Keywords.some(k => q.includes(k));
      const isT2 = t2Keywords.some(k => q.includes(k));
      const isT3 = t3Keywords.some(k => q.includes(k));

      // T1 intent takes priority, then chains to T2 automatically
      if (isT1) return 'prediction';
      if (isT2) return 'xai';
      if (isT3) return 'knowledge';
      return 'knowledge'; // default to T3 RAG
    }

    // ========== LAMBDA API CALLS ==========
    // Parse Lambda response - body can be a string or object
    function parseLambdaResponse(data) {
      let body = data.body || data;
      if (typeof body === 'string') {
        try { body = JSON.parse(body); } catch (e) { /* keep as-is */ }
      }
      console.log('Lambda response parsed:', body);
      return body;
    }

    async function callLambdaT1(features) {
      try {
        console.log('Calling Lambda T1:', LAMBDA_T1);
        const res = await fetch(LAMBDA_T1, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ features })
        });
        console.log('Lambda T1 response status:', res.status);
        const data = await res.json();
        console.log('Lambda T1 data:', data);
        
        if (data.error) {
          console.warn('Lambda T1 에러, mock 데이터 사용:', data.message);
          return getMockT1Response();
        }
        
        return data;
      } catch (err) {
        console.error('Lambda T1 호출 실패, mock 데이터 사용:', err);
        return getMockT1Response();
      }
    }

    function getMockT1Response() {
      // Mock response for testing UI
      const isDefect = Math.random() > 0.7;
      const defectProb = isDefect ? 0.75 + Math.random() * 0.2 : 0.1 + Math.random() * 0.2;
      return {
        prediction: {
          class: isDefect ? 'defect' : 'normal',
          probability: defectProb,
          confidence: defectProb > 0.8 ? 'high' : defectProb > 0.6 ? 'medium' : 'low',
          confidence_score: defectProb,
          class_probabilities: {
            normal: 1 - defectProb,
            defect: defectProb
          }
        },
        latent_features: Array(24).fill(0).map(() => Math.random() * 2 - 1),
        processing_time_ms: 45.2,
        model_version: 'v1.0_24D_GB (mock)'
      };
    }

    async function callLambdaT2(features, latentFeatures) {
      try {
        const payload = {
          features,
          latent_features: latentFeatures || [],
          top_n: 10,
          generate_chart: false
        };
        console.log('Calling Lambda T2:', LAMBDA_T2);
        const res = await fetch(LAMBDA_T2, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        console.log('Lambda T2 response status:', res.status);
        const data = await res.json();
        console.log('Lambda T2 data:', data);
        
        if (data.error) {
          console.warn('Lambda T2 에러, mock 데이터 사용:', data.message);
          return getMockT2Response();
        }
        
        return data;
      } catch (err) {
        console.error('Lambda T2 호출 실패, mock 데이터 사용:', err);
        return getMockT2Response();
      }
    }

    function getMockT2Response() {
      const featureNames = Object.keys(SAMPLE_FEATURES);
      const shuffled = featureNames.sort(() => Math.random() - 0.5);
      const topFeatures = shuffled.slice(0, 10).map((name, idx) => [name, 0.15 - idx * 0.012]);
      return {
        top_features: topFeatures,
        equipment_descriptions: []
      };
    }

    async function callLambdaT3(query) {
      try {
        const payload = { query };
        if (lastT1Result) {
          payload.context = { last_prediction: lastT1Result };
        }
        console.log('Calling Lambda T3:', LAMBDA_T3);
        const res = await fetch(LAMBDA_T3, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        console.log('Lambda T3 response status:', res.status);
        const data = await res.json();
        console.log('Lambda T3 data:', data);
        
        if (data.error) {
          console.warn('Lambda T3 에러:', data.message);
          return { answer: `죄송합니다. Knowledge Base 검색 중 오류가 발생했습니다: ${data.message}`, sources: [] };
        }
        
        return data;
      } catch (err) {
        console.error('Lambda T3 호출 실패:', err);
        return { answer: `죄송합니다. Knowledge Base 서비스에 연결할 수 없습니다. (${err.message})`, sources: [] };
      }
    }

    // ========== UI HELPERS ==========
    function toggleSidebar() {
      document.getElementById('sidebar').classList.toggle('collapsed');
    }

    function toggleInsightPanel() {
      const panel = document.getElementById('insightPanel');
      panel.classList.toggle('collapsed');
    }
    
    function showInsight(type, data) {
      const insightPanel = document.getElementById('insightPanel');
      const insightEmpty = document.getElementById('insightEmpty');
      const insightContent = document.getElementById('insightContent');
      
      if (!insightEmpty || !insightContent || !insightPanel) {
        console.warn('Insight panel elements not found');
        return;
      }
      
      // 패널이 닫혀있으면 열기
      if (insightPanel.classList.contains('collapsed')) {
        insightPanel.classList.remove('collapsed');
      }
      
      insightEmpty.style.display = 'none';
      insightContent.style.display = 'flex';
      
      let newCard = '';
      if (type === 'defect_rate') {
        newCard = createDefectRateCard(data);
      } else if (type === 'feature_importance') {
        newCard = createFeatureImportanceCard(data);
      } else if (type === 'equipment') {
        newCard = createEquipmentCard(data);
      } else if (type === 'sensor') {
        newCard = createSensorCard(data);
      }
      
      if (newCard) {
        insightContent.innerHTML += newCard;
      }
    }
    
    function createDefectRateCard(data) {
      return `
        <div class="insight-section" style="animation: slideInRight 0.4s ease">
          <div class="insight-section-title">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M2 14L8 2L14 14H2Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
            </svg>
            불량률 예측
          </div>
          <div style="font-size: 32px; font-weight: 700; color: ${data.rate > 50 ? 'var(--status-bad)' : 'var(--status-good)'}; margin: 12px 0;">
            ${data.rate}%
          </div>
          <div style="font-size: 13px; color: var(--text-muted);">
            ${data.description || '현재 공정 조건 기준'}
          </div>
        </div>
      `;
    }
    
    function createFeatureImportanceCard(data) {
      const bars = data.features.map(f => `
        <div style="margin-bottom: 10px;">
          <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
            <span style="font-size: 13px; color: var(--text-secondary);">${f.name}</span>
            <span style="font-size: 13px; font-weight: 600; color: var(--accent);">${f.importance}%</span>
          </div>
          <div style="height: 6px; background: var(--bg-base); border-radius: 3px; overflow: hidden;">
            <div style="height: 100%; width: ${f.importance}%; background: linear-gradient(90deg, var(--accent), var(--accent-hover)); transition: width 0.6s ease;"></div>
          </div>
        </div>
      `).join('');
      
      return `
        <div class="insight-section" style="animation: slideInRight 0.5s ease">
          <div class="insight-section-title">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <rect x="2" y="10" width="3" height="4" stroke="currentColor" stroke-width="1.5"/>
              <rect x="6.5" y="6" width="3" height="8" stroke="currentColor" stroke-width="1.5"/>
              <rect x="11" y="2" width="3" height="12" stroke="currentColor" stroke-width="1.5"/>
            </svg>
            주요 영향 요인
          </div>
          ${bars}
        </div>
      `;
    }
    
    function createEquipmentCard(data) {
      return `
        <div class="insight-section" style="animation: slideInRight 0.6s ease">
          <div class="insight-section-title">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <rect x="3" y="3" width="10" height="10" rx="2" stroke="currentColor" stroke-width="1.5"/>
              <path d="M6 6h4M6 9h4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
            관련 장비
          </div>
          <div style="font-size: 15px; font-weight: 600; color: var(--text-primary); margin: 8px 0;">
            ${data.name}
          </div>
          <div style="font-size: 13px; color: var(--text-secondary); line-height: 1.6;">
            ${data.description}
          </div>
        </div>
      `;
    }
    
    function createSensorCard(data) {
      return `
        <div class="insight-section" style="animation: slideInRight 0.7s ease">
          <div class="insight-section-title">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.5"/>
              <circle cx="8" cy="8" r="2" fill="currentColor"/>
            </svg>
            센서 정보
          </div>
          <div style="font-size: 14px; color: var(--text-secondary); margin-top: 8px;">
            ${data.sensors.map(s => `
              <div style="padding: 6px 0; border-bottom: 1px solid var(--border-default);">
                <span style="color: var(--text-primary); font-weight: 500;">${s.name}</span>: ${s.value}
              </div>
            `).join('')}
          </div>
        </div>
      `;
    }
    
    function toggleContext() {
      toggleInsightPanel();
    }
    
    function startNewConversation() {
      // 새 세션 ID 생성
      const newSessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
      localStorage.setItem('diecasting_session_id', newSessionId);
      
      // 채팅 UI 초기화 (초기 화면과 동일한 구조)
      const chatMessages = document.getElementById('chatMessages');
      chatMessages.innerHTML = `
        <div class="chat-empty" id="chatEmpty">
          <div class="chat-empty-icon">
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none"><path d="M11 2C6.03 2 2 5.58 2 10c0 2.17 1.06 4.13 2.76 5.52L3.5 19.5l4.4-1.96C8.9 17.83 9.93 18 11 18c4.97 0 9-3.58 9-8s-4.03-8-9-8z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>
          </div>
          <h3>다이캐스팅 AI 도우미</h3>
          <p>현장 상황을 자연어로 입력하면<br />AI가 품질 예측, 원인 분석, 공정 지식 검색을 수행합니다.</p>
          <div class="sample-questions">
            <div class="sample-q" onclick="sendSample(this)">현재 조건에서 불량 가능성은?</div>
            <div class="sample-q" onclick="sendSample(this)">용탕 온도가 품질에 미치는 영향</div>
            <div class="sample-q" onclick="sendSample(this)">사출 압력 권장 범위 알려줘</div>
            <div class="sample-q" onclick="sendSample(this)">금형 온도 센서 스펙 확인</div>
          </div>
        </div>
      `;
      
      // 입력창 초기화
      const textarea = document.getElementById('userInput');
      textarea.value = '';
      textarea.style.height = 'auto';
      
      console.log('새 대화 시작:', newSessionId);
    }

    function autoGrow(el) {
      el.style.height = 'auto';
      el.style.height = Math.min(el.scrollHeight, 144) + 'px';
    }

    function toggleSend() {
      const btn = document.getElementById('sendBtn');
      const input = document.getElementById('chatInput');
      btn.classList.toggle('active', !!input.value.trim());
    }

    function handleKey(e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    }

    function sendSample(el) {
      document.getElementById('chatInput').value = el.textContent;
      toggleSend();
      sendMessage();
    }

    function newChat() {
      lastT1Result = null;
      const msgs = document.getElementById('chatMessages');
      msgs.innerHTML = '';
      msgs.appendChild(createEmptyState());
      updateContextPanel(null);
    }

    function createEmptyState() {
      const div = document.createElement('div');
      div.className = 'chat-empty';
      div.id = 'chatEmpty';
      div.innerHTML = `
        <div class="chat-empty-icon">
          <svg width="22" height="22" viewBox="0 0 22 22" fill="none"><path d="M11 2C6.03 2 2 5.58 2 10c0 2.17 1.06 4.13 2.76 5.52L3.5 19.5l4.4-1.96C8.9 17.83 9.93 18 11 18c4.97 0 9-3.58 9-8s-4.03-8-9-8z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>
        </div>
        <h3>다이캐스팅 AI 도우미</h3>
        <p>현장 상황을 자연어로 입력하면<br />AI가 품질 예측, 원인 분석, 공정 지식 검색을 수행합니다.</p>
        <div class="sample-questions">
          <div class="sample-q" onclick="sendSample(this)">현재 조건에서 불량 가능성은?</div>
          <div class="sample-q" onclick="sendSample(this)">용탕 온도가 품질에 미치는 영향</div>
          <div class="sample-q" onclick="sendSample(this)">사출 압력 권장 범위 알려줘</div>
          <div class="sample-q" onclick="sendSample(this)">금형 온도 센서 스펙 확인</div>
        </div>
      `;
      return div;
    }

    function escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }

    // ========== MARKDOWN RENDERING ==========
    function renderMarkdown(text) {
      return DOMPurify.sanitize(marked.parse(text || ''));
    }

    // 테스트 함수
    window.testMarkdown = function(text) {
      const testText = text || "문서에는 **냉각수 온도(Temperature3)**만 제시되어 있으며, 권장값은 **30°C** (범위: 25-40°C)입니다.";
      const result = renderMarkdown(testText);
      console.log('Test result:', result);
      
      // 실제로 화면에 표시해보기
      const testDiv = document.createElement('div');
      testDiv.innerHTML = result;
      testDiv.style.cssText = 'position:fixed;top:10px;right:10px;background:white;color:black;padding:10px;border:2px solid red;z-index:9999;max-width:300px;';
      document.body.appendChild(testDiv);
      
      setTimeout(() => testDiv.remove(), 5000);
      return result;
    };

    function scrollToBottom() {
      const msgs = document.getElementById('chatMessages');
      msgs.scrollTop = msgs.scrollHeight;
    }

    // ========== LOADING INDICATOR ==========
    function showLoading(container, statusText) {
      const loader = document.createElement('div');
      loader.className = 'msg ai';
      loader.id = 'aiLoading';
      loader.innerHTML = `
        <div class="msg-header">
          <span class="ai-badge">AI</span>
          <span class="ai-label">Assistant</span>
        </div>
        <div class="agent-status"><span class="dot"></span> ${statusText}</div>
      `;
      container.appendChild(loader);
      scrollToBottom();
      return loader;
    }

    function updateLoadingStatus(text) {
      const loader = document.getElementById('aiLoading');
      if (loader) {
        const status = loader.querySelector('.agent-status');
        if (status) status.innerHTML = `<span class="dot"></span> ${text}`;
      }
    }

    function removeLoading() {
      const loader = document.getElementById('aiLoading');
      if (loader) loader.remove();
    }

    // ========== EQUIPMENT/SENSOR MAPPING ==========
    const EQUIPMENT_MAP = {
      "melting_furnace": {
        name: "용탕로", name_en: "Melting Furnace",
        description: "알루미늄 합금을 용융시키는 핵심 장비입니다. 용탕 온도와 품질에 직접적인 영향을 미칩니다.",
        action: "온도 편차가 클 경우 버너 상태 및 열전대 교정을 확인하세요."
      },
      "injection_unit": {
        name: "사출 유닛", name_en: "Injection Unit",
        description: "용탕을 금형에 고속으로 주입하는 장비입니다. 사출 압력과 속도가 제품 밀도에 영향을 줍니다.",
        action: "압력 이상 시 유압 시스템 및 플런저 마모 상태를 점검하세요."
      },
      "cooling_system": {
        name: "냉각 시스템", name_en: "Cooling System",
        description: "금형과 제품을 냉각시키는 시스템입니다. 냉각 시간과 온도 균일성이 수축 결함에 영향을 줍니다.",
        action: "냉각수 유량과 온도를 확인하고, 냉각 채널 막힘 여부를 점검하세요."
      },
      "clamping_unit": {
        name: "클램핑 유닛", name_en: "Clamping Unit",
        description: "금형을 고정하고 사출 시 형체력을 유지하는 장비입니다.",
        action: "형체력 설정값과 실제 압력을 비교하고, 타이바 균형을 확인하세요."
      },
      "mold": {
        name: "금형", name_en: "Die/Mold",
        description: "제품 형상을 결정하는 핵심 도구입니다. 금형 온도와 상태가 표면 품질에 직접 영향을 줍니다.",
        action: "금형 표면 상태와 이형제 도포 상태를 확인하세요."
      },
      "screw_barrel": {
        name: "스크류/배럴", name_en: "Screw & Barrel",
        description: "재료를 가소화하고 계량하는 장비입니다. 스크류 속도와 배압이 용융 품질에 영향을 줍니다.",
        action: "스크류 마모 상태와 배럴 온도 분포를 확인하세요."
      }
    };

    const FEATURE_TO_EQUIPMENT = {
      Process_Temperature: "melting_furnace",
      Process_Pressure: "injection_unit",
      Process_InjectionSpeed: "injection_unit",
      Process_InjectionTime: "injection_unit",
      Process_CoolingTime: "cooling_system",
      Process_ClampForce: "clamping_unit",
      Process_MoldTemperature: "mold",
      Process_MeltTemperature: "melting_furnace",
      Process_CycleTime: "injection_unit",
      Process_ShotSize: "injection_unit",
      Process_BackPressure: "screw_barrel",
      Process_ScrewSpeed: "screw_barrel",
      Process_HoldPressure: "injection_unit",
      Process_HoldTime: "injection_unit",
      Process_CushionPosition: "injection_unit",
      Process_PlasticizingTime: "screw_barrel",
      Sensor_Vibration: "injection_unit",
      Sensor_Noise: "injection_unit",
      Sensor_Temperature1: "melting_furnace",
      Sensor_Temperature2: "mold",
      Sensor_Temperature3: "mold",
      Sensor_Pressure1: "injection_unit",
      Sensor_Pressure2: "injection_unit",
      Sensor_Pressure3: "clamping_unit",
      Sensor_Flow: "cooling_system",
      Sensor_Position: "injection_unit",
      Sensor_Speed: "injection_unit",
      Sensor_Torque: "screw_barrel",
      Sensor_Current: "injection_unit",
      Sensor_Voltage: "injection_unit"
    };

    const SENSOR_INFO = {
      Sensor_Vibration: { name: "진동 센서", unit: "mm/s", range: "0.1~0.5", desc: "장비의 진동 수준을 측정합니다." },
      Sensor_Noise: { name: "소음 센서", unit: "dB", range: "70~85", desc: "장비 작동 소음을 측정합니다." },
      Sensor_Temperature1: { name: "용탕 온도 센서", unit: "°C", range: "660~720", desc: "용탕로의 알루미늄 용탕 온도를 측정합니다." },
      Sensor_Temperature2: { name: "금형 온도 센서 (고정측)", unit: "°C", range: "180~220", desc: "금형 고정측의 온도를 측정합니다." },
      Sensor_Temperature3: { name: "금형 온도 센서 (가동측)", unit: "°C", range: "175~215", desc: "금형 가동측의 온도를 측정합니다." },
      Sensor_Pressure1: { name: "사출 압력 센서", unit: "MPa", range: "130~160", desc: "사출 시 용탕에 가해지는 압력을 측정합니다." },
      Sensor_Pressure2: { name: "보압 센서", unit: "MPa", range: "90~120", desc: "보압 단계의 압력을 측정합니다." },
      Sensor_Pressure3: { name: "형체 압력 센서", unit: "MPa", range: "55~75", desc: "금형을 닫는 형체력을 측정합니다." },
      Sensor_Flow: { name: "냉각수 유량 센서", unit: "L/min", range: "20~35", desc: "냉각 시스템의 냉각수 유량을 측정합니다." },
      Sensor_Position: { name: "위치 센서", unit: "mm", range: "100~130", desc: "스크류 또는 플런저의 위치를 측정합니다." },
      Sensor_Speed: { name: "사출 속도 센서", unit: "m/s", range: "2.0~4.0", desc: "사출 시 플런저의 이동 속도를 측정합니다." },
      Sensor_Torque: { name: "토크 센서", unit: "N·m", range: "150~200", desc: "스크류 회전 토크를 측정합니다." },
      Sensor_Current: { name: "전류 센서", unit: "A", range: "45~60", desc: "모터 전류를 측정합니다." },
      Sensor_Voltage: { name: "전압 센서", unit: "V", range: "380~400", desc: "공급 전압을 측정합니다." }
    };

    // ========== RENDER FUNCTIONS ==========
    function renderPredictionCard(prediction) {
      if (!prediction) {
        console.error('No prediction data:', prediction);
        return '<div class="msg-text" style="color: var(--status-bad);">예측 데이터를 파싱할 수 없습니다.</div>';
      }
      
      const isDefect = prediction.class === 'defect';
      const label = isDefect ? '불량 판정' : '양품 판정';
      const statusClass = isDefect ? 'bad' : 'good';
      const classProbabilities = prediction.class_probabilities || { 
        normal: isDefect ? (1 - prediction.probability) : prediction.probability, 
        defect: isDefect ? prediction.probability : (1 - prediction.probability) 
      };
      const mainProb = isDefect ? classProbabilities.defect : classProbabilities.normal;
      const probPercent = (mainProb * 100).toFixed(1);
      
      // SVG gauge calculation
      const radius = 42;
      const circumference = 2 * Math.PI * radius;
      const offset = circumference - (mainProb * circumference);
      
      const description = isDefect 
        ? '현재 공정 조건에서 불량 발생 가능성이 높습니다. 아래 Feature Importance를 확인하여 주요 원인을 파악하세요.'
        : '현재 공정 조건이 양호합니다. 품질 기준을 충족할 것으로 예측됩니다.';

      return `
        <div class="prediction-card ${statusClass}">
          <div class="prediction-main">
            <div class="prediction-gauge">
              <svg width="100" height="100" viewBox="0 0 100 100">
                <circle class="prediction-gauge-bg" cx="50" cy="50" r="${radius}"/>
                <circle class="prediction-gauge-fill ${statusClass}" cx="50" cy="50" r="${radius}" 
                  stroke-dasharray="${circumference}" 
                  stroke-dashoffset="${offset}"/>
              </svg>
              <div class="prediction-gauge-text">
                <div class="prediction-gauge-percent">${probPercent}%</div>
                <div class="prediction-gauge-label">확률</div>
              </div>
            </div>
            <div class="prediction-info">
              <h4 class="${statusClass}">${label}</h4>
              <p>${description}</p>
            </div>
          </div>
          <div class="prediction-probs">
            <div class="prob-item">
              <div class="label">양품 확률</div>
              <div class="value good">${(classProbabilities.normal * 100).toFixed(1)}%</div>
            </div>
            <div class="prob-item">
              <div class="label">불량 확률</div>
              <div class="value bad">${(classProbabilities.defect * 100).toFixed(1)}%</div>
            </div>
          </div>
        </div>
      `;
    }

    function renderXaiCard(t2Data) {
      const topFeatures = (t2Data.top_features || []);
      if (!topFeatures.length) return '';

      const maxVal = topFeatures[0][1];

      let barsHtml = topFeatures.map(([name, val], idx) => {
        const label = FEATURE_LABELS[name] || name;
        const pct = Math.round((val / maxVal) * 100);
        const rankClass = idx < 3 ? 'top' : '';
        const valPercent = (val * 100).toFixed(1);  // 소수점 → %로 변환
        return `
          <div class="xai-bar-row">
            <span class="xai-bar-rank ${rankClass}">${idx + 1}</span>
            <span class="xai-bar-label" title="${name}">${label}</span>
            <div class="xai-bar-track">
              <div class="xai-bar-fill" style="width:${pct}%">
                <span class="xai-bar-value">${valPercent}%</span>
              </div>
            </div>
          </div>
        `;
      }).join('');

      return `
        <div class="xai-card">
          <div class="xai-header">
            <div class="xai-title">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M2 12h2V6H2v6zm4 0h2V4H6v8zm4 0h2V8h-2v4zm4 0h2V2h-2v10z" fill="currentColor"/></svg>
              Feature Importance
            </div>
            <div class="xai-subtitle">품질에 영향을 미치는 주요 변수 (상위 ${topFeatures.length}개)</div>
          </div>
          <div class="xai-bars">${barsHtml}</div>
        </div>
      `;
    }

    function renderEquipmentDescriptions(topFeatures) {
      if (!topFeatures || !topFeatures.length) return '';
      
      // Get unique equipment from top 5 features
      const seenEquipment = new Set();
      const equipmentList = [];
      
      topFeatures.slice(0, 5).forEach(([featureName]) => {
        const eqKey = FEATURE_TO_EQUIPMENT[featureName];
        if (eqKey && !seenEquipment.has(eqKey)) {
          seenEquipment.add(eqKey);
          const eq = EQUIPMENT_MAP[eqKey];
          if (eq) {
            equipmentList.push({ ...eq, featureName });
          }
        }
      });

      if (!equipmentList.length) return '';

      let html = `
        <div class="equipment-section">
          <div class="equipment-section-title">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="2" y="4" width="12" height="8" rx="1.5" stroke="currentColor" stroke-width="1.3"/><path d="M5 4V3M11 4V3" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg>
            관련 장비 및 조치 가이드
          </div>
          <div class="equipment-cards">
      `;

      equipmentList.forEach(eq => {
        html += `
          <div class="equipment-card">
            <div class="equipment-card-header">
              <div class="equipment-icon">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 2L2 5v6l6 3 6-3V5L8 2z" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/></svg>
              </div>
              <div>
                <div class="equipment-name">${eq.name}</div>
                <div class="equipment-name-en">${eq.name_en}</div>
              </div>
            </div>
            <div class="equipment-desc">${eq.description}</div>
            <div class="equipment-action">
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M8 3v10M3 8h10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
              ${eq.action}
            </div>
          </div>
        `;
      });

      html += '</div></div>';
      return html;
    }

    function renderKbAnswer(t3Data) {
      const answer = renderMarkdown(t3Data.answer || '');
      const sources = t3Data.sources || [];
      
      let sourcesHtml = '';
      if (sources.length) {
        sourcesHtml = `
          <div class="rag-sources">
            <div class="rag-sources-title">
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M4 2h8a1 1 0 011 1v10a1 1 0 01-1 1H4a1 1 0 01-1-1V3a1 1 0 011-1z" stroke="currentColor" stroke-width="1.2"/><path d="M6 5h4M6 8h4M6 11h2" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>
              참고 문서
            </div>
        `;
        sources.forEach(src => {
          const title = src.title || src.uri || '문서';
          const type = src.type || 'Knowledge Base';
          sourcesHtml += `
            <div class="rag-source-item">
              <div class="rag-source-icon">
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M4 2h8a1 1 0 011 1v10a1 1 0 01-1 1H4a1 1 0 01-1-1V3a1 1 0 011-1z" stroke="currentColor" stroke-width="1.2"/></svg>
              </div>
              <div class="rag-source-info">
                <div class="rag-source-name">${escapeHtml(title)}</div>
                <div class="rag-source-type">${escapeHtml(type)}</div>
              </div>
            </div>
          `;
        });
        sourcesHtml += '</div>';
      }

      return `
        <div class="rag-answer">
          <div class="rag-answer-text">${answer}</div>
          ${sourcesHtml}
        </div>
      `;
    }

    // ========== SEND MESSAGE ==========
    let isSending = false;

    async function sendMessage() {
      if (isSending) return;
      const input = document.getElementById('chatInput');
      const text = input.value.trim();
      if (!text) return;

      isSending = true;

      // Remove empty state
      const empty = document.getElementById('chatEmpty');
      if (empty) empty.remove();

      const msgs = document.getElementById('chatMessages');

      // User message
      const userMsg = document.createElement('div');
      userMsg.className = 'msg user';
      userMsg.innerHTML = `<div class="msg-bubble">${escapeHtml(text)}</div>`;
      msgs.appendChild(userMsg);

      // Clear input
      input.value = '';
      input.style.height = 'auto';
      toggleSend();
      scrollToBottom();

      // Backend Agent SSE 호출
      try {
        await handleBackendAgentSSE(text, msgs);
      } catch (err) {
        removeLoading();
        const errMsg = document.createElement('div');
        errMsg.className = 'msg ai';
        errMsg.innerHTML = `
          <div class="msg-header"><span class="ai-badge">AI</span><span class="ai-label">Assistant</span></div>
          <div class="msg-text" style="color: var(--status-bad);">요청 처리 중 오류가 발생했습니다.<br />${escapeHtml(err.message)}</div>
        `;
        msgs.appendChild(errMsg);
        scrollToBottom();
      }

      isSending = false;
    }

    // ========== BACKEND AGENT SSE HANDLER (Enhanced) ==========
    // 메시지별 고유 ID 생성
    let messageIdCounter = 0;
    let currentMsgId = null;
    let renderedCards = {}; // 메시지별 렌더링된 카드 추적
    let renderTimers = {}; // 렌더링 타이머 (debounce용)

    async function handleBackendAgentSSE(question, container) {
      // 고유 메시지 ID 생성
      currentMsgId = `msg_${Date.now()}_${++messageIdCounter}`;
      renderedCards[currentMsgId] = { t1: false, t2: false, t3: false };
      renderTimers[currentMsgId] = { t1: null, t2: null, t3: null };

      // 실시간 AI 메시지 컨테이너 생성
      const aiMsgDiv = document.createElement('div');
      aiMsgDiv.className = 'msg ai';
      aiMsgDiv.id = `aiLiveMessage_${currentMsgId}`;
      aiMsgDiv.innerHTML = `
        <div class="msg-header">
          <span class="ai-badge">AI</span>
          <span class="ai-label">Assistant</span>
          <span class="live-indicator" id="liveIndicator_${currentMsgId}"><span class="live-dot"></span>LIVE</span>
        </div>
        <div id="agentStepsContainer_${currentMsgId}"></div>
        <div id="aiResponseContainer_${currentMsgId}"></div>
      `;
      container.appendChild(aiMsgDiv);
      scrollToBottom();

      // Step Indicator 초기화
      const stepsContainer = document.getElementById(`agentStepsContainer_${currentMsgId}`);
      if (stepsContainer) {
        stepsContainer.innerHTML = createStepIndicator(currentMsgId);
      }

      let t1Result = null;
      let t2Result = null;
      let t3Result = null;
      let aiSummary = '';
      let startTime = Date.now();
      const msgId = currentMsgId;  // 클로저용 로컬 복사
      
      // 세션 ID 가져오기 또는 생성
      let sessionId = localStorage.getItem('diecasting_session_id');
      if (!sessionId) {
        sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        localStorage.setItem('diecasting_session_id', sessionId);
      }

      try {
        const response = await fetch(BACKEND_CHAT, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            question: question,
            features: currentFeatures,
            session_id: sessionId
          })
        });

        if (!response.ok) {
          throw new Error(`Backend Agent 오류: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
                console.log('📨 SSE Event:', data.type, data);

                if (data.type === 'status') {
                  updateStepStatus(data.message, elapsed, msgId);
                } else if (data.type === 'thinking') {
                  console.log('🤔 Thinking event received');
                  updateStep('thinking', 'active', data.message, msgId);
                } else if (data.type === 'tool_start') {
                  // Tool 호출 시작
                  console.log('🔧 Tool Start:', data.tool);
                  handleToolStart(data.tool, data.input, elapsed, msgId);
                } else if (data.type === 'tool_end') {
                  // Tool 호출 완료
                  console.log('✅ Tool End:', data.tool);
                  handleToolEnd(data.tool, data.result, elapsed, msgId);
                } else if (data.type === 't1_result') {
                  t1Result = data.data;
                  lastT1Result = t1Result;
                  updateStep('predict', 'completed', '품질 예측 완료', msgId);
                  renderLiveT1Result(t1Result, msgId);
                } else if (data.type === 't2_result') {
                  console.log('📊 Received t2_result, already rendered:', renderedCards[msgId]?.t2);
                  
                  // 중복 렌더링 방지
                  if (renderedCards[msgId]?.t2) {
                    console.log('⚠️ T2 already rendered, skipping');
                  } else {
                    t2Result = data.data;
                    updateStep('analyze', 'completed', 'Feature Importance 분석 완료', msgId);
                    renderLiveT2Result(t2Result, msgId);
                  }
                } else if (data.type === 't3_result') {
                  t3Result = data.data;
                  updateStep('search', 'completed', 'Knowledge Base 검색 완료', msgId);
                  renderLiveT3Result(t3Result, msgId);
                } else if (data.type === 'ai_response') {
                  aiSummary = data.data?.answer || '';
                  renderLiveAIResponse(aiSummary, msgId);
                } else if (data.type === 'done') {
                  console.log('✅ SSE Stream completed');
                  finalizeLiveResponse(t1Result, t2Result, t3Result, aiSummary, elapsed, msgId);
                  reader.cancel(); // 스트림 명시적 종료
                  return; // 함수 종료
                } else if (data.type === 'error') {
                  handleSSEError(data.message, msgId);
                  throw new Error(data.message);
                }

                scrollToBottom();
              } catch (parseErr) {
                if (parseErr.message && !parseErr.message.includes('JSON')) {
                  throw parseErr;
                }
                console.warn('SSE 파싱 오류:', parseErr);
              }
            }
          }
        }
      } catch (err) {
        console.error('Backend Agent SSE 오류:', err);

        // 이미 결과가 렌더링되었으면 fallback 실행하지 않음
        if (renderedCards[currentMsgId]?.t1 || renderedCards[currentMsgId]?.t2 || renderedCards[currentMsgId]?.t3) {
          console.log('⚠️ SSE 연결 끊김, 하지만 이미 결과가 렌더링되어 fallback 건너뜀');
          return;
        }

        // Fallback: 기존 방식으로 처리
        console.log('Fallback: 기존 Lambda 직접 호출 방식 사용');
        const aiLiveMsg = document.getElementById(`aiLiveMessage_${currentMsgId}`);
        if (aiLiveMsg) aiLiveMsg.remove();
        
        const intent = classifyIntent(question);
        if (intent === 'prediction' || intent === 'xai') {
          await handlePrediction(question, container);
        } else {
          await handleKnowledge(question, container);
        }
      }
    }

    // ========== DYNAMIC STEP INDICATOR FUNCTIONS ==========
    // Tool 정보 매핑
    const TOOL_INFO = {
      'predict_quality': {
        id: 'predict',
        title: '품질 예측 (Lambda T1)',
        desc: 'ML 모델로 품질을 예측합니다',
        icon: '<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M8 2v4M8 10v4M2 8h4M10 8h4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>'
      },
      'analyze_feature_importance': {
        id: 'analyze',
        title: '원인 분석 (Lambda T2)',
        desc: 'Feature Importance를 분석합니다',
        icon: '<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M2 12h2V6H2v6zm4 0h2V4H6v8zm4 0h2V8h-2v4zm4 0h2V2h-2v10z" fill="currentColor"/></svg>'
      },
      'search_knowledge_base': {
        id: 'search',
        title: '지식 검색 (Lambda T3)',
        desc: 'Knowledge Base에서 관련 문서를 검색합니다',
        icon: '<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="7" cy="7" r="4" stroke="currentColor" stroke-width="1.5"/><path d="M10 10l3 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>'
      }
    };

    // 초기 Step Indicator (AI 분석 단계만)
    function createStepIndicator(msgId) {
      return `
        <div class="agent-steps" id="agentSteps_${msgId}">
          <div class="agent-step active" id="step-thinking_${msgId}">
            <div class="step-icon">
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.5"/><path d="M8 5v3l2 2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
            </div>
            <div class="step-content">
              <div class="step-title">🤖 AI 의도 분석</div>
              <div class="step-desc">질문을 분석하고 적절한 Lambda를 선택합니다...</div>
            </div>
          </div>
        </div>
      `;
    }

    // Tool 단계를 동적으로 추가
    function addToolStep(toolName, input, elapsed, msgId) {
      const toolInfo = TOOL_INFO[toolName];
      if (!toolInfo) return;

      const stepsContainer = document.getElementById(`agentSteps_${msgId}`);
      if (!stepsContainer) return;

      // 이미 존재하면 업데이트만
      const existingStep = document.getElementById(`step-${toolInfo.id}_${msgId}`);
      if (existingStep) {
        existingStep.className = 'agent-step active';
        return;
      }

      // 입력 파라미터 요약
      let inputSummary = '';
      if (toolName === 'predict_quality') {
        inputSummary = `<div class="tool-input">📊 공정 파라미터 ${Object.keys(input.features || {}).length}개 전송</div>`;
      } else if (toolName === 'analyze_feature_importance') {
        inputSummary = `<div class="tool-input">🔍 Latent Features 24개 분석</div>`;
      } else if (toolName === 'search_knowledge_base') {
        inputSummary = `<div class="tool-input">🔎 검색어: "${input.query}"</div>`;
      }

      const stepHtml = `
        <div class="agent-step active" id="step-${toolInfo.id}_${msgId}">
          <div class="step-icon">${toolInfo.icon}</div>
          <div class="step-content">
            <div class="step-title">${toolInfo.title}</div>
            <div class="step-desc">${toolInfo.desc}</div>
            ${inputSummary}
            <div class="step-result" id="step-${toolInfo.id}-result_${msgId}">
              <span class="tool-badge">⏳ 실행 중...</span> <span class="step-time">${elapsed}s</span>
            </div>
          </div>
        </div>
      `;

      // 응답 생성 단계 전에 삽입
      const responseStep = document.getElementById(`step-response_${msgId}`);
      if (responseStep) {
        responseStep.insertAdjacentHTML('beforebegin', stepHtml);
      } else {
        stepsContainer.insertAdjacentHTML('beforeend', stepHtml);
      }
    }

    // 응답 생성 단계 추가
    function addResponseStep(msgId) {
      const stepsContainer = document.getElementById(`agentSteps_${msgId}`);
      if (!stepsContainer || document.getElementById(`step-response_${msgId}`)) return;

      const stepHtml = `
        <div class="agent-step active" id="step-response_${msgId}">
          <div class="step-icon">
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M3 4h10M3 8h6M3 12h8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          </div>
          <div class="step-content">
            <div class="step-title">✨ 응답 생성</div>
            <div class="step-desc">분석 결과를 종합하여 답변을 생성합니다</div>
          </div>
        </div>
      `;
      stepsContainer.insertAdjacentHTML('beforeend', stepHtml);
    }

    function updateStep(stepId, status, message, msgId) {
      const step = document.getElementById(`step-${stepId}_${msgId}`);
      if (!step) return;

      // 상태 업데이트
      step.className = `agent-step ${status}`;

      // 설명 업데이트
      const desc = step.querySelector('.step-desc');
      if (desc && message) desc.textContent = message;

      // 아이콘 업데이트
      const icon = step.querySelector('.step-icon');
      if (icon && status === 'completed') {
        icon.innerHTML = '<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M4 8l3 3 5-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
      } else if (icon && status === 'error') {
        icon.innerHTML = '<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M5 5l6 6M11 5l-6 6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>';
      }
    }

    function updateStepStatus(message, elapsed, msgId) {
      // AI 분석 단계 업데이트
      const thinkingStep = document.getElementById(`step-thinking_${msgId}`);
      if (thinkingStep) {
        const desc = thinkingStep.querySelector('.step-desc');
        if (desc) desc.textContent = message;
      }
    }

    // Tool 시작 핸들러
    function handleToolStart(toolName, input, elapsed, msgId) {
      console.log(`🔧 Tool Start: ${toolName}`, input);
      
      // AI 분석 단계 완료 처리
      updateStep('thinking', 'completed', `${toolName} 호출 결정`, msgId);
      
      // Tool 단계 추가
      addToolStep(toolName, input, elapsed, msgId);
    }

    // Tool 완료 핸들러
    function handleToolEnd(toolName, result, elapsed, msgId) {
      console.log(`✅ Tool End: ${toolName}`, result);
      
      const toolInfo = TOOL_INFO[toolName];
      if (!toolInfo) return;

      // Tool 단계 완료 처리
      updateStep(toolInfo.id, 'completed', `${toolInfo.title} 완료`, msgId);
      
      // 결과 요약 업데이트
      const resultDiv = document.getElementById(`step-${toolInfo.id}-result_${msgId}`);
      if (resultDiv) {
        let resultSummary = '';
        if (toolName === 'predict_quality') {
          const pred = result.prediction || {};
          const probPercent = pred.probability_percent || `${(pred.probability * 100).toFixed(1)}%`;
          resultSummary = `<span class="tool-badge">✅ 완료</span> <span class="step-time">${elapsed}s</span><br/><span class="result-summary">${pred.class === 'defect' ? '불량' : '양품'} 확률 ${probPercent}</span>`;
        } else if (toolName === 'analyze_feature_importance') {
          const topN = (result.top_features || []).length;
          resultSummary = `<span class="tool-badge">✅ 완료</span> <span class="step-time">${elapsed}s</span><br/><span class="result-summary">상위 ${topN}개 변수 분석</span>`;
        } else if (toolName === 'search_knowledge_base') {
          const sources = (result.sources || []).length;
          resultSummary = `<span class="tool-badge">✅ 완료</span> <span class="step-time">${elapsed}s</span><br/><span class="result-summary">${sources}개 문서 검색</span>`;
        }
        resultDiv.innerHTML = resultSummary;
      }
      
      // 응답 생성 단계 추가 (마지막 tool 완료 후)
      addResponseStep(msgId);
    }

    function getToolDisplayName(toolName) {
      const toolInfo = TOOL_INFO[toolName];
      return toolInfo ? toolInfo.title : toolName;
    }

    // ========== LIVE RENDERING FUNCTIONS ==========
    function renderLiveT1Result(t1Result, msgId) {
      const container = document.getElementById(`aiResponseContainer_${msgId}`);
      if (!container || !t1Result) return;

      // 전역 중복 체크
      if (renderedCards[msgId]?.t1) {
        console.log('T1 already rendered for', msgId);
        return;
      }

      // 이미 예측 카드가 있으면 업데이트하지 않음 (중복 방지)
      const existingPred = container.querySelector('.prediction-card');
      if (existingPred) {
        console.log('Prediction card already exists, skipping duplicate render');
        return;
      }

      // 데이터 구조 확인 - prediction이 직접 있거나 중첩되어 있을 수 있음
      console.log('t1Result:', JSON.stringify(t1Result, null, 2));
      const prediction = t1Result.prediction || t1Result;

      const predHtml = renderPredictionCard(prediction);
      container.insertAdjacentHTML('beforeend', predHtml);
      
      // 렌더링 완료 표시
      if (renderedCards[msgId]) {
        renderedCards[msgId].t1 = true;
      }
    }

    function renderLiveT2Result(t2Result, msgId) {
      console.log('🔍 renderLiveT2Result called for', msgId, 'already rendered:', renderedCards[msgId]?.t2);
      
      const container = document.getElementById(`aiResponseContainer_${msgId}`);
      if (!container || !t2Result) {
        console.log('❌ Container not found or no t2Result');
        return;
      }

      // 전역 중복 체크 - 가장 먼저 확인
      if (renderedCards[msgId]?.t2) {
        console.log('⛔ T2 already rendered for', msgId, '- BLOCKING');
        return;
      }

      // DOM 중복 체크
      const existingXai = container.querySelector('.xai-card');
      if (existingXai) {
        console.log('⛔ XAI card already exists in DOM - BLOCKING');
        renderedCards[msgId].t2 = true; // 플래그 설정
        return;
      }

      console.log('✅ Rendering T2 for', msgId);
      const xaiHtml = renderXaiCard(t2Result);
      container.insertAdjacentHTML('beforeend', xaiHtml);
      
      // 렌더링 완료 표시 - 즉시 설정
      if (renderedCards[msgId]) {
        renderedCards[msgId].t2 = true;
        console.log('✅ T2 rendered flag set for', msgId);
      }

      // Equipment descriptions
      const topFeatures = t2Result.top_features || [];
      const eqHtml = renderEquipmentDescriptions(topFeatures);
      if (eqHtml) {
        const existingEq = container.querySelector('.equipment-section');
        if (!existingEq) {
          container.insertAdjacentHTML('beforeend', eqHtml);
        }
      }
    }

    function renderLiveT3Result(t3Result, msgId) {
      // KB 검색 결과는 인사이트 패널에만 표시하고 채팅에는 표시하지 않음
      // LLM이 요약한 답변만 채팅에 표시됨
      return;
    }

    function renderLiveAIResponse(aiSummary, msgId) {
      if (!aiSummary) return;

      // 응답 생성 단계 추가
      addResponseStep(msgId);
      updateStep('response', 'active', '응답 생성 중...', msgId);

      const container = document.getElementById(`aiResponseContainer_${msgId}`);
      if (!container) return;

      // AI Summary를 맨 앞에 추가 (마크다운 렌더링 강제 적용)
      const renderedSummary = renderMarkdown(aiSummary);
      const existingSummary = container.querySelector('.ai-summary');
      if (existingSummary) {
        existingSummary.innerHTML = renderedSummary;
      } else {
        const summaryHtml = `<div class="ai-summary msg-text" style="margin-bottom: 16px; padding: 12px; background: rgba(56, 189, 248, 0.08); border-radius: 10px; border-left: 3px solid var(--accent);">${renderedSummary}</div>`;
        container.insertAdjacentHTML('afterbegin', summaryHtml);
      }
    }

    function finalizeLiveResponse(t1Result, t2Result, t3Result, aiSummary, elapsed, msgId) {
      // LIVE 인디케이터를 완료 상태로 변경
      const liveIndicator = document.getElementById(`liveIndicator_${msgId}`);
      if (liveIndicator) {
        liveIndicator.innerHTML = `<svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M4 8l3 3 5-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg> 완료 (${elapsed}s)`;
        liveIndicator.style.background = 'rgba(34, 197, 94, 0.1)';
        liveIndicator.style.borderColor = 'rgba(34, 197, 94, 0.3)';
      }

      // 응답 생성 단계가 있으면 완료 처리
      if (document.getElementById(`step-response_${msgId}`)) {
        updateStep('response', 'completed', '응답 생성 완료', msgId);
      }

      // Step indicator 숨기기
      const stepsContainer = document.getElementById(`agentSteps_${msgId}`);
      if (stepsContainer) {
        stepsContainer.style.display = 'none';
      }

      // 인사이트 패널 업데이트 - 실제 백엔드 데이터 기반
      updateInsightPanel(t1Result, t2Result, t3Result);
    }
    
    function updateInsightPanel(t1Result, t2Result, t3Result) {
      const insightPanel = document.getElementById('insightPanel');
      const insightEmpty = document.getElementById('insightEmpty');
      const insightContent = document.getElementById('insightContent');
      
      if (!insightPanel || !insightEmpty || !insightContent) return;
      
      // 패널 열기
      if (insightPanel.classList.contains('collapsed')) {
        insightPanel.classList.remove('collapsed');
      }
      
      insightEmpty.style.display = 'none';
      insightContent.style.display = 'flex';
      insightContent.innerHTML = '';
      
      // T1 결과: 불량률 예측
      if (t1Result && t1Result.prediction) {
        const pred = t1Result.prediction;
        const isDefect = pred.class === 'defect';
        const probability = pred.probability_percent || `${(pred.probability * 100).toFixed(1)}%`;
        
        insightContent.innerHTML += `
          <div class="insight-section" style="animation: slideInRight 0.4s ease">
            <div class="insight-section-title">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M2 14L8 2L14 14H2Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
              </svg>
              품질 예측
            </div>
            <div style="font-size: 32px; font-weight: 700; color: ${isDefect ? 'var(--status-bad)' : 'var(--status-good)'}; margin: 12px 0;">
              ${isDefect ? '불량' : '양품'}
            </div>
            <div style="font-size: 15px; color: var(--text-secondary); margin-bottom: 8px;">
              확률: ${probability}
            </div>
            <div style="font-size: 13px; color: var(--text-muted);">
              현재 공정 조건 기준
            </div>
          </div>
        `;
      }
      
      // T2 결과: Feature Importance
      if (t2Result && t2Result.top_features && t2Result.top_features.length > 0) {
        const topFeatures = t2Result.top_features.slice(0, 5);
        const maxVal = topFeatures[0][1];
        
        const bars = topFeatures.map(([name, val]) => {
          const label = FEATURE_LABELS[name] || name;
          const importance = ((val / maxVal) * 100).toFixed(0);
          return `
            <div style="margin-bottom: 10px;">
              <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                <span style="font-size: 13px; color: var(--text-secondary);">${label}</span>
                <span style="font-size: 13px; font-weight: 600; color: var(--accent);">${importance}%</span>
              </div>
              <div style="height: 6px; background: var(--bg-base); border-radius: 3px; overflow: hidden;">
                <div style="height: 100%; width: ${importance}%; background: linear-gradient(90deg, var(--accent), var(--accent-hover)); transition: width 0.6s ease;"></div>
              </div>
            </div>
          `;
        }).join('');
        
        insightContent.innerHTML += `
          <div class="insight-section" style="animation: slideInRight 0.5s ease">
            <div class="insight-section-title">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <rect x="2" y="10" width="3" height="4" stroke="currentColor" stroke-width="1.5"/>
                <rect x="6.5" y="6" width="3" height="8" stroke="currentColor" stroke-width="1.5"/>
                <rect x="11" y="2" width="3" height="12" stroke="currentColor" stroke-width="1.5"/>
              </svg>
              주요 영향 요인 (상위 5개)
            </div>
            ${bars}
          </div>
        `;
      }
      
      // T3 결과: Knowledge Base 검색
      if (t3Result && t3Result.sources && t3Result.sources.length > 0) {
        const sources = t3Result.sources.slice(0, 3);
        const sourcesList = sources.map(s => `
          <div style="padding: 8px 0; border-bottom: 1px solid var(--border-default);">
            <div style="font-size: 14px; color: var(--text-primary); font-weight: 500; margin-bottom: 4px;">
              ${escapeHtml(s.title || '문서')}
            </div>
            <div style="font-size: 12px; color: var(--text-muted);">
              ${escapeHtml((s.content || '').substring(0, 80))}...
            </div>
          </div>
        `).join('');
        
        insightContent.innerHTML += `
          <div class="insight-section" style="animation: slideInRight 0.6s ease">
            <div class="insight-section-title">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M4 2h8a1 1 0 011 1v10a1 1 0 01-1 1H4a1 1 0 01-1-1V3a1 1 0 011-1z" stroke="currentColor" stroke-width="1.5"/>
                <path d="M6 5h4M6 8h4M6 11h2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
              </svg>
              참조 문서 (${t3Result.sources.length}개)
            </div>
            ${sourcesList}
          </div>
        `;
      }
    }

    function handleSSEError(message, msgId) {
      const stepsContainer = document.getElementById(`agentSteps_${msgId}`);
      if (stepsContainer) {
        // 현재 active인 step을 error로 변경
        const activeStep = stepsContainer.querySelector('.agent-step.active');
        if (activeStep) {
          activeStep.className = 'agent-step error';
          const desc = activeStep.querySelector('.step-desc');
          if (desc) desc.textContent = `오류: ${message}`;
        }
      }

      const liveIndicator = document.getElementById(`liveIndicator_${msgId}`);
      if (liveIndicator) {
        liveIndicator.innerHTML = '오류 발생';
        liveIndicator.style.background = 'rgba(239, 68, 68, 0.1)';
        liveIndicator.style.borderColor = 'rgba(239, 68, 68, 0.3)';
        liveIndicator.style.color = 'var(--status-bad)';
      }
    }

    function renderAgentResponse(container, t1Result, t2Result, t3Result, question, aiSummary = '') {
      const aiMsg = document.createElement('div');
      aiMsg.className = 'msg ai';
      
      let contentHtml = '';
      
      // AI 요약이 있으면 먼저 표시 (마크다운 렌더링 적용)
      const summaryHtml = aiSummary ? `<div class="msg-text" style="margin-bottom: 16px; padding: 12px; background: rgba(56, 189, 248, 0.08); border-radius: 10px; border-left: 3px solid var(--accent);">${renderMarkdown(aiSummary)}</div>` : '';
      
      if (t1Result && t2Result) {
        // Prediction + XAI
        const prediction = t1Result.prediction || t1Result;
        const predHtml = renderPredictionCard(prediction);
        const xaiHtml = renderXaiCard(t2Result);
        const topFeatures = t2Result.top_features || [];
        const eqHtml = renderEquipmentDescriptions(topFeatures);
        
        contentHtml = `
          ${summaryHtml}
          <div class="msg-text">현재 공정 데이터를 기반으로 품질 예측 및 원인 분석을 수행했습니다.</div>
          ${predHtml}
          ${xaiHtml}
          ${eqHtml}
        `;
        
        // Update context panel
        const equipmentNames = [...new Set(topFeatures.slice(0, 5).map(([f]) => {
          const eqKey = FEATURE_TO_EQUIPMENT[f];
          return eqKey ? EQUIPMENT_MAP[eqKey]?.name : null;
        }).filter(Boolean))];
        updateContextPanel({ equipment: equipmentNames, sensors: topFeatures.slice(0, 5).map(([f]) => f) });
        
      } else if (t1Result) {
        // Prediction only
        const prediction = t1Result.prediction || t1Result;
        const predHtml = renderPredictionCard(prediction);
        contentHtml = `
          ${summaryHtml}
          <div class="msg-text">현재 공정 데이터를 기반으로 품질 예측을 수행했습니다.</div>
          ${predHtml}
        `;
        
      } else if (t3Result) {
        // Knowledge (RAG)
        const ragHtml = renderKbAnswer(t3Result);
        contentHtml = summaryHtml + ragHtml;
        
        // Update context panel with sources
        if (t3Result.sources && t3Result.sources.length) {
          updateContextPanel({ sources: t3Result.sources });
        }
      } else {
        contentHtml = '<div class="msg-text">응답을 처리할 수 없습니다.</div>';
      }
      
      aiMsg.innerHTML = `
        <div class="msg-header"><span class="ai-badge">AI</span><span class="ai-label">Assistant</span></div>
        ${contentHtml}
      `;
      container.appendChild(aiMsg);
      scrollToBottom();
    }

    // ========== INTENT HANDLERS (Fallback) ==========
    async function handlePrediction(question, container) {
      // Step 1: Call T1
      showLoading(container, '예측 모델 호출 중...');
      const t1Data = await callLambdaT1(currentFeatures);
      lastT1Result = t1Data;

      // Step 2: Chain to T2
      updateLoadingStatus('Feature Importance 분석 중...');
      const latent = t1Data.latent_features || [];
      const t2Data = await callLambdaT2(currentFeatures, latent);

      removeLoading();

      // Render AI message
      const aiMsg = document.createElement('div');
      aiMsg.className = 'msg ai';

      const prediction = t1Data.prediction || t1Data;
      const predHtml = renderPredictionCard(prediction);
      const xaiHtml = renderXaiCard(t2Data);
      const topFeatures = t2Data.top_features || [];
      const eqHtml = renderEquipmentDescriptions(topFeatures);

      aiMsg.innerHTML = `
        <div class="msg-header"><span class="ai-badge">AI</span><span class="ai-label">Assistant</span></div>
        <div class="msg-text">현재 공정 데이터를 기반으로 품질 예측 및 원인 분석을 수행했습니다.</div>
        ${predHtml}
        ${xaiHtml}
        ${eqHtml}
      `;
      container.appendChild(aiMsg);
      scrollToBottom();

      // Update context panel
      const equipmentNames = [...new Set(topFeatures.slice(0, 5).map(([f]) => {
        const eqKey = FEATURE_TO_EQUIPMENT[f];
        return eqKey ? EQUIPMENT_MAP[eqKey]?.name : null;
      }).filter(Boolean))];
      
      const sensorNames = topFeatures.slice(0, 5)
        .filter(([f]) => f.startsWith('Sensor_'))
        .map(([f]) => SENSOR_INFO[f]?.name || FEATURE_LABELS[f]);

      updateContextPanel({
        equipment: equipmentNames,
        sensors: sensorNames.length ? sensorNames : Object.keys(currentFeatures).filter(k => k.startsWith('Sensor_')).slice(0, 5).map(k => FEATURE_LABELS[k])
      });
    }

    async function handleXAI(question, container) {
      showLoading(container, 'Feature Importance 분석 중...');
      const latent = lastT1Result ? (lastT1Result.latent_features || []) : [];
      const t2Data = await callLambdaT2(currentFeatures, latent);

      removeLoading();

      const aiMsg = document.createElement('div');
      aiMsg.className = 'msg ai';

      const xaiHtml = renderXaiCard(t2Data);
      const topFeatures = t2Data.top_features || [];
      const eqHtml = renderEquipmentDescriptions(topFeatures);

      aiMsg.innerHTML = `
        <div class="msg-header"><span class="ai-badge">AI</span><span class="ai-label">Assistant</span></div>
        <div class="msg-text">공정 변수별 품질 영향도를 분석했습니다. 상위 변수들이 품질에 가장 큰 영향을 미칩니다.</div>
        ${xaiHtml}
        ${eqHtml}
      `;
      container.appendChild(aiMsg);
      scrollToBottom();

      const equipmentNames = [...new Set(topFeatures.slice(0, 5).map(([f]) => {
        const eqKey = FEATURE_TO_EQUIPMENT[f];
        return eqKey ? EQUIPMENT_MAP[eqKey]?.name : null;
      }).filter(Boolean))];
      
      const sensorNames = topFeatures.slice(0, 5)
        .filter(([f]) => f.startsWith('Sensor_'))
        .map(([f]) => SENSOR_INFO[f]?.name || FEATURE_LABELS[f]);

      updateContextPanel({
        equipment: equipmentNames,
        sensors: sensorNames
      });
    }

    async function handleKnowledge(question, container) {
      showLoading(container, 'Knowledge Base 검색 중...');
      const t3Data = await callLambdaT3(question);

      removeLoading();

      const aiMsg = document.createElement('div');
      aiMsg.className = 'msg ai';

      // 마크다운 렌더링 강제 적용
      const answer = renderMarkdown(t3Data.answer || '응답을 받을 수 없습니다.');
      const sources = t3Data.sources || [];
      
      let sourcesHtml = '';
      if (sources.length) {
        sourcesHtml = `
          <div class="rag-sources">
            <div class="rag-sources-title">
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M4 2h8a1 1 0 011 1v10a1 1 0 01-1 1H4a1 1 0 01-1-1V3a1 1 0 011-1z" stroke="currentColor" stroke-width="1.2"/><path d="M6 5h4M6 8h4M6 11h2" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>
              참고 문서
            </div>
        `;
        sources.forEach(src => {
          const title = src.title || src.uri || '문서';
          const type = src.type || 'Knowledge Base';
          sourcesHtml += `
            <div class="rag-source-item">
              <div class="rag-source-icon">
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M4 2h8a1 1 0 011 1v10a1 1 0 01-1 1H4a1 1 0 01-1-1V3a1 1 0 011-1z" stroke="currentColor" stroke-width="1.2"/></svg>
              </div>
              <div class="rag-source-info">
                <div class="rag-source-name">${escapeHtml(title)}</div>
                <div class="rag-source-type">${escapeHtml(type)}</div>
              </div>
            </div>
          `;
        });
        sourcesHtml += '</div>';
      }

      aiMsg.innerHTML = `
        <div class="msg-header"><span class="ai-badge">AI</span><span class="ai-label">Assistant</span></div>
        <div class="rag-answer">
          <div class="rag-answer-text">${answer}</div>
          ${sourcesHtml}
        </div>
      `;
      container.appendChild(aiMsg);
      scrollToBottom();

      // Update context with sources
      const sourceNames = (t3Data.sources || []).map(s => s.title || s.uri || '문서');
      updateContextPanel({ sources: sourceNames });
    }

    // ========== CONTEXT PANEL ==========
    function updateContextPanel(data) {
      const panel = document.getElementById('insightPanel');
      if (!panel) {
        console.warn('Insight panel not found');
        return;
      }
      
      if (!data) {
        panel.innerHTML = `
          <div class="insight-empty" id="insightEmpty">
            <div class="insight-empty-icon">📊</div>
            <p>질문하면 관련 인사이트가<br/>여기에 표시됩니다</p>
          </div>
          <div class="insight-content" id="insightContent" style="display: none;"></div>
        `;
        return;
      }

      let html = '<div class="insight-content" id="insightContent" style="display: flex;">';

      html += '<div class="insight-section"><div class="insight-section-title">Sources</div>';
      if (data.sources && data.sources.length) {
        data.sources.forEach(s => {
          html += `<div class="ctx-item"><svg viewBox="0 0 16 16" fill="none"><path d="M4 2h8a1 1 0 011 1v10a1 1 0 01-1 1H4a1 1 0 01-1-1V3a1 1 0 011-1z" stroke="currentColor" stroke-width="1.2"/><path d="M6 5h4M6 8h4M6 11h2" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>${escapeHtml(s)}</div>`;
        });
      } else {
        html += '<div class="ctx-empty">참조 문서 없음</div>';
      }
      html += '</div>';

      html += '<div class="insight-section"><div class="insight-section-title">Equipment</div>';
      if (data.equipment && data.equipment.length) {
        data.equipment.forEach(e => {
          html += `<div class="ctx-item"><svg viewBox="0 0 16 16" fill="none"><rect x="2" y="4" width="12" height="8" rx="1.5" stroke="currentColor" stroke-width="1.2"/><path d="M5 4V3M11 4V3" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>${escapeHtml(e)}</div>`;
        });
      } else {
        html += '<div class="ctx-empty">관련 장비 정보 없음</div>';
      }
      html += '</div>';

      html += '<div class="insight-section"><div class="insight-section-title">Sensors</div>';
      if (data.sensors && data.sensors.length) {
        data.sensors.forEach(s => {
          html += `<div class="ctx-item"><svg viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="5.5" stroke="currentColor" stroke-width="1.2"/><path d="M8 5v3l2 1.5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>${escapeHtml(s)}</div>`;
        });
      } else {
        html += '<div class="ctx-empty">관련 센서 정보 없음</div>';
      }
      html += '</div>';
      html += '</div>';

      panel.innerHTML = html;
    }

    // ========== KB UPDATE FUNCTIONS ==========
    let kbPollingInterval = null;
    let currentJobId = null;

    function openKBUpdateModal() {
      document.getElementById('kbModal').classList.add('open');
      // 최근 Job 상태 조회
      checkRecentKBJobs();
    }

    function closeKBUpdateModal() {
      document.getElementById('kbModal').classList.remove('open');
      if (kbPollingInterval) {
        clearInterval(kbPollingInterval);
        kbPollingInterval = null;
      }
    }

    async function checkRecentKBJobs() {
      try {
        const res = await fetch(BACKEND_KB_INGEST, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'list_jobs' })
        });
        const data = await res.json();
        
        if (data.jobs && data.jobs.length > 0) {
          const latestJob = data.jobs[0];
          updateKBStatusUI(latestJob);
          
          // 진행 중인 Job이 있으면 폴링 시작
          if (latestJob.status === 'IN_PROGRESS' || latestJob.status === 'STARTING') {
            currentJobId = latestJob.job_id;
            startKBPolling();
          }
        }
      } catch (err) {
        console.error('Failed to check KB jobs:', err);
      }
    }

    async function startKBIngest() {
      const btn = document.getElementById('kbStartBtn');
      btn.disabled = true;
      btn.textContent = '시작 중...';
      
      try {
        const res = await fetch(BACKEND_KB_INGEST, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'start_ingestion' })
        });
        const data = await res.json();
        
        if (data.error) {
          alert('인제스트 시작 실패: ' + data.error);
          btn.disabled = false;
          btn.textContent = '인제스트 시작';
          return;
        }
        
        currentJobId = data.job_id;
        updateKBStatusUI({
          job_id: data.job_id,
          status: data.status,
          started_at: data.started_at
        });
        
        // 폴링 시작
        startKBPolling();
        
      } catch (err) {
        console.error('Failed to start KB ingest:', err);
        alert('인제스트 시작 실패: ' + err.message);
        btn.disabled = false;
        btn.textContent = '인제스트 시작';
      }
    }

    function startKBPolling() {
      if (kbPollingInterval) clearInterval(kbPollingInterval);
      
      kbPollingInterval = setInterval(async () => {
        if (!currentJobId) return;
        
        try {
          const res = await fetch(BACKEND_KB_INGEST, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'check_status', job_id: currentJobId })
          });
          const data = await res.json();
          
          updateKBStatusUI(data);
          
          // 완료 또는 실패 시 폴링 중지
          if (data.status === 'COMPLETE' || data.status === 'FAILED') {
            clearInterval(kbPollingInterval);
            kbPollingInterval = null;
            
            const btn = document.getElementById('kbStartBtn');
            btn.disabled = false;
            btn.textContent = '인제스트 시작';
          }
        } catch (err) {
          console.error('Failed to check KB status:', err);
        }
      }, 5000); // 5초마다 폴링
    }

    function updateKBStatusUI(data) {
      const statusEl = document.getElementById('kbStatusValue');
      const jobIdEl = document.getElementById('kbJobId');
      const docsEl = document.getElementById('kbDocsCount');
      const lastUpdateEl = document.getElementById('kbLastUpdate');
      const btn = document.getElementById('kbStartBtn');
      
      // Status
      const statusMap = {
        'STARTING': { text: '시작 중...', class: 'running' },
        'IN_PROGRESS': { text: '진행 중...', class: 'running' },
        'COMPLETE': { text: '완료', class: 'complete' },
        'FAILED': { text: '실패', class: 'failed' }
      };
      const statusInfo = statusMap[data.status] || { text: data.status || '대기 중', class: '' };
      statusEl.textContent = statusInfo.text;
      statusEl.className = 'kb-status-value ' + statusInfo.class;
      
      // Job ID
      jobIdEl.textContent = data.job_id ? data.job_id.substring(0, 12) + '...' : '-';
      
      // Documents count
      if (data.statistics) {
        const stats = data.statistics;
        docsEl.textContent = `${stats.documents_indexed || 0} 인덱싱 / ${stats.documents_scanned || 0} 스캔`;
      } else {
        docsEl.textContent = '-';
      }
      
      // Last update
      if (data.updated_at || data.started_at) {
        const date = new Date(data.updated_at || data.started_at);
        lastUpdateEl.textContent = date.toLocaleString('ko-KR');
      }
      
      // Button state
      if (data.status === 'IN_PROGRESS' || data.status === 'STARTING') {
        btn.disabled = true;
        btn.textContent = '진행 중...';
      } else {
        btn.disabled = false;
        btn.textContent = '인제스트 시작';
      }
    }
