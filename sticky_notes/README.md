# Sticky Note Generation from Casual Meeting Conversations

> An NLP + Machine Learning system that analyzes casual meeting conversations and automatically generates concise, color-coded sticky notes for participants.

---

## Overview

Meetings are a fundamental part of academic and professional life, but important information often gets lost in casual conversation. This project develops an automated system that:

1. **Identifies** important content features from meeting transcripts (action verbs, decisions, deadlines, questions, named entities, and more)
2. **Classifies** each utterance as important or casual using a trained ML model
3. **Generates** concise sticky notes with titles, categories, importance scores, and color coding
4. **Evaluates** performance using precision, recall, F1-score, accuracy, ROUGE, BLEU, and METEOR
5. **Renders** the result on a fancy, interactive corkboard UI with a sticky-note theme

---

## Features

| Feature | How it's used |
|---|---|
| Word Count | Longer utterances often contain decisions or summaries |
| Sentence Count | Multi-sentence turns carry key info |
| Has Question | Q&A drives next steps |
| Has Action Verb | Detects "prepare", "create", "send", etc. |
| Has Decision | Detects "decided", "agreed", "confirmed" |
| Contains Date/Deadline | Deadlines and timelines are critical |
| Keyword Density (Action) | Ratio of action keywords to total words |
| Named Entities | Person names, dates, times, emails |
| Sentiment Indicators | Agreement vs. concern signals |
| Speaker Continuity | Context from previous turn |

---

## Project Structure

```
sticky_notes/
├── app.py                    # Streamlit UI (corkboard + sticky notes)
├── run_all.py                # Full pipeline launcher
├── run_all.bat               # Windows batch launcher
├── run_app.bat               # Windows UI launcher
├── requirements.txt          # Python dependencies
├── data/                     # Generated datasets
│   ├── meeting_transcripts.csv
│   ├── labeled_segments.csv
│   └── extracted_features.csv
├── outputs/
│   ├── models/               # Trained classifier + comparison
│   ├── plots/                # Visualization images
│   └── reports/              # Word report + evaluation JSONs
└── src/
    ├── config.py             # Constants & paths
    ├── generate_dataset.py   # Synthetic meeting dataset
    ├── features.py           # NLP feature extraction
    ├── train_pipeline.py     # Model training & comparison
    ├── sticky_notes.py       # Sticky note generation
    ├── evaluate.py           # Performance evaluation
    └── generate_report.py    # Word document report
```

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the full pipeline (data → features → training → evaluation → report)

```bash
# Windows PowerShell
cd sticky_notes
..\..\.venv\Scripts\python.exe run_all.py

# Or double-click run_all.bat
```

### 3. Launch the UI

```bash
# Windows PowerShell
cd sticky_notes
..\..\.venv\Scripts\python.exe -m streamlit run app.py

# Or double-click run_app.bat
```

Open **http://localhost:8501** in your browser.

---

## Models Compared

| Model | Accuracy | Precision | Recall | F1-Macro |
|---|---|---|---|---|
| Logistic Regression | 0.7647 | 0.7803 | 0.7569 | 0.7571 |
| Random Forest | 0.7647 | 0.7803 | 0.7569 | 0.7571 |
| Gradient Boosting | 0.7059 | 0.7071 | 0.7014 | 0.7018 |
| SVM (RBF) | 0.7647 | 0.8462 | 0.7500 | 0.7424 |

**Full dataset performance (best model):** Accuracy **89.0%**, Precision **89.7%**, Recall **88.9%**, F1 **88.9%**

---

## How It Works

1. **Paste or upload a meeting transcript** (each line: `Speaker: text`)
2. **Feature extraction** runs on every utterance
3. **Trained classifier** scores each utterance (0–1 importance)
4. **Sticky notes** are generated with:
   - Title
   - Full text
   - Speaker
   - Category (*Action Item, Decision, Deadline, Question, Key Information, Event, General*)
   - Color coding
   - Importance score
   - Auto-detected tags
5. **Board** renders as a corkboard with pinned, color-coded sticky notes that tilt on hover

---

## Future Work

- Use transformer-based models (BERT/GPT) for deeper semantics
- Integrate real audio features (prosody, speaker diarization)
- Train on real datasets (AMI, ICSI)
- Abstractive summarization using T5/BART
- Real-time processing of live meetings

*Built with Python, scikit-learn, and Streamlit.*
