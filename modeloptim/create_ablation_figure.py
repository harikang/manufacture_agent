import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# Set style
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("Set2")

# Load results
df = pd.read_csv('ml_classification_results.csv')

# Create main ablation study figure
fig = plt.figure(figsize=(20, 10))
gs = fig.add_gridspec(2, 3, hspace=0.3, wspace=0.3)

models = ['Gradient Boosting', 'XGBoost', 'LightGBM']
feature_sets_order = ['Original Only', 'Latent Only', 'Original + Latent']
colors = ['#3498db', '#e74c3c', '#2ecc71']
labels = ['Baseline\n(30D)', 'Latent Only\n(8D)', 'Combined\n(30D+8D=38D)']

# Top row: F1-Score comparison
for idx, model in enumerate(models):
    ax = fig.add_subplot(gs[0, idx])
    
    model_data = df[df['Model'] == model]
    values = [model_data[model_data['Feature Set'] == fs]['F1-Score'].values[0] 
              for fs in feature_sets_order]
    
    bars = ax.bar(range(3), values, color=colors, alpha=0.85, edgecolor='black', linewidth=2)
    
    # Add values on bars
    for i, (bar, val) in enumerate(zip(bars, values)):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.01,
               f'{val:.4f}',
               ha='center', va='bottom', fontsize=12, fontweight='bold')
    
    # Calculate and show improvement
    baseline_val = values[0]
    combined_val = values[2]
    improvement = ((combined_val - baseline_val) / baseline_val) * 100
    
    # Add improvement annotation
    ax.annotate('', xy=(2, combined_val), xytext=(0, baseline_val),
                arrowprops=dict(arrowstyle='<->', color='red', lw=2))
    ax.text(1, (baseline_val + combined_val) / 2,
           f'+{improvement:.1f}%',
           ha='center', va='center', fontsize=14, fontweight='bold',
           bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.8))
    
    ax.set_xticks(range(3))
    ax.set_xticklabels(labels, fontsize=11, fontweight='bold')
    ax.set_ylabel('F1-Score', fontsize=13, fontweight='bold')
    ax.set_title(f'{model}', fontsize=14, fontweight='bold')
    ax.set_ylim([0, max(values) * 1.15])
    ax.grid(True, alpha=0.3, axis='y')

# Bottom row: All metrics comparison
ax_bottom = fig.add_subplot(gs[1, :])

# Prepare data for grouped bar chart
metrics = ['F1-Score', 'Accuracy', 'ROC-AUC']
x = np.arange(len(models))
width = 0.25

for i, fs in enumerate(feature_sets_order):
    f1_scores = [df[(df['Model'] == m) & (df['Feature Set'] == fs)]['F1-Score'].values[0] for m in models]
    accuracies = [df[(df['Model'] == m) & (df['Feature Set'] == fs)]['Accuracy'].values[0] for m in models]
    aucs = [df[(df['Model'] == m) & (df['Feature Set'] == fs)]['ROC-AUC'].values[0] for m in models]
    
    offset = (i - 1) * width
    ax_bottom.bar(x + offset, f1_scores, width, label=f'{labels[i]} (F1)', 
                  color=colors[i], alpha=0.8, edgecolor='black')

ax_bottom.set_xlabel('Model', fontsize=13, fontweight='bold')
ax_bottom.set_ylabel('F1-Score', fontsize=13, fontweight='bold')
ax_bottom.set_title('F1-Score Comparison Across All Models', fontsize=15, fontweight='bold')
ax_bottom.set_xticks(x)
ax_bottom.set_xticklabels(models, fontsize=12, fontweight='bold')
ax_bottom.legend(fontsize=11, loc='upper left')
ax_bottom.grid(True, alpha=0.3, axis='y')

plt.suptitle('Ablation Study: Impact of Adding 8D Latent Features to 30D Baseline', 
            fontsize=18, fontweight='bold', y=0.98)

plt.savefig('ablation_study_main.png', dpi=300, bbox_inches='tight')
print("메인 ablation study 저장: ablation_study_main.png")
plt.close()

# Create detailed improvement chart
fig, axes = plt.subplots(1, 3, figsize=(18, 6))

metrics_full = ['F1-Score', 'Accuracy', 'ROC-AUC']

for metric_idx, metric in enumerate(metrics_full):
    ax = axes[metric_idx]
    
    improvements = []
    model_names = []
    
    for model in models:
        baseline = df[(df['Model'] == model) & (df['Feature Set'] == 'Original Only')][metric].values[0]
        combined = df[(df['Model'] == model) & (df['Feature Set'] == 'Original + Latent')][metric].values[0]
        
        improvement = ((combined - baseline) / baseline) * 100
        improvements.append(improvement)
        model_names.append(model)
    
    bars = ax.barh(range(len(models)), improvements, color='#2ecc71', alpha=0.8, edgecolor='black', linewidth=2)
    
    # Add value labels
    for i, (bar, val) in enumerate(zip(bars, improvements)):
        width = bar.get_width()
        ax.text(width + 0.1, bar.get_y() + bar.get_height()/2.,
               f'+{val:.2f}%',
               ha='left', va='center', fontsize=12, fontweight='bold')
    
    ax.set_yticks(range(len(models)))
    ax.set_yticklabels(model_names, fontsize=12, fontweight='bold')
    ax.set_xlabel('Improvement (%)', fontsize=12, fontweight='bold')
    ax.set_title(f'{metric} Improvement\n(38D vs 30D)', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='x')
    ax.axvline(x=0, color='black', linestyle='-', linewidth=1)

plt.suptitle('Performance Improvement by Adding Latent Features', fontsize=16, fontweight='bold')
plt.tight_layout()
plt.savefig('ablation_improvement_chart.png', dpi=300, bbox_inches='tight')
print("개선도 차트 저장: ablation_improvement_chart.png")
plt.close()

# Create dimension contribution chart
fig, ax = plt.subplots(figsize=(12, 8))

# Data for stacked bar
model_names = models
baseline_contribution = []
latent_contribution = []

for model in models:
    baseline = df[(df['Model'] == model) & (df['Feature Set'] == 'Original Only')]['F1-Score'].values[0]
    combined = df[(df['Model'] == model) & (df['Feature Set'] == 'Original + Latent')]['F1-Score'].values[0]
    
    baseline_contribution.append(baseline)
    latent_contribution.append(combined - baseline)

x = np.arange(len(models))
width = 0.6

p1 = ax.bar(x, baseline_contribution, width, label='Baseline (30D)', 
           color='#3498db', alpha=0.8, edgecolor='black', linewidth=2)
p2 = ax.bar(x, latent_contribution, width, bottom=baseline_contribution,
           label='Latent Contribution (8D)', color='#2ecc71', alpha=0.8, 
           edgecolor='black', linewidth=2)

# Add labels
for i, (b, l) in enumerate(zip(baseline_contribution, latent_contribution)):
    # Baseline label
    ax.text(i, b/2, f'{b:.4f}', ha='center', va='center', 
           fontsize=12, fontweight='bold', color='white')
    # Latent label
    ax.text(i, b + l/2, f'+{l:.4f}', ha='center', va='center',
           fontsize=12, fontweight='bold', color='white')
    # Total label
    ax.text(i, b + l + 0.02, f'{b+l:.4f}', ha='center', va='bottom',
           fontsize=13, fontweight='bold', color='black')

ax.set_ylabel('F1-Score', fontsize=13, fontweight='bold')
ax.set_xlabel('Model', fontsize=13, fontweight='bold')
ax.set_title('Feature Dimension Contribution to F1-Score\n(30D Baseline + 8D Latent = 38D Combined)', 
            fontsize=15, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(model_names, fontsize=12, fontweight='bold')
ax.legend(fontsize=12, loc='upper left')
ax.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig('dimension_contribution.png', dpi=300, bbox_inches='tight')
print("차원 기여도 차트 저장: dimension_contribution.png")
plt.close()

print("\n" + "="*80)
print("Ablation Study 시각화 완료!")
print("="*80)
print("\n생성된 파일:")
print("  1. ablation_study_main.png - 메인 ablation study (상단: 개별 모델, 하단: 전체 비교)")
print("  2. ablation_improvement_chart.png - 성능 향상률 차트")
print("  3. dimension_contribution.png - 차원별 기여도 (30D + 8D = 38D)")
print("  4. ablation_study_summary.csv - 요약 테이블")
