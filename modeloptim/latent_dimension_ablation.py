import torch
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import f1_score, accuracy_score, roc_auc_score
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from sklearn.ensemble import GradientBoostingClassifier
import matplotlib.pyplot as plt
import seaborn as sns
from autoencoder_model import DieCastingAutoEncoder, load_and_preprocess_data, train_autoencoder, DieCastingDataset
from torch.utils.data import DataLoader
import warnings
warnings.filterwarnings('ignore')

plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")


def train_autoencoder_with_latent_dim(latent_dim, X, y, device='cpu'):
    """Train AutoEncoder with specific latent dimension"""
    print(f"\n{'='*80}")
    print(f"AutoEncoder 학습: Latent Dimension = {latent_dim}")
    print(f"{'='*80}")
    
    # Standardize
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Train-test split
    X_train, X_val, y_train, y_val = train_test_split(
        X_scaled, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Create datasets
    train_dataset = DieCastingDataset(X_train, y_train)
    val_dataset = DieCastingDataset(X_val, y_val)
    
    train_loader = DataLoader(train_dataset, batch_size=128, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=128, shuffle=False)
    
    # Initialize model
    model = DieCastingAutoEncoder(
        input_dim=X.shape[1],
        latent_dim=latent_dim,
        hidden_dims=[64, 32, 16]
    ).to(device)
    
    print(f"모델 파라미터 수: {sum(p.numel() for p in model.parameters()):,}")
    
    # Train
    history = train_autoencoder(model, train_loader, val_loader, epochs=100, device=device)
    
    # Extract latent vectors
    model.eval()
    with torch.no_grad():
        X_tensor = torch.FloatTensor(X_scaled).to(device)
        latent_vectors = []
        batch_size = 256
        for i in range(0, len(X_tensor), batch_size):
            batch = X_tensor[i:i+batch_size]
            z, _ = model.encode(batch)
            latent_vectors.append(z.cpu().numpy())
        latent_vectors = np.vstack(latent_vectors)
    
    print(f"Latent vectors shape: {latent_vectors.shape}")
    
    return latent_vectors, scaler, model, history


def evaluate_ml_models(X_original, X_latent, y, latent_dim):
    """Evaluate ML models with original + latent features"""
    print(f"\n{'='*80}")
    print(f"ML 모델 평가: Latent Dimension = {latent_dim}")
    print(f"{'='*80}")
    
    # Standardize original features
    scaler = StandardScaler()
    X_original_scaled = scaler.fit_transform(X_original)
    
    # Combine features
    X_combined = np.hstack([X_original_scaled, X_latent])
    
    print(f"Combined features shape: {X_combined.shape}")
    
    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(
        X_combined, y, test_size=0.2, random_state=42, stratify=y
    )
    
    models = {
        'Gradient Boosting': GradientBoostingClassifier(
            n_estimators=200, max_depth=6, learning_rate=0.1, random_state=42
        ),
        'XGBoost': XGBClassifier(
            n_estimators=200, max_depth=6, learning_rate=0.1, 
            subsample=0.8, colsample_bytree=0.8, random_state=42, eval_metric='logloss'
        ),
        'LightGBM': LGBMClassifier(
            n_estimators=200, max_depth=6, learning_rate=0.1,
            subsample=0.8, colsample_bytree=0.8, random_state=42, verbose=-1
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
        f1 = f1_score(y_test, y_pred)
        accuracy = accuracy_score(y_test, y_pred)
        roc_auc = roc_auc_score(y_test, y_pred_proba)
        
        results[model_name] = {
            'f1_score': f1,
            'accuracy': accuracy,
            'roc_auc': roc_auc
        }
        
        print(f"  F1-Score: {f1:.4f}")
        print(f"  Accuracy: {accuracy:.4f}")
        print(f"  ROC-AUC: {roc_auc:.4f}")
    
    return results


def run_latent_dimension_ablation():
    """Run ablation study for different latent dimensions"""
    
    print("="*80)
    print("Latent Dimension Ablation Study")
    print("="*80)
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"사용 디바이스: {device}")
    
    # Load data
    csv_path = '/Users/kang/Downloads/dataset/DieCasting_Quality_Raw_Data.csv'
    X, y, feature_cols = load_and_preprocess_data(csv_path)
    
    latent_dims = [4, 8, 12, 16]
    all_results = {}
    
    for latent_dim in latent_dims:
        # Train AutoEncoder
        latent_vectors, scaler, model, history = train_autoencoder_with_latent_dim(
            latent_dim, X, y, device
        )
        
        # Save model and latent vectors
        torch.save(model.state_dict(), f'autoencoder_latent{latent_dim}.pth')
        np.save(f'latent_vectors_{latent_dim}d.npy', latent_vectors)
        
        # Evaluate ML models
        ml_results = evaluate_ml_models(X, latent_vectors, y, latent_dim)
        
        all_results[latent_dim] = ml_results
    
    return all_results, feature_cols


def visualize_latent_dimension_results(all_results):
    """Visualize ablation study results"""
    
    # Prepare data
    data = []
    for latent_dim, models_results in all_results.items():
        for model_name, metrics in models_results.items():
            data.append({
                'Latent Dim': latent_dim,
                'Model': model_name,
                'F1-Score': metrics['f1_score'],
                'Accuracy': metrics['accuracy'],
                'ROC-AUC': metrics['roc_auc']
            })
    
    df = pd.DataFrame(data)
    
    # Save to CSV
    df.to_csv('latent_dimension_ablation_results.csv', index=False)
    print("\n결과 저장: latent_dimension_ablation_results.csv")
    
    # Create visualization
    fig, axes = plt.subplots(1, 3, figsize=(20, 6))
    
    metrics = ['F1-Score', 'Accuracy', 'ROC-AUC']
    colors = ['#e74c3c', '#3498db', '#2ecc71']
    
    for idx, metric in enumerate(metrics):
        ax = axes[idx]
        
        for model_name in df['Model'].unique():
            model_data = df[df['Model'] == model_name]
            ax.plot(model_data['Latent Dim'], model_data[metric], 
                   marker='o', linewidth=2.5, markersize=10, label=model_name)
            
            # Add value labels
            for _, row in model_data.iterrows():
                ax.text(row['Latent Dim'], row[metric] + 0.005, 
                       f"{row[metric]:.4f}",
                       ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        ax.set_xlabel('Latent Dimension', fontsize=13, fontweight='bold')
        ax.set_ylabel(metric, fontsize=13, fontweight='bold')
        ax.set_title(f'{metric} vs Latent Dimension', fontsize=14, fontweight='bold')
        ax.legend(fontsize=11, loc='best')
        ax.grid(True, alpha=0.3)
        ax.set_xticks([4, 8, 12, 16])
    
    plt.suptitle('Latent Dimension Ablation Study: 30D + [4D, 8D, 12D, 16D]', 
                fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.savefig('latent_dimension_ablation.png', dpi=300, bbox_inches='tight')
    print("시각화 저장: latent_dimension_ablation.png")
    plt.close()
    
    # Create detailed comparison
    fig, axes = plt.subplots(3, 1, figsize=(14, 16))
    
    models = df['Model'].unique()
    latent_dims = sorted(df['Latent Dim'].unique())
    
    for idx, model_name in enumerate(models):
        ax = axes[idx]
        model_data = df[df['Model'] == model_name]
        
        x = np.arange(len(latent_dims))
        width = 0.25
        
        for i, metric in enumerate(metrics):
            values = [model_data[model_data['Latent Dim'] == ld][metric].values[0] 
                     for ld in latent_dims]
            bars = ax.bar(x + i*width, values, width, label=metric, 
                         color=colors[i], alpha=0.8, edgecolor='black', linewidth=1.5)
            
            # Add value labels
            for bar, val in zip(bars, values):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.005,
                       f'{val:.4f}',
                       ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        ax.set_xlabel('Latent Dimension', fontsize=12, fontweight='bold')
        ax.set_ylabel('Score', fontsize=12, fontweight='bold')
        ax.set_title(f'{model_name} Performance', fontsize=13, fontweight='bold')
        ax.set_xticks(x + width)
        ax.set_xticklabels([f'{ld}D\n(30+{ld}={30+ld}D)' for ld in latent_dims], fontsize=11)
        ax.legend(fontsize=11, loc='best')
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_ylim([0.5, 1.0])
    
    plt.suptitle('Detailed Performance Comparison by Latent Dimension', 
                fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.savefig('latent_dimension_detailed.png', dpi=300, bbox_inches='tight')
    print("상세 시각화 저장: latent_dimension_detailed.png")
    plt.close()
    
    # Print summary
    print("\n" + "="*80)
    print("Latent Dimension Ablation Study 요약")
    print("="*80)
    
    for model_name in models:
        print(f"\n{model_name}:")
        model_data = df[df['Model'] == model_name].sort_values('Latent Dim')
        
        best_f1_idx = model_data['F1-Score'].idxmax()
        best_f1_row = model_data.loc[best_f1_idx]
        
        print(f"  최고 F1-Score: {best_f1_row['F1-Score']:.4f} (Latent Dim = {int(best_f1_row['Latent Dim'])})")
        
        for _, row in model_data.iterrows():
            dim = int(row['Latent Dim'])
            total_dim = 30 + dim
            print(f"    {dim}D (Total {total_dim}D): F1={row['F1-Score']:.4f}, "
                  f"Acc={row['Accuracy']:.4f}, AUC={row['ROC-AUC']:.4f}")
    
    # Find overall best
    best_overall = df.loc[df['F1-Score'].idxmax()]
    print(f"\n{'='*80}")
    print(f"전체 최고 성능:")
    print(f"  Model: {best_overall['Model']}")
    print(f"  Latent Dim: {int(best_overall['Latent Dim'])}D (Total: {30 + int(best_overall['Latent Dim'])}D)")
    print(f"  F1-Score: {best_overall['F1-Score']:.4f}")
    print(f"  Accuracy: {best_overall['Accuracy']:.4f}")
    print(f"  ROC-AUC: {best_overall['ROC-AUC']:.4f}")
    print(f"{'='*80}")
    
    return df


if __name__ == "__main__":
    # Run ablation study
    all_results, feature_cols = run_latent_dimension_ablation()
    
    # Visualize results
    df_results = visualize_latent_dimension_results(all_results)
    
    print("\n" + "="*80)
    print("Latent Dimension Ablation Study 완료!")
    print("="*80)
    print("\n생성된 파일:")
    print("  - autoencoder_latent4.pth, latent_vectors_4d.npy")
    print("  - autoencoder_latent8.pth, latent_vectors_8d.npy")
    print("  - autoencoder_latent12.pth, latent_vectors_12d.npy")
    print("  - autoencoder_latent16.pth, latent_vectors_16d.npy")
    print("  - latent_dimension_ablation_results.csv")
    print("  - latent_dimension_ablation.png")
    print("  - latent_dimension_detailed.png")
