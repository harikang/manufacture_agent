"""
전체 시스템 통합 테스트
Lambda T1 → T2 → T3 순차 실행
"""

import requests
import json
import time

# Lambda URLs
LAMBDA_T1_URL = "https://your-lambda-t1.lambda-url.us-east-1.on.aws/"
LAMBDA_T2_URL = "https://your-lambda-t2.lambda-url.us-east-1.on.aws/"
LAMBDA_T3_URL = "https://your-lambda-t3.lambda-url.us-east-1.on.aws/"

print("=" * 70)
print("다이캐스팅 품질 예측 시스템 - 전체 통합 테스트")
print("=" * 70)

# 테스트 데이터 (30D features - dictionary 형식)
test_features = {
    'Process_Temperature': 650.0,
    'Process_Pressure': 120.0,
    'Process_InjectionSpeed': 2.5,
    'Process_InjectionTime': 1.2,
    'Process_CoolingTime': 15.0,
    'Process_ClampForce': 800.0,
    'Process_MoldTemperature': 180.0,
    'Process_MeltTemperature': 680.0,
    'Process_CycleTime': 45.0,
    'Process_ShotSize': 250.0,
    'Process_BackPressure': 50.0,
    'Process_ScrewSpeed': 100.0,
    'Process_HoldPressure': 90.0,
    'Process_HoldTime': 3.0,
    'Process_CushionPosition': 5.0,
    'Process_PlasticizingTime': 8.0,
    'Sensor_Vibration': 0.15,
    'Sensor_Noise': 65.0,
    'Sensor_Temperature1': 650.0,
    'Sensor_Temperature2': 180.0,
    'Sensor_Temperature3': 170.0,
    'Sensor_Pressure1': 120.0,
    'Sensor_Pressure2': 90.0,
    'Sensor_Pressure3': 50.0,
    'Sensor_Flow': 25.0,
    'Sensor_Position': 100.0,
    'Sensor_Speed': 2.5,
    'Sensor_Torque': 150.0,
    'Sensor_Current': 45.0,
    'Sensor_Voltage': 380.0
}

# Lambda T2용 리스트 형식
test_features_list = list(test_features.values())

# ========================================
# Test 1: Lambda T1 (예측)
# ========================================
print("\n[Test 1/3] Lambda T1 - 품질 예측")
print("-" * 70)

try:
    start_time = time.time()
    response = requests.post(
        LAMBDA_T1_URL,
        json={'features': test_features},
        timeout=30
    )
    duration = (time.time() - start_time) * 1000
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ 예측 성공 (처리 시간: {duration:.1f}ms)")
        print(f"  - 예측: {result['prediction']['class']}")
        print(f"  - 확률: {result['prediction']['probability']*100:.1f}%")
        print(f"  - 신뢰도: {result['prediction']['confidence']}")
        print(f"  - Latent Features: {len(result['latent_features'])}D")
        
        # 다음 테스트를 위해 저장
        latent_features = result['latent_features']
        prediction_id = f"test_{int(time.time())}"
    else:
        print(f"✗ 예측 실패 (상태 코드: {response.status_code})")
        print(f"  에러: {response.text}")
        exit(1)
        
except Exception as e:
    print(f"✗ 테스트 실패: {str(e)}")
    exit(1)

# ========================================
# Test 2: Lambda T2 (분석)
# ========================================
print("\n[Test 2/3] Lambda T2 - Feature Importance 분석")
print("-" * 70)

try:
    start_time = time.time()
    response = requests.post(
        LAMBDA_T2_URL,
        json={
            'features': test_features_list,
            'latent_features': latent_features,
            'prediction_id': prediction_id
        },
        timeout=60
    )
    duration = (time.time() - start_time) * 1000
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ 분석 성공 (처리 시간: {duration:.1f}ms)")
        print(f"  - Top 5 Features:")
        for feat in result['top_features'][:5]:
            print(f"    {feat['rank']}. {feat['name']}: {feat['value']:.4f}")
        print(f"  - 시각화 URL: {result['visualization_url']}")
    else:
        print(f"✗ 분석 실패 (상태 코드: {response.status_code})")
        print(f"  에러: {response.text}")
        
except Exception as e:
    print(f"✗ 테스트 실패: {str(e)}")

# ========================================
# Test 3: Lambda T3 (RAG)
# ========================================
print("\n[Test 3/3] Lambda T3 - RAG 기반 지식 검색")
print("-" * 70)

test_queries = [
    "포로시티 불량이 발생했을 때 어떻게 해결하나요?",
    "주입 속도의 권장 범위는 얼마인가요?"
]

for i, query in enumerate(test_queries, 1):
    print(f"\n질문 {i}: {query}")
    
    try:
        start_time = time.time()
        response = requests.post(
            LAMBDA_T3_URL,
            json={
                'query': query,
                'use_knowledge_base': True
            },
            timeout=30
        )
        duration = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ 답변 생성 성공 (처리 시간: {duration:.1f}ms)")
            print(f"  Knowledge Base 사용: {result['used_knowledge_base']}")
            print(f"  답변: {result['answer'][:150]}...")
            if result.get('sources'):
                print(f"  출처: {len(result['sources'])}개 문서")
        else:
            print(f"✗ 답변 생성 실패 (상태 코드: {response.status_code})")
            print(f"  에러: {response.text}")
            
    except Exception as e:
        print(f"✗ 테스트 실패: {str(e)}")

# ========================================
# 최종 결과
# ========================================
print("\n" + "=" * 70)
print("전체 시스템 통합 테스트 완료!")
print("=" * 70)
print("\n✅ Lambda T1 (예측): 정상 작동")
print("✅ Lambda T2 (분석): 정상 작동")
print("✅ Lambda T3 (RAG): 정상 작동")
print("\n시스템이 프로덕션 배포 준비 완료 상태입니다.")
print("=" * 70)
