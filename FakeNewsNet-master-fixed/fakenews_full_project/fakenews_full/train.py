import pandas as pd
import numpy as np
import joblib
import json
import sys
import csv
import re
import os
import warnings
warnings.filterwarnings('ignore')

csv.field_size_limit(sys.maxsize)

from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.metrics import (accuracy_score, f1_score,
                              precision_score, recall_score)
from sklearn.utils import resample

os.makedirs('models', exist_ok=True)

print("=" * 60)
print("  IMPROVED FAKE NEWS DETECTOR — 3 FIXES APPLIED")
print("=" * 60)

# ── Load Data ──────────────────────────────────────────────────
print("\n[1] Loading dataset...")
df = pd.read_csv('data.csv')
print(f"    Total   : {len(df):,}")
print(f"    Fake    : {(df['label']=='fake').sum():,} ({(df['label']=='fake').mean()*100:.1f}%)")
print(f"    Real    : {(df['label']=='real').sum():,} ({(df['label']=='real').mean()*100:.1f}%)")

# ── FIX 2: Better Text Cleaning + Source Context ───────────────
print("\n[FIX 2] Better text cleaning + source context...")

def clean_text(text):
    text = str(text).strip()
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'[^\w\s!?.]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def add_source_prefix(row):
    return f"source_{row['source']} " + clean_text(row['title'])

df['title_enhanced'] = df.apply(add_source_prefix, axis=1)
print("    Done — added source tag to each headline")

# ── Split ──────────────────────────────────────────────────────
X = df['title_enhanced']
y = df['label_binary']
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y)

# ── FIX 3: Fix Class Imbalance ─────────────────────────────────
print("\n[FIX 3] Fixing class imbalance with oversampling...")
train_df         = pd.DataFrame({'text': X_train, 'label': y_train})
fake_train       = train_df[train_df['label'] == 1]
real_train       = train_df[train_df['label'] == 0]
fake_oversampled = resample(fake_train, replace=True,
                             n_samples=len(real_train), random_state=42)
train_balanced   = pd.concat([real_train, fake_oversampled]).sample(frac=1, random_state=42)
X_train_bal      = train_balanced['text']
y_train_bal      = train_balanced['label']
print(f"    Before: Fake={len(fake_train):,}  Real={len(real_train):,}")
print(f"    After : Fake={len(fake_oversampled):,}  Real={len(real_train):,}  (balanced!)")

# ── FIX 1: Improved Models ─────────────────────────────────────
print("\n[FIX 1] Training improved models with richer features...")

models = {
    'Logistic Regression': Pipeline([
        ('tfidf', TfidfVectorizer(
            max_features=20000,
            ngram_range=(1, 3),
            stop_words='english',
            sublinear_tf=True,
            min_df=2, max_df=0.95
        )),
        ('clf', LogisticRegression(
            max_iter=2000, C=0.5,
            class_weight='balanced',
            random_state=42, solver='lbfgs'
        ))
    ]),
    'Linear SVM': Pipeline([
        ('tfidf', TfidfVectorizer(
            max_features=20000,
            ngram_range=(1, 3),
            stop_words='english',
            sublinear_tf=True,
            min_df=2, max_df=0.95
        )),
        ('clf', LinearSVC(
            max_iter=3000, C=0.3,
            class_weight='balanced',
            random_state=42
        ))
    ]),
    'Naive Bayes': Pipeline([
        ('tfidf', TfidfVectorizer(
            max_features=20000,
            ngram_range=(1, 2),
            stop_words='english',
            min_df=2, max_df=0.95
        )),
        ('clf', MultinomialNB(alpha=0.5))
    ]),
}

results = {}

for name, pipeline in models.items():
    print(f"\n  Training {name}...")
    pipeline.fit(X_train_bal, y_train_bal)
    y_pred    = pipeline.predict(X_test)
    acc       = accuracy_score(y_test, y_pred)
    f1        = f1_score(y_test, y_pred, average='weighted')
    f1_fake   = f1_score(y_test, y_pred, pos_label=1, zero_division=0)
    rec_fake  = recall_score(y_test, y_pred, pos_label=1, zero_division=0)
    prec_fake = precision_score(y_test, y_pred, pos_label=1, zero_division=0)

    results[name] = {
        'accuracy':       round(acc, 4),
        'f1':             round(f1, 4),
        'f1_fake':        round(f1_fake, 4),
        'recall_fake':    round(rec_fake, 4),
        'precision_fake': round(prec_fake, 4)
    }
    joblib.dump(pipeline, f"models/{name.replace(' ', '_')}.pkl")

    print(f"    Accuracy       : {acc*100:.2f}%")
    print(f"    Weighted F1    : {f1:.4f}")
    print(f"    Fake Recall    : {rec_fake*100:.2f}%  ← catches fake news")
    print(f"    Fake Precision : {prec_fake*100:.2f}%")

# ── Save Best Model ────────────────────────────────────────────
best = max(results, key=lambda k: results[k]['f1_fake'])
joblib.dump(models[best], 'models/best_model.pkl')

meta = {
    'best_model':   best,
    'models':       results,
    'train_size':   len(X_train_bal),
    'test_size':    len(X_test),
    'total':        len(df),
    'fake_count':   int((df['label'] == 'fake').sum()),
    'real_count':   int((df['label'] == 'real').sum()),
    'improvements': [
        'FIX 1: TF-IDF expanded to trigrams + 20,000 features',
        'FIX 2: Source context prefix added + better text cleaning',
        'FIX 3: Fake news oversampled to 50/50 balance',
        'FIX 3: class_weight=balanced added to LR and SVM'
    ]
}
json.dump(meta, open('models/meta.json', 'w'), indent=2)

# ── Summary ────────────────────────────────────────────────────
print(f"\n{'=' * 60}")
print(f"  RESULTS SUMMARY")
print(f"{'=' * 60}")
print(f"\n  {'Model':<25} {'Accuracy':>10} {'F1':>8} {'FakeRecall':>12}")
print(f"  {'-' * 58}")
for name, m in results.items():
    star = ' ← BEST' if name == best else ''
    print(f"  {name:<25} {m['accuracy']*100:>9.2f}%"
          f" {m['f1']:>8.4f} {m['recall_fake']*100:>11.2f}%{star}")

print(f"\n  ✅ FIX 1 Applied : Trigrams + 20,000 features")
print(f"  ✅ FIX 2 Applied : Source context + better cleaning")
print(f"  ✅ FIX 3 Applied : Balanced training data")
print(f"\n  Fake Recall improved from ~30% → {results[best]['recall_fake']*100:.1f}%")
print(f"\n  Now run: python app.py")
print(f"  Open   : http://127.0.0.1:5000")
