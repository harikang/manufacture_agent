"""
SHAP Explainer 사전 생성 스크립트
Lambda에서 사용할 SHAP explainer를 미리 생성하여 S3에 업로드
"""

import pickle
import shap
import numpy as np
import os
from sklearn.model_selection import train_test_split

print("Loading models...")

# Gradient Boosting 모델 로드
with open('deployment_models/gradient_boosting_model.pkl', 'rb') as f:
    gb_model = pickle.load(f)

print("Model loaded successfully!")

# 샘플 데이터 생성 (실제로는 학습 데이터 사용)
# 42D features (30D original + 12D latent)
np.random.seed(42)
n_samples = 1000
X_sample = np.random.randn(n_samples, 42)

print(f"Creating SHAP explainer with {n_samples} samples...")

# SHAP TreeExplainer 생성
explainer = shap.TreeExplainer(gb_model, X_sample)

print("SHAP explainer created!")

# 저장
output_path = 'deployment_models/shap_explainer.pkl'
with open(output_path, 'wb') as f:
    pickle.dump(explainer, f)

print(f"SHAP explainer saved to {output_path}")

# 테스트
print("\nTesting explainer...")
test_sample = X_sample[:1]
shap_values = explainer.shap_values(test_sample)

if isinstance(shap_values, list):
    print(f"SHAP values shape (class 0): {shap_values[0].shape}")
    print(f"SHAP values shape (class 1): {shap_values[1].shape}")
else:
    print(f"SHAP values shape: {shap_values.shape}")

print(f"Base value: {explainer.expected_value}")

print("\n✅ SHAP explainer is ready for deployment!")
print(f"File size: {os.path.getsize(output_path) / 1024 / 1024:.2f} MB")

print("\nNext steps:")
print("1. Upload to S3:")
print(f"   aws s3 cp {output_path} s3://diecasting-models/models/shap_explainer.pkl")
print("2. Deploy Lambda T2 with SHAP support")
