# Optimizer 및 Scheduler 업데이트 요약

## 🔄 변경 사항

### 이전 구성
```python
# Optimizer
optimizer = torch.optim.AdamW(
    model.parameters(), 
    lr=1e-3, 
    weight_decay=1e-4
)

# Scheduler
scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
    optimizer, 
    mode='min', 
    factor=0.5, 
    patience=10
)
```

### 새로운 구성
```python
# Optimizer (개선됨)
optimizer = torch.optim.AdamW(
    model.parameters(), 
    lr=1e-3, 
    weight_decay=1e-4,
    betas=(0.9, 0.999),  # 추가
    eps=1e-8             # 추가
)

# Scheduler (불균형 데이터에 최적화)
scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(
    optimizer,
    T_0=10,        # 초기 재시작 주기 (10 epochs)
    T_mult=2,      # 재시작마다 주기 2배 증가
    eta_min=1e-6   # 최소 학습률
)
```

---

## 🎯 변경 이유

### 1. AdamW Optimizer 파라미터 명시화
- **betas=(0.9, 0.999)**: 모멘텀 계수 명시적 설정
- **eps=1e-8**: 수치 안정성을 위한 작은 값
- 기존에도 AdamW를 사용했지만, 파라미터를 명시적으로 설정하여 재현성 향상

### 2. CosineAnnealingWarmRestarts 스케줄러 도입

#### ReduceLROnPlateau의 한계
- **Validation loss 기반**: 불균형 데이터에서 validation loss가 불안정할 수 있음
- **Patience 필요**: 10 epoch 동안 개선이 없어야 학습률 감소
- **단조 감소**: 한번 감소한 학습률은 다시 증가하지 않음

#### CosineAnnealingWarmRestarts의 장점
- **주기적 재시작**: Local minima에서 탈출 가능
- **부드러운 감소**: Cosine 함수로 학습률이 부드럽게 감소
- **불균형 데이터에 효과적**: 
  - 주기적으로 높은 학습률로 재시작하여 다양한 해 탐색
  - 불량률 22.42%인 불균형 데이터에서 더 나은 성능
- **자동 스케줄링**: Validation loss에 의존하지 않음

---

## 📊 학습률 스케줄 비교

### ReduceLROnPlateau
```
Epoch:  0-10  → lr = 1e-3
Epoch: 11-20  → lr = 1e-3 (patience 대기)
Epoch: 21-30  → lr = 5e-4 (감소)
Epoch: 31-40  → lr = 5e-4
Epoch: 41-50  → lr = 2.5e-4 (감소)
...
```
- 단조 감소
- Validation loss에 의존

### CosineAnnealingWarmRestarts
```
Epoch:  0-10  → lr: 1e-3 → 1e-6 (cosine)
Epoch: 10     → lr: 1e-3 (재시작)
Epoch: 11-30  → lr: 1e-3 → 1e-6 (cosine, 20 epochs)
Epoch: 30     → lr: 1e-3 (재시작)
Epoch: 31-70  → lr: 1e-3 → 1e-6 (cosine, 40 epochs)
...
```
- 주기적 재시작
- 부드러운 cosine 감소
- Local minima 탈출

---

## 🔬 불균형 데이터에서의 효과

### 다이캐스팅 데이터 특성
- **불량률**: 22.42% (불균형)
- **정상**: 5,845 samples (77.58%)
- **불량**: 1,690 samples (22.42%)

### CosineAnnealingWarmRestarts의 이점
1. **주기적 재탐색**: 
   - 높은 학습률로 재시작하여 소수 클래스(불량) 패턴 재학습
   - Local minima에 갇히지 않음

2. **부드러운 수렴**:
   - Cosine 함수로 학습률이 부드럽게 감소
   - 급격한 학습률 변화로 인한 불안정성 방지

3. **자동 스케줄링**:
   - Validation loss에 의존하지 않아 불균형 데이터의 불안정한 validation 영향 최소화

---

## 📝 업데이트된 파일 목록

### 코드 파일
- ✅ `autoencoder_model.py` - Optimizer 및 Scheduler 변경

### 문서 파일
- ✅ `model_summary.md` - 모델 구성 업데이트
- ✅ `README.md` - 프로젝트 개요 업데이트
- ✅ `FINAL_ABLATION_REPORT.md` - Ablation study 보고서 업데이트
- ✅ `EXECUTIVE_SUMMARY.md` - Executive summary 업데이트
- ✅ `LATENT_DIM_ABLATION.md` - Latent dimension ablation 업데이트
- ✅ `ABLATION_STUDY.md` - Ablation study 업데이트
- ✅ `POC_SUMMARY.md` - PoC 요약 업데이트

---

## 🚀 기대 효과

### 1. 성능 향상
- 불균형 데이터에서 더 나은 F1-Score 기대
- Local minima 탈출로 최적해 탐색 개선

### 2. 학습 안정성
- 부드러운 학습률 감소로 안정적 수렴
- 주기적 재시작으로 과적합 방지

### 3. 재현성
- 명시적 파라미터 설정으로 재현성 향상
- Validation loss에 의존하지 않아 일관된 학습

---

## 📌 참고 사항

### CosineAnnealingWarmRestarts 파라미터 설명

- **T_0=10**: 첫 번째 재시작까지 10 epochs
- **T_mult=2**: 재시작마다 주기가 2배로 증가
  - 1차: 10 epochs
  - 2차: 20 epochs
  - 3차: 40 epochs
  - 4차: 80 epochs (100 epochs 학습 시 도달 안함)
- **eta_min=1e-6**: 최소 학습률 (완전히 0이 되지 않음)

### 학습 로그 변경
- 기존: Epoch 정보만 출력
- 변경: **현재 학습률(LR)도 함께 출력**
- Best model 저장 시 메시지 출력

---

**업데이트 일자**: 2026-01-16  
**버전**: v1.1  
**작성자**: AI Assistant
