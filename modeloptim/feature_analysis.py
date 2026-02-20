import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

# 데이터 로드
df = pd.read_csv('/Users/kang/Downloads/dataset/DieCasting_Quality_Raw_Data.csv', header=[0, 1])

# 컬럼명 정리
df.columns = ['_'.join(col).strip() for col in df.columns.values]

print("=" * 80)
print("다이캐스팅 품질 데이터 Feature 분석")
print("=" * 80)

# 1. 기본 정보
print("\n[1] 데이터 기본 정보")
print(f"총 샘플 수: {len(df)}")
print(f"총 Feature 수: {len(df.columns)}")
print(f"\n데이터 shape: {df.shape}")

# 2. Feature 그룹별 분류
process_features = [col for col in df.columns if col.startswith('Process_')]
sensor_features = [col for col in df.columns if col.startswith('Sensor_')]
defect_features = [col for col in df.columns if col.startswith('Defects_')]

print(f"\n[2] Feature 그룹별 분류")
print(f"Process Features: {len(process_features)}개")
print(f"Sensor Features: {len(sensor_features)}개")
print(f"Defect Features: {len(defect_features)}개")

# 3. 결측치 확인
print(f"\n[3] 결측치 분석")
missing = df.isnull().sum()
if missing.sum() > 0:
    print(missing[missing > 0])
else:
    print("결측치 없음")

# 4. 기술 통계량
print(f"\n[4] Process Features 기술 통계량")
print(df[process_features].describe().T)

print(f"\n[5] Sensor Features 기술 통계량")
print(df[sensor_features].describe().T)

# 5. 불량 발생 현황
print(f"\n[6] 불량(Defects) 발생 현황")
defect_counts = df[defect_features].sum().sort_values(ascending=False)
print(defect_counts)
print(f"\n총 불량 발생 건수: {defect_counts.sum()}")
print(f"불량률: {(df[defect_features].sum(axis=1) > 0).mean() * 100:.2f}%")

# 6. 상관관계 분석
print(f"\n[7] 상관관계 분석 (상위 10개)")

# 전체 불량 여부 컬럼 생성
df['has_defect'] = (df[defect_features].sum(axis=1) > 0).astype(int)

# Process features와 불량 간 상관관계
correlations = []
for col in process_features + sensor_features:
    if df[col].dtype in ['float64', 'int64']:
        corr = df[col].corr(df['has_defect'])
        correlations.append({'feature': col, 'correlation': abs(corr)})

corr_df = pd.DataFrame(correlations).sort_values('correlation', ascending=False)
print(corr_df.head(10))

# 7. 데이터 분포 분석
print(f"\n[8] 주요 Process Features 분포")
for col in process_features[:5]:
    print(f"\n{col}:")
    print(f"  평균: {df[col].mean():.4f}")
    print(f"  표준편차: {df[col].std():.4f}")
    print(f"  최소값: {df[col].min():.4f}")
    print(f"  최대값: {df[col].max():.4f}")
    print(f"  왜도(Skewness): {stats.skew(df[col]):.4f}")
    print(f"  첨도(Kurtosis): {stats.kurtosis(df[col]):.4f}")

# 8. 불량 유형별 분석
print(f"\n[9] 불량 유형별 상세 분석")
defect_types = {}
for col in defect_features:
    defect_name = col.replace('Defects_', '')
    count = df[col].sum()
    if count > 0:
        defect_types[defect_name] = count

defect_types_sorted = dict(sorted(defect_types.items(), key=lambda x: x[1], reverse=True))
for defect, count in defect_types_sorted.items():
    print(f"{defect}: {count}건 ({count/len(df)*100:.2f}%)")

# 9. Feature 변동성 분석
print(f"\n[10] Feature 변동성 분석 (CV: Coefficient of Variation)")
cv_analysis = []
for col in process_features + sensor_features:
    if df[col].dtype in ['float64', 'int64'] and df[col].mean() != 0:
        cv = (df[col].std() / df[col].mean()) * 100
        cv_analysis.append({'feature': col, 'CV(%)': cv})

cv_df = pd.DataFrame(cv_analysis).sort_values('CV(%)', ascending=False)
print(cv_df.head(10))

print("\n" + "=" * 80)
print("분석 완료!")
print("=" * 80)
