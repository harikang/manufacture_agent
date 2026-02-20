import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    classification_report, confusion_matrix, roc_auc_score, 
    precision_recall_curve, f1_score, accuracy_score, roc_curve
)
import matplotlib.pyplot as plt
import seaborn as sns
from xgboost import XGBClassifier
from catboost import CatBoostClassifier
from lightgbm import LGBMClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
import warnings
warnings.filterwarnings('ignore')

plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")


def load_data():
    """Load original features and latent vectors"""
    print("데이터 로딩 중...")
    
    # Load original data
    df = pd.read_csv('/Users/kang/Downloads/dataset/DieCasting_Quality_Raw_Data.csv', header=[0, 1])
    df.columns = ['_'.join(col).strip() for col in df.columns.values]
    
    # Select features
    process_features = [col for col in df.columns if col.startswith('Process_')]
    sensor_features = [col for col in df.columns if col.startswith('Sensor_')]
    feature_cols = [col for col in process_features + sensor_features if col != 'Process_id'][:30]
    
    # Original features
    X_original = df[feature_cols].values
    X_original = np.nan_to_num(X_original, nan=np.nanmean(X_original, axis=0))
    
    # Labels
    defect_features = [col for col in df.columns if col.startswith('Defects_')]
    y = (df[defect_features].sum(axis=1) > 0).astype(int).values
    
    # Load latent vectors
    X_latent = np.load('latent_vectors.npy')
    
    print(f"원본 features shape: {X_original.shape}")
    print(f"Latent features shape: {X_latent.shape}")
    print(f"Labels shape: {y.shape}")
    print(f"불량률: {y.mean()*100:.2f}%")
    
    return X_original, X_latent, y, feature_cols


def create_feature_combinations(X_original, X_latent):
    """Create different feature combinations"""
    # Standardize original features
    scaler = StandardScaler()
    X_original_scaled = scaler.fit_transform(X_original)
    
    combinations = {
        'Original Only': X_original_scaled,
        'Latent Only': X_latent,
        'Original + Latent': np.hstack([X_original_scaled, X_latent])
    }
    
    print("\n특징 조합:")
    for name, X in combinations.items():
        print(f"  {name}: {X.shape}")
    
    return combinations


def train_models(X_train, X_test, y_train, y_test, feature_name):
    """Train multiple ML models"""
    print(f"\n{'='*80}")
    print(f"학습 중: {feature_name}")
    print(f"{'='*80}")
    
    models = {
        'XGBoost': XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            eval_metric='logloss'
        ),
        'CatBoost': CatBoostClassifier(
            iterations=200,
            depth=6,
            learning_rate=0.1,
            random_state=42,
            verbose=False
        ),
        'LightGBM': LGBMClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            verbose=-1
        ),
        'Random Forest': RandomForestClassifier(
            n_estimators=200,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        ),
        'Gradient Boosting': GradientBoostingClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            random_state=42
        ),
        'Logistic Regression': LogisticRegression(
            max_iter=1000,
            random_state=42
        )
    }
    
    results = {}
    
    for model_name, model in models.items():
        print(f"\n{model_name} 학습 중...")
        
        # Train
        model.fit(X_train, y_train)
        
        # Predict
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)[:, 1]
        
        # Metrics
        accuracy = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred)
        roc_auc = roc_auc_score(y_test, y_pred_proba)
        
        # Cross-validation (skip for CatBoost due to sklearn compatibility)
        if model_name == 'CatBoost':
            cv_scores = np.array([f1])  # Use test F1 as proxy
        else:
            cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
            cv_scores = cross_val_score(model, X_train, y_train, cv=cv, scoring='f1')
        
        results[model_name] = {
            'model': model,
            'accuracy': accuracy,
            'f1_score': f1,
            'roc_auc': roc_auc,
            'cv_f1_mean': cv_scores.mean(),
            'cv_f1_std': cv_scores.std(),
            'y_pred': y_pred,
            'y_pred_proba': y_pred_proba
        }
        
        print(f"  Accuracy: {accuracy:.4f}")
        print(f"  F1-Score: {f1:.4f}")
        print(f"  ROC-AUC: {roc_auc:.4f}")
        print(f"  CV F1: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")
    
    return results


def compare_results(all_results):
    """Compare results across all feature combinations"""
    print("\n" + "="*80)
    print("전체 결과 비교")
    print("="*80)
    
    comparison_data = []
    
    for feature_name, models_results in all_results.items():
        for model_name, metrics in models_results.items():
            comparison_data.append({
                'Feature Set': feature_name,
                'Model': model_name,
                'Accuracy': metrics['accuracy'],
                'F1-Score': metrics['f1_score'],
                'ROC-AUC': metrics['roc_auc'],
                'CV F1 Mean': metrics['cv_f1_mean'],
                'CV F1 Std': metrics['cv_f1_std']
            })
    
    df_comparison = pd.DataFrame(comparison_data)
    
    # Sort by F1-Score
    df_comparison = df_comparison.sort_values('F1-Score', ascending=False)
    
    print("\n상위 10개 모델:")
    print(df_comparison.head(10).to_string(index=False))
    
    # Save to CSV
    df_comparison.to_csv('ml_classification_results.csv', index=False)
    print("\n결과 저장: ml_classification_results.csv")
    
    return df_comparison


def visualize_results(df_comparison):
    """Visualize comparison results"""
    
    # 1. F1-Score comparison
    fig, axes = plt.subplots(2, 2, figsize=(18, 12))
    
    # F1-Score by model and feature set
    pivot_f1 = df_comparison.pivot(index='Model', columns='Feature Set', values='F1-Score')
    pivot_f1.plot(kind='bar', ax=axes[0, 0], width=0.8)
    axes[0, 0].set_title('F1-Score Comparison', fontsize=14, fontweight='bold')
    axes[0, 0].set_xlabel('Model', fontsize=12)
    axes[0, 0].set_ylabel('F1-Score', fontsize=12)
    axes[0, 0].legend(title='Feature Set', fontsize=10)
    axes[0, 0].grid(True, alpha=0.3)
    axes[0, 0].tick_params(axis='x', rotation=45)
    
    # ROC-AUC comparison
    pivot_auc = df_comparison.pivot(index='Model', columns='Feature Set', values='ROC-AUC')
    pivot_auc.plot(kind='bar', ax=axes[0, 1], width=0.8)
    axes[0, 1].set_title('ROC-AUC Comparison', fontsize=14, fontweight='bold')
    axes[0, 1].set_xlabel('Model', fontsize=12)
    axes[0, 1].set_ylabel('ROC-AUC', fontsize=12)
    axes[0, 1].legend(title='Feature Set', fontsize=10)
    axes[0, 1].grid(True, alpha=0.3)
    axes[0, 1].tick_params(axis='x', rotation=45)
    
    # Accuracy comparison
    pivot_acc = df_comparison.pivot(index='Model', columns='Feature Set', values='Accuracy')
    pivot_acc.plot(kind='bar', ax=axes[1, 0], width=0.8)
    axes[1, 0].set_title('Accuracy Comparison', fontsize=14, fontweight='bold')
    axes[1, 0].set_xlabel('Model', fontsize=12)
    axes[1, 0].set_ylabel('Accuracy', fontsize=12)
    axes[1, 0].legend(title='Feature Set', fontsize=10)
    axes[1, 0].grid(True, alpha=0.3)
    axes[1, 0].tick_params(axis='x', rotation=45)
    
    # CV F1 with error bars
    for i, feature_set in enumerate(df_comparison['Feature Set'].unique()):
        subset = df_comparison[df_comparison['Feature Set'] == feature_set]
        x = np.arange(len(subset))
        axes[1, 1].errorbar(x + i*0.25, subset['CV F1 Mean'], 
                           yerr=subset['CV F1 Std'],
                           fmt='o-', label=feature_set, capsize=5, capthick=2)
    
    axes[1, 1].set_xticks(np.arange(len(subset)) + 0.25)
    axes[1, 1].set_xticklabels(subset['Model'], rotation=45, ha='right')
    axes[1, 1].set_title('Cross-Validation F1-Score', fontsize=14, fontweight='bold')
    axes[1, 1].set_xlabel('Model', fontsize=12)
    axes[1, 1].set_ylabel('CV F1-Score', fontsize=12)
    axes[1, 1].legend(title='Feature Set', fontsize=10)
    axes[1, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('ml_models_comparison.png', dpi=300, bbox_inches='tight')
    print("모델 비교 시각화 저장: ml_models_comparison.png")
    plt.close()


def plot_best_model_analysis(all_results, df_comparison, y_test):
    """Detailed analysis of the best model"""
    
    # Find best model
    best_row = df_comparison.iloc[0]
    best_feature_set = best_row['Feature Set']
    best_model_name = best_row['Model']
    
    print(f"\n최고 성능 모델: {best_model_name} with {best_feature_set}")
    print(f"F1-Score: {best_row['F1-Score']:.4f}")
    
    best_results = all_results[best_feature_set][best_model_name]
    y_pred = best_results['y_pred']
    y_pred_proba = best_results['y_pred_proba']
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # 1. Confusion Matrix
    cm = confusion_matrix(y_test, y_pred)
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=axes[0, 0],
                xticklabels=['Normal', 'Defect'],
                yticklabels=['Normal', 'Defect'])
    axes[0, 0].set_title(f'Confusion Matrix\n{best_model_name} - {best_feature_set}', 
                        fontsize=14, fontweight='bold')
    axes[0, 0].set_ylabel('True Label', fontsize=12)
    axes[0, 0].set_xlabel('Predicted Label', fontsize=12)
    
    # 2. ROC Curve
    fpr, tpr, _ = roc_curve(y_test, y_pred_proba)
    axes[0, 1].plot(fpr, tpr, linewidth=2, label=f'ROC (AUC = {best_row["ROC-AUC"]:.4f})')
    axes[0, 1].plot([0, 1], [0, 1], 'k--', linewidth=1, label='Random')
    axes[0, 1].set_xlabel('False Positive Rate', fontsize=12)
    axes[0, 1].set_ylabel('True Positive Rate', fontsize=12)
    axes[0, 1].set_title('ROC Curve', fontsize=14, fontweight='bold')
    axes[0, 1].legend(fontsize=11)
    axes[0, 1].grid(True, alpha=0.3)
    
    # 3. Precision-Recall Curve
    precision, recall, _ = precision_recall_curve(y_test, y_pred_proba)
    axes[1, 0].plot(recall, precision, linewidth=2, label=f'PR (F1 = {best_row["F1-Score"]:.4f})')
    axes[1, 0].set_xlabel('Recall', fontsize=12)
    axes[1, 0].set_ylabel('Precision', fontsize=12)
    axes[1, 0].set_title('Precision-Recall Curve', fontsize=14, fontweight='bold')
    axes[1, 0].legend(fontsize=11)
    axes[1, 0].grid(True, alpha=0.3)
    
    # 4. Prediction Distribution
    axes[1, 1].hist(y_pred_proba[y_test == 0], bins=50, alpha=0.6, label='Normal', color='blue', density=True)
    axes[1, 1].hist(y_pred_proba[y_test == 1], bins=50, alpha=0.6, label='Defect', color='red', density=True)
    axes[1, 1].set_xlabel('Predicted Probability', fontsize=12)
    axes[1, 1].set_ylabel('Density', fontsize=12)
    axes[1, 1].set_title('Prediction Distribution', fontsize=14, fontweight='bold')
    axes[1, 1].legend(fontsize=11)
    axes[1, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('best_model_analysis.png', dpi=300, bbox_inches='tight')
    print("최고 모델 분석 저장: best_model_analysis.png")
    plt.close()
    
    # Classification Report
    print("\n" + "="*80)
    print(f"Classification Report - {best_model_name} ({best_feature_set})")
    print("="*80)
    print(classification_report(y_test, y_pred, target_names=['Normal', 'Defect']))


def analyze_feature_importance(all_results, feature_cols):
    """Analyze feature importance for tree-based models"""
    
    print("\n" + "="*80)
    print("Feature Importance 분석")
    print("="*80)
    
    # Get best model with Original + Latent features
    best_combo = 'Original + Latent'
    
    fig, axes = plt.subplots(2, 2, figsize=(18, 14))
    axes = axes.flatten()
    
    tree_models = ['XGBoost', 'CatBoost', 'LightGBM', 'Random Forest']
    
    for idx, model_name in enumerate(tree_models):
        if model_name in all_results[best_combo]:
            model = all_results[best_combo][model_name]['model']
            
            # Get feature importance
            if hasattr(model, 'feature_importances_'):
                importances = model.feature_importances_
            else:
                continue
            
            # Create feature names
            n_original = len(feature_cols)
            n_latent = 8
            all_feature_names = feature_cols + [f'Latent_{i+1}' for i in range(n_latent)]
            
            # Sort by importance
            indices = np.argsort(importances)[::-1][:20]  # Top 20
            
            axes[idx].barh(range(len(indices)), importances[indices], color='steelblue')
            axes[idx].set_yticks(range(len(indices)))
            axes[idx].set_yticklabels([all_feature_names[i] for i in indices], fontsize=9)
            axes[idx].set_xlabel('Importance', fontsize=11, fontweight='bold')
            axes[idx].set_title(f'{model_name} - Top 20 Features', fontsize=12, fontweight='bold')
            axes[idx].grid(True, alpha=0.3, axis='x')
            axes[idx].invert_yaxis()
    
    plt.tight_layout()
    plt.savefig('feature_importance_comparison.png', dpi=300, bbox_inches='tight')
    print("Feature importance 저장: feature_importance_comparison.png")
    plt.close()


if __name__ == "__main__":
    print("="*80)
    print("ML 분류 모델 학습 및 평가")
    print("="*80)
    
    # Load data
    X_original, X_latent, y, feature_cols = load_data()
    
    # Create feature combinations
    feature_combinations = create_feature_combinations(X_original, X_latent)
    
    # Train-test split
    all_results = {}
    
    for feature_name, X in feature_combinations.items():
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Train models
        results = train_models(X_train, X_test, y_train, y_test, feature_name)
        all_results[feature_name] = results
    
    # Compare results
    df_comparison = compare_results(all_results)
    
    # Visualize results
    visualize_results(df_comparison)
    
    # Best model analysis
    plot_best_model_analysis(all_results, df_comparison, y_test)
    
    # Feature importance
    analyze_feature_importance(all_results, feature_cols)
    
    print("\n" + "="*80)
    print("분석 완료!")
    print("="*80)
    print("\n생성된 파일:")
    print("  - ml_classification_results.csv: 전체 결과")
    print("  - ml_models_comparison.png: 모델 비교")
    print("  - best_model_analysis.png: 최고 모델 상세 분석")
    print("  - feature_importance_comparison.png: Feature importance")
