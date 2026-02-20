"""
Feature Selection 비교 차트 생성
v1.0 (42D) vs v1.1 (37D)
"""

import matplotlib.pyplot as plt
import numpy as np

plt.style.use('seaborn-v0_8-darkgrid')

# 데이터
configs = ['v1.0\n(42D)', 'v1.1\n(37D)']

# 성능 지표
f1_scores = [0.7027, 0.6970]
accuracies = [0.8832, 0.8806]
roc_aucs = [0.9175, 0.9106]

# 효율성 지표
dimensions = [42, 37]
inference_times = [50, 44]  # ms
costs = [10.42, 9.17]  # $/month (100만 요청)

# 시각화
fig = plt.figure(figsize=(18, 10))
gs = fig.add_gridspec(2, 3, hspace=0.3, wspace=0.3)

# (1) 성능 비교
ax1 = fig.add_subplot(gs[0, 0])
metrics = ['F1-Score', 'Accuracy', 'ROC-AUC']
v1_0_scores = [f1_scores[0], accuracies[0], roc_aucs[0]]
v1_1_scores = [f1_scores[1], accuracies[1], roc_aucs[1]]

x = np.arange(len(metrics))
width = 0.35

bars1 = ax1.bar(x - width/2, v1_0_scores, width, label='v1.0 (42D)', 
                color='#3498db', alpha=0.8, edgecolor='black', linewidth=1.5)
bars2 = ax1.bar(x + width/2, v1_1_scores, width, label='v1.1 (37D)', 
                color='#2ecc71', alpha=0.8, edgecolor='black', linewidth=1.5)

ax1.set_ylabel('Score', fontsize=12, fontweight='bold')
ax1.set_title('Performance Comparison', fontsize=14, fontweight='bold')
ax1.set_xticks(x)
ax1.set_xticklabels(metrics, fontsize=11)
ax1.legend(fontsize=11, loc='lower right')
ax1.grid(axis='y', alpha=0.3)
ax1.set_ylim([0.65, 0.95])

# 값 레이블
for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 0.005,
                f'{height:.4f}', ha='center', va='bottom', fontsize=9, fontweight='bold')

# 성능 차이 표시
for i, (v1, v2) in enumerate(zip(v1_0_scores, v1_1_scores)):
    diff_pct = ((v2 - v1) / v1) * 100
    color = '#e74c3c' if diff_pct < 0 else '#2ecc71'
    ax1.text(i, 0.67, f'{diff_pct:+.2f}%', ha='center', fontsize=9, 
            color=color, fontweight='bold')

# (2) 차원 비교
ax2 = fig.add_subplot(gs[0, 1])
colors_dim = ['#e74c3c', '#2ecc71']
bars = ax2.bar(configs, dimensions, color=colors_dim, alpha=0.7, 
              edgecolor='black', linewidth=2, width=0.6)

ax2.set_ylabel('Total Dimensions', fontsize=12, fontweight='bold')
ax2.set_title('Dimension Reduction', fontsize=14, fontweight='bold')
ax2.grid(axis='y', alpha=0.3)
ax2.set_ylim([0, 50])

# 값 레이블
for bar, dim in zip(bars, dimensions):
    ax2.text(bar.get_x() + bar.get_width()/2., dim + 1,
            f'{dim}D', ha='center', va='bottom', fontsize=13, fontweight='bold')

# 감소율 표시
ax2.annotate('', xy=(1, 42), xytext=(1, 37),
            arrowprops=dict(arrowstyle='<->', color='red', lw=2))
ax2.text(1.15, 39.5, '11.9%\n감소', fontsize=11, fontweight='bold', color='red',
        bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))

# (3) 추론 시간 비교
ax3 = fig.add_subplot(gs[0, 2])
colors_time = ['#e74c3c', '#2ecc71']
bars = ax3.bar(configs, inference_times, color=colors_time, alpha=0.7,
              edgecolor='black', linewidth=2, width=0.6)

ax3.set_ylabel('Inference Time (ms)', fontsize=12, fontweight='bold')
ax3.set_title('Inference Speed Improvement', fontsize=14, fontweight='bold')
ax3.grid(axis='y', alpha=0.3)
ax3.set_ylim([0, 60])

# 값 레이블
for bar, time in zip(bars, inference_times):
    ax3.text(bar.get_x() + bar.get_width()/2., time + 1,
            f'{time}ms', ha='center', va='bottom', fontsize=13, fontweight='bold')

# 개선율 표시
time_improvement = ((inference_times[0] - inference_times[1]) / inference_times[0]) * 100
ax3.text(0.5, 52, f'{time_improvement:.1f}% 빠름', ha='center', fontsize=11,
        fontweight='bold', color='green',
        bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.7))

# (4) 비용 비교
ax4 = fig.add_subplot(gs[1, 0])
colors_cost = ['#e74c3c', '#2ecc71']
bars = ax4.bar(configs, costs, color=colors_cost, alpha=0.7,
              edgecolor='black', linewidth=2, width=0.6)

ax4.set_ylabel('Monthly Cost ($)', fontsize=12, fontweight='bold')
ax4.set_title('Cost Reduction (1M requests/month)', fontsize=14, fontweight='bold')
ax4.grid(axis='y', alpha=0.3)
ax4.set_ylim([0, 12])

# 값 레이블
for bar, cost in zip(bars, costs):
    ax4.text(bar.get_x() + bar.get_width()/2., cost + 0.2,
            f'${cost:.2f}', ha='center', va='bottom', fontsize=13, fontweight='bold')

# 절감액 표시
cost_saving = costs[0] - costs[1]
cost_saving_pct = (cost_saving / costs[0]) * 100
ax4.text(0.5, 10.5, f'${cost_saving:.2f} 절감\n({cost_saving_pct:.1f}%)', 
        ha='center', fontsize=11, fontweight='bold', color='green',
        bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.7))

# (5) Feature 구성 비교
ax5 = fig.add_subplot(gs[1, 1])

categories = ['Baseline\nFeatures', 'Latent\nFeatures']
v1_0_features = [30, 12]
v1_1_features = [25, 12]

x = np.arange(len(categories))
width = 0.35

bars1 = ax5.bar(x - width/2, v1_0_features, width, label='v1.0 (42D)', 
                color='#3498db', alpha=0.8, edgecolor='black', linewidth=1.5)
bars2 = ax5.bar(x + width/2, v1_1_features, width, label='v1.1 (37D)', 
                color='#2ecc71', alpha=0.8, edgecolor='black', linewidth=1.5)

ax5.set_ylabel('Number of Features', fontsize=12, fontweight='bold')
ax5.set_title('Feature Configuration', fontsize=14, fontweight='bold')
ax5.set_xticks(x)
ax5.set_xticklabels(categories, fontsize=11)
ax5.legend(fontsize=11)
ax5.grid(axis='y', alpha=0.3)
ax5.set_ylim([0, 35])

# 값 레이블
for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        ax5.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                f'{int(height)}', ha='center', va='bottom', fontsize=11, fontweight='bold')

# (6) 종합 평가
ax6 = fig.add_subplot(gs[1, 2])
ax6.axis('off')

# 평가 테이블
evaluation = [
    ['항목', 'v1.0 (42D)', 'v1.1 (37D)', '변화'],
    ['─' * 15, '─' * 12, '─' * 12, '─' * 12],
    ['F1-Score', '0.7027', '0.6970', '-0.82%'],
    ['Accuracy', '0.8832', '0.8806', '-0.29%'],
    ['ROC-AUC', '0.9175', '0.9106', '-0.75%'],
    ['', '', '', ''],
    ['Dimensions', '42D', '37D', '-11.9%'],
    ['Inference', '50ms', '44ms', '-12.0%'],
    ['Cost/Month', '$10.42', '$9.17', '-12.0%'],
    ['', '', '', ''],
    ['권장사항', '', 'v1.1 배포 권장', '✅'],
]

# 테이블 그리기
table = ax6.table(cellText=evaluation, cellLoc='left', loc='center',
                 colWidths=[0.25, 0.25, 0.25, 0.25])

table.auto_set_font_size(False)
table.set_fontsize(10)
table.scale(1, 2.5)

# 헤더 스타일
for i in range(4):
    cell = table[(0, i)]
    cell.set_facecolor('#3498db')
    cell.set_text_props(weight='bold', color='white')

# 구분선 스타일
for i in range(4):
    cell = table[(1, i)]
    cell.set_facecolor('#ecf0f1')

# 권장사항 행 강조
for i in range(4):
    cell = table[(10, i)]
    cell.set_facecolor('#2ecc71')
    cell.set_text_props(weight='bold', color='white')

ax6.set_title('Comprehensive Evaluation', fontsize=14, fontweight='bold', pad=20)

# 전체 제목
fig.suptitle('Feature Selection Optimization: v1.0 (42D) vs v1.1 (37D)\n' +
            'Performance: -0.82% | Efficiency: +11.9% | Cost: -12.0%',
            fontsize=16, fontweight='bold', y=0.98)

plt.savefig('feature_selection_comparison.png', dpi=300, bbox_inches='tight')
print("✅ feature_selection_comparison.png 생성 완료!")
plt.close()

print("\n" + "="*80)
print("Feature Selection 비교 차트 생성 완료!")
print("="*80)
print("\n📊 주요 결과:")
print(f"  • 성능 저하: F1-Score -0.82% (허용 범위 내)")
print(f"  • 차원 감소: 11.9% (42D → 37D)")
print(f"  • 추론 속도: 12.0% 향상 (50ms → 44ms)")
print(f"  • 비용 절감: 12.0% ($10.42 → $9.17/월)")
print(f"\n💡 권장사항: v1.1 (37D) 배포 권장!")
print("="*80)
