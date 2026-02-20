import torch
import torch.nn as nn
import torch.nn.functional as F

class SwiGLU(nn.Module):
    def __init__(self, dim_in, dim_out):
        super().__init__()
        self.linear = nn.Linear(dim_in, dim_out)
        self.gate = nn.Linear(dim_in, dim_out)
    
    def forward(self, x):
        return F.silu(self.gate(x)) * self.linear(x)

class AttentionModule(nn.Module):
    def __init__(self, dim, num_heads=4):
        super().__init__()
        self.num_heads = num_heads
        self.dim = dim
        self.head_dim = dim // num_heads
        self.qkv = nn.Linear(dim, dim * 3)
        self.proj = nn.Linear(dim, dim)
        self.scale = self.head_dim ** -0.5
        
    def forward(self, x):
        B, D = x.shape
        qkv = self.qkv(x).reshape(B, 3, self.num_heads, self.head_dim)
        qkv = qkv.permute(1, 0, 2, 3)
        q, k, v = qkv[0], qkv[1], qkv[2]
        attn = (q @ k.transpose(-2, -1)) * self.scale
        attn = F.softmax(attn, dim=-1)
        x = (attn @ v).reshape(B, D)
        x = self.proj(x)
        return x, attn

class AutoEncoder(nn.Module):
    """Simplified AutoEncoder for Lambda inference"""
    def __init__(self, input_dim=30, latent_dim=12, hidden_dims=[64, 32, 16]):
        super().__init__()
        self.input_dim = input_dim
        self.latent_dim = latent_dim
        
        # Encoder
        encoder_layers = []
        prev_dim = input_dim
        for hidden_dim in hidden_dims:
            encoder_layers.append(SwiGLU(prev_dim, hidden_dim))
            encoder_layers.append(nn.BatchNorm1d(hidden_dim))
            encoder_layers.append(nn.Dropout(0.1))
            prev_dim = hidden_dim
        
        self.encoder = nn.Sequential(*encoder_layers)
        self.attention = AttentionModule(hidden_dims[-1], num_heads=4)
        self.to_latent = nn.Linear(hidden_dims[-1], latent_dim)
    
    def encode(self, x):
        h = self.encoder(x)
        h, attn_weights = self.attention(h)
        z = self.to_latent(h)
        return z, attn_weights
