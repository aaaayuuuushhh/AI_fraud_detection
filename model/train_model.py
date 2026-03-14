import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
import pickle
import os

print("🚀 Starting Optimized Fraud Model Training...")

# Create data directory if missing
if not os.path.exists("data/creditcard.csv"):
    print("❌ ERROR: data/creditcard.csv not found!")
    exit(1)

# Load dataset
data = pd.read_csv("data/creditcard.csv")

# Use a large subset to ensure fraud samples are included, but train faster
# Full dataset usually has 492 frauds.
X = data.drop(columns=["Class"])
y = data["Class"]

# Stratified split to preserve fraud ratio
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# Solver 'liblinear' is often faster for small-medium datasets with penalty
# class_weight='balanced' is CRITICAL to actually predict 'Fraud' class (1)
print("⚙️  Training model (Optimized for imbalanced data)...")
model = LogisticRegression(solver='liblinear', class_weight='balanced', max_iter=1000)
model.fit(X_train, y_train)

# Save model
model_path = "model/fraud_model.pkl"
os.makedirs("model", exist_ok=True)
with open(model_path, "wb") as f:
    pickle.dump(model, f)

print(f"✅ Model trained and saved as '{model_path}' successfully.")