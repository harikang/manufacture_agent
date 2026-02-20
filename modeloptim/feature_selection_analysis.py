"""
Feature Selection 분석
30개 features → 20개 features 선택
+ 12D Latent Vector = 32D Total
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import f1_score, accuracy_score, roc_auc_score, classification_report
import matplotlib.pyplot as plt
import seaborn as sns
import pickle

plt.style.use('seaborn-v0_8-darkgrid')

print("="*80)
print("Feature Selection 분석")
print("="*80)

# 1. 데이터 로딩
print("\n1. 데이터 로딩 중...")
df = pd.read_csv('/Users/kang/Downloads/dataset/DieCasting_Quality_Raw_Data.csv', header=[0, 1])
df.columns = ['_'.join(col).strip() for col in df.columns.values]

# Features 선택
process_features = [col for col in df.columns if col.startswith('Process_')]
sensor_features = [col for col in df.columns if col.startswith('Sensor_')]
feature_cols = [col for col in process_features + sensor_features if col != 'Process_id'][:30]

X = df[feature_cols].values
X = np.nan_to_num(X, nan=np.nanmean(X, axis=0))

# Labels
defect_features = [col for col in df.columns if col.startswith('Defects_')]
y = (df[defect_features].sum(axis=1) > 0).astype(int).values

print(f"   원본 데이터 shape: {X.shape}")
print(f"   불량률: {y.mean()*100:.2f}%")

# 2. Latent features 로딩
print("\n2. Latent features 로딩 중...")
X_latent = np.load('latent_vectors_12d.npy')
print(f"   Latent features shape: {X_latent.shape}")

# 3. Scaling
print("\n3. Feature Scaling 중...")
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# 4. Combined features (30D + 12D = 42D)
X_combined_full = np.hstack([X_scaled, X_latent])
print(f"   Combined features (full): {X_combined_full.shape}")

# 5. Train-test split
X_train, X_test, y_train, y_test = train_test_split(
    X_combined_full, y, test_size=0.2, random_state=42, stratify=y
)

# 6. Baseline 모델 학습 (42D)
print("\n4. Baseline 모델 학습 (30D + 12D = 42D)...")
gb_baseline = GradientBoostingClassifier(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.1,
    subsample=1.0,
    random_state=42
)
gb_baseline.fit(X_train, y_train)

y_pred_baseline = gb_baseline.predict(X_test)
y_proba_baseline = gb_baseline.predict_proba(X_test)[:, 1]

f1_baseline = f1_score(y_test, y_pred_baseline)
acc_baseline = accuracy_score(y_test, y_pred_baseline)
auc_baseline = roc_auc_score(y_test, y_proba_baseline)

print(f"\n   Baseline 성능 (42D):")
print(f"   - F1-Score: {f1_baseline:.4f}")
print(f"   - Accuracy: {acc_baseline:.4f}")
print(f"   - ROC-AUC: {auc_baseline:.4f}")

# 7. Feature Importance 계산 (30D baseline features만)
print("\n5. Feature Importance 계산 중...")
feature_importance = gb_baseline.feature_importances_[:30]  # 처음 30개만 (baseline features)

# Feature importance DataFrame
importance_df = pd.DataFrame({
    'Feature': feature_cols,
    'Importance': feature_importance
}).sort_values('Importance', ascending=False)

print("\n   Top 20 Features:")
print(importance_df.head(20).to_string(index=False))

# 8. Top 20 features 선택
top_20_features = importance_df.head(20)['Feature'].tolist()
top_20_indices = [feature_cols.index(f) for f in top_20_features]

print(f"\n6. Top 20 Features 선택 완료")
print(f"   선택된 features: {len(top_20_features)}개")

# 9. 선택된 features로 새로운 데이터셋 생성
X_selected = X[:, top_20_indices]
X_selected_scaled = scaler.fit_transform(X_selected)

# 10. Combined features (20D + 12D = 32D)
X_combined_selected = np.hstack([X_selected_scaled, X_latent])
print(f"   Combined features (selected): {X_combined_selected.shape}")

# 11. Train-test split (selected)
X_train_sel, X_test_sel, y_train_sel, y_test_sel = train_test_split(
    X_combined_selected, y, test_size=0.2, random_state=42, stratify=y
)

# 12. 선택된 features로 모델 학습 (32D)
print("\n7. Feature Selection 모델 학습 (20D + 12D = 32D)...")
gb_selected = GradientBoostingClassifier(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.1,
    subsample=1.0,
    random_state=42
)
gb_selected.fit(X_train_sel, y_train_sel)

y_pred_selected = gb_selected.predict(X_test_sel)
y_proba_selected = gb_selected.predict_proba(X_test_sel)[:, 1]

f1_selected = f1_score(y_test_sel, y_pred_selected)
acc_selected = accuracy_score(y_test_sel, y_pred_selected)
auc_selected = roc_auc_score(y_test_sel, y_proba_selected)

print(f"\n   Feature Selection 성능 (32D):")
print(f"   - F1-Score: {f1_selected:.4f}")
print(f"   - Accuracy: {acc_selected:.4f}")
print(f"   - ROC-AUC: {auc_selected:.4f}")

# 13. 성능 비교
print("\n" + "="*80)
print("성능 비교")
print("="*80)

comparison_df = pd.DataFrame({
    'Configuration': ['Baseline (30D + 12D)', 'Selected (20D + 12D)'],
    'Total Dim': [42, 32],
    'F1-Score': [f1_baseline, f1_selected],
    'Accuracy': [acc_baseline, acc_selected],
    'ROC-AUC': [auc_baseline, auc_selected],
    'Dimension Reduction': ['0%', '23.8%']
})

print("\n" + comparison_df.to_string(index=False))

# 성능 차이 계산
f1_diff = ((f1_selected - f1_baseline) / f1_baseline) * 100
acc_diff = ((acc_selected - acc_baseline) / acc_baseline) * 100
auc_diff = ((auc_selected - auc_baseline) / auc_baseline) * 100

print(f"\n성능 변화:")
print(f"  - F1-Score: {f1_diff:+.2f}%")
print(f"  - Accuracy: {acc_diff:+.2f}%")
print(f"  - ROC-AUC: {auc_diff:+.2f}%")

# 14. 시각화
print("\n8. 시각화 생성 중...")

fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# (1) Feature Importance (Top 20)
ax1 = axes[0, 0]
top_20_imp = importance_df.head(20)
colors = plt.cm.RdYlGn_r(np.linspace(0.2, 0.8, 20))
bars = ax1.barh(range(20), top_20_imp['Importance'], color=colors)
ax1.set_yticks(range(20))
ax1.set_yticklabels(top_20_imp['Feature'], fontsize=9)
ax1.set_xlabel('Importance', fontsize=11, fontweight='bold')
ax1.set_title('Top 20 Features by Importance', fontsize=13, fontweight='bold')
ax1.grid(axis='x', alpha=0.3)
ax1.invert_yaxis()

# 값 레이블
for i, (bar, val) in enumerate(zip(bars, top_20_imp['Importance'])):
    ax1.text(val + 0.001, i, f'{val:.4f}', va='center', fontsize=8)

# (2) 성능 비교 (Bar Chart)
ax2 = axes[0, 1]
metrics = ['F1-Score', 'Accuracy', 'ROC-AUC']
baseline_scores = [f1_baseline, acc_baseline, auc_baseline]
selected_scores = [f1_selected, acc_selected, auc_selected]

x = np.arange(len(metrics))
width = 0.35

bars1 = ax2.bar(x - width/2, baseline_scores, width, label='Baseline (42D)', color='#3498db', alpha=0.8)
bars2 = ax2.bar(x + width/2, selected_scores, width, label='Selected (32D)', color='#2ecc71', alpha=0.8)

ax2.set_ylabel('Score', fontsize=11, fontweight='bold')
ax2.set_title('Performance Comparison', fontsize=13, fontweight='bold')
ax2.set_xticks(x)
ax2.set_xticklabels(metrics, fontsize=10)
ax2.legend(fontsize=10)
ax2.grid(axis='y', alpha=0.3)
ax2.set_ylim([0.65, 0.95])

# 값 레이블
for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + 0.005,
                f'{height:.4f}', ha='center', va='bottom', fontsize=9, fontweight='bold')

# (3) Dimension Reduction
ax3 = axes[1, 0]
configs = ['Baseline', 'Selected']
dimensions = [42, 32]
colors_dim = ['#e74c3c', '#2ecc71']

bars = ax3.bar(configs, dimensions, color=colors_dim, alpha=0.7, edgecolor='black', linewidth=2)
ax3.set_ylabel('Total Dimensions', fontsize=11, fontweight='bold')
ax3.set_title('Dimension Reduction (42D → 32D)', fontsize=13, fontweight='bold')
ax3.grid(axis='y', alpha=0.3)

# 값 레이블
for bar, dim in zip(bars, dimensions):
    ax3.text(bar.get_x() + bar.get_width()/2., dim + 1,
            f'{dim}D', ha='center', va='bottom', fontsize=12, fontweight='bold')

# 감소율 표시
ax3.text(0.5, 37, '23.8% 감소', ha='center', fontsize=11, 
        bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.5))

# (4) Feature Categories
ax4 = axes[1, 1]

# 선택된 features의 카테고리 분석
process_count = sum(1 for f in top_20_features if f.startswith('Process_'))
sensor_count = sum(1 for f in top_20_features if f.startswith('Sensor_'))

categories = ['Process\nFeatures', 'Sensor\nFeatures']
counts = [process_count, sensor_count]
colors_cat = ['#3498db', '#e67e22']

wedges, texts, autotexts = ax4.pie(counts, labels=categories, autopct='%1.1f%%',
                                     colors=colors_cat, startangle=90,
                                     textprops={'fontsize': 11, 'fontweight': 'bold'})

ax4.set_title(f'Selected Features Distribution (Top 20)\nProcess: {process_count}, Sensor: {sensor_count}',
             fontsize=13, fontweight='bold')

plt.suptitle('Feature Selection Analysis: 30D → 20D (+ 12D Latent = 32D Total)',
            fontsize=16, fontweight='bold')
plt.tight_layout()
plt.savefig('feature_selection_analysis.png', dpi=300, bbox_inches='tight')
print("   ✅ feature_selection_analysis.png 저장 완료")
plt.close()

# 15. 선택된 features 저장
print("\n9. 선택된 features 저장 중...")

selected_features_info = {
    'top_20_features': top_20_features,
    'feature_importance': importance_df.head(20).to_dict('records'),
    'performance': {
        'baseline_42d': {
            'f1_score': f1_baseline,
            'accuracy': acc_baseline,
            'roc_auc': auc_baseline
        },
        'selected_32d': {
            'f1_score': f1_selected,
            'accuracy': acc_selected,
            'roc_auc': auc_selected
        }
    }
}

import json
with open('selected_features_top20.json', 'w') as f:
    json.dump(selected_features_info, f, indent=2)
print("   ✅ selected_features_top20.json 저장 완료")

# 16. 배포용 모델 및 scaler 저장
print("\n10. 배포용 모델 저장 중...")

# Scaler (20D features용)
scaler_20d = StandardScaler()
scaler_20d.fit(X_selected)

with open('deployment_models/scaler_20d.pkl', 'wb') as f:
    pickle.dump(scaler_20d, f)
print("   ✅ scaler_20d.pkl 저장 완료")

# Gradient Boosting 모델 (32D)
with open('deployment_models/gradient_boosting_model_32d.pkl', 'wb') as f:
    pickle.dump(gb_selected, f)
print("   ✅ gradient_boosting_model_32d.pkl 저장 완료")

# 17. 최종 요약
print("\n" + "="*80)
print("✅ Feature Selection 완료!")
print("="*80)

print(f"\n📊 결과 요약:")
print(f"  • 원본: 30D baseline + 12D latent = 42D total")
print(f"  • 선택: 20D baseline + 12D latent = 32D total")
print(f"  • 차원 감소: 23.8% (42D → 32D)")
print(f"\n  • F1-Score: {f1_baseline:.4f} → {f1_selected:.4f} ({f1_diff:+.2f}%)")
print(f"  • Accuracy: {acc_baseline:.4f} → {acc_selected:.4f} ({acc_diff:+.2f}%)")
print(f"  • ROC-AUC: {auc_baseline:.4f} → {auc_selected:.4f} ({auc_diff:+.2f}%)")

print(f"\n📁 생성된 파일:")
print(f"  • feature_selection_analysis.png")
print(f"  • selected_features_top20.json")
print(f"  • deployment_models/scaler_20d.pkl")
print(f"  • deployment_models/gradient_boosting_model_32d.pkl")

print(f"\n💡 권장사항:")
if f1_diff >= -1.0:  # 1% 이내 성능 저하
    print(f"  ✅ Feature Selection 권장!")
    print(f"  • 성능 유지하면서 23.8% 차원 감소")
    print(f"  • 추론 속도 향상 예상")
    print(f"  • 메모리 사용량 감소")
else:
    print(f"  ⚠️  성능 저하 검토 필요")
    print(f"  • F1-Score {abs(f1_diff):.2f}% 감소")
    print(f"  • 더 많은 features 선택 고려")

print("\n" + "="*80)
