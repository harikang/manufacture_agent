# 품질 예측 사용 가이드

## 📋 개요

학습된 AutoEncoder + Gradient Boosting 모델을 사용하여 새로운 다이캐스팅 데이터의 불량 여부를 예측하는 방법을 설명합니다.

---

## 🚀 빠른 시작

### 1. 필요한 파일 확인

```bash
deployment_models/
├── autoencoder_latent12.pth      # AutoEncoder 모델
├── gradient_boosting_model.pkl   # Gradient Boosting 모델
└── scaler.pkl                     # Feature Scaler
```

### 2. 의존성 설치

```bash
pip install torch numpy pandas scikit-learn
```

### 3. 예측 실행

```bash
# CSV 파일로 예측
python predict_quality.py --input test_data.csv

# 단일 샘플 예측 (대화형)
python predict_quality.py --single

# 상세 정보 포함
python predict_quality.py --input test_data.csv --details

# 결과를 JSON 파일로 저장
python predict_quality.py --input test_data.csv --output results.json
```

---

## 📊 입력 데이터 형식

### 필요한 30개 Features (순서 중요!)

1. **Process Features (16개)**
   - Process_Temperature
   - Process_Pressure
   - Process_InjectionSpeed
   - Process_InjectionTime
   - Process_CoolingTime
   - Process_ClampForce
   - Process_MoldTemperature
   - Process_MeltTemperature
   - Process_CycleTime
   - Process_ShotSize
   - Process_BackPressure
   - Process_ScrewSpeed
   - Process_HoldPressure
   - Process_HoldTime
   - Process_CushionPosition
   - Process_PlasticizingTime

2. **Sensor Features (14개)**
   - Sensor_Vibration
   - Sensor_Noise
   - Sensor_Temperature1
   - Sensor_Temperature2
   - Sensor_Temperature3
   - Sensor_Pressure1
   - Sensor_Pressure2
   - Sensor_Pressure3
   - Sensor_Flow
   - Sensor_Position
   - Sensor_Speed
   - Sensor_Torque
   - Sensor_Current
   - Sensor_Voltage

### CSV 파일 예시

```csv
Process_Temperature,Process_Pressure,Process_InjectionSpeed,...
650.5,120.3,2.5,1.2,15.0,800.0,180.0,680.0,45.0,250.0,...
655.2,118.7,2.6,1.1,14.5,795.0,182.0,675.0,46.0,248.0,...
```

---

## 💻 Python 코드 사용 예제

### 예제 1: CSV 파일 예측

```python
from predict_quality import QualityPredictor

# 모델 로딩
predictor = QualityPredictor(model_dir='deployment_models')

# CSV 파일 예측
results = predictor.predict_from_csv('test_data.csv')

# 결과 출력
for i, result in enumerate(results):
    print(f"Sample {i+1}:")
    print(f"  예측: {result['prediction']}")
    print(f"  불량 확률: {result['defect_probability']:.2%}")
    print(f"  신뢰도: {result['confidence']}")
    print()
```

### 예제 2: NumPy 배열 예측

```python
import numpy as np
from predict_quality import QualityPredictor

# 모델 로딩
predictor = QualityPredictor()

# 30개 features (예시 데이터)
X = np.array([
    [650.5, 120.3, 2.5, 1.2, 15.0, 800.0, 180.0, 680.0, 45.0, 250.0,
     50.0, 100.0, 90.0, 3.0, 5.0, 8.0, 0.15, 65.0, 650.0, 180.0,
     170.0, 120.0, 90.0, 50.0, 25.0, 100.0, 2.5, 150.0, 45.0, 380.0]
])

# 예측
result = predictor.predict(X, return_details=True)

print(f"예측: {result['prediction']}")
print(f"불량 확률: {result['defect_probability']:.2%}")
print(f"Latent features: {result['latent_features']}")
```

### 예제 3: Dictionary 입력

```python
from predict_quality import QualityPredictor

predictor = QualityPredictor()

# Dictionary 형태로 입력
feature_dict = {
    'Process_Temperature': 650.5,
    'Process_Pressure': 120.3,
    'Process_InjectionSpeed': 2.5,
    # ... 나머지 27개 features
}

result = predictor.predict_from_dict(feature_dict)
print(result)
```

### 예제 4: 배치 예측

```python
import numpy as np
from predict_quality import QualityPredictor

predictor = QualityPredictor()

# 여러 샘플 동시 예측
X_batch = np.random.randn(100, 30)  # 100개 샘플
results = predictor.predict(X_batch)

# 불량 개수 집계
defect_count = sum(1 for r in results if r['prediction'] == 'defect')
print(f"불량 개수: {defect_count} / {len(results)}")
```

---

## 📤 출력 형식

### 기본 출력

```json
{
  "prediction": "defect",
  "defect_probability": 0.78,
  "normal_probability": 0.22,
  "confidence": "high",
  "confidence_score": 0.78
}
```

### 상세 출력 (--details 옵션)

```json
{
  "prediction": "defect",
  "defect_probability": 0.78,
  "normal_probability": 0.22,
  "confidence": "high",
  "confidence_score": 0.78,
  "latent_features": [0.12, -0.45, 0.33, ...],
  "attention_weights": [0.08, 0.15, 0.12, ...],
  "original_features": [650.5, 120.3, ...],
  "scaled_features": [1.23, -0.45, ...]
}
```

### 필드 설명

- **prediction**: "normal" 또는 "defect"
- **defect_probability**: 불량일 확률 (0~1)
- **normal_probability**: 정상일 확률 (0~1)
- **confidence**: 신뢰도 수준
  - "high": 확률 > 0.8
  - "medium": 0.6 < 확률 ≤ 0.8
  - "low": 확률 ≤ 0.6
- **confidence_score**: 최대 확률 값
- **latent_features**: AutoEncoder가 추출한 12D latent vector
- **attention_weights**: Attention 가중치 (12D)

---

## 🔍 예측 프로세스

### 내부 처리 흐름

```
1. 입력 데이터 (30D)
   ↓
2. Feature Scaling (StandardScaler)
   ↓
3. AutoEncoder Encoding
   - 30D → 64 → 32 → 16 → 12D (latent)
   - 4-head Attention
   ↓
4. Feature Combination
   - 30D (scaled) + 12D (latent) = 42D
   ↓
5. Gradient Boosting Prediction
   - 200 decision trees
   - Output: 불량 확률
   ↓
6. 결과 반환
```

### 처리 시간

- **모델 로딩**: ~2초 (최초 1회)
- **단일 샘플 예측**: ~15ms
- **배치 예측 (100개)**: ~50ms

---

## 🎯 신뢰도 해석

### High Confidence (> 0.8)
- 모델이 매우 확신하는 예측
- 즉시 조치 가능
- 예: 불량 확률 85% → 불량으로 판정

### Medium Confidence (0.6 ~ 0.8)
- 모델이 어느 정도 확신하는 예측
- 추가 검증 권장
- 예: 불량 확률 70% → 주의 깊게 관찰

### Low Confidence (< 0.6)
- 모델이 불확실한 예측
- 반드시 추가 검증 필요
- 예: 불량 확률 55% → 수동 검사 필요

---

## 🛠️ 문제 해결

### 오류: "모델 파일을 찾을 수 없습니다"

```bash
# 모델 디렉토리 확인
ls deployment_models/

# 모델 디렉토리 경로 지정
python predict_quality.py --input test.csv --model-dir /path/to/models
```

### 오류: "입력 features는 30개여야 합니다"

- CSV 파일의 컬럼 개수 확인
- Feature 이름이 정확한지 확인
- 순서가 올바른지 확인

### 오류: "CUDA out of memory"

```python
# CPU 사용 강제
import torch
torch.device('cpu')
```

---

## 📊 성능 지표

### 모델 성능 (검증 데이터 기준)

- **F1-Score**: 0.7027
- **ROC-AUC**: 0.9175
- **Accuracy**: 0.8832
- **Precision**: 0.82 (예측한 불량 중 82%가 실제 불량)
- **Recall**: 0.58 (실제 불량 중 58%를 탐지)

### 해석

- **Precision 높음**: False Positive 적음 (정상을 불량으로 오판 적음)
- **Recall 중간**: False Negative 있음 (불량을 정상으로 오판 가능)
- **권장**: 불량 예측 시 추가 검증 수행

---

## 🔄 모델 업데이트

### 새로운 데이터로 재학습 후

1. 새 모델 파일을 `deployment_models/`에 복사
2. 파일명 유지:
   - `autoencoder_latent12.pth`
   - `gradient_boosting_model.pkl`
   - `scaler.pkl`
3. 예측 스크립트 재실행 (자동으로 새 모델 로딩)

---

## 📞 문의

문제 발생 시:
1. 입력 데이터 형식 확인
2. 모델 파일 존재 여부 확인
3. Python 버전 확인 (3.8 이상 권장)
4. 의존성 버전 확인

---

**작성일**: 2026-01-16  
**버전**: v1.0  
**모델**: AutoEncoder (12D) + Gradient Boosting (42D)
