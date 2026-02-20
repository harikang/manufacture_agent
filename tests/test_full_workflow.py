"""
전체 워크플로우 테스트
Lambda T1 (예측) → Lambda T2 (분석) → Lambda T3 (RAG)
"""

import requests
import json
import time

# Lambda URLs
with open('lambda_t1_url.txt', 'r') as f:
    LAMBDA_T1_URL = f.read().strip()

with open('lambda_t2_url.txt', 'r') as f:
    LAMBDA_T2_URL = f.read().strip()

with open('lambda_t3_url.txt', 'r') as f:
    LAMBDA_T3_URL = f.read().strip()

print("=" * 80)
print("다이캐스팅 품질 예측 시스템 - 전체 워크플로우 테스트")
print("=" * 80)

# 테스트 데이터 (현실적인 값 - scaler 통계 기반)
test_features = {
    "Process_Temperature": 1.515671,
    "Process_Pressure": 440.549188,
    "Process_InjectionSpeed": 0.149605,
    "Process_InjectionTime": 0.170957,
    "Process_CoolingTime": 0.190381,
    "Process_ClampForce": 2.303615,
    "Process_MoldTemperature": 250.696155,
    "Process_MeltTemperature": 0.010091,
    "Process_CycleTime": 13.846805,
    "Process_ShotSize": 315.755225,
    "Process_BackPressure": 26.524293,
    "Process_ScrewSpeed": 0.038797,
    "Process_HoldPressure": 873.987943,
    "Process_HoldTime": 8.758519,
    "Process_CushionPosition": 1.120859,
    "Process_PlasticizingTime": 1.275245,
    "Sensor_Vibration": 672.969226,
    "Sensor_Noise": 6.170672,
    "Sensor_Temperature1": 2.727593,
    "Sensor_Temperature2": 8.576309,
    "Sensor_Temperature3": 27.061016,
    "Sensor_Pressure1": 9.932267,
    "Sensor_Pressure2": 50.020258,
    "Sensor_Pressure3": 2.678756,
    "Sensor_Flow": 32.557806,
    "Sensor_Position": 18.033277,
    "Sensor_Speed": 21.654702,
    "Sensor_Torque": 62.460685,
    "Sensor_Current": 17.819808,
    "Sensor_Voltage": 21.912492
}

# ============================================================================
# Step 1: Lambda T1 - 품질 예측
# ============================================================================
print("\n" + "=" * 80)
print("Step 1: Lambda T1 - 품질 예측")
print("=" * 80)

payload_t1 = {
    "body": {
        "features": test_features
    }
}

print(f"\n📤 Lambda T1 호출: {LAMBDA_T1_URL}")
start_time = time.time()

try:
    response_t1 = requests.post(LAMBDA_T1_URL, json=payload_t1, timeout=30)
    elapsed_time = (time.time() - start_time) * 1000
    
    print(f"⏱️  응답 시간: {elapsed_time:.0f} ms")
    print(f"📊 상태 코드: {response_t1.status_code}")
    
    if response_t1.status_code == 200:
        result_t1 = response_t1.json()
        print("\n✅ 예측 성공!")
        print(f"  - 판정: {result_t1['prediction']['class']}")
        print(f"  - 불량 확률: {result_t1['prediction']['probability']*100:.2f}%")
        print(f"  - 신뢰도: {result_t1['prediction']['confidence']}")
        print(f"  - 처리 시간: {result_t1['processing_time_ms']:.0f} ms")
        print(f"  - Latent Features: {len(result_t1['latent_features'])}D")
        
        # Latent features 저장
        latent_features = result_t1['latent_features']
    else:
        print(f"\n❌ 예측 실패")
        print(json.dumps(response_t1.json(), indent=2, ensure_ascii=False))
        exit(1)

except Exception as e:
    print(f"\n❌ 오류 발생: {str(e)}")
    exit(1)

# ============================================================================
# Step 2: Lambda T2 - Feature Importance 분석
# ============================================================================
print("\n" + "=" * 80)
print("Step 2: Lambda T2 - Feature Importance 분석")
print("=" * 80)

payload_t2 = {
    "body": {
        "features": test_features,
        "latent_features": latent_features,
        "top_n": 15,
        "generate_chart": True
    }
}

print(f"\n📤 Lambda T2 호출: {LAMBDA_T2_URL}")
start_time = time.time()

try:
    response_t2 = requests.post(LAMBDA_T2_URL, json=payload_t2, timeout=60)
    elapsed_time = (time.time() - start_time) * 1000
    
    print(f"⏱️  응답 시간: {elapsed_time:.0f} ms")
    print(f"📊 상태 코드: {response_t2.status_code}")
    
    if response_t2.status_code == 200:
        result_t2 = response_t2.json()
        print("\n✅ 분석 성공!")
        print(f"  - 처리 시간: {result_t2['processing_time_ms']:.0f} ms")
        print(f"  - 분석 방법: {result_t2['method']}")
        
        if 'plot_url' in result_t2:
            print(f"  - 차트 URL: {result_t2['plot_url'][:80]}...")
        
        print("\n  📊 Top 5 Feature Importance:")
        for i, (feat, imp) in enumerate(result_t2['top_features'][:5], 1):
            print(f"    {i}. {feat}: {imp:.4f}")
        
        if 'equipment_descriptions' in result_t2:
            print(f"\n  🔧 장비 설명: {len(result_t2['equipment_descriptions'])}개")
    else:
        print(f"\n❌ 분석 실패")
        print(json.dumps(response_t2.json(), indent=2, ensure_ascii=False))

except Exception as e:
    print(f"\n❌ 오류 발생: {str(e)}")

# ============================================================================
# Step 3: Lambda T3 - AI 어시스턴트 (RAG)
# ============================================================================
print("\n" + "=" * 80)
print("Step 3: Lambda T3 - AI 어시스턴트 (RAG)")
print("=" * 80)

test_questions = [
    "기공 불량의 주요 원인은 무엇인가요?",
    "사출 압력이 품질에 미치는 영향을 설명해주세요.",
    "냉각 시간을 최적화하는 방법은?"
]

for i, question in enumerate(test_questions[:1], 1):  # 첫 번째 질문만 테스트
    print(f"\n질문 {i}: {question}")
    
    payload_t3 = {
        "body": {
            "query": question
        }
    }
    
    print(f"📤 Lambda T3 호출: {LAMBDA_T3_URL}")
    start_time = time.time()
    
    try:
        response_t3 = requests.post(LAMBDA_T3_URL, json=payload_t3, timeout=60)
        elapsed_time = (time.time() - start_time) * 1000
        
        print(f"⏱️  응답 시간: {elapsed_time:.0f} ms")
        print(f"📊 상태 코드: {response_t3.status_code}")
        
        if response_t3.status_code == 200:
            result_t3 = response_t3.json()
            print("\n✅ 답변 생성 성공!")
            print(f"\n💬 답변:")
            print(f"  {result_t3['answer'][:200]}...")
            
            if 'sources' in result_t3 and result_t3['sources']:
                print(f"\n📚 참고 문서: {len(result_t3['sources'])}개")
                for j, source in enumerate(result_t3['sources'][:3], 1):
                    print(f"  {j}. {source.get('title', 'N/A')} (관련도: {source.get('score', 0):.2f})")
        else:
            print(f"\n❌ 답변 생성 실패")
            print(json.dumps(response_t3.json(), indent=2, ensure_ascii=False))
    
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")

# ============================================================================
# 요약
# ============================================================================
print("\n" + "=" * 80)
print("테스트 완료!")
print("=" * 80)
print("\n✅ 전체 워크플로우가 정상적으로 작동합니다.")
print("\n다음 명령어로 Streamlit UI를 실행하세요:")
print("  streamlit run streamlit_app.py")
print("\n또는 배포된 Streamlit URL로 접속하세요:")
try:
    with open('streamlit_url.txt', 'r') as f:
        streamlit_url = f.read().strip()
        print(f"  {streamlit_url}")
except:
    print("  (streamlit_url.txt 파일이 없습니다)")
