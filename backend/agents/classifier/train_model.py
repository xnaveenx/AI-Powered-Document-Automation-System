import os
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

# ---------------- CONFIG ----------------
TRAINING_FOLDER = "D:/Langs/Final_year_project/AI-Powered-Document-Automation-System/training_data" # Folder with subfolders as categories
MODEL_OUTPUT_FILE = "ai_model.pkl"
CONFIDENCE_THRESHOLD = 0.5  # Probability threshold for unknown docs

# ---------------- LOAD DATA ----------------
texts = []
labels = []

for category in os.listdir(TRAINING_FOLDER):
    category_folder = os.path.join(TRAINING_FOLDER, category)
    if not os.path.isdir(category_folder):
        continue
    for file in os.listdir(category_folder):
        file_path = os.path.join(category_folder, file)
        with open(file_path, "r", encoding="utf-8") as f:
            texts.append(f.read())
            labels.append(category)

print(f"[INFO] Loaded {len(texts)} documents from {len(set(labels))} categories.")

# ---------------- SPLIT DATA ----------------
X_train, X_test, y_train, y_test = train_test_split(texts, labels, test_size=0.2, random_state=42)

# ---------------- VECTORIZE TEXT ----------------
vectorizer = TfidfVectorizer(stop_words='english', max_features=5000)
X_train_tfidf = vectorizer.fit_transform(X_train)
X_test_tfidf = vectorizer.transform(X_test)

# ---------------- TRAIN MODEL ----------------
clf = RandomForestClassifier(n_estimators=100, random_state=42)
clf.fit(X_train_tfidf, y_train)

# ---------------- EVALUATE MODEL ----------------
y_pred = clf.predict(X_test_tfidf)
print("[INFO] Classification Report:\n")
print(classification_report(y_test, y_pred))

# ---------------- SAVE MODEL ----------------
with open(MODEL_OUTPUT_FILE, "wb") as f:
    pickle.dump({
        "vectorizer": vectorizer,
        "model": clf,
        "confidence_threshold": CONFIDENCE_THRESHOLD
    }, f)

print(f"[INFO] Model saved to {MODEL_OUTPUT_FILE}")
