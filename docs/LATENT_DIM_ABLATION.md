# Latent Dimension Ablation Study

## 실험 목적

AutoEncoder의 latent dimension을 4, 8, 12, 16으로 변경하면서 최적의 차원을 찾기 위한 ablation study

## 실험 설계

### Feature 조합
- **Baseline**: 30차원 원본 features (고정)
- **Latent**: 4D, 8D, 12D, 16D (변경)
- **Combined**: 34D, 38D, 42D, 46D (30 + latent)

### AutoEncoder 설정
- Architecture: 30 → 64 → 32 → 16 → **[4/8/12/16]** (latent)
- Activation: SwiGLU
- Attention: 4-head self-attention
- Loss: MSE + Focal Loss
- Optimizer: AdamW (lr=1e-3, weight_decay=1e-4, betas=(0.9, 0.999))
- Scheduler: CosineAnnealingWarmRestarts (T_0=10, T_mult=2, eta_min=1e-6)
- Epochs: 100

### ML 모델
- Gradient Boosting
- XGBoost
- LightGBM

## 실험 결과

### 전체 성능 비교

| Latent Dim | Total Dim | Gradient Boosting | XGBoost | LightGBM |
|------------|-----------|-------------------|---------|----------|
| **4D** | **34D** | 0.6803 | 0.6115 | 0.5623 |
| **8D** | **38D** | 0.6797 | 0.6254 | **0.6093** |
| **12D** | **42D** | 0.7027 | 0.6197 | 0.6050 |
| **16D** | **46D** | **0.7043** | **0.6609** | 0.5917 |

### 모델별 상세 분석

#### 1. Gradient Boosting (최고 성능 모델)

| Latent Dim | Total Dim | F1-Score | Accuracy | ROC-AUC | Improvement |
|------------|-----------|----------|----------|---------|-------------|
| 4D | 34D | 0.6803 | 0.8752 | 0.8896 | baseline |
| 8D | 38D | 0.6797 | 0.8806 | 0.9023 | -0.09% |
| 12D | 42D | 0.7027 | 0.8832 | 0.9175 | **+3.29%** |
| 16D | 46D | **0.7043** | **0.8852** | 0.9073 | **+3.53%** |

**분석**:
- 16D에서 최고 F1-Score (0.7043)
- 12D와 16D가 비슷한 성능 (차이 0.23%)
- 4D → 16D로 증가하면서 지속적 성능 향상
- ROC-AUC는 12D에서 최고 (0.9175)

#### 2. XGBoost

| Latent Dim | Total Dim | F1-Score | Accuracy | ROC-AUC | Improvement |
|------------|-----------|----------|----------|---------|-------------|
| 4D | 34D | 0.6115 | 0.8567 | 0.8848 | baseline |
| 8D | 38D | 0.6254 | 0.8593 | 0.8864 | +2.27% |
| 12D | 42D | 0.6197 | 0.8567 | 0.8958 | +1.34% |
| 16D | 46D | **0.6609** | **0.8693** | 0.8934 | **+8.08%** |

**분석**:
- 16D에서 최고 F1-Score (0.6609)
- 4D → 16D로 8.08% 대폭 향상
- 차원이 증가할수록 성능 향상 (단조 증가는 아님)
- 16D에서 가장 큰 도약

#### 3. LightGBM

| Latent Dim | Total Dim | F1-Score | Accuracy | ROC-AUC | Improvement |
|------------|-----------|----------|----------|---------|-------------|
| 4D | 34D | 0.5623 | 0.8461 | 0.8717 | baseline |
| 8D | 38D | **0.6093** | **0.8553** | 0.8825 | **+8.36%** |
| 12D | 42D | 0.6050 | 0.8527 | 0.8908 | +7.59% |
| 16D | 46D | 0.5917 | 0.8507 | 0.8830 | +5.23% |

**분석**:
- 8D에서 최고 F1-Score (0.6093)
- 8D 이후 성능 감소 (과적합 가능성)
- 차원이 너무 높으면 오히려 성능 저하
- LightGBM은 중간 차원(8D)에서 최적

## 종합 분석

### 1. 최적 Latent Dimension

#### 전체 최고 성능
```
🏆 Gradient Boosting + 16D Latent (Total 46D)
   - F1-Score: 0.7043
   - Accuracy: 0.8852
   - ROC-AUC: 0.9073
```

#### 모델별 최적 차원
- **Gradient Boosting**: 16D (F1: 0.7043)
- **XGBoost**: 16D (F1: 0.6609)
- **LightGBM**: 8D (F1: 0.6093)

### 2. 차원 증가에 따른 효과

#### Gradient Boosting
```
4D (34D total):  F1 = 0.6803
8D (38D total):  F1 = 0.6797  (-0.09%)
12D (42D total): F1 = 0.7027  (+3.29%)
16D (46D total): F1 = 0.7043  (+3.53%)
```
→ 12D부터 큰 성능 향상, 16D에서 최고

#### XGBoost
```
4D (34D total):  F1 = 0.6115
8D (38D total):  F1 = 0.6254  (+2.27%)
12D (42D total): F1 = 0.6197  (+1.34%)
16D (46D total): F1 = 0.6609  (+8.08%)
```
→ 16D에서 급격한 성능 향상

#### LightGBM
```
4D (34D total):  F1 = 0.5623
8D (38D total):  F1 = 0.6093  (+8.36%) ← 최고
12D (42D total): F1 = 0.6050  (+7.59%)
16D (46D total): F1 = 0.5917  (+5.23%)
```
→ 8D에서 최고, 이후 감소 (과적합)

### 3. 차원별 특성

#### 4D (Total 34D)
- **장점**: 가장 적은 차원, 빠른 학습
- **단점**: 정보 압축 과도, 성능 제한적
- **F1 평균**: 0.6180
- **추천**: ❌ 성능 부족

#### 8D (Total 38D)
- **장점**: 균형잡힌 성능, LightGBM 최적
- **단점**: Gradient Boosting에서는 최적 아님
- **F1 평균**: 0.6381
- **추천**: ✅ 범용적 선택

#### 12D (Total 42D)
- **장점**: Gradient Boosting 우수, 높은 ROC-AUC
- **단점**: XGBoost에서 16D보다 낮음
- **F1 평균**: 0.6425
- **추천**: ✅ Gradient Boosting 사용 시

#### 16D (Total 46D)
- **장점**: Gradient Boosting, XGBoost 최고 성능
- **단점**: LightGBM 과적합, 차원 증가
- **F1 평균**: 0.6523
- **추천**: ✅✅ 최고 성능 원할 때

### 4. 성능 vs 차원 Trade-off

| Latent Dim | Avg F1 | Dimension Increase | F1 per Dimension |
|------------|--------|-------------------|------------------|
| 4D | 0.6180 | +4 (13.3%) | 0.0155 |
| 8D | 0.6381 | +8 (26.7%) | 0.0080 |
| 12D | 0.6425 | +12 (40.0%) | 0.0054 |
| 16D | 0.6523 | +16 (53.3%) | 0.0041 |

**분석**:
- 차원당 성능 향상은 감소 (수확 체감)
- 4D → 8D: 가장 효율적 (차원당 0.0080)
- 12D → 16D: 효율 낮음 (차원당 0.0025)

### 5. 모델별 차원 민감도

#### Gradient Boosting
- 차원 증가에 강건함
- 16D까지 지속적 향상
- 고차원 features 잘 활용

#### XGBoost
- 16D에서 급격한 향상
- 비선형 패턴 포착 능력 우수
- 차원 증가 효과 큼

#### LightGBM
- 8D에서 최적
- 고차원에서 과적합 경향
- 차원 증가에 민감

## 결론 및 권장사항

### 🎯 최종 권장사항

#### 1. 최고 성능 추구
```
✅ 16D Latent (Total 46D) + Gradient Boosting
   - F1-Score: 0.7043
   - 모든 실험 중 최고 성능
   - 비용: 차원 53.3% 증가
```

#### 2. 균형잡힌 선택
```
✅ 12D Latent (Total 42D) + Gradient Boosting
   - F1-Score: 0.7027 (최고 대비 -0.23%)
   - ROC-AUC: 0.9175 (최고)
   - 비용: 차원 40% 증가
   - 성능/차원 균형 우수
```

#### 3. 효율성 중시
```
✅ 8D Latent (Total 38D) + Gradient Boosting
   - F1-Score: 0.6797
   - 차원 26.7% 증가
   - 모든 모델에서 안정적
   - 실시간 시스템에 적합
```

### 📊 모델별 권장 차원

| 모델 | 권장 Latent Dim | Total Dim | F1-Score | 이유 |
|------|----------------|-----------|----------|------|
| Gradient Boosting | **16D** | 46D | 0.7043 | 최고 성능 |
| XGBoost | **16D** | 46D | 0.6609 | 최고 성능 |
| LightGBM | **8D** | 38D | 0.6093 | 과적합 방지 |

### 💡 핵심 인사이트

1. **차원이 높을수록 좋은가?**
   - Gradient Boosting, XGBoost: Yes (16D 최적)
   - LightGBM: No (8D 최적, 이후 과적합)

2. **8D vs 16D 선택 기준**
   - 최고 성능 필요: 16D
   - 안정성/효율성: 8D
   - 범용성: 8D (모든 모델 안정)

3. **차원 증가의 한계**
   - 16D 이상은 테스트 필요
   - 수확 체감 법칙 적용
   - 과적합 위험 증가

4. **실무 적용**
   - 프로토타입: 8D (빠른 학습, 안정적)
   - 프로덕션: 12D or 16D (최고 성능)
   - 실시간: 8D (계산 효율)

### 🔬 추가 실험 제안

1. **더 높은 차원 테스트**
   - 20D, 24D 실험
   - 성능 포화점 확인

2. **Variational AutoEncoder (VAE)**
   - 정규화 효과로 과적합 방지
   - 고차원에서도 안정적 학습

3. **앙상블 전략**
   - 8D, 12D, 16D 모델 앙상블
   - 다양한 추상화 레벨 활용

4. **Feature Selection**
   - 16D latent에서 중요 차원 선택
   - 8~12개 핵심 차원만 사용

## 시각화 자료

생성된 파일:
- `latent_dimension_ablation.png` - 차원별 성능 비교
- `latent_dimension_detailed.png` - 모델별 상세 분석
- `latent_dimension_ablation_results.csv` - 전체 결과 데이터

---

**최종 결론**: **16D latent (Total 46D) + Gradient Boosting**이 최고 성능(F1: 0.7043)을 달성했으며, 실무에서는 성능과 효율의 균형을 고려하여 **12D (F1: 0.7027)** 또는 **8D (F1: 0.6797)**를 선택할 수 있습니다.
