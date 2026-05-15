"""J.A.R.V.I.S. — Intent Classifier (TF-IDF + SVM)
ML Component: Supervised classification for routing user intents.
"""

import os
import joblib
import numpy as np
from pathlib import Path
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

# Absolute path → invariant to CWD (was relative, caused stale-pkl issues across run dirs)
MODEL_PATH = Path(__file__).resolve().parents[2] / "data" / "intent_classifier.pkl"

# Training data: (text, intent)
TRAINING_DATA = [
    # weather
    ("clima en bogota", "weather"),
    ("como esta el tiempo en medellin", "weather"),
    ("va a llover hoy", "weather"),
    ("temperatura actual", "weather"),
    ("weather in new york", "weather"),
    ("what's the weather like", "weather"),
    ("is it going to rain today", "weather"),
    ("forecast for tomorrow", "weather"),
    ("hace frio o calor hoy", "weather"),
    ("pronostico del tiempo", "weather"),

    # time
    ("que hora es", "time"),
    ("dime la fecha de hoy", "time"),
    ("que dia es hoy", "time"),
    ("what time is it", "time"),
    ("what is today's date", "time"),
    ("current time please", "time"),
    ("hora actual", "time"),
    ("fecha y hora", "time"),
    ("que dia de la semana es", "time"),
    ("tell me the time", "time"),

    # search
    ("busca informacion sobre langchain", "search"),
    ("search for python tutorials", "search"),
    ("find me news about ai", "search"),
    ("buscar recetas de cocina", "search"),
    ("que es el machine learning", "search"),
    ("busca en internet", "search"),
    ("google how to use fastapi", "search"),
    ("search the web for", "search"),
    ("dame informacion de", "search"),
    ("investiga sobre", "search"),

    # memory_store
    ("recuerda que mi cumpleanos es el 15 de marzo", "memory_store"),
    ("guarda que el proyecto se llama jarvis", "memory_store"),
    ("memoriza esta informacion", "memory_store"),
    ("save that my favorite color is blue", "memory_store"),
    ("remember that I prefer Python", "memory_store"),
    ("store this fact", "memory_store"),
    ("anota que tengo reunion los lunes", "memory_store"),
    ("guarda mi contrasena del wifi", "memory_store"),
    ("save my birthday", "memory_store"),
    ("please remember this", "memory_store"),

    # memory_recall
    ("que recuerdas de mi cumpleanos", "memory_recall"),
    ("cual es el nombre del proyecto", "memory_recall"),
    ("recuerda algo sobre", "memory_recall"),
    ("what do you remember about", "memory_recall"),
    ("recall my favorite", "memory_recall"),
    ("busca en tu memoria", "memory_recall"),
    ("que guardaste sobre", "memory_recall"),
    ("do you remember my", "memory_recall"),
    ("retrieve the information about", "memory_recall"),
    ("que sabes de mi trabajo", "memory_recall"),

    # calculate
    ("cuanto es 15 por 7", "calculate"),
    ("calcula 2 elevado a 10", "calculate"),
    ("how much is 100 divided by 4", "calculate"),
    ("what is the square root of 144", "calculate"),
    ("suma 345 mas 678", "calculate"),
    ("cuanto es 30 porciento de 200", "calculate"),
    ("calculate 15 times 8", "calculate"),
    ("multiplica 6 por 9", "calculate"),
    ("math: 2 ** 32", "calculate"),
    ("cuanto es sqrt 256", "calculate"),

    # system
    ("como esta el cpu", "system"),
    ("cuanta memoria ram tengo disponible", "system"),
    ("uso del disco duro", "system"),
    ("system status", "system"),
    ("check cpu usage", "system"),
    ("how much RAM is being used", "system"),
    ("disk space remaining", "system"),
    ("monitor system resources", "system"),
    ("estado del sistema", "system"),
    ("recursos del computador", "system"),

    # general
    ("hola jarvis", "general"),
    ("hello", "general"),
    ("como estas", "general"),
    ("cuéntame un chiste", "general"),
    ("tell me a joke", "general"),
    ("quien eres", "general"),
    ("who are you", "general"),
    ("que puedes hacer", "general"),
    ("what can you do", "general"),
    ("gracias por tu ayuda", "general"),
    ("thank you", "general"),
    ("ayudame con algo", "general"),
    ("necesito ayuda", "general"),
    ("help me please", "general"),
]

CLASSES = ["weather", "time", "search", "memory_store", "memory_recall", "calculate", "system", "general"]


def build_pipeline() -> Pipeline:
    # word + char_wb ngrams → robust to morphological variation in Spanish/English
    # LogisticRegression calibrated natively (no Platt scaling drift like SVC.predict_proba)
    return Pipeline([
        ("feats", FeatureUnion([
            ("word", TfidfVectorizer(
                ngram_range=(1, 2),
                min_df=1,
                sublinear_tf=True,
            )),
            ("char", TfidfVectorizer(
                analyzer="char_wb",
                ngram_range=(3, 5),
                min_df=1,
                sublinear_tf=True,
            )),
        ])),
        ("clf", LogisticRegression(
            C=4,
            max_iter=2000,
            class_weight="balanced",
        )),
    ])


def train_classifier() -> Pipeline:
    """Train the intent classifier and save to disk."""
    texts = [item[0] for item in TRAINING_DATA]
    labels = [item[1] for item in TRAINING_DATA]

    pipeline = build_pipeline()
    pipeline.fit(texts, labels)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)

    # Evaluate on training set (for course report)
    preds = pipeline.predict(texts)
    acc = accuracy_score(labels, preds)
    print(f"[IntentClassifier] Training accuracy: {acc:.3f}")
    return pipeline


def load_or_train() -> Pipeline:
    """Load saved model or train if not found."""
    if MODEL_PATH.exists():
        return joblib.load(MODEL_PATH)
    return train_classifier()


class IntentClassifier:
    def __init__(self):
        self._pipeline = load_or_train()

    def predict(self, text: str) -> tuple[str, float]:
        """Return (intent, confidence)."""
        probs = self._pipeline.predict_proba([text])[0]
        classes = self._pipeline.classes_
        idx = np.argmax(probs)
        return classes[idx], float(probs[idx])

    def predict_top_k(self, text: str, k: int = 3) -> list[dict]:
        """Return top-k intents with probabilities."""
        probs = self._pipeline.predict_proba([text])[0]
        classes = self._pipeline.classes_
        top = sorted(zip(classes, probs), key=lambda x: x[1], reverse=True)[:k]
        return [{"intent": c, "confidence": round(float(p), 4)} for c, p in top]

    def retrain(self) -> dict:
        """Retrain the classifier and return metrics."""
        texts = [item[0] for item in TRAINING_DATA]
        labels = [item[1] for item in TRAINING_DATA]
        self._pipeline = train_classifier()
        preds = self._pipeline.predict(texts)
        return {"accuracy": float(accuracy_score(labels, preds)), "samples": len(texts)}


# Singleton
classifier = IntentClassifier()
