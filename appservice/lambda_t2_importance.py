"""
Lambda T2: Feature Importance 분석 (Gradient Boosting 기반)
- Gradient Boosting 모델의 feature_importances_를 사용하여 실시간 feature importance 계산
- 개별 예측에 대한 feature importance 분석
- S3에서 로드한 장비/센서 매핑 정보를 통해 영향을 미친 장비/센서에 대한 상세 설명 제공
- PNG 차트 생성 및 presigned URL 발급
- Streamlit UI에서 시각화
"""

import json
import boto3
import numpy as np
import pickle
import time
from typing import Dict, Any, List, Tuple
from datetime import datetime

# SHAP는 선택적으로 사용
try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    print("SHAP not available - using model's feature_importances_ instead")

# matplotlib for chart generation
try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("matplotlib not available - chart generation disabled")

# AWS clients
s3 = boto3.client('s3')

# Configuration
BUCKET_NAME = 'diecasting-models'
GB_MODEL_KEY = 'models/gradient_boosting_model.pkl'
SCALER_KEY = 'models/scaler.pkl'
EQUIPMENT_MAPPING_KEY = 'config/equipment_sensor_mapping.json'
PRESIGNED_URL_EXPIRATION = 3600  # 1 hour

# Model cache
gb_model = None
scaler = None
feature_names = None
equipment_mapping = None


# Feature 이름 정의 (Lambda T1과 동일)
FEATURE_NAMES = [
    'Process_Temperature', 'Process_Pressure', 'Process_InjectionSpeed',
    'Process_InjectionTime', 'Process_CoolingTime', 'Process_ClampForce',
    'Process_MoldTemperature', 'Process_MeltTemperature', 'Process_CycleTime',
    'Process_ShotSize', 'Process_BackPressure', 'Process_ScrewSpeed',
    'Process_HoldPressure', 'Process_HoldTime', 'Process_CushionPosition',
    'Process_PlasticizingTime', 'Sensor_Vibration', 'Sensor_Noise',
    'Sensor_Temperature1', 'Sensor_Temperature2', 'Sensor_Temperature3',
    'Sensor_Pressure1', 'Sensor_Pressure2', 'Sensor_Pressure3',
    'Sensor_Flow', 'Sensor_Position', 'Sensor_Speed', 'Sensor_Torque',
    'Sensor_Current', 'Sensor_Voltage'
]

# 장비/센서 설명 데이터베이스
EQUIPMENT_DESCRIPTIONS = {
    'Process_Temperature': {
        'name': '용탕 온도',
        'equipment': '용탕로 (Melting Furnace)',
        'description': '알루미늄 합금을 용융시키는 온도입니다. 650-680°C가 적정 범위이며, 온도가 높으면 기공 발생 위험이 증가하고, 낮으면 유동성이 저하됩니다.',
        'impact': '품질에 가장 큰 영향을 미치는 요인 중 하나로, 온도 관리가 불량률을 좌우합니다.',
        'action': '온도 센서를 정기적으로 교정하고, ±5°C 이내로 유지하세요.'
    },
    'Process_Pressure': {
        'name': '사출 압력',
        'equipment': '사출 유닛 (Injection Unit)',
        'description': '용탕을 금형에 주입하는 압력입니다. 120-130 MPa가 적정 범위이며, 압력이 부족하면 미충전, 과다하면 플래시가 발생합니다.',
        'impact': '충전 품질과 직결되며, 압력 제어가 불량률에 큰 영향을 미칩니다.',
        'action': '유압 시스템을 점검하고, 압력 프로파일을 최적화하세요.'
    },
    'Process_InjectionSpeed': {
        'name': '사출 속도',
        'equipment': '사출 유닛',
        'description': '용탕이 금형에 주입되는 속도입니다. 2.0-3.0 m/s가 적정 범위이며, 속도가 빠르면 난류로 인한 기공 발생, 느리면 콜드 샷이 발생합니다.',
        'impact': '표면 품질과 내부 기공에 영향을 미칩니다.',
        'action': '사출 속도 프로파일을 단계별로 조정하세요.'
    },
    'Process_CoolingTime': {
        'name': '냉각 시간',
        'equipment': '냉각 시스템 (Cooling System)',
        'description': '제품이 금형 내에서 냉각되는 시간입니다. 15-20초가 적정 범위이며, 시간이 부족하면 변형 발생, 과다하면 생산성 저하됩니다.',
        'impact': '치수 정밀도와 변형에 직접적인 영향을 미칩니다.',
        'action': '냉각수 온도와 유량을 확인하고, 금형 온도 분포를 균일하게 유지하세요.'
    },
    'Process_MoldTemperature': {
        'name': '금형 온도',
        'equipment': '금형 (Die/Mold)',
        'description': '금형의 표면 온도입니다. 170-190°C가 적정 범위이며, 온도가 낮으면 콜드 샷, 높으면 냉각 지연이 발생합니다.',
        'impact': '표면 품질과 충전 상태에 영향을 미칩니다.',
        'action': '금형 예열을 충분히 하고, 냉각 채널을 정기적으로 청소하세요.'
    },
    'Process_ClampForce': {
        'name': '형체력',
        'equipment': '형체 유닛 (Clamping Unit)',
        'description': '금형을 닫는 힘입니다. 700-900 kN이 적정 범위이며, 힘이 부족하면 플래시 발생, 과다하면 금형 손상 위험이 있습니다.',
        'impact': '플래시 발생과 금형 수명에 영향을 미칩니다.',
        'action': '형체력을 정기적으로 점검하고, 금형 마모 상태를 확인하세요.'
    },
    'Sensor_Vibration': {
        'name': '진동 센서',
        'equipment': '사출 유닛 베이스',
        'description': '장비의 진동을 측정합니다. 0.10-0.20 g가 정상 범위이며, 0.25 g 이상이면 기계적 이상을 의미합니다.',
        'impact': '장비 상태를 나타내는 지표로, 예방 정비에 활용됩니다.',
        'action': '진동이 증가하면 베어링, 기어 등을 점검하세요.'
    },
    'Sensor_Noise': {
        'name': '소음 센서',
        'equipment': '장비 상단',
        'description': '작동 소음을 측정합니다. 60-70 dB가 정상 범위이며, 75 dB 이상이면 이상 소음을 의미합니다.',
        'impact': '장비 이상을 조기에 감지할 수 있습니다.',
        'action': '소음이 증가하면 유압 펌프, 모터 등을 점검하세요.'
    },
    'Sensor_Temperature1': {
        'name': '온도 센서 1 (용탕)',
        'equipment': '용탕로',
        'description': 'Process_Temperature와 동일한 용탕 온도를 측정하는 센서입니다.',
        'impact': '온도 관리의 핵심 센서입니다.',
        'action': '월 1회 교정하고, 2년마다 교체하세요.'
    },
    'Sensor_Pressure1': {
        'name': '압력 센서 1 (사출)',
        'equipment': '사출 실린더',
        'description': 'Process_Pressure와 동일한 사출 압력을 측정하는 센서입니다.',
        'impact': '압력 제어의 핵심 센서입니다.',
        'action': '월 1회 교정하고, 3년마다 교체하세요.'
    },
    'Sensor_Flow': {
        'name': '유량 센서',
        'equipment': '냉각수 배관',
        'description': '냉각수 유량을 측정합니다. 22-28 L/min이 정상 범위이며, 유량이 부족하면 냉각 불량이 발생합니다.',
        'impact': '냉각 효율에 직접적인 영향을 미칩니다.',
        'action': '배관 막힘을 확인하고, 필터를 정기적으로 청소하세요.'
    }
}


def load_models():
    """
    S3에서 모델 및 장비 매핑 정보 로드
    """
    global gb_model, scaler, feature_names, equipment_mapping
    
    if gb_model is None:
        print("Loading models from S3...")
        
        try:
            # Gradient Boosting 모델
            gb_path = '/tmp/gb_model.pkl'
            print(f"Downloading GB model from s3://{BUCKET_NAME}/{GB_MODEL_KEY}")
            s3.download_file(BUCKET_NAME, GB_MODEL_KEY, gb_path)
            with open(gb_path, 'rb') as f:
                gb_model = pickle.load(f)
            print(f"✅ GB model loaded (n_features: {gb_model.n_features_in_})")
            
            # Scaler
            scaler_path = '/tmp/scaler.pkl'
            print(f"Downloading scaler from s3://{BUCKET_NAME}/{SCALER_KEY}")
            s3.download_file(BUCKET_NAME, SCALER_KEY, scaler_path)
            with open(scaler_path, 'rb') as f:
                scaler = pickle.load(f)
            print(f"✅ Scaler loaded (n_features: {scaler.n_features_in_})")
            
            # 장비/센서 매핑 정보 (optional)
            try:
                mapping_path = '/tmp/equipment_mapping.json'
                print(f"Downloading equipment mapping from s3://{BUCKET_NAME}/{EQUIPMENT_MAPPING_KEY}")
                s3.download_file(BUCKET_NAME, EQUIPMENT_MAPPING_KEY, mapping_path)
                with open(mapping_path, 'r', encoding='utf-8') as f:
                    equipment_mapping = json.load(f)
                print("✅ Equipment mapping loaded")
            except Exception as e:
                print(f"⚠️ Equipment mapping not available: {e}")
                equipment_mapping = None
            
            feature_names = FEATURE_NAMES
            print("Models loaded successfully!")
            
        except Exception as e:
            print(f"❌ Error loading models: {str(e)}")
            import traceback
            traceback.print_exc()
            raise


def calculate_shap_values(features: np.ndarray, latent: np.ndarray = None) -> Dict[str, Any]:
    """
    Feature importance 계산 (모델의 feature_importances_ 사용)
    
    Args:
        features: 30D features (scaled)
        latent: 12D latent features (optional)
    
    Returns:
        Feature importance analysis results
    """
    load_models()
    
    # Debug logging
    print(f"DEBUG: features shape: {features.shape}")
    print(f"DEBUG: latent is None: {latent is None}")
    if latent is not None:
        print(f"DEBUG: latent shape: {latent.shape}")
    
    # Feature 결합 (30D + 12D = 42D)
    if latent is not None:
        combined_features = np.concatenate([features, latent], axis=1)
        all_feature_names = FEATURE_NAMES + [f'Latent_{i+1}' for i in range(latent.shape[1])]
        print(f"DEBUG: combined_features shape: {combined_features.shape}")
    else:
        combined_features = features
        all_feature_names = FEATURE_NAMES
        print(f"DEBUG: No latent features, using only original features")
    
    # XGBoostingClassifier의 feature_importances_ 사용
    # 이는 각 feature가 트리 분할에 기여한 정도를 나타냄
    feature_importance = gb_model.feature_importances_
    
    # Latent feature 제외 (원본 28개 feature만 사용)
    original_feature_importance = feature_importance[:len(FEATURE_NAMES)]
    
    # 정렬
    importance_dict = {
        name: float(imp) 
        for name, imp in zip(FEATURE_NAMES, original_feature_importance)
    }
    sorted_importance = sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)
    
    # 예측 수행
    prediction_proba = gb_model.predict_proba(combined_features)[0]
    
    return {
        'feature_values': combined_features[0].tolist(),
        'feature_importance': importance_dict,
        'sorted_importance': sorted_importance,
        'feature_names': FEATURE_NAMES,  # Latent 제외
        'prediction_proba': prediction_proba.tolist(),
        'method': 'GradientBoosting feature_importances_ (original features only)'
    }


def generate_shap_chart(feature_importance: Dict[str, float], 
                       feature_names: List[str], top_n: int = 20) -> str:
    """
    Feature importance chart 생성 및 S3 업로드 (matplotlib 사용)
    
    Returns:
        S3 key or None if matplotlib not available
    """
    if not MATPLOTLIB_AVAILABLE:
        print("matplotlib not available - skipping chart generation")
        return None
    
    try:
        # Top N features만 선택
        sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:top_n]
        top_feature_names = [f[0] for f in sorted_features]
        top_importance_values = [f[1] for f in sorted_features]
        
        # Matplotlib 차트 생성
        fig, ax = plt.subplots(figsize=(12, 8))
        
        y_pos = np.arange(len(top_feature_names))
        colors = ['#4CAF50' for _ in top_importance_values]  # 녹색
        
        ax.barh(y_pos, top_importance_values, color=colors, edgecolor='black', linewidth=0.5)
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels(top_feature_names, fontsize=10)
        ax.set_xlabel('Feature Importance', fontsize=12)
        ax.set_title(f'Top {top_n} Feature Importance (GradientBoosting)', fontsize=14, fontweight='bold')
        ax.grid(axis='x', alpha=0.3)
        
        # 값 표시
        for i, v in enumerate(top_importance_values):
            ax.text(v, i, f' {v:.4f}', va='center', fontsize=9)
        
        plt.tight_layout()
        
        # PNG로 저장
        img_path = '/tmp/importance_chart.png'
        plt.savefig(img_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        # S3 업로드
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        s3_key = f'analysis/importance_chart_{timestamp}.png'
        
        with open(img_path, 'rb') as f:
            s3.put_object(
                Bucket=BUCKET_NAME,
                Key=s3_key,
                Body=f,
                ContentType='image/png'
            )
        
        print(f"Chart uploaded to S3: {s3_key}")
        return s3_key
    
    except Exception as e:
        print(f"Chart generation error: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_equipment_descriptions(top_features: List[Tuple[str, float]]) -> List[Dict]:
    """
    상위 feature들에 대한 장비/센서 설명 추가
    """
    descriptions = []
    
    for feat_name, importance in top_features:
        if feat_name in EQUIPMENT_DESCRIPTIONS:
            desc = EQUIPMENT_DESCRIPTIONS[feat_name].copy()
            desc['feature_name'] = feat_name
            desc['importance'] = importance
            descriptions.append(desc)
        else:
            # Latent feature인 경우
            descriptions.append({
                'feature_name': feat_name,
                'name': feat_name,
                'equipment': 'Latent Feature',
                'description': 'AutoEncoder가 학습한 잠재 특성입니다.',
                'importance': importance
            })
    
    return descriptions


def generate_presigned_url(key: str, expiration: int = PRESIGNED_URL_EXPIRATION) -> str:
    """
    S3 객체에 대한 presigned URL 생성
    """
    try:
        url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET_NAME, 'Key': key},
            ExpiresIn=expiration
        )
        return url
    except Exception as e:
        print(f"Error generating presigned URL: {e}")
        return None


def lambda_handler(event, context):
    """
    Lambda 핸들러
    
    Input:
        {
            "features": {...},  # optional: 30D features
            "latent_features": [...],  # optional: 12D latent
            "top_n": 10,
            "generate_chart": true
        }
    
    Output:
        {
            "statusCode": 200,
            "body": {
                "feature_values": [...],
                "feature_importance": {...},
                "top_features": [...],
                "equipment_descriptions": [...],
                "chart_url": "...",
                "prediction_proba": [0.2, 0.8],
                "processing_time_ms": 123.45,
                "timestamp": "2024-01-01T00:00:00",
                "method": "GradientBoosting feature_importances_"
            }
        }
    """
    start_time = time.time()
    
    try:
        # 입력 파싱
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', event)
        
        # body가 또 다른 body를 포함하는 경우 처리 (중첩 구조)
        if 'body' in body and isinstance(body['body'], dict):
            body = body['body']
        
        print(f"DEBUG: body keys: {body.keys()}")
        print(f"DEBUG: body.get('latent_features'): {body.get('latent_features')}")
        
        features = body.get('features')
        latent_features = body.get('latent_features')
        top_n = body.get('top_n', 10)
        generate_chart = body.get('generate_chart', True)
        
        # Features 처리
        if features:
            # Dict to array
            feature_array = np.array([
                [features.get(name, 0) for name in FEATURE_NAMES]
            ])
            
            # Scaling
            load_models()
            feature_array = scaler.transform(feature_array)
        else:
            # 샘플 데이터 사용 (전역 importance)
            feature_array = np.zeros((1, 30))
        
        # Latent features 처리
        if latent_features:
            latent_array = np.array([latent_features])
        else:
            latent_array = None
        
        # Feature importance 계산
        importance_results = calculate_shap_values(feature_array, latent_array)
        
        # 상위 N개 추출
        top_features = importance_results['sorted_importance'][:top_n]
        
        # 장비/센서 설명 추가
        equipment_descriptions = get_equipment_descriptions(top_features)
        
        # Chart 생성
        chart_url = None
        if generate_chart:
            chart_key = generate_shap_chart(
                importance_results['feature_importance'],
                importance_results['feature_names'],
                top_n
            )
            if chart_key:
                chart_url = generate_presigned_url(chart_key)
        
        # 처리 시간
        processing_time = (time.time() - start_time) * 1000
        
        # 응답 생성
        response_body = {
            'feature_values': importance_results['feature_values'],
            'feature_importance': importance_results['feature_importance'],
            'top_features': top_features,
            'equipment_descriptions': equipment_descriptions,
            'chart_url': chart_url,
            'prediction_proba': importance_results['prediction_proba'],
            'processing_time_ms': round(processing_time, 2),
            'timestamp': datetime.utcnow().isoformat(),
            'method': importance_results['method']
        }
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response_body)
        }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }


# Local testing
if __name__ == '__main__':
    # Test with sample features
    test_event = {
        'body': {
            'features': {
                'Process_Temperature': 690.0,  # 높음 - 불량 위험
                'Process_Pressure': 145.0,     # 높음
                'Process_InjectionSpeed': 4.5,
                'Process_InjectionTime': 0.8,
                'Process_CoolingTime': 10.0,   # 낮음 - 불량 위험
                'Process_ClampForce': 750.0,
                'Process_MoldTemperature': 195.0,
                'Process_MeltTemperature': 695.0,
                'Process_CycleTime': 35.0,
                'Process_ShotSize': 280.0,
                'Process_BackPressure': 65.0,
                'Process_ScrewSpeed': 115.0,
                'Process_HoldPressure': 105.0,
                'Process_HoldTime': 2.0,
                'Process_CushionPosition': 3.5,
                'Process_PlasticizingTime': 6.0,
                'Sensor_Vibration': 0.28,
                'Sensor_Noise': 78.0,
                'Sensor_Temperature1': 695.0,
                'Sensor_Temperature2': 195.0,
                'Sensor_Temperature3': 185.0,
                'Sensor_Pressure1': 145.0,
                'Sensor_Pressure2': 105.0,
                'Sensor_Pressure3': 65.0,
                'Sensor_Flow': 28.0,
                'Sensor_Position': 115.0,
                'Sensor_Speed': 2.8,
                'Sensor_Torque': 180.0,
                'Sensor_Current': 55.0,
                'Sensor_Voltage': 395.0
            },
            'latent_features': [0.12, -0.45, 0.33, 0.67, -0.23, 0.89, 
                               -0.12, 0.45, -0.67, 0.23, -0.89, 0.34],
            'top_n': 10,
            'generate_chart': False
        }
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(json.loads(result['body']), indent=2, ensure_ascii=False))
