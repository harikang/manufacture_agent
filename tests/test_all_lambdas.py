#!/usr/bin/env python3
"""
전체 Lambda 시스템 테스트
- Lambda T1: 품질 예측
- Lambda T2: Feature Importance 분석
- Lambda T3: RAG 질의응답
"""

import requests
import json

# Lambda URLs
LAMBDA_T1_URL = "https://your-lambda-t1.lambda-url.us-east-1.on.aws/"
LAMBDA_T2_URL = "https://your-lambda-t2.lambda-url.us-east-1.on.aws/"
LAMBDA_T3_URL = "https://your-lambda-t3.lambda-url.us-east-1.on.aws/"

# 테스트 데이터 (불량 위험 높은 샘플)
test_features = {
    "Process_Temperature": 690.0,
    "Process_Pressure": 145.0,
    "Process_InjectionSpeed": 4.5,
    "Process_InjectionTime": 0.8,
    "Process_CoolingTime": 10.0,
    "Process_ClampForce": 750.0,
    "Process_MoldTemperature": 195.0,
    "Process_MeltTemperature": 695.0,
    "Process_CycleTime": 35.0,
    "Process_ShotSize": 280.0,
    "Process_BackPressure": 65.0,
    "Process_ScrewSpeed": 115.0,
    "Process_HoldPressure": 105.0,
    "Process_HoldTime": 2.0,
    "Process_CushionPosition": 3.5,
    "Process_PlasticizingTime": 6.0,
    "Sensor_Vibration": 0.28,
    "Sensor_Noise": 78.0,
    "Sensor_Temperature1": 695.0,
    "Sensor_Temperature2": 195.0,
    "Sensor_Temperature3": 185.0,
    "Sensor_Pressure1": 145.0,
    "Sensor_Pressure2": 105.0,
    "Sensor_Pressure3": 65.0,
    "Sensor_Flow": 28.0,
    "Sensor_Position": 115.0,
    "Sensor_Speed": 2.8,
    "Sensor_Torque": 180.0,
    "Sensor_Current": 55.0,
    "Sensor_Voltage": 395.0
}


def test_lambda_t1():
    """Lambda T1: 품질 예측 테스트"""
    print("\n" + "="*60)
    print("Lambda T1: 품질 예측 테스트")
    print("="*60)
    
    payload = {
        "body": {
            "features": test_features
        }
    }
    
    try:
        response = requests.post(LAMBDA_T1_URL, json=payload, timeout=30)
        result = response.json()
        
        if response.status_code == 200:
            print("✅ Lambda T1 성공!")
            print(f"  - 예측: {result['prediction']['class']}")
            print(f"  - 확률: {result['prediction']['probability']:.2%}")
            print(f"  - 신뢰도: {result['prediction']['confidence']}")
            print(f"  - 처리 시간: {result['processing_time_ms']:.2f}ms")
            print(f"  - Latent 차원: {len(result['latent_features'])}D")
            return result
        else:
            print(f"❌ Lambda T1 실패: {result}")
            return None
    except Exception as e:
        print(f"❌ Lambda T1 오류: {e}")
        return None


def test_lambda_t2(latent_features):
    """Lambda T2: Feature Importance 분석 테스트"""
    print("\n" + "="*60)
    print("Lambda T2: Feature Importance 분석 테스트")
    print("="*60)
    
    payload = {
        "body": {
            "features": test_features,
            "latent_features": latent_features,
            "top_n": 5,
            "generate_chart": False
        }
    }
    
    try:
        response = requests.post(LAMBDA_T2_URL, json=payload, timeout=30)
        result = response.json()
        
        if response.status_code == 200:
            print("✅ Lambda T2 성공!")
            print(f"  - 처리 시간: {result['processing_time_ms']:.2f}ms")
            print(f"  - 예측 확률: {result['prediction_proba']}")
            print(f"\n  Top 5 중요 Features:")
            for i, (feat, imp) in enumerate(result['top_features'][:5], 1):
                print(f"    {i}. {feat}: {imp:.4f}")
            
            if result.get('equipment_descriptions'):
                print(f"\n  장비/센서 설명:")
                for desc in result['equipment_descriptions'][:3]:
                    print(f"    - {desc['name']}: {desc['description'][:80]}...")
            
            return result
        else:
            print(f"❌ Lambda T2 실패: {result}")
            return None
    except Exception as e:
        print(f"❌ Lambda T2 오류: {e}")
        return None


def test_lambda_t3():
    """Lambda T3: RAG 질의응답 테스트"""
    print("\n" + "="*60)
    print("Lambda T3: RAG 질의응답 테스트")
    print("="*60)
    
    queries = [
        "기공 불량의 주요 원인은?",
        "사출 압력이 높으면 어떤 문제가 발생하나요?",
        "냉각 시간을 최적화하는 방법은?"
    ]
    
    for query in queries:
        print(f"\n질문: {query}")
        
        payload = {
            "body": {
                "query": query,
                "use_knowledge_base": True
            }
        }
        
        try:
            response = requests.post(LAMBDA_T3_URL, json=payload, timeout=30)
            result = response.json()
            
            if response.status_code == 200:
                print(f"✅ 답변 ({result['processing_time_ms']:.0f}ms):")
                print(f"  {result['answer'][:200]}...")
                print(f"  - Knowledge Base 사용: {result['used_knowledge_base']}")
                print(f"  - 참고 문서: {len(result['sources'])}개")
            else:
                print(f"❌ 실패: {result}")
        except Exception as e:
            print(f"❌ 오류: {e}")


def main():
    print("\n" + "="*60)
    print("다이캐스팅 품질 예측 시스템 - 전체 Lambda 테스트")
    print("="*60)
    
    # 1. Lambda T1 테스트 (품질 예측)
    t1_result = test_lambda_t1()
    
    if t1_result:
        # 2. Lambda T2 테스트 (Feature Importance)
        latent_features = t1_result['latent_features']
        test_lambda_t2(latent_features)
    
    # 3. Lambda T3 테스트 (RAG 질의응답)
    test_lambda_t3()
    
    print("\n" + "="*60)
    print("테스트 완료!")
    print("="*60)


if __name__ == '__main__':
    main()
