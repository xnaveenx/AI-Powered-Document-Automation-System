import os
import pickle
import random
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder

MODEL_FILENAME = "ai_model.pkl"

class AIModel:
    def __init__(self, model_path=None):
        """
        Initializes the AI model.
        If a trained model exists at model_path, it loads it.
        Otherwise, creates a new untrained model.
        """
        self.model_path = model_path or os.path.join(os.path.dirname(__file__), MODEL_FILENAME)
        self.pipeline = None
        self.label_encoder = LabelEncoder()
        self.labels = ["Finance", "Legal", "Resume", "Medical", "Technical", "General"]

        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, "rb") as f:
                    data = pickle.load(f)
                    self.pipeline = data["pipeline"]
                    self.label_encoder = data["label_encoder"]
                print("[AI MODEL] Loaded trained AI model from file.")
            except Exception as e:
                print(f"[AI MODEL] Failed to load model: {e}. Using untrained AI.")
        else:
            print("[AI MODEL] No trained model found. Using untrained AI.")

    def train(self, texts: list, categories: list):
        """
        Train the Random Forest model.
        """
        # Encode labels
        y = self.label_encoder.fit_transform(categories)

        # Create pipeline
        self.pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(stop_words="english", max_features=5000)),
            ("rf", RandomForestClassifier(n_estimators=100, random_state=42))
        ])
        self.pipeline.fit(texts, y)
        print("[AI MODEL] Training complete.")

        # Save model to disk
        self.save_model()

    def save_model(self):
        """
        Save the trained model and label encoder to disk.
        """
        try:
            with open(self.model_path, "wb") as f:
                pickle.dump({
                    "pipeline": self.pipeline,
                    "label_encoder": self.label_encoder
                }, f)
            print(f"[AI MODEL] Model saved to {self.model_path}")
        except Exception as e:
            print(f"[AI MODEL] Failed to save model: {e}")

    def classify(self, text: str, hints: dict = None) -> dict:
        """
        Classify a single document text.
        If hints exist, bias the prediction towards them.
        """
        if self.pipeline is None:
            # Untrained fallback
            chosen_label = random.choice(self.labels)
            confidence = round(random.uniform(0.3, 0.7), 2)
            return {
                "category": chosen_label,
                "confidence": confidence,
                "details": "Random fallback (untrained AI model)"
            }

        try:
            # Predict probabilities
            probs = self.pipeline.predict_proba([text])[0]
            classes = self.label_encoder.inverse_transform(range(len(probs)))
            class_probs = dict(zip(classes, probs))

            # Apply rule hints if provided
            if hints and "forced_category" in hints:
                forced = hints["forced_category"]
                if forced in class_probs:
                    class_probs[forced] += 0.3  # boost probability
                    # Normalize
                    total = sum(class_probs.values())
                    for k in class_probs:
                        class_probs[k] /= total

            # Select top category
            chosen_label = max(class_probs, key=class_probs.get)
            confidence = round(class_probs[chosen_label], 2)

            return {
                "category": chosen_label,
                "confidence": confidence,
                "details": f"AI classification with rule hint applied: {bool(hints)}"
            }

        except Exception as e:
            print(f"[AI MODEL] Classification failed: {e}")
            # Random fallback
            chosen_label = random.choice(self.labels)
            confidence = round(random.uniform(0.3, 0.7), 2)
            return {
                "category": chosen_label,
                "confidence": confidence,
                "details": f"Fallback due to error: {str(e)}"
            }
