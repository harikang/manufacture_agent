import torch
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.manifold import TSNE
from sklearn.decomposition import PCA
import pickle
from autoencoder_model import DieCastingAutoEncoder, load_and_preprocess_data

plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")


def visualize_training_history(history):
    """Visualize training history"""
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    # Total loss
    axes[0].plot(history['train_loss'], label='Train', linewidth=2)
    axes[0].plot(history['val_loss'], label='Validation', linewidth=2)
    axes[0].set_xlabel('Epoch', fontsize=12)
    axes[0].set_ylabel('Total Loss', fontsize=12)
    axes[0].set_title('Total Loss', fontsize=14, fontweight='bold')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    # Reconstruction loss
    axes[1].plot(history['train_recon_loss'], label='Train', linewidth=2)
    axes[1].plot(history['val_recon_loss'], label='Validation', linewidth=2)
    axes[1].set_xlabel('Epoch', fontsize=12)
    axes[1].set_ylabel('Reconstruction Loss', fontsize=12)
    axes[1].set_title('Reconstruction Loss (MSE)', fontsize=14, fontweight='bold')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    
    # Focal loss
    axes[2].plot(history['train_focal_loss'], label='Train', linewidth=2)
    axes[2].plot(history['val_focal_loss'], label='Validation', linewidth=2)
    axes[2].set_xlabel('Epoch', fontsize=12)
    axes[2].set_ylabel('Focal Loss', fontsize=12)
    axes[2].set_title('Focal Loss (Defect Classification)', fontsize=14, fontweight='bold')
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('training_history.png', dpi=300, bbox_inches='tight')
    print("학습 히스토리 저장: training_history.png")
    plt.close()


def extract_latent_vectors(model, X, y, device='cpu'):
    """Extract latent vectors from trained model"""
    model.eval()
    latent_vectors = []
    attention_weights = []
    
    with torch.no_grad():
        X_tensor = torch.FloatTensor(X).to(device)
        
        # Process in batches
        batch_size = 256
        for i in range(0, len(X), batch_size):
            batch = X_tensor[i:i+batch_size]
            z, attn = model.encode(batch)
            latent_vectors.append(z.cpu().numpy())
            attention_weights.append(attn.cpu().numpy())
    
    latent_vectors = np.vstack(latent_vectors)
    attention_weights = np.vstack([a.mean(axis=1) for a in attention_weights])
    
    return latent_vectors, attention_weights


def visualize_latent_space(latent_vectors, labels, method='tsne'):
    """Visualize latent space using t-SNE or PCA"""
    print(f"\n{method.upper()}로 latent space 시각화 중...")
    
    if method == 'tsne':
        reducer = TSNE(n_components=2, random_state=42, perplexity=30)
        embedded = reducer.fit_transform(latent_vectors)
    else:
        reducer = PCA(n_components=2, random_state=42)
        embedded = reducer.fit_transform(latent_vectors)
    
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # Plot normal samples
    normal_mask = labels == 0
    defect_mask = labels == 1
    
    scatter1 = ax.scatter(embedded[normal_mask, 0], embedded[normal_mask, 1], 
                         c='blue', alpha=0.5, s=30, label='정상', edgecolors='k', linewidth=0.5)
    scatter2 = ax.scatter(embedded[defect_mask, 0], embedded[defect_mask, 1], 
                         c='red', alpha=0.7, s=50, label='불량', edgecolors='k', linewidth=0.5)
    
    ax.set_xlabel(f'{method.upper()} Component 1', fontsize=14, fontweight='bold')
    ax.set_ylabel(f'{method.upper()} Component 2', fontsize=14, fontweight='bold')
    ax.set_title(f'Latent Space Visualization ({method.upper()})', fontsize=16, fontweight='bold')
    ax.legend(fontsize=12, loc='best')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'latent_space_{method}.png', dpi=300, bbox_inches='tight')
    print(f"Latent space 시각화 저장: latent_space_{method}.png")
    plt.close()


def analyze_latent_dimensions(latent_vectors, labels):
    """Analyze each latent dimension"""
    n_dims = latent_vectors.shape[1]
    
    fig, axes = plt.subplots(2, 4, figsize=(20, 10))
    axes = axes.flatten()
    
    for i in range(n_dims):
        ax = axes[i]
        
        # Distribution for normal vs defect
        normal_vals = latent_vectors[labels == 0, i]
        defect_vals = latent_vectors[labels == 1, i]
        
        ax.hist(normal_vals, bins=50, alpha=0.6, label='정상', color='blue', density=True)
        ax.hist(defect_vals, bins=50, alpha=0.6, label='불량', color='red', density=True)
        
        ax.set_xlabel(f'Latent Dim {i+1}', fontsize=11, fontweight='bold')
        ax.set_ylabel('Density', fontsize=11)
        ax.set_title(f'Latent Dimension {i+1}', fontsize=12, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        
        # Add statistics
        mean_diff = abs(normal_vals.mean() - defect_vals.mean())
        ax.text(0.02, 0.98, f'Δμ={mean_diff:.3f}', 
               transform=ax.transAxes, fontsize=9,
               verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    plt.savefig('latent_dimensions_analysis.png', dpi=300, bbox_inches='tight')
    print("Latent 차원 분석 저장: latent_dimensions_analysis.png")
    plt.close()


def analyze_latent_correlations(latent_vectors, labels):
    """Analyze correlations between latent dimensions"""
    # Correlation matrix
    corr_matrix = np.corrcoef(latent_vectors.T)
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap='coolwarm', 
                center=0, square=True, linewidths=1, cbar_kws={"shrink": 0.8},
                xticklabels=[f'L{i+1}' for i in range(latent_vectors.shape[1])],
                yticklabels=[f'L{i+1}' for i in range(latent_vectors.shape[1])],
                ax=ax)
    
    ax.set_title('Latent Dimensions Correlation Matrix', fontsize=16, fontweight='bold', pad=20)
    
    plt.tight_layout()
    plt.savefig('latent_correlation_matrix.png', dpi=300, bbox_inches='tight')
    print("Latent 상관관계 매트릭스 저장: latent_correlation_matrix.png")
    plt.close()


def compute_latent_statistics(latent_vectors, labels):
    """Compute statistics for each latent dimension"""
    n_dims = latent_vectors.shape[1]
    
    stats_data = []
    
    for i in range(n_dims):
        normal_vals = latent_vectors[labels == 0, i]
        defect_vals = latent_vectors[labels == 1, i]
        
        stats_data.append({
            'Dimension': f'Latent_{i+1}',
            'Normal_Mean': normal_vals.mean(),
            'Normal_Std': normal_vals.std(),
            'Defect_Mean': defect_vals.mean(),
            'Defect_Std': defect_vals.std(),
            'Mean_Diff': abs(normal_vals.mean() - defect_vals.mean()),
            'Separation_Score': abs(normal_vals.mean() - defect_vals.mean()) / 
                              (normal_vals.std() + defect_vals.std())
        })
    
    stats_df = pd.DataFrame(stats_data)
    stats_df = stats_df.sort_values('Separation_Score', ascending=False)
    
    print("\n" + "="*80)
    print("Latent Dimension 통계")
    print("="*80)
    print(stats_df.to_string(index=False))
    print("\n가장 구분력이 높은 차원:", stats_df.iloc[0]['Dimension'])
    
    stats_df.to_csv('latent_statistics.csv', index=False)
    print("\nLatent 통계 저장: latent_statistics.csv")
    
    return stats_df


def visualize_attention_weights(attention_weights, feature_names):
    """Visualize attention weights"""
    avg_attention = attention_weights.mean(axis=0)
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Sort by attention weight
    sorted_indices = np.argsort(avg_attention)[::-1][:20]  # Top 20
    
    ax.barh(range(len(sorted_indices)), avg_attention[sorted_indices], color='steelblue')
    ax.set_yticks(range(len(sorted_indices)))
    ax.set_yticklabels([feature_names[i] for i in sorted_indices], fontsize=10)
    ax.set_xlabel('Average Attention Weight', fontsize=12, fontweight='bold')
    ax.set_title('Top 20 Features by Attention Weight', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='x')
    
    plt.tight_layout()
    plt.savefig('attention_weights.png', dpi=300, bbox_inches='tight')
    print("Attention weights 저장: attention_weights.png")
    plt.close()


if __name__ == "__main__":
    print("="*80)
    print("AutoEncoder Latent Space 분석")
    print("="*80)
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"사용 디바이스: {device}")
    
    # Load data
    csv_path = '/Users/kang/Downloads/dataset/DieCasting_Quality_Raw_Data.csv'
    X, y, feature_names = load_and_preprocess_data(csv_path)
    
    # Standardize
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Load trained model
    print("\n학습된 모델 로딩 중...")
    model = DieCastingAutoEncoder(
        input_dim=X.shape[1],
        latent_dim=8,
        hidden_dims=[64, 32, 16]
    ).to(device)
    
    model.load_state_dict(torch.load('best_autoencoder.pth', map_location=device))
    print("모델 로딩 완료!")
    
    # Load training history
    with open('training_history.pkl', 'rb') as f:
        history = pickle.load(f)
    
    # Visualize training history
    print("\n학습 히스토리 시각화 중...")
    visualize_training_history(history)
    
    # Extract latent vectors
    print("\nLatent vectors 추출 중...")
    latent_vectors, attention_weights = extract_latent_vectors(model, X_scaled, y, device)
    print(f"Latent vectors shape: {latent_vectors.shape}")
    
    # Save latent vectors
    np.save('latent_vectors.npy', latent_vectors)
    np.save('attention_weights.npy', attention_weights)
    print("Latent vectors 저장 완료!")
    
    # Visualize latent space
    visualize_latent_space(latent_vectors, y, method='tsne')
    visualize_latent_space(latent_vectors, y, method='pca')
    
    # Analyze latent dimensions
    print("\nLatent dimensions 분석 중...")
    analyze_latent_dimensions(latent_vectors, y)
    
    # Analyze correlations
    print("\nLatent 상관관계 분석 중...")
    analyze_latent_correlations(latent_vectors, y)
    
    # Compute statistics
    stats_df = compute_latent_statistics(latent_vectors, y)
    
    # Visualize attention weights
    print("\nAttention weights 시각화 중...")
    visualize_attention_weights(attention_weights, feature_names)
    
    print("\n" + "="*80)
    print("분석 완료!")
    print("="*80)
    print("\n생성된 파일:")
    print("  - best_autoencoder.pth: 학습된 모델")
    print("  - training_history.pkl: 학습 기록")
    print("  - latent_vectors.npy: Latent vectors")
    print("  - attention_weights.npy: Attention weights")
    print("  - training_history.png: 학습 히스토리")
    print("  - latent_space_tsne.png: t-SNE 시각화")
    print("  - latent_space_pca.png: PCA 시각화")
    print("  - latent_dimensions_analysis.png: 차원별 분석")
    print("  - latent_correlation_matrix.png: 상관관계 매트릭스")
    print("  - latent_statistics.csv: 통계 정보")
    print("  - attention_weights.png: Attention weights")
