"""Test which scaler produces reasonable scaled values"""
import pickle
import numpy as np

# Test input
test_features = np.array([[
    650.0, 120.0, 2.5, 1.2, 15.0, 800.0, 180.0, 680.0, 45.0, 250.0,
    50.0, 100.0, 90.0, 3.0, 5.0, 8.0, 0.15, 65.0, 650.0, 180.0,
    170.0, 120.0, 90.0, 50.0, 25.0, 100.0, 2.5, 150.0, 45.0, 380.0
]])

scalers = [
    ('deployment_models/scaler.pkl', 'deployment_models'),
    ('scaler_retrained.pkl', 'root retrained')
]

print("Testing scalers with sample input:")
print(f"Input shape: {test_features.shape}")
print(f"Input min/max: {test_features.min():.2f} / {test_features.max():.2f}")
print()

for path, name in scalers:
    try:
        with open(path, 'rb') as f:
            scaler = pickle.load(f)
        
        scaled = scaler.transform(test_features)
        
        print(f"{name}:")
        print(f"  n_features: {scaler.n_features_in_}")
        print(f"  Scaled min/max: {scaled.min():.4f} / {scaled.max():.4f}")
        print(f"  Scaled mean: {scaled.mean():.4f}")
        print(f"  Scaled std: {scaled.std():.4f}")
        print(f"  Has NaN: {np.isnan(scaled).any()}")
        print(f"  Has Inf: {np.isinf(scaled).any()}")
        print()
        
    except Exception as e:
        print(f"{name}: ERROR - {e}\n")

print("Expected: Scaled values should be roughly in range [-3, 3] for StandardScaler")
