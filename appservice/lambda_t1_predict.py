"""
Lambda T1: 품질 예측
- 31개 feature 입력 받기
- AutoEncoder로 latent features 생성 (12D)
- Gradient Boosting으로 예측
"""

import json
import boto3
import numpy as np
import pickle
import torch
import time
import os
from typing import Dict, Any

# S3 client
s3 = boto3.client('s3')

# Global variables for model caching
autoencoder_model = None
gb_model = None
scaler = None

BUCKET_NAME = os.environ.get('BUCKET_NAME', 'diecasting-models')
AUTOENCODER_KEY = 'models/autoencoder_latent12.pth'
GB_MODEL_KEY = 'models/gradient_boosting_model.pkl'
SCALER_PARAMS_KEY = 'models/scaler_params.npz'  # Use npz instead of pkl for compatibility
MODEL_VERSION = os.environ.get('MODEL_VERSION', 'v1.4')  # Cache buster


def load_models():
    """
    S3에서 모델 로드 (Cold start 시 1회만 실행)
    """
    global autoencoder_model, gb_model, scaler
    
    if autoencoder_model is None:
        print("Loading models from S3...")
        
        try:
            # AutoEncoder 로드
            autoencoder_path = '/tmp/autoencoder.pth'
            print(f"Downloading AutoEncoder from s3://{BUCKET_NAME}/{AUTOENCODER_KEY}")
            s3.download_file(BUCKET_NAME, AUTOENCODER_KEY, autoencoder_path)
            
            # PyTorch 모델 로드
            from autoencoder_model_lambda import AutoEncoder
            autoencoder_model = AutoEncoder(input_dim=30, latent_dim=12)
            autoencoder_model.load_state_dict(torch.load(autoencoder_path, map_location='cpu'), strict=False)
            autoencoder_model.eval()
            print("✅ AutoEncoder loaded successfully")
            
            # Gradient Boosting 모델 로드
            gb_path = '/tmp/gb_model.pkl'
            print(f"Downloading GB model from s3://{BUCKET_NAME}/{GB_MODEL_KEY}")
            s3.download_file(BUCKET_NAME, GB_MODEL_KEY, gb_path)
            with open(gb_path, 'rb') as f:
                gb_model = pickle.load(f)
            print(f"✅ GB model loaded successfully (n_features: {gb_model.n_features_in_})")
            
            # Scaler 로드 (npz 파일에서 파라미터를 로드하여 재구성)
            from sklearn.preprocessing import StandardScaler
            scaler_path = '/tmp/scaler_params.npz'
            print(f"Downloading scaler params from s3://{BUCKET_NAME}/{SCALER_PARAMS_KEY}")
            s3.download_file(BUCKET_NAME, SCALER_PARAMS_KEY, scaler_path)

            # Load parameters and recreate scaler
            params = np.load(scaler_path)
            scaler = StandardScaler()
            scaler.mean_ = params['mean']
            scaler.scale_ = params['scale']
            scaler.var_ = params['var']
            scaler.n_features_in_ = int(params['n_features_in'][0])
            scaler.n_samples_seen_ = int(params['n_samples_seen'][0])
            print(f"✅ Scaler loaded successfully (n_features: {scaler.n_features_in_})")
            
            print("All models loaded successfully!")
            
        except Exception as e:
            print(f"❌ Error loading models: {str(e)}")
            import traceback
            traceback.print_exc()
            raise


def extract_features(event_body: Dict) -> np.ndarray:
    """
    입력에서 30개 feature 추출 및 정렬
    List 또는 Dictionary 형식 모두 지원
    """
    feature_names = [
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
    
    features = event_body.get('features')
    
    if features is None:
        raise ValueError("Missing 'features' field in request body")
    
    # List 형식인 경우
    if isinstance(features, list):
        if len(features) != 30:
            raise ValueError(f"Expected 30 features, got {len(features)}")
        feature_values = [float(f) for f in features]
    
    # Dictionary 형식인 경우
    elif isinstance(features, dict):
        feature_values = []
        for name in feature_names:
            if name not in features:
                raise ValueError(f"Missing feature: {name}")
            feature_values.append(float(features[name]))
    
    else:
        raise ValueError(f"Features must be list or dict, got {type(features)}")
    
    return np.array(feature_values).reshape(1, -1)


def generate_latent_features(features: np.ndarray) -> tuple:
    """
    AutoEncoder로 latent features 생성

    Returns:
        (latent_features, scaled_features)
    """
    # Scaling
    features_scaled = scaler.transform(features)

    print(f"DEBUG: Original features shape: {features.shape}")
    print(f"DEBUG: Scaled features shape: {features_scaled.shape}")
    print(f"DEBUG: Scaled features has NaN (before clip): {np.isnan(features_scaled).any()}")
    print(f"DEBUG: Scaled features min/max (before clip): {features_scaled.min():.4f} / {features_scaled.max():.4f}")

    # Clip extreme values to prevent NaN in AutoEncoder
    features_scaled = np.clip(features_scaled, -10.0, 10.0)
    print(f"DEBUG: Scaled features min/max (after clip): {features_scaled.min():.4f} / {features_scaled.max():.4f}")
    
    # PyTorch tensor 변환
    features_tensor = torch.FloatTensor(features_scaled)
    
    print(f"DEBUG: Tensor has NaN: {torch.isnan(features_tensor).any().item()}")
    print(f"DEBUG: Tensor has Inf: {torch.isinf(features_tensor).any().item()}")
    
    # Latent features 추출 (encode 메서드는 (z, attn_weights) 튜플 반환)
    autoencoder_model.eval()  # Evaluation 모드 설정
    with torch.no_grad():
        latent, attn_weights = autoencoder_model.encode(features_tensor)
    
    print(f"DEBUG: Latent tensor has NaN: {torch.isnan(latent).any().item()}")
    print(f"DEBUG: Latent tensor has Inf: {torch.isinf(latent).any().item()}")
    print(f"DEBUG: Latent shape: {latent.shape}")
    print(f"DEBUG: Latent values min/max: {latent.min().item():.4f} / {latent.max().item():.4f}")
    
    return latent.numpy(), features_scaled


def predict_quality(features_scaled: np.ndarray, latent: np.ndarray) -> Dict[str, Any]:
    """
    Gradient Boosting으로 품질 예측
    
    Args:
        features_scaled: scaled된 30D features
        latent: 12D latent features
    
    Returns:
        예측 결과
    """
    # 30D + 12D = 42D 결합
    combined_features = np.concatenate([features_scaled, latent], axis=1)
    
    print(f"DEBUG: features_scaled shape: {features_scaled.shape}")
    print(f"DEBUG: latent shape: {latent.shape}")
    print(f"DEBUG: combined_features shape: {combined_features.shape}")
    print(f"DEBUG: features_scaled has NaN: {np.isnan(features_scaled).any()}")
    print(f"DEBUG: latent has NaN: {np.isnan(latent).any()}")
    print(f"DEBUG: combined_features has NaN: {np.isnan(combined_features).any()}")
    
    if np.isnan(combined_features).any():
        print(f"ERROR: NaN detected in combined features!")
        print(f"features_scaled: {features_scaled}")
        print(f"latent: {latent}")
        raise ValueError("NaN detected in features")
    
    # 예측
    prediction_proba = gb_model.predict_proba(combined_features)[0]
    prediction_class = gb_model.predict(combined_features)[0]
    
    # 신뢰도 계산
    confidence_score = max(prediction_proba)
    if confidence_score > 0.8:
        confidence = 'high'
    elif confidence_score > 0.6:
        confidence = 'medium'
    else:
        confidence = 'low'
    
    return {
        'class': 'defect' if prediction_class == 1 else 'normal',
        'probability': float(prediction_proba[1]),  # 불량 확률
        'confidence': confidence,
        'confidence_score': float(confidence_score),
        'class_probabilities': {
            'normal': float(prediction_proba[0]),
            'defect': float(prediction_proba[1])
        }
    }


def lambda_handler(event, context):
    """
    Lambda 핸들러
    
    Input:
        {
            "features": {
                "Process_Temperature": 650.0,
                "Process_Pressure": 120.0,
                ...
            }
        }
    
    Output:
        {
            "statusCode": 200,
            "body": {
                "prediction": {...},
                "latent_features": [...],
                "processing_time_ms": 15.3,
                "model_version": "v1.0_12D_GB"
            }
        }
    """
    start_time = time.time()
    
    try:
        # 모델 로드 (Cold start 시)
        load_models()
        
        # 입력 파싱
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', event)
        
        # body가 또 다른 body를 포함하는 경우 처리 (중첩 구조)
        if 'body' in body and isinstance(body['body'], dict):
            body = body['body']
        
        # Feature 추출
        features = extract_features(body)
        
        # Latent features 생성 (scaled features도 함께 반환)
        latent, features_scaled = generate_latent_features(features)
        
        # 예측
        prediction = predict_quality(features_scaled, latent)
        
        # 처리 시간 계산
        processing_time = (time.time() - start_time) * 1000
        
        # 응답 생성
        response_body = {
            'prediction': prediction,
            'latent_features': latent[0].tolist(),
            'processing_time_ms': round(processing_time, 2),
            'model_version': 'v1.0_12D_GB',
            'model_performance': {
                'f1_score': 0.7027,
                'roc_auc': 0.9175,
                'accuracy': 0.8832
            }
        }
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response_body)
        }
    
    except ValueError as e:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Invalid input',
                'message': str(e)
            })
        }
    
    except Exception as e:
        print(f"Error: {str(e)}")
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
    # Test event
    test_event = {
        'body': {
            'features': {
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
        }
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(json.loads(result['body']), indent=2))
