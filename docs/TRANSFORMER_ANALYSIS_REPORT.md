# Transformer Models vs ML Models 비교 분석 보고서

**프로젝트**: 다이캐스팅 품질 예측 - Transformer 아키텍처 평가  
**작성일**: 2026-01-15  
**목적**: FT-Transformer 및 TabTransformer의 성능을 기존 ML 모델과 비교 분석

---

## Executive Summary

본 연구는 tabular data에 특화된 transformer 아키텍처(FT-Transformer, TabTransformer)를 다이캐스팅 불량 예측 task에 적용하고, 기존 tree-based ML 모델들과 성능을 비교하였습니다.

### 핵심 결과
- **최고 성능 모델**: Gradient Boosting (16D latent) - F1: 0.7043
- **최고 Transformer**: TabTransformer (16D latent) - F1: 0.5169
- **성능 격차**: ML 모델이 transformer 대비 **26.6% 우수**
- **결론**: 현재 데이터셋에서는 tree-based ML 모델이 transformer보다 효과적

---

## 1. 평가 모델 소개

### 1.1 FT-Transformer (Feature Tokenizer + Transformer)

**출처**: "Revisiting Deep Learning Models for Tabular Data" (NeurIPS 2021)

**아키텍처 특징**:
- 각 feature를 독립적인 token으로 변환
- CLS token을 통한 classification
- Multi-head self-attention으로 feature 간 관계 학습
- Transformer encoder blocks (2 layers)

**구현 설정**:
```python
FTTransformer(
    n_features=38/42/46,  # 30 + latent_dim
    d_token=96,           # Token dimension
    n_blocks=2,           # Transformer blocks
    n_heads=4,            # Attention heads
    attention_dropout=0.2,
    ffn_dropout=0.1
)
```

**파라미터 수**: 224,257

### 1.2 TabTransformer (Simplified)

**출처**: "TabTransformer: Tabular Data Modeling Using Contextual Embeddings" (2020)

**아키텍처 특징**:
- Feature projection + positional embeddings
- Transformer encoder (2 layers)
- Global average pooling
- 연속형 features에 최적화된 단순화 버전

**구현 설정**:
```python
SimpleTabTransformer(
    n_features=38/42/46,
    d_model=64,
    n_heads=4,
    n_layers=2,
    dropout=0.1
)
```

**파라미터 수**: 106,881 ~ 107,393

### 1.3 학습 설정

**공통 설정**:
- Optimizer: AdamW (lr=3e-4, weight_decay=1e-5)
- Loss: Weighted BCE (pos_weight=3.5, 불균형 데이터 대응)
- Batch size: 128
- Max epochs: 100
- Early stopping: patience=15
- Gradient clipping: max_norm=1.0

---

## 2. 실험 결과

### 2.1 전체 성능 비교 (F1-Score 기준)

#### Top 10 모델

| Rank | Latent Dim | Model | Type | F1-Score | Accuracy | ROC-AUC |
|------|------------|-------|------|----------|----------|---------|
| 🥇 1 | 16D | Gradient Boosting | ML | **0.7043** | 0.8852 | 0.9073 |
| 🥈 2 | 12D | Gradient Boosting | ML | **0.7027** | 0.8832 | **0.9175** |
| 🥉 3 | 4D | Gradient Boosting | ML | 0.6803 | 0.8752 | 0.8896 |
| 4 | 8D | Gradient Boosting | ML | 0.6797 | 0.8806 | 0.9023 |
| 5 | 16D | XGBoost | ML | 0.6609 | 0.8693 | 0.8934 |
| 6 | 8D | XGBoost | ML | 0.6254 | 0.8593 | 0.8864 |
| 7 | 12D | XGBoost | ML | 0.6197 | 0.8567 | 0.8958 |
| 8 | 4D | XGBoost | ML | 0.6115 | 0.8567 | 0.8848 |
| 9 | 8D | LightGBM | ML | 0.6093 | 0.8553 | 0.8825 |
| 10 | 12D | LightGBM | ML | 0.6050 | 0.8527 | 0.8908 |

**Transformer 모델 순위**:
- **16위**: TabTransformer (16D) - F1: 0.5169
- **17위**: TabTransformer (12D) - F1: 0.5165
- **18위**: TabTransformer (8D) - F1: 0.5104
- **19위**: FT-Transformer (8D) - F1: 0.4517
- **20위**: FT-Transformer (16D) - F1: 0.4506
- **21위**: FT-Transformer (12D) - F1: 0.4199

### 2.2 Latent Dimension별 상세 결과

#### 8D Latent (38D Total Features)

| Model | Type | F1-Score | Accuracy | ROC-AUC | vs Best ML |
|-------|------|----------|----------|---------|------------|
| Gradient Boosting | ML | 0.6797 | 0.8806 | 0.9023 | - |
| XGBoost | ML | 0.6254 | 0.8593 | 0.8864 | -8.0% |
| LightGBM | ML | 0.6093 | 0.8553 | 0.8825 | -10.4% |
| **TabTransformer** | Transformer | **0.5104** | 0.7034 | 0.7574 | **-24.9%** |
| **FT-Transformer** | Transformer | **0.4517** | 0.6344 | 0.6954 | **-33.5%** |

#### 12D Latent (42D Total Features)

| Model | Type | F1-Score | Accuracy | ROC-AUC | vs Best ML |
|-------|------|----------|----------|---------|------------|
| Gradient Boosting | ML | 0.7027 | 0.8832 | **0.9175** | - |
| XGBoost | ML | 0.6197 | 0.8567 | 0.8958 | -11.8% |
| LightGBM | ML | 0.6050 | 0.8527 | 0.8908 | -13.9% |
| **TabTransformer** | Transformer | **0.5165** | 0.6795 | 0.7575 | **-26.5%** |
| **FT-Transformer** | Transformer | **0.4199** | 0.6204 | 0.6442 | **-40.3%** |

#### 16D Latent (46D Total Features)

| Model | Type | F1-Score | Accuracy | ROC-AUC | vs Best ML |
|-------|------|----------|----------|---------|------------|
| Gradient Boosting | ML | **0.7043** | 0.8852 | 0.9073 | - |
| XGBoost | ML | 0.6609 | 0.8693 | 0.8934 | -6.2% |
| LightGBM | ML | 0.5917 | 0.8507 | 0.8830 | -16.0% |
| **TabTransformer** | Transformer | **0.5169** | 0.6961 | 0.7585 | **-26.6%** |
| **FT-Transformer** | Transformer | **0.4506** | 0.6828 | 0.6960 | **-36.0%** |

### 2.3 모델 타입별 평균 성능

| Model Type | Avg F1-Score | Avg Accuracy | Avg ROC-AUC | Std F1 |
|------------|--------------|--------------|-------------|--------|
| **ML Models** | **0.6372** | **0.8643** | **0.8918** | 0.0413 |
| **Transformers** | **0.4810** | **0.6694** | **0.7175** | 0.0398 |
| **Performance Gap** | **-24.5%** | **-22.5%** | **-19.5%** | - |

---

## 3. 심층 분석

### 3.1 Transformer 모델의 한계

#### 3.1.1 데이터셋 크기 문제
- **학습 샘플**: 6,028개 (train set)
- **Transformer 파라미터**: 106K ~ 224K
- **문제**: Transformer는 대규모 데이터에서 강점 발휘
- **결과**: 작은 데이터셋에서 과적합 경향

#### 3.1.2 Tabular Data 특성
- **Tree-based 모델 강점**:
  - Feature 간 비선형 관계 효과적 포착
  - Missing values 자연스럽게 처리
  - Feature importance 직관적
  - 적은 데이터로도 좋은 성능

- **Transformer 약점**:
  - Tabular data의 구조적 특성 활용 제한
  - Inductive bias 부족
  - 대규모 데이터 필요

#### 3.1.3 학습 안정성
- **ML 모델**: 안정적이고 빠른 수렴
- **Transformer**: 
  - 학습 불안정 (early stopping 빈번)
  - 예측 분포 불균형 (positive class 과소/과다 예측)
  - 하이퍼파라미터 민감도 높음

### 3.2 TabTransformer vs FT-Transformer

| 측면 | TabTransformer | FT-Transformer |
|------|----------------|----------------|
| **평균 F1-Score** | 0.5146 | 0.4407 |
| **성능 우위** | ✅ +16.8% | ❌ |
| **파라미터 수** | ~107K | ~224K |
| **효율성** | ✅ 더 효율적 | ❌ |
| **학습 안정성** | ✅ 더 안정적 | ❌ 불안정 |
| **수렴 속도** | ✅ 빠름 (45 epochs) | ❌ 느림 (62-100 epochs) |

**결론**: TabTransformer가 FT-Transformer보다 tabular data에 더 적합

### 3.3 Latent Dimension 영향

#### ML 모델
- **4D → 8D**: 소폭 감소 (-0.1%)
- **8D → 12D**: 큰 향상 (+3.4%)
- **12D → 16D**: 미세 향상 (+0.2%)
- **최적**: 16D (성능) 또는 12D (효율)

#### Transformer 모델
- **일관된 패턴 없음**: 차원 증가가 성능 향상 보장 안 함
- **TabTransformer**: 16D에서 최고 (0.5169)
- **FT-Transformer**: 8D에서 최고 (0.4517)
- **해석**: 모델 용량 대비 데이터 부족으로 불안정

---

## 4. 비즈니스 영향 분석

### 4.1 성능 차이의 실무적 의미

**가정**:
- 일일 생산량: 1,000개
- 불량률: 22.42%
- 불량품 손실: 50,000원/개

#### 시나리오 비교

| 모델 | F1-Score | 일일 탐지 불량 | 일일 손실 절감 | 연간 절감 (억원) |
|------|----------|----------------|----------------|------------------|
| Baseline (30D) | 0.6422 | 144개 | 7,210,000원 | 26.3 |
| **Gradient Boosting (16D)** | **0.7043** | **158개** | **7,915,000원** | **28.9** |
| TabTransformer (16D) | 0.5169 | 116개 | 5,800,000원 | 21.2 |
| FT-Transformer (16D) | 0.4506 | 101개 | 5,050,000원 | 18.4 |

**ML vs Transformer 차이**:
- **일일 손실 절감 차이**: 2,115,000원
- **연간 차이**: **7.7억원**
- **ROI 차이**: ML 모델이 압도적 우위

### 4.2 운영 비용 고려

| 측면 | ML Models | Transformers |
|------|-----------|--------------|
| **학습 시간** | 1-5분 | 30-60분 |
| **추론 속도** | 매우 빠름 | 느림 |
| **메모리 사용** | 낮음 | 높음 |
| **유지보수** | 쉬움 | 복잡 |
| **해석 가능성** | 높음 | 낮음 |
| **재학습 비용** | 낮음 | 높음 |

---

## 5. 결론 및 권장사항

### 5.1 핵심 결론

1. **Tree-based ML 모델이 Transformer보다 우수**
   - F1-Score: 평균 24.5% 높음
   - 모든 latent dimension에서 일관된 우위

2. **TabTransformer > FT-Transformer**
   - Tabular data에는 TabTransformer가 더 적합
   - 16.8% 성능 우위, 더 효율적

3. **데이터셋 크기가 핵심 요인**
   - 7,535 샘플은 transformer에 부족
   - Tree-based 모델이 소규모 데이터에 강점

4. **실무 적용 관점**
   - ML 모델: 빠르고, 안정적이고, 해석 가능
   - Transformer: 추가 이점 없음

### 5.2 최종 권장사항

#### 🏆 프로덕션 배포 권장 구성

**1순위: Gradient Boosting + 12D Latent (42D Total)**
- F1-Score: 0.7027
- ROC-AUC: 0.9175 (최고)
- 성능/효율 최적 균형
- 연간 절감: 28.7억원

**2순위: Gradient Boosting + 16D Latent (46D Total)**
- F1-Score: 0.7043 (최고)
- ROC-AUC: 0.9073
- 최고 성능 추구 시
- 연간 절감: 28.9억원

**비권장: Transformer 모델**
- 현재 데이터셋에서는 실용성 없음
- 성능, 효율, 해석성 모두 열위

### 5.3 Transformer 모델 개선 방향 (향후 연구)

만약 transformer를 개선하고자 한다면:

1. **데이터 증강**
   - 최소 50,000+ 샘플 확보
   - SMOTE, ADASYN 등 오버샘플링
   - Data augmentation 기법 적용

2. **아키텍처 최적화**
   - 더 작은 모델 (파라미터 50K 이하)
   - Regularization 강화
   - Ensemble with ML models

3. **하이퍼파라미터 튜닝**
   - Learning rate 최적화
   - Dropout 조정
   - Loss function 개선 (Focal Loss 등)

4. **Pre-training**
   - 유사 도메인 데이터로 사전 학습
   - Transfer learning 적용

5. **Hybrid 접근**
   - Transformer features + ML classifier
   - Stacking ensemble

### 5.4 실무 체크리스트

✅ **즉시 적용 가능**:
- [x] Gradient Boosting + 12D/16D Latent
- [x] AutoEncoder로 latent features 생성
- [x] 기존 30D features와 결합

❌ **추가 연구 필요**:
- [ ] Transformer 모델 (현재 성능 부족)
- [ ] 대규모 데이터 수집 후 재평가
- [ ] Hybrid 아키텍처 실험

---

## 6. 기술적 세부사항

### 6.1 재현성 정보

**환경**:
- Python 3.8+
- PyTorch 2.0+
- scikit-learn 1.3+
- Device: CPU (GPU 사용 시 더 빠른 학습 가능)

**파일**:
- `transformer_models.py`: 모델 구현 및 학습 코드
- `best_FTTransformer.pth`: FT-Transformer 가중치
- `best_SimpleTabTransformer.pth`: TabTransformer 가중치
- `transformer_vs_ml_results.csv`: 전체 결과
- `transformer_vs_ml_comparison.png`: 시각화

### 6.2 학습 시간

| Model | Latent Dim | Epochs | Time (CPU) |
|-------|------------|--------|------------|
| FT-Transformer | 8D | 100 | ~45분 |
| TabTransformer | 8D | 45 | ~25분 |
| FT-Transformer | 12D | 38 | ~20분 |
| TabTransformer | 12D | 36 | ~20분 |
| FT-Transformer | 16D | 62 | ~35분 |
| TabTransformer | 16D | 52 | ~30분 |

**Total**: ~175분 (약 3시간)

### 6.3 메모리 사용량

| Model | Parameters | Memory (Training) | Memory (Inference) |
|-------|------------|-------------------|-------------------|
| FT-Transformer | 224K | ~500MB | ~50MB |
| TabTransformer | 107K | ~300MB | ~30MB |
| Gradient Boosting | - | ~100MB | ~10MB |

---

## 7. 참고문헌

1. **FT-Transformer**:
   - Gorishniy et al., "Revisiting Deep Learning Models for Tabular Data", NeurIPS 2021
   - https://arxiv.org/abs/2106.11959

2. **TabTransformer**:
   - Huang et al., "TabTransformer: Tabular Data Modeling Using Contextual Embeddings", 2020
   - https://arxiv.org/abs/2012.06678

3. **Tree-based Models for Tabular Data**:
   - Shwartz-Ziv & Armon, "Tabular data: Deep learning is not all you need", 2021
   - https://arxiv.org/abs/2106.03253

---

## 부록: 상세 실험 로그

### A.1 FT-Transformer 학습 로그 (8D Latent)

```
Epoch [10/100]
  Train Loss: 1.0591, Val Loss: 1.0409
  F1: 0.3831, Acc: 0.6025, AUC: 0.6204

Epoch [90/100]
  Train Loss: 1.0043, Val Loss: 0.9822
  F1: 0.4517, Acc: 0.6344, AUC: 0.6954

최종 성능: F1: 0.4517, Acc: 0.6344, AUC: 0.6954
```

### A.2 TabTransformer 학습 로그 (8D Latent)

```
Epoch [10/100]
  Train Loss: 0.9411, Val Loss: 0.9094
  F1: 0.4880, Acc: 0.6045, AUC: 0.7514

Epoch [30/100]
  Train Loss: 0.8951, Val Loss: 0.9043
  F1: 0.5104, Acc: 0.7034, AUC: 0.7574

Early stopping at epoch 45
최종 성능: F1: 0.5104, Acc: 0.7034, AUC: 0.7574
```

---

**보고서 작성**: Kiro AI Assistant  
**검증**: Ablation Study 기반 실험 결과  
**최종 업데이트**: 2026-01-15
