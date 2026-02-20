import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("Set2")

# Load results
df = pd.read_csv('latent_dimension_ablation_results.csv')

# Create comprehensive summary figure
fig = plt.figure(figsize=(20, 12))
gs = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.3)

# Color scheme
colors_dim = {4: '#e74c3c', 8: '#3498db', 12: '#2ecc71', 16: '#f39c12'}
colors_model = {'Gradient Boosting': '#e74c3c', 'XGBoost': '#3498db', 'LightGBM': '#2ecc71'}

# 1. Main comparison - F1 Score by dimension and model
ax1 = fig.add_subplot(gs[0, :])
latent_dims = sorted(df['Latent Dim'].unique())
models = df['Model'].unique()
x = np.arange(len(latent_dims))
width = 0.25

for i, model in enumerate(models):
    model_data = df[df['Model'] == model]
    f1_scores = [model_data[model_data['Latent Dim'] == ld]['F1-Score'].values[0] for ld in latent_dims]
    bars = ax1.bar(x + i*width, f1_scores, width, label=model, 
                   color=colors_model[model], alpha=0.85, edgecolor='black', linewidth=2)
    
    # Add value labels
    for bar, val in zip(bars, f1_scores):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 0.005,
                f'{val:.4f}',
                ha='center', va='bottom', fontsize=10, fontweight='bold')

ax1.set_xlabel('Latent Dimension (Total Dimension)', fontsize=14, fontweight='bold')
ax1.set_ylabel('F1-Score', fontsize=14, fontweight='bold')
ax1.set_title('F1-Score Comparison Across Latent Dimensions', fontsize=16, fontweight='bold')
ax1.set_xticks(x + width)
ax1.set_xticklabels([f'{ld}D\n({30+ld}D total)' for ld in latent_dims], fontsize=12, fontweight='bold')
ax1.legend(fontsize=12, loc='upper left')
ax1.grid(True, alpha=0.3, axis='y')
ax1.set_ylim([0.55, 0.75])

# Highlight best
best_idx = df['F1-Score'].idxmax()
best_row = df.loc[best_idx]
ax1.axhline(y=best_row['F1-Score'], color='red', linestyle='--', linewidth=2, alpha=0.5)
ax1.text(0.98, best_row['F1-Score'] + 0.005, 
        f"Best: {best_row['Model']} @ {int(best_row['Latent Dim'])}D = {best_row['F1-Score']:.4f}",
        transform=ax1.get_yaxis_transform(), ha='right', va='bottom',
        fontsize=11, fontweight='bold', bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.8))

# 2-4. Individual model trends
for idx, model in enumerate(models):
    ax = fig.add_subplot(gs[1, idx])
    model_data = df[df['Model'] == model].sort_values('Latent Dim')
    
    ax.plot(model_data['Latent Dim'], model_data['F1-Score'], 
           marker='o', linewidth=3, markersize=12, color=colors_model[model], label='F1-Score')
    ax.plot(model_data['Latent Dim'], model_data['Accuracy'], 
           marker='s', linewidth=3, markersize=10, color='gray', alpha=0.6, label='Accuracy')
    
    # Add value labels
    for _, row in model_data.iterrows():
        ax.text(row['Latent Dim'], row['F1-Score'] + 0.01, 
               f"{row['F1-Score']:.4f}",
               ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    # Highlight best
    best_f1_idx = model_data['F1-Score'].idxmax()
    best_f1 = model_data.loc[best_f1_idx]
    ax.scatter([best_f1['Latent Dim']], [best_f1['F1-Score']], 
              s=300, c='red', marker='*', edgecolors='black', linewidth=2, zorder=5)
    
    ax.set_xlabel('Latent Dimension', fontsize=12, fontweight='bold')
    ax.set_ylabel('Score', fontsize=12, fontweight='bold')
    ax.set_title(f'{model}\nBest: {int(best_f1["Latent Dim"])}D (F1={best_f1["F1-Score"]:.4f})', 
                fontsize=13, fontweight='bold')
    ax.set_xticks([4, 8, 12, 16])
    ax.legend(fontsize=10, loc='best')
    ax.grid(True, alpha=0.3)
    ax.set_ylim([0.55, 0.9])

# 5. Performance improvement from 4D baseline
ax5 = fig.add_subplot(gs[2, 0])
for model in models:
    model_data = df[df['Model'] == model].sort_values('Latent Dim')
    baseline = model_data[model_data['Latent Dim'] == 4]['F1-Score'].values[0]
    improvements = [(row['F1-Score'] - baseline) / baseline * 100 
                   for _, row in model_data.iterrows()]
    ax5.plot(model_data['Latent Dim'], improvements, 
            marker='o', linewidth=2.5, markersize=10, label=model, color=colors_model[model])

ax5.set_xlabel('Latent Dimension', fontsize=12, fontweight='bold')
ax5.set_ylabel('F1-Score Improvement (%)', fontsize=12, fontweight='bold')
ax5.set_title('Performance Improvement from 4D Baseline', fontsize=13, fontweight='bold')
ax5.set_xticks([4, 8, 12, 16])
ax5.legend(fontsize=11, loc='best')
ax5.grid(True, alpha=0.3)
ax5.axhline(y=0, color='black', linestyle='-', linewidth=1)

# 6. Dimension efficiency (F1 per added dimension)
ax6 = fig.add_subplot(gs[2, 1])
efficiency_data = []
for model in models:
    model_data = df[df['Model'] == model].sort_values('Latent Dim')
    for _, row in model_data.iterrows():
        dim = int(row['Latent Dim'])
        f1 = row['F1-Score']
        efficiency = f1 / dim  # F1 per dimension
        efficiency_data.append({'Model': model, 'Latent Dim': dim, 'Efficiency': efficiency})

eff_df = pd.DataFrame(efficiency_data)
for model in models:
    model_eff = eff_df[eff_df['Model'] == model]
    ax6.plot(model_eff['Latent Dim'], model_eff['Efficiency'], 
            marker='o', linewidth=2.5, markersize=10, label=model, color=colors_model[model])

ax6.set_xlabel('Latent Dimension', fontsize=12, fontweight='bold')
ax6.set_ylabel('F1-Score / Dimension', fontsize=12, fontweight='bold')
ax6.set_title('Dimension Efficiency', fontsize=13, fontweight='bold')
ax6.set_xticks([4, 8, 12, 16])
ax6.legend(fontsize=11, loc='best')
ax6.grid(True, alpha=0.3)

# 7. Summary table
ax7 = fig.add_subplot(gs[2, 2])
ax7.axis('off')

summary_text = "📊 Summary\n\n"
summary_text += "Best Overall:\n"
summary_text += f"  {best_row['Model']}\n"
summary_text += f"  {int(best_row['Latent Dim'])}D latent (46D total)\n"
summary_text += f"  F1: {best_row['F1-Score']:.4f}\n\n"

summary_text += "Best by Model:\n"
for model in models:
    model_data = df[df['Model'] == model]
    best_model = model_data.loc[model_data['F1-Score'].idxmax()]
    summary_text += f"  {model}:\n"
    summary_text += f"    {int(best_model['Latent Dim'])}D (F1: {best_model['F1-Score']:.4f})\n"

summary_text += "\nRecommendations:\n"
summary_text += "  🥇 Best: 16D (46D total)\n"
summary_text += "  ⚖️  Balanced: 12D (42D total)\n"
summary_text += "  ⚡ Efficient: 8D (38D total)\n"

ax7.text(0.1, 0.95, summary_text, transform=ax7.transAxes,
        fontsize=11, verticalalignment='top', fontfamily='monospace',
        bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.3))

plt.suptitle('Latent Dimension Ablation Study: Comprehensive Analysis', 
            fontsize=18, fontweight='bold', y=0.995)

plt.savefig('latent_dimension_summary.png', dpi=300, bbox_inches='tight')
print("최종 요약 시각화 저장: latent_dimension_summary.png")
plt.close()

# Create recommendation chart
fig, ax = plt.subplots(figsize=(14, 8))

recommendations = {
    '4D\n(34D total)': {'score': 0.6180, 'color': '#e74c3c', 'label': '❌ Not Recommended\nLow Performance'},
    '8D\n(38D total)': {'score': 0.6381, 'color': '#3498db', 'label': '✅ Efficient\nBalanced Choice'},
    '12D\n(42D total)': {'score': 0.6425, 'color': '#2ecc71', 'label': '✅ Balanced\nHigh Performance'},
    '16D\n(46D total)': {'score': 0.6523, 'color': '#f39c12', 'label': '✅✅ Best\nHighest Performance'}
}

x_pos = np.arange(len(recommendations))
scores = [v['score'] for v in recommendations.values()]
colors = [v['color'] for v in recommendations.values()]
labels = [v['label'] for v in recommendations.values()]

bars = ax.bar(x_pos, scores, color=colors, alpha=0.85, edgecolor='black', linewidth=3, width=0.6)

# Add value labels
for bar, score, label in zip(bars, scores, labels):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height + 0.01,
           f'{score:.4f}',
           ha='center', va='bottom', fontsize=14, fontweight='bold')
    ax.text(bar.get_x() + bar.get_width()/2., height/2,
           label,
           ha='center', va='center', fontsize=11, fontweight='bold',
           bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

ax.set_xticks(x_pos)
ax.set_xticklabels(recommendations.keys(), fontsize=13, fontweight='bold')
ax.set_ylabel('Average F1-Score', fontsize=14, fontweight='bold')
ax.set_title('Latent Dimension Recommendations\n(Average across all models)', 
            fontsize=16, fontweight='bold')
ax.grid(True, alpha=0.3, axis='y')
ax.set_ylim([0.5, 0.7])

# Add best marker
best_idx = np.argmax(scores)
ax.scatter([best_idx], [scores[best_idx]], s=500, c='red', marker='*', 
          edgecolors='black', linewidth=2, zorder=5)

plt.tight_layout()
plt.savefig('latent_dimension_recommendations.png', dpi=300, bbox_inches='tight')
print("권장사항 차트 저장: latent_dimension_recommendations.png")
plt.close()

print("\n" + "="*80)
print("최종 요약 시각화 완료!")
print("="*80)
print("\n생성된 파일:")
print("  - latent_dimension_summary.png (종합 분석)")
print("  - latent_dimension_recommendations.png (권장사항)")
