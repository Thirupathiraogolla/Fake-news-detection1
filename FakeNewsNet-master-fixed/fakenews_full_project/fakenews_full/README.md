# FakeNewsNet — Complete Course Project

## Project Structure
```
fakenews_full/
├── app.py                          ← Flask web app (connects to real ML model)
├── data.csv                        ← Preprocessed dataset (23,196 articles)
├── FakeNewsNet_Complete_Pipeline.ipynb  ← Jupyter notebook (full ML pipeline)
├── models/
│   ├── best_model.pkl              ← Best scikit-learn model (auto-selected)
│   ├── Logistic_Regression.pkl
│   ├── Linear_SVM.pkl
│   ├── Naive_Bayes.pkl
│   ├── lstm_model.h5               ← LSTM model (if TensorFlow available)
│   ├── tokenizer.pkl
│   └── meta.json                   ← Model accuracy/F1 results
├── static/
│   ├── eda.png
│   ├── model_comparison.png
│   ├── confusion_matrices.png
│   ├── feature_importance.png
│   ├── lstm_training.png
│   └── full_comparison.png
└── templates/
    └── index.html                  ← Flask HTML template

```

## Model Results
| Model              | Accuracy | F1 Score |
|--------------------|----------|----------|
| Logistic Regression| 84.46%   | 0.8288   |
| Linear SVM         | 84.81%   | 0.8422   |
| Naive Bayes        | 84.91%   | 0.8419   |
| Bi-LSTM            | 87.21%   | 0.8689   |

## How to Run

### Step 1 — Install dependencies
```bash
pip install flask scikit-learn pandas numpy matplotlib seaborn joblib tensorflow
```

### Step 2 — Place your dataset files
Put these 4 files in a `dataset/` folder next to `app.py`:
- `politifact_fake.csv`
- `politifact_real.csv`
- `gossipcop_fake.csv`
- `gossipcop_real.csv`

### Step 3 — Run the Jupyter Notebook first
```bash
jupyter notebook FakeNewsNet_Complete_Pipeline.ipynb
```
Run all cells to train models and generate plots.

### Step 4 — Start the Flask web app
```bash
python app.py
```
Open: **http://localhost:5000**

## What Each File Does
- **Jupyter Notebook** — Full ML pipeline: EDA → preprocessing → training → evaluation → plots
- **app.py** — Flask server that loads trained models and serves predictions via API
- **templates/index.html** — Web interface with real ML predictions (not keyword matching)
