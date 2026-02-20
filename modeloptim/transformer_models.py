import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import f1_score, accuracy_score, roc_auc_score, classification_report
from torch.utils.data import Dataset, DataLoader
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

plt.style.use('seaborn-v0_8-darkgrid')


class TabularDataset(Dataset):
    """Dataset for tabular data"""
    def __init__(self, X, y):
        self.X = torch.FloatTensor(X)
        self.y = torch.FloatTensor(y)
    
    def __len__(self):
        return len(self.X)
    
    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]


class FTTransformer(nn.Module):
    """
    Feature Tokenizer + Transformer (FT-Transformer)
    Paper: "Revisiting Deep Learning Models for Tabular Data" (NeurIPS 2021)
    """
    def __init__(self, n_features, d_token=192, n_blocks=3, attention_dropout=0.2, 
                 ffn_dropout=0.1, residual_dropout=0.0, n_heads=8):
        super().__init__()
        self.n_features = n_features
        self.d_token = d_token
        
        # Feature tokenizer: each feature gets its own embedding
        self.feature_tokenizer = nn.Linear(1, d_token)
        
        # CLS token for classification
        self.cls_token = nn.Parameter(torch.randn(1, 1, d_token))
        
        # Transformer blocks
        self.blocks = nn.ModuleList([
            TransformerBlock(
                d_token=d_token,
                n_heads=n_heads,
                attention_dropout=attention_dropout,
                ffn_dropout=ffn_dropout,
                residual_dropout=residual_dropout
            )
            for _ in range(n_blocks)
        ])
        
        # Classification head
        self.head = nn.Sequential(
            nn.LayerNorm(d_token),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(d_token, 1)
        )
    
    def forward(self, x):
        # x: (batch_size, n_features)
        batch_size = x.shape[0]
        
        # Tokenize features: (batch_size, n_features, d_token)
        x = x.unsqueeze(-1)  # (batch_size, n_features, 1)
        tokens = self.feature_tokenizer(x)  # (batch_size, n_features, d_token)
        
        # Add CLS token
        cls_tokens = self.cls_token.expand(batch_size, -1, -1)
        tokens = torch.cat([cls_tokens, tokens], dim=1)  # (batch_size, n_features+1, d_token)
        
        # Apply transformer blocks
        for block in self.blocks:
            tokens = block(tokens)
        
        # Use CLS token for classification
        cls_output = tokens[:, 0]  # (batch_size, d_token)
        logits = self.head(cls_output)  # (batch_size, 1)
        
        return logits.squeeze(-1)


class TransformerBlock(nn.Module):
    """Transformer block with multi-head attention and FFN"""
    def __init__(self, d_token, n_heads, attention_dropout, ffn_dropout, residual_dropout):
        super().__init__()
        
        # Multi-head attention
        self.attention = nn.MultiheadAttention(
            embed_dim=d_token,
            num_heads=n_heads,
            dropout=attention_dropout,
            batch_first=True
        )
        self.attention_dropout = nn.Dropout(residual_dropout)
        self.attention_norm = nn.LayerNorm(d_token)
        
        # Feed-forward network
        self.ffn = nn.Sequential(
            nn.Linear(d_token, d_token * 4),
            nn.GELU(),
            nn.Dropout(ffn_dropout),
            nn.Linear(d_token * 4, d_token),
            nn.Dropout(ffn_dropout)
        )
        self.ffn_dropout = nn.Dropout(residual_dropout)
        self.ffn_norm = nn.LayerNorm(d_token)
    
    def forward(self, x):
        # Multi-head attention with residual
        attn_out, _ = self.attention(x, x, x)
        x = x + self.attention_dropout(attn_out)
        x = self.attention_norm(x)
        
        # FFN with residual
        ffn_out = self.ffn(x)
        x = x + self.ffn_dropout(ffn_out)
        x = self.ffn_norm(x)
        
        return x


class TabTransformer(nn.Module):
    """
    TabTransformer for tabular data
    Paper: "TabTransformer: Tabular Data Modeling Using Contextual Embeddings" (2020)
    
    Note: Original TabTransformer uses categorical embeddings + continuous features.
    This implementation treats all features as continuous for simplicity.
    """
    def __init__(self, n_features, d_model=128, n_heads=8, n_layers=6, 
                 dim_feedforward=512, dropout=0.1):
        super().__init__()
        self.n_features = n_features
        self.d_model = d_model
        
        # Feature embedding
        self.feature_embedding = nn.Linear(n_features, d_model)
        
        # Positional encoding (learnable)
        self.pos_encoding = nn.Parameter(torch.randn(1, n_features, d_model))
        
        # Transformer encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=n_heads,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            activation='gelu',
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)
        
        # Classification head
        self.head = nn.Sequential(
            nn.LayerNorm(d_model),
            nn.Linear(d_model, 128),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(128, 1)
        )
    
    def forward(self, x):
        # x: (batch_size, n_features)
        batch_size = x.shape[0]
        
        # Reshape for feature-wise processing
        x = x.unsqueeze(1).expand(-1, self.n_features, -1)  # (batch_size, n_features, n_features)
        
        # Create feature-wise representation (diagonal)
        feature_tokens = []
        for i in range(self.n_features):
            feature_tokens.append(x[:, i, i].unsqueeze(1))
        x = torch.cat(feature_tokens, dim=1)  # (batch_size, n_features, 1)
        
        # Embed features
        x = x.expand(-1, -1, self.d_model)  # Simple expansion
        x = x * self.pos_encoding  # Add positional encoding
        
        # Apply transformer
        x = self.transformer(x)  # (batch_size, n_features, d_model)
        
        # Global average pooling
        x = x.mean(dim=1)  # (batch_size, d_model)
        
        # Classification
        logits = self.head(x)  # (batch_size, 1)
        
        return logits.squeeze(-1)


class SimpleTabTransformer(nn.Module):
    """
    Simplified TabTransformer that works better with continuous features
    """
    def __init__(self, n_features, d_model=128, n_heads=8, n_layers=4, dropout=0.1):
        super().__init__()
        self.n_features = n_features
        self.d_model = d_model
        
        # Project each feature to d_model dimension
        self.feature_projection = nn.Linear(1, d_model)
        
        # Learnable positional embeddings
        self.pos_embedding = nn.Parameter(torch.randn(1, n_features, d_model))
        
        # Transformer encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=n_heads,
            dim_feedforward=d_model * 4,
            dropout=dropout,
            activation='gelu',
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)
        
        # Classification head
        self.classifier = nn.Sequential(
            nn.LayerNorm(d_model),
            nn.Linear(d_model, 64),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(64, 1)
        )
    
    def forward(self, x):
        # x: (batch_size, n_features)
        batch_size = x.shape[0]
        
        # Project each feature independently
        x = x.unsqueeze(-1)  # (batch_size, n_features, 1)
        x = self.feature_projection(x)  # (batch_size, n_features, d_model)
        
        # Add positional embeddings
        x = x + self.pos_embedding
        
        # Apply transformer
        x = self.transformer(x)  # (batch_size, n_features, d_model)
        
        # Global average pooling
        x = x.mean(dim=1)  # (batch_size, d_model)
        
        # Classification
        logits = self.classifier(x)
        
        return logits.squeeze(-1)


def train_transformer_model(model, train_loader, val_loader, epochs=50, lr=1e-4, device='cpu'):
    """Train transformer model"""
    model = model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-5)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='max', factor=0.5, patience=5
    )
    
    # Use weighted loss for imbalanced data
    pos_weight = torch.tensor([3.5]).to(device)  # Weight for positive class
    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    
    best_f1 = 0
    history = {'train_loss': [], 'val_loss': [], 'val_f1': [], 'val_acc': [], 'val_auc': []}
    patience_counter = 0
    max_patience = 15
    
    for epoch in range(epochs):
        # Training
        model.train()
        train_losses = []
        
        for X_batch, y_batch in train_loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)
            
            optimizer.zero_grad()
            logits = model(X_batch)
            loss = criterion(logits, y_batch)
            loss.backward()
            
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            
            train_losses.append(loss.item())
        
        # Validation
        model.eval()
        val_losses = []
        all_preds = []
        all_labels = []
        all_probs = []
        
        with torch.no_grad():
            for X_batch, y_batch in val_loader:
                X_batch, y_batch = X_batch.to(device), y_batch.to(device)
                
                logits = model(X_batch)
                loss = criterion(logits, y_batch)
                
                probs = torch.sigmoid(logits)
                preds = (probs > 0.5).float()
                
                val_losses.append(loss.item())
                all_preds.extend(preds.cpu().numpy())
                all_labels.extend(y_batch.cpu().numpy())
                all_probs.extend(probs.cpu().numpy())
        
        # Metrics
        train_loss = np.mean(train_losses)
        val_loss = np.mean(val_losses)
        val_f1 = f1_score(all_labels, all_preds, zero_division=0)
        val_acc = accuracy_score(all_labels, all_preds)
        val_auc = roc_auc_score(all_labels, all_probs)
        
        history['train_loss'].append(train_loss)
        history['val_loss'].append(val_loss)
        history['val_f1'].append(val_f1)
        history['val_acc'].append(val_acc)
        history['val_auc'].append(val_auc)
        
        scheduler.step(val_f1)
        
        if val_f1 > best_f1:
            best_f1 = val_f1
            torch.save(model.state_dict(), f'best_{model.__class__.__name__}.pth')
            patience_counter = 0
        else:
            patience_counter += 1
        
        if (epoch + 1) % 10 == 0:
            print(f"Epoch [{epoch+1}/{epochs}]")
            print(f"  Train Loss: {train_loss:.4f}")
            print(f"  Val Loss: {val_loss:.4f}, F1: {val_f1:.4f}, Acc: {val_acc:.4f}, AUC: {val_auc:.4f}")
            print(f"  Pred distribution: {np.sum(all_preds)}/{len(all_preds)} positive")
        
        # Early stopping
        if patience_counter >= max_patience:
            print(f"Early stopping at epoch {epoch+1}")
            break
    
    return history, best_f1


def evaluate_transformer_models():
    """Evaluate FT-Transformer and TabTransformer"""
    
    print("="*80)
    print("Transformer Models Evaluation")
    print("="*80)
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"사용 디바이스: {device}")
    
    # Load data
    print("\n데이터 로딩 중...")
    df = pd.read_csv('/Users/kang/Downloads/dataset/DieCasting_Quality_Raw_Data.csv', header=[0, 1])
    df.columns = ['_'.join(col).strip() for col in df.columns.values]
    
    # Select features
    process_features = [col for col in df.columns if col.startswith('Process_')]
    sensor_features = [col for col in df.columns if col.startswith('Sensor_')]
    feature_cols = [col for col in process_features + sensor_features if col != 'Process_id'][:30]
    
    X = df[feature_cols].values
    X = np.nan_to_num(X, nan=np.nanmean(X, axis=0))
    
    # Labels
    defect_features = [col for col in df.columns if col.startswith('Defects_')]
    y = (df[defect_features].sum(axis=1) > 0).astype(int).values
    
    # Load latent vectors
    latent_dims = [8, 12, 16]
    results = {}
    
    for latent_dim in latent_dims:
        print(f"\n{'='*80}")
        print(f"Latent Dimension: {latent_dim}D")
        print(f"{'='*80}")
        
        # Load latent vectors
        X_latent = np.load(f'latent_vectors_{latent_dim}d.npy')
        
        # Combine features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        X_combined = np.hstack([X_scaled, X_latent])
        
        print(f"Combined features shape: {X_combined.shape}")
        
        # Train-test split
        X_train, X_test, y_train, y_test = train_test_split(
            X_combined, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Create datasets
        train_dataset = TabularDataset(X_train, y_train)
        test_dataset = TabularDataset(X_test, y_test)
        
        train_loader = DataLoader(train_dataset, batch_size=128, shuffle=True)
        test_loader = DataLoader(test_dataset, batch_size=128, shuffle=False)
        
        n_features = X_combined.shape[1]
        
        # Models to evaluate
        models = {
            'FT-Transformer': FTTransformer(
                n_features=n_features,
                d_token=96,  # Reduced
                n_blocks=2,  # Reduced
                n_heads=4,  # Reduced
                attention_dropout=0.2,
                ffn_dropout=0.1
            ),
            'TabTransformer': SimpleTabTransformer(
                n_features=n_features,
                d_model=64,  # Reduced
                n_heads=4,  # Reduced
                n_layers=2,  # Reduced
                dropout=0.1
            )
        }
        
        latent_results = {}
        
        for model_name, model in models.items():
            print(f"\n{model_name} 학습 중...")
            print(f"파라미터 수: {sum(p.numel() for p in model.parameters()):,}")
            
            # Train
            history, best_f1 = train_transformer_model(
                model, train_loader, test_loader, epochs=100, lr=3e-4, device=device
            )
            
            # Load best model and evaluate
            if best_f1 > 0:  # Only load if model was saved
                model.load_state_dict(torch.load(f'best_{model.__class__.__name__}.pth'))
            model.eval()
            
            all_preds = []
            all_labels = []
            all_probs = []
            
            with torch.no_grad():
                for X_batch, y_batch in test_loader:
                    X_batch = X_batch.to(device)
                    logits = model(X_batch)
                    probs = torch.sigmoid(logits)
                    preds = (probs > 0.5).float()
                    
                    all_preds.extend(preds.cpu().numpy())
                    all_labels.extend(y_batch.numpy())
                    all_probs.extend(probs.cpu().numpy())
            
            # Metrics
            f1 = f1_score(all_labels, all_preds)
            acc = accuracy_score(all_labels, all_preds)
            auc = roc_auc_score(all_labels, all_probs)
            
            print(f"\n최종 성능:")
            print(f"  F1-Score: {f1:.4f}")
            print(f"  Accuracy: {acc:.4f}")
            print(f"  ROC-AUC: {auc:.4f}")
            
            latent_results[model_name] = {
                'f1_score': f1,
                'accuracy': acc,
                'roc_auc': auc,
                'history': history
            }
        
        results[latent_dim] = latent_results
    
    return results


def compare_with_ml_models(transformer_results):
    """Compare transformer results with ML models"""
    
    print("\n" + "="*80)
    print("Transformer vs ML Models 비교")
    print("="*80)
    
    # Load ML results
    ml_df = pd.read_csv('latent_dimension_ablation_results.csv')
    
    # Prepare comparison data
    comparison_data = []
    
    # Add ML results
    for _, row in ml_df.iterrows():
        comparison_data.append({
            'Latent Dim': int(row['Latent Dim']),
            'Model': row['Model'],
            'Type': 'ML',
            'F1-Score': row['F1-Score'],
            'Accuracy': row['Accuracy'],
            'ROC-AUC': row['ROC-AUC']
        })
    
    # Add Transformer results
    for latent_dim, models_results in transformer_results.items():
        for model_name, metrics in models_results.items():
            comparison_data.append({
                'Latent Dim': latent_dim,
                'Model': model_name,
                'Type': 'Transformer',
                'F1-Score': metrics['f1_score'],
                'Accuracy': metrics['accuracy'],
                'ROC-AUC': metrics['roc_auc']
            })
    
    df = pd.DataFrame(comparison_data)
    
    # Save results
    df.to_csv('transformer_vs_ml_results.csv', index=False)
    print("\n결과 저장: transformer_vs_ml_results.csv")
    
    # Print comparison
    print("\n상위 10개 모델 (F1-Score 기준):")
    print(df.sort_values('F1-Score', ascending=False).head(10).to_string(index=False))
    
    # Visualize
    visualize_comparison(df)
    
    return df


def visualize_comparison(df):
    """Visualize transformer vs ML comparison"""
    
    fig, axes = plt.subplots(1, 3, figsize=(20, 6))
    
    latent_dims = sorted(df['Latent Dim'].unique())
    metrics = ['F1-Score', 'Accuracy', 'ROC-AUC']
    
    for idx, metric in enumerate(metrics):
        ax = axes[idx]
        
        # Plot ML models
        ml_data = df[df['Type'] == 'ML']
        for model in ml_data['Model'].unique():
            model_data = ml_data[ml_data['Model'] == model]
            ax.plot(model_data['Latent Dim'], model_data[metric], 
                   marker='o', linewidth=2, markersize=8, label=f'{model} (ML)', alpha=0.7)
        
        # Plot Transformer models
        trans_data = df[df['Type'] == 'Transformer']
        for model in trans_data['Model'].unique():
            model_data = trans_data[trans_data['Model'] == model]
            ax.plot(model_data['Latent Dim'], model_data[metric], 
                   marker='s', markersize=10, label=f'{model}', 
                   linestyle='--', linewidth=3)
        
        ax.set_xlabel('Latent Dimension', fontsize=12, fontweight='bold')
        ax.set_ylabel(metric, fontsize=12, fontweight='bold')
        ax.set_title(f'{metric} Comparison', fontsize=14, fontweight='bold')
        ax.legend(fontsize=9, loc='best')
        ax.grid(True, alpha=0.3)
        ax.set_xticks(latent_dims)
    
    plt.suptitle('Transformer Models vs ML Models', fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.savefig('transformer_vs_ml_comparison.png', dpi=300, bbox_inches='tight')
    print("시각화 저장: transformer_vs_ml_comparison.png")
    plt.close()


if __name__ == "__main__":
    # Evaluate transformer models
    transformer_results = evaluate_transformer_models()
    
    # Compare with ML models
    comparison_df = compare_with_ml_models(transformer_results)
    
    print("\n" + "="*80)
    print("Transformer Models 평가 완료!")
    print("="*80)
    print("\n생성된 파일:")
    print("  - best_FTTransformer.pth")
    print("  - best_SimpleTabTransformer.pth")
    print("  - transformer_vs_ml_results.csv")
    print("  - transformer_vs_ml_comparison.png")
