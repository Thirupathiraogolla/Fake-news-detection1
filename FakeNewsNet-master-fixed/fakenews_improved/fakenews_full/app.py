import json, joblib, os, re
from flask import Flask, request, jsonify, render_template, send_from_directory

app = Flask(__name__)
BASE = os.path.dirname(__file__)
MODELS = {}

for name in ['Logistic_Regression', 'Linear_SVM', 'Naive_Bayes']:
    path = os.path.join(BASE, 'models', f'{name}.pkl')
    if os.path.exists(path):
        MODELS[name.replace('_', ' ')] = joblib.load(path)

META = json.load(open(os.path.join(BASE, 'models', 'meta.json')))

def clean_text(text):
    text = str(text).strip()
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'[^\w\s!?.]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def prepare_input(text):
    political_words = ['obama','trump','clinton','congress','senate','president',
                       'democrat','republican','white house','fbi','cia','government',
                       'pelosi','biden','pence','hillary','election','vote']
    lower = text.lower()
    detected = 'politifact' if any(w in lower for w in political_words) else 'gossipcop'
    return f"source_{detected} " + clean_text(text)

@app.route('/')
def index():
    return render_template('index.html', meta=META)

@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json()
    text = data.get('text', '').strip()
    if not text or len(text) < 5:
        return jsonify({'error': 'Text too short'}), 400

    prepared    = prepare_input(text)
    predictions = {}

    for name, model in MODELS.items():
        try:
            pred = model.predict([prepared])[0]
            if hasattr(model, 'predict_proba'):
                prob      = model.predict_proba([prepared])[0]
                fake_prob = float(prob[1])
            elif hasattr(model.named_steps['clf'], 'decision_function'):
                score     = model.decision_function([prepared])[0]
                fake_prob = float(1 / (1 + pow(2.718, -score * 0.8)))
            else:
                fake_prob = float(pred)

            fake_prob = max(0.05, min(0.95, fake_prob))
            predictions[name] = {
                'label':            'FAKE' if pred == 1 else 'REAL',
                'fake_probability': round(fake_prob * 100, 1),
                'real_probability': round((1 - fake_prob) * 100, 1),
                'confidence':       round(max(fake_prob, 1 - fake_prob) * 100, 1)
            }
        except Exception as e:
            predictions[name] = {'error': str(e)}

    votes      = [1 if v.get('label') == 'FAKE' else 0 for v in predictions.values() if 'label' in v]
    fake_probs = [v['fake_probability'] for v in predictions.values() if 'fake_probability' in v]
    avg_prob   = sum(fake_probs) / len(fake_probs) if fake_probs else 50

    return jsonify({
        'text': text[:200],
        'models': predictions,
        'ensemble': {
            'label':            'FAKE' if sum(votes) > len(votes)/2 else 'REAL',
            'fake_probability': round(avg_prob, 1),
            'real_probability': round(100 - avg_prob, 1),
            'votes_fake':       sum(votes),
            'votes_real':       len(votes) - sum(votes),
            'total_models':     len(votes)
        }
    })

@app.route('/meta')
def get_meta():
    return jsonify(META)

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(os.path.join(BASE, 'static'), filename)

if __name__ == '__main__':
    print("\n✅ FakeNewsNet Flask App — IMPROVED VERSION")
    print(f"   Models loaded : {list(MODELS.keys())}")
    print(f"   Best model    : {META['best_model']}")
    print("\n   Open: http://127.0.0.1:5000\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
