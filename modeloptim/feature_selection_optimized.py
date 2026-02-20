"""
Feature Selection 최적화
다양한 feature 개수 테스트: 15, 20, 25개
+ 12D Latent Vector
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import f1_score, accuracy_score, roc_auc_score
import matplotlib.pyplot as plt
import seaborn as sns
import pickle
import json

plt.style.use('seaborn-v0_8-darkgrid')

print("="*80)
print("Feature Selection 최적화")
print("="*80)

# 1. 데이터 로딩
print("\n1. 데이터 로딩 중...")
df = pd.read_csv('/Users/kang/Downloads/dataset/DieCasting_Quality_Raw_Data.csv', header=[0, 1])
df.columns = ['_'.join(col).strip() for col in df.columns.values]

process_features = [col for col in df.columns if col.startswith('Process_')]
sensor_features = [col for col in df.columns if col.startswith('Sensor_')]
feature_cols = [col for col in process_features + sensor_features if col != 'Process_id'][:30]

X = df[feature_cols].values
X = np.nan_to_num(X, nan=np.nanmean(X, axis=0))

defect_features = [col for col in df.columns if col.startswith('Defects_')]
y = (df[defect_features].sum(axis=1) > 0).astype(int).values

# 2. Latent features 로딩
X_latent = np.load('latent_vectors_12d.npy')

# 3. Baseline 모델로 feature importance 계산
print("\n2. Feature Importance 계산 중...")
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
X_combined_full = np.hstack([X_scaled, X_latent])

X_train, X_test, y_train, y_test = train_test_split(
    X_combined_full, y, test_size=0.2, random_state=42, stratify=y
)

gb_baseline = GradientBoostingClassifier(
    n_estimators=200, max_depth=6, learning_rate=0.1,
    subsample=1.0, random_state=42, verbose=0
)
gb_baseline.fit(X_train, y_train)

feature_importance = gb_baseline.feature_importances_[:30]
importance_df = pd.DataFrame({
    'Feature': feature_cols,
    'Importance': feature_importance
}).sort_values('Importance', ascending=False)

# 4. 다양한 feature 개수 테스트
print("\n3. 다양한 feature 개수 테스트 중...")
feature_counts = [15, 20, 25, 30]
results = []

for n_features in feature_counts:
    print(f"\n   Testing {n_features} features...")
    
    # Feature 선택
    if n_features == 30:
        selected_features = feature_cols
        selected_indices = list(range(30))
    else:
        selected_features = importance_df.head(n_features)['Feature'].tolist()
        selected_indices = [feature_cols.index(f) for f in selected_features]
    
    # 데이터 준비
    X_selected = X[:, selected_indices]
    scaler_temp = StandardScaler()
    X_selected_scaled = scaler_temp.fit_transform(X_selected)
    X_combined = np.hstack([X_selected_scaled, X_latent])
    
    # Train-test split
    X_train_temp, X_test_temp, y_train_temp, y_test_temp = train_test_split(
        X_combined, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # 모델 학습
    gb_temp = GradientBoostingClassifier(
        n_estimators=200, max_depth=6, learning_rate=0.1,
        subsample=1.0, random_state=42, verbose=0
    )
    gb_temp.fit(X_train_temp, y_train_temp)
    
    # 평가
    y_pred = gb_temp.predict(X_test_temp)
    y_proba = gb_temp.predict_proba(X_test_temp)[:, 1]
    
    f1 = f1_score(y_test_temp, y_pred)
    acc = accuracy_score(y_test_temp, y_pred)
    auc = roc_auc_score(y_test_temp, y_proba)
    
    total_dim = n_features + 12
    
    results.append({
        'n_features': n_features,
        'total_dim': total_dim,
        'f1_score': f1,
        'accuracy': acc,
        'roc_auc': auc,
        'selected_features': selected_features,
        'model': gb_temp,
        'scaler': scaler_temp
    })
    
    print(f"      F1: {f1:.4f}, Acc: {acc:.4f}, AUC: {auc:.4f}")

# 5. 결과 분석
print("\n" + "="*80)
print("결과 비교")
print("="*80)

results_df = pd.DataFrame([
    {
        'Features': f"{r['n_features']}D + 12D Latent",
        'Total Dim': r['total_dim'],
        'F1-Score': r['f1_score'],
        'Accuracy': r['accuracy'],
        'ROC-AUC': r['roc_auc'],
        'vs 42D': f"{((r['f1_score'] - results[-1]['f1_score']) / results[-1]['f1_score'] * 100):+.2f}%"
    }
    for r in results
])

print("\n" + results_df.to_string(index=False))

# 6. 최적 구성 선택 (F1-Score 기준, 성능 저하 1% 이내)
baseline_f1 = results[-1]['f1_score']
optimal_config = None

for r in results:
    f1_diff_pct = ((r['f1_score'] - baseline_f1) / baseline_f1) * 100
    if f1_diff_pct >= -1.0:  # 1% 이내 성능 저하
        optimal_config = r
        break

if optimal_config is None:
    optimal_config = results[-1]  # Baseline 사용

print(f"\n✅ 최적 구성 선택:")
print(f"   Features: {optimal_config['n_features']}D + 12D Latent = {optimal_config['total_dim']}D")
print(f"   F1-Score: {optimal_config['f1_score']:.4f}")
print(f"   Accuracy: {optimal_config['accuracy']:.4f}")
print(f"   ROC-AUC: {optimal_config['roc_auc']:.4f}")

# 7. 시각화
print("\n4. 시각화 생성 중...")

fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# (1) F1-Score vs Feature Count
ax1 = axes[0, 0]
feature_counts_plot = [r['n_features'] for r in results]
f1_scores = [r['f1_score'] for r in results]
colors = ['#2ecc71' if r == optimal_config else '#3498db' for r in results]

bars = ax1.bar(range(len(results)), f1_scores, color=colors, alpha=0.7, edgecolor='black', linewidth=2)
ax1.set_xticks(range(len(results)))
ax1.set_xticklabels([f"{r['n_features']}D\n+12D" for r in results], fontsize=10)
ax1.set_ylabel('F1-Score', fontsize=11, fontweight='bold')
ax1.set_title('F1-Score by Feature Count', fontsize=13, fontweight='bold')
ax1.grid(axis='y', alpha=0.3)
ax1.axhline(y=baseline_f1, color='red', linestyle='--', linewidth=2, label='Baseline (30D+12D)')
ax1.legend()

for i, (bar, f1) in enumerate(zip(bars, f1_scores)):
    ax1.text(bar.get_x() + bar.get_width()/2., f1 + 0.005,
            f'{f1:.4f}', ha='center', va='bottom', fontsize=10, fontweight='bold')

# (2) All Metrics Comparison
ax2 = axes[0, 1]
metrics = ['F1-Score', 'Accuracy', 'ROC-AUC']
x = np.arange(len(metrics))
width = 0.2

for i, r in enumerate(results):
    scores = [r['f1_score'], r['accuracy'], r['roc_auc']]
    offset = (i - len(results)/2 + 0.5) * width
    label = f"{r['n_features']}D+12D"
    color = '#2ecc71' if r == optimal_config else None
    ax2.bar(x + offset, scores, width, label=label, alpha=0.7, color=color)

ax2.set_ylabel('Score', fontsize=11, fontweight='bold')
ax2.set_title('All Metrics Comparison', fontsize=13, fontweight='bold')
ax2.set_xticks(x)
ax2.set_xticklabels(metrics, fontsize=10)
ax2.legend(fontsize=9)
ax2.grid(axis='y', alpha=0.3)
ax2.set_ylim([0.65, 0.95])

# (3) Dimension Reduction
ax3 = axes[1, 0]
total_dims = [r['total_dim'] for r in results]
colors_dim = ['#2ecc71' if r == optimal_config else '#3498db' for r in results]

bars = ax3.bar(range(len(results)), total_dims, color=colors_dim, alpha=0.7, edgecolor='black', linewidth=2)
ax3.set_xticks(range(len(results)))
ax3.set_xticklabels([f"{r['n_features']}D\n+12D" for r in results], fontsize=10)
ax3.set_ylabel('Total Dimensions', fontsize=11, fontweight='bold')
ax3.set_title('Total Dimensions by Configuration', fontsize=13, fontweight='bold')
ax3.grid(axis='y', alpha=0.3)

for bar, dim in zip(bars, total_dims):
    ax3.text(bar.get_x() + bar.get_width()/2., dim + 0.5,
            f'{dim}D', ha='center', va='bottom', fontsize=11, fontweight='bold')

# (4) Top Features (Optimal Config)
ax4 = axes[1, 1]
n_top = min(15, optimal_config['n_features'])
top_features = importance_df.head(n_top)
colors_feat = plt.cm.RdYlGn_r(np.linspace(0.2, 0.8, n_top))

bars = ax4.barh(range(n_top), top_features['Importance'], color=colors_feat)
ax4.set_yticks(range(n_top))
ax4.set_yticklabels(top_features['Feature'], fontsize=8)
ax4.set_xlabel('Importance', fontsize=11, fontweight='bold')
ax4.set_title(f'Top {n_top} Features (Optimal Config)', fontsize=13, fontweight='bold')
ax4.grid(axis='x', alpha=0.3)
ax4.invert_yaxis()

plt.suptitle(f'Feature Selection Optimization\nOptimal: {optimal_config["n_features"]}D + 12D Latent = {optimal_config["total_dim"]}D',
            fontsize=16, fontweight='bold')
plt.tight_layout()
plt.savefig('feature_selection_optimized.png', dpi=300, bbox_inches='tight')
print("   ✅ feature_selection_optimized.png")
plt.close()

# 8. 최적 구성 저장
print("\n5. 최적 구성 저장 중...")

optimal_info = {
    'n_features': optimal_config['n_features'],
    'total_dim': optimal_config['total_dim'],
    'selected_features': optimal_config['selected_features'],
    'performance': {
        'f1_score': optimal_config['f1_score'],
        'accuracy': optimal_config['accuracy'],
        'roc_auc': optimal_config['roc_auc']
    },
    'feature_importance': importance_df.head(optimal_config['n_features']).to_dict('records')
}

with open('optimal_features_config.json', 'w') as f:
    json.dump(optimal_info, f, indent=2)
print("   ✅ optimal_features_config.json")

# 배포용 모델 저장
with open(f'deployment_models/scaler_{optimal_config["n_features"]}d.pkl', 'wb') as f:
    pickle.dump(optimal_config['scaler'], f)
print(f"   ✅ scaler_{optimal_config['n_features']}d.pkl")

with open(f'deployment_models/gradient_boosting_model_{optimal_config["total_dim"]}d.pkl', 'wb') as f:
    pickle.dump(optimal_config['model'], f)
print(f"   ✅ gradient_boosting_model_{optimal_config['total_dim']}d.pkl")

# 9. 최종 요약
print("\n" + "="*80)
print("✅ Feature Selection 최적화 완료!")
print("="*80)

print(f"\n📊 최적 구성:")
print(f"  • Features: {optimal_config['n_features']}D baseline + 12D latent = {optimal_config['total_dim']}D total")
print(f"  • F1-Score: {optimal_config['f1_score']:.4f}")
print(f"  • Accuracy: {optimal_config['accuracy']:.4f}")
print(f"  • ROC-AUC: {optimal_config['roc_auc']:.4f}")

dim_reduction = ((42 - optimal_config['total_dim']) / 42) * 100
print(f"\n  • 차원 감소: {dim_reduction:.1f}% (42D → {optimal_config['total_dim']}D)")

baseline_f1 = results[-1]['f1_score']
f1_change = ((optimal_config['f1_score'] - baseline_f1) / baseline_f1) * 100
print(f"  • F1-Score 변화: {f1_change:+.2f}%")

print(f"\n💡 권장사항:")
if abs(f1_change) <= 1.0:
    print(f"  ✅ 최적 구성 사용 권장!")
    print(f"  • 성능 유지 ({abs(f1_change):.2f}% 이내)")
    print(f"  • {dim_reduction:.1f}% 차원 감소로 효율성 향상")
else:
    print(f"  ⚠️  Baseline (42D) 사용 권장")
    print(f"  • 최고 성능 유지")

print("\n" + "="*80)
