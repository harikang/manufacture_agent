"""
다이캐스팅 품질 예측 추론 스크립트

학습된 AutoEncoder + Gradient Boosting 모델을 사용하여
새로운 데이터의 불량 여부를 예측합니다.

Usage:
    python predict_quality.py --input sample_data.csv
    python predict_quality.py --single  # 단일 샘플 예측
"""

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import pickle
import argparse
import json
from pathlib import Path


# ============================================================================
# AutoEncoder 모델 정의 (autoencoder_model.py와 동일)
# ============================================================================

class SwiGLU(nn.Module):
    """SwiGLU activation function"""
    def forward(self, x):
        x, gate = x.chunk(2, dim=-1)
        return x * torch.sigmoid(gate) * gate


class AttentionModule(nn.Module):
    """Multi-head self-attention module"""
    def __init__(self, dim, num_heads=4):
        super().__init__()
        self.attention = nn.MultiheadAttention(dim, num_heads, batch_first=True)
        self.norm = nn.LayerNorm(dim)
    
    def forward(self, x):
        x = x.unsqueeze(1)
        attn_out, weights = self.attention(x, x, x)
        x = self.norm(x + attn_out)
        return x.squeeze(1), weights


class AutoEncoder(nn.Module):
    """AutoEncoder for latent feature extraction"""
    def __init__(self, input_dim=30, latent_dim=12):
        super().__init__()
        
        # Encoder
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.BatchNorm1d(64),
            SwiGLU(),
            nn.Linear(32, 32),
            nn.BatchNorm1d(32),
            SwiGLU(),
            nn.Linear(16, 16),
            nn.BatchNorm1d(16),
            SwiGLU(),
            nn.Linear(8, latent_dim)
        )
        
        # Attention
        self.attention = AttentionModule(latent_dim, num_heads=4)
        
        # Decoder (추론 시에는 사용하지 않음)
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, 16),
            nn.BatchNorm1d(16),
            SwiGLU(),
            nn.Linear(8, 32),
            nn.BatchNorm1d(32),
            SwiGLU(),
            nn.Linear(16, 64),
            nn.BatchNorm1d(64),
            SwiGLU(),
            nn.Linear(32, input_dim)
        )
    
    def encode(self, x):
        """Extract latent features (추론 시 사용)"""
        latent = self.encoder(x)
        latent_attended, attention_weights = self.attention(latent)
        return latent_attended, attention_weights


# ============================================================================
# 모델 로더
# ============================================================================

class QualityPredictor:
    """다이캐스팅 품질 예측기"""
    
    def __init__(self, model_dir='deployment_models'):
        """
        Args:
            model_dir: 모델 파일이 저장된 디렉토리
        """
        self.model_dir = Path(model_dir)
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Feature 이름 정의 (학습 시와 동일한 순서)
        self.feature_names = [
            'Process_Temperature', 'Process_Pressure', 'Process_InjectionSpeed',
            'Process_InjectionTime', 'Process_CoolingTime', 'Process_ClampForce',
            'Process_MoldTemperature', 'Process_MeltTemperature', 'Process_CycleTime',
            'Process_ShotSize', 'Process_BackPressure', 'Process_ScrewSpeed',
            'Process_HoldPressure', 'Process_HoldTime', 'Process_CushionPosition',
            'Process_PlasticizingTime',
            'Sensor_Vibration', 'Sensor_Noise', 'Sensor_Temperature1',
            'Sensor_Temperature2', 'Sensor_Temperature3', 'Sensor_Pressure1',
            'Sensor_Pressure2', 'Sensor_Pressure3', 'Sensor_Flow',
            'Sensor_Position', 'Sensor_Speed', 'Sensor_Torque',
            'Sensor_Current', 'Sensor_Voltage'
        ]
        
        self.autoencoder = None
        self.gb_model = None
        self.scaler = None
        
        self._load_models()
    
    def _load_models(self):
        """모델 파일 로딩"""
        print("=" * 80)
        print("모델 로딩 중...")
        print("=" * 80)
        
        # 1. AutoEncoder 로딩
        autoencoder_path = self.model_dir / 'autoencoder_latent12.pth'
        if not autoencoder_path.exists():
            raise FileNotFoundError(f"AutoEncoder 모델을 찾을 수 없습니다: {autoencoder_path}")
        
        self.autoencoder = AutoEncoder(input_dim=30, latent_dim=12)
        self.autoencoder.load_state_dict(torch.load(autoencoder_path, map_location=self.device))
        self.autoencoder.eval()
        self.autoencoder.to(self.device)
        print(f"✅ AutoEncoder 로딩 완료: {autoencoder_path}")
        
        # 2. Gradient Boosting 모델 로딩
        gb_path = self.model_dir / 'gradient_boosting_model.pkl'
        if not gb_path.exists():
            raise FileNotFoundError(f"Gradient Boosting 모델을 찾을 수 없습니다: {gb_path}")
        
        with open(gb_path, 'rb') as f:
            self.gb_model = pickle.load(f)
        print(f"✅ Gradient Boosting 로딩 완료: {gb_path}")
        
        # 3. Scaler 로딩
        scaler_path = self.model_dir / 'scaler.pkl'
        if not scaler_path.exists():
            raise FileNotFoundError(f"Scaler를 찾을 수 없습니다: {scaler_path}")
        
        with open(scaler_path, 'rb') as f:
            self.scaler = pickle.load(f)
        print(f"✅ Scaler 로딩 완료: {scaler_path}")
        
        print("=" * 80)
        print("모든 모델 로딩 완료!")
        print("=" * 80)
        print()
    
    def predict(self, X, return_details=False):
        """
        품질 예측 수행
        
        Args:
            X: numpy array (n_samples, 30) 또는 (30,)
            return_details: True면 상세 정보 반환
        
        Returns:
            predictions: dict 또는 list of dict
        """
        # 입력 형태 확인
        if X.ndim == 1:
            X = X.reshape(1, -1)
            single_sample = True
        else:
            single_sample = False
        
        if X.shape[1] != 30:
            raise ValueError(f"입력 features는 30개여야 합니다. 현재: {X.shape[1]}개")
        
        # 1. Feature Scaling
        X_scaled = self.scaler.transform(X)
        
        # 2. AutoEncoder로 Latent Features 추출
        X_tensor = torch.FloatTensor(X_scaled).to(self.device)
        with torch.no_grad():
            latent, attention_weights = self.autoencoder.encode(X_tensor)
        
        latent_np = latent.cpu().numpy()
        attention_np = attention_weights.cpu().numpy()
        
        # 3. Combined Features (30D + 12D = 42D)
        X_combined = np.hstack([X_scaled, latent_np])
        
        # 4. Gradient Boosting 예측
        predictions = self.gb_model.predict(X_combined)
        probabilities = self.gb_model.predict_proba(X_combined)
        
        # 5. 결과 생성
        results = []
        for i in range(len(X)):
            pred_class = predictions[i]
            pred_proba = probabilities[i]
            
            result = {
                'prediction': 'defect' if pred_class == 1 else 'normal',
                'defect_probability': float(pred_proba[1]),
                'normal_probability': float(pred_proba[0]),
                'confidence': 'high' if max(pred_proba) > 0.8 else 'medium' if max(pred_proba) > 0.6 else 'low',
                'confidence_score': float(max(pred_proba))
            }
            
            if return_details:
                result['latent_features'] = latent_np[i].tolist()
                result['attention_weights'] = attention_np[i].tolist()
                result['original_features'] = X[i].tolist()
                result['scaled_features'] = X_scaled[i].tolist()
            
            results.append(result)
        
        return results[0] if single_sample else results
    
    def predict_from_dict(self, feature_dict, return_details=False):
        """
        Dictionary 형태의 입력으로 예측
        
        Args:
            feature_dict: {feature_name: value} 형태의 dict
            return_details: True면 상세 정보 반환
        
        Returns:
            prediction: dict
        """
        # Feature 배열 생성
        X = np.array([[feature_dict.get(name, 0.0) for name in self.feature_names]])
        
        return self.predict(X, return_details=return_details)
    
    def predict_from_csv(self, csv_path, return_details=False):
        """
        CSV 파일에서 데이터를 읽어 예측
        
        Args:
            csv_path: CSV 파일 경로
            return_details: True면 상세 정보 반환
        
        Returns:
            predictions: list of dict
        """
        print(f"CSV 파일 로딩 중: {csv_path}")
        df = pd.read_csv(csv_path)
        
        # Feature 추출
        X = df[self.feature_names].values
        
        # 결측치 처리
        X = np.nan_to_num(X, nan=0.0)
        
        print(f"데이터 shape: {X.shape}")
        print(f"예측 시작...")
        
        results = self.predict(X, return_details=return_details)
        
        print(f"✅ {len(results)}개 샘플 예측 완료!")
        
        return results


# ============================================================================
# CLI 인터페이스
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='다이캐스팅 품질 예측')
    parser.add_argument('--input', type=str, help='입력 CSV 파일 경로')
    parser.add_argument('--single', action='store_true', help='단일 샘플 예측 (대화형)')
    parser.add_argument('--model-dir', type=str, default='deployment_models', 
                       help='모델 디렉토리 경로')
    parser.add_argument('--output', type=str, help='결과 저장 경로 (JSON)')
    parser.add_argument('--details', action='store_true', help='상세 정보 포함')
    
    args = parser.parse_args()
    
    # 모델 로딩
    predictor = QualityPredictor(model_dir=args.model_dir)
    
    if args.single:
        # 단일 샘플 대화형 예측
        print("\n" + "=" * 80)
        print("단일 샘플 예측 모드")
        print("=" * 80)
        print("30개 features 값을 입력하세요 (쉼표로 구분):")
        print("예: 650.5,120.3,2.5,1.2,15.0,800.0,180.0,680.0,45.0,250.0,...")
        print()
        
        values_str = input("Features: ")
        values = [float(v.strip()) for v in values_str.split(',')]
        
        if len(values) != 30:
            print(f"❌ 오류: 30개 features가 필요합니다. 입력된 개수: {len(values)}")
            return
        
        X = np.array(values)
        result = predictor.predict(X, return_details=args.details)
        
        print("\n" + "=" * 80)
        print("예측 결과")
        print("=" * 80)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    elif args.input:
        # CSV 파일 예측
        results = predictor.predict_from_csv(args.input, return_details=args.details)
        
        # 결과 요약
        print("\n" + "=" * 80)
        print("예측 결과 요약")
        print("=" * 80)
        
        defect_count = sum(1 for r in results if r['prediction'] == 'defect')
        normal_count = len(results) - defect_count
        
        print(f"총 샘플 수: {len(results)}")
        print(f"정상: {normal_count} ({normal_count/len(results)*100:.1f}%)")
        print(f"불량: {defect_count} ({defect_count/len(results)*100:.1f}%)")
        print()
        
        # 신뢰도 분포
        high_conf = sum(1 for r in results if r['confidence'] == 'high')
        med_conf = sum(1 for r in results if r['confidence'] == 'medium')
        low_conf = sum(1 for r in results if r['confidence'] == 'low')
        
        print("신뢰도 분포:")
        print(f"  High: {high_conf} ({high_conf/len(results)*100:.1f}%)")
        print(f"  Medium: {med_conf} ({med_conf/len(results)*100:.1f}%)")
        print(f"  Low: {low_conf} ({low_conf/len(results)*100:.1f}%)")
        
        # 결과 저장
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"\n✅ 결과 저장 완료: {args.output}")
    
    else:
        print("❌ --input 또는 --single 옵션을 지정해주세요.")
        parser.print_help()


if __name__ == '__main__':
    main()
