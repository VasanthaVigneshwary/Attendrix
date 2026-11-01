"""
ATTENDRIX Evaluation Script
============================
Evaluates the face recognition pipeline using registered students.

Usage:
    venv\\Scripts\\python.exe evaluation\\evaluate.py

What it does:
1. Loads all registered students and their stored embeddings from the DB.
2. For each student, re-processes their registered face image (if available in dataset/).
3. Runs recognition and records predicted vs actual identity.
4. Computes accuracy, precision, recall, F1-score.
5. Generates confusion matrix and saves results to results/.

NOTE: This script performs INFERENCE using the pretrained FaceNet model.
No training is performed. Training curves are NOT applicable here because
FaceNet is used as a pretrained feature extractor, not trained from scratch.
"""

import os
import sys
import json
import datetime
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# ── Paths ──────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
RESULTS_DIR  = os.path.join(PROJECT_ROOT, 'results')
DATASET_DIR  = os.path.join(PROJECT_ROOT, 'dataset')
os.makedirs(RESULTS_DIR, exist_ok=True)

from backend.database import SessionLocal, init_db
from backend.models import Student, FaceEmbedding
from backend.services.face_utils import (
    decode_image, detect_face_boxes, generate_embedding,
    cosine_distance, embedding_from_bytes, THRESHOLD
)

init_db()
db = SessionLocal()

print("=" * 60)
print("ATTENDRIX - Face Recognition Evaluation")
print("=" * 60)

# ── Load all students and embeddings from DB ────────────────────
students      = db.query(Student).all()
emb_records   = db.query(FaceEmbedding).all()
emb_map       = {e.student_id: embedding_from_bytes(e.embedding) for e in emb_records}  # student.id -> emb

print(f"Registered students: {len(students)}")

if len(students) < 2:
    print("\n⚠  LIMITATION: Need at least 2 registered students for meaningful evaluation.")
    print("   Register students via the dashboard, then re-run this script.")
    db.close()
    sys.exit(0)

# ── Try to find test images in dataset/ ────────────────────────
# Convention: dataset/<student_id>/<any>.jpg  or  dataset/<student_id>.jpg
test_pairs = []   # (actual_student_id_str, image_path)

# Check for student test images: dataset/<student_id>/ or dataset/<student_id>.jpg
for student in students:
    folder = os.path.join(DATASET_DIR, student.student_id)
    if os.path.isdir(folder):
        for fname in os.listdir(folder):
            if fname.lower().endswith(('.jpg','.jpeg','.png')):
                test_pairs.append((student.student_id, os.path.join(folder, fname)))
    single = os.path.join(DATASET_DIR, student.student_id + '.jpg')
    if os.path.isfile(single):
        test_pairs.append((student.student_id, single))

# Also check for unknown face images for rejection evaluation
for fname in os.listdir(DATASET_DIR):
    if fname.lower().startswith("unknown") and fname.lower().endswith(('.jpg', '.jpeg', '.png')):
        test_pairs.append(("Unknown", os.path.join(DATASET_DIR, fname)))

if not test_pairs:
    print("\n⚠  LIMITATION: No test images found in dataset/.")
    print("   To evaluate:")
    print("   • Create dataset/<STUDENT_ID>/ folder with face images.")
    print("   • OR place dataset/<STUDENT_ID>.jpg images.")
    print("   Registration images are not suitable for self-evaluation (trivially correct).")
    db.close()
    sys.exit(0)

print(f"Test image pairs found: {len(test_pairs)}")

# ── Run recognition ────────────────────────────────────────────
actuals    = []
predicted  = []
details    = []

for actual_sid, img_path in test_pairs:
    with open(img_path, 'rb') as f:
        img_bytes = f.read()
    try:
        img  = decode_image(img_bytes)
        boxes = detect_face_boxes(img)
        if not boxes:
            pred_sid = "no_face_detected"
        else:
            x, y, w, h = boxes[0]
            face        = img[y:y+h, x:x+w]
            query_emb   = generate_embedding(face)

            best_dist   = float('inf')
            best_sid    = "Unknown"
            for stu in students:
                if stu.id not in emb_map:
                    continue
                dist = cosine_distance(query_emb, emb_map[stu.id])
                if dist < best_dist:
                    best_dist = dist
                    best_sid  = stu.student_id
            pred_sid = best_sid if best_dist <= THRESHOLD else "Unknown"
    except Exception as ex:
        pred_sid = f"error:{ex}"

    actuals.append(actual_sid)
    predicted.append(pred_sid)
    details.append({
        "image": os.path.basename(img_path),
        "actual": actual_sid,
        "predicted": pred_sid,
        "correct": actual_sid == pred_sid,
    })
    print(f"  {os.path.basename(img_path)}: actual={actual_sid} predicted={pred_sid}")

db.close()

# ── Metrics ────────────────────────────────────────────────────
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report
)

labels      = sorted(set(actuals + predicted))
accuracy    = accuracy_score(actuals, predicted)
precision   = precision_score(actuals, predicted, labels=labels, average='weighted', zero_division=0)
recall      = recall_score(actuals, predicted, labels=labels, average='weighted', zero_division=0)
f1          = f1_score(actuals, predicted, labels=labels, average='weighted', zero_division=0)

print("\n-- Evaluation Metrics --")
print(f"  Accuracy  : {accuracy:.4f}")
print(f"  Precision : {precision:.4f}")
print(f"  Recall    : {recall:.4f}")
print(f"  F1-Score  : {f1:.4f}")
print("\n-- Classification Report --")
print(classification_report(actuals, predicted, labels=labels, zero_division=0))

# -- Save CSV ---------------------------------------------------
df_pred = pd.DataFrame(details)
df_pred.to_csv(os.path.join(RESULTS_DIR, 'predictions.csv'), index=False)
print("Predictions saved -> results/predictions.csv")

metrics = {
    "timestamp": datetime.datetime.now().isoformat(),
    "model": "FaceNet (pretrained, 128-dim)",
    "threshold": THRESHOLD,
    "total_samples": len(actuals),
    "accuracy": round(accuracy, 4),
    "precision": round(precision, 4),
    "recall": round(recall, 4),
    "f1_score": round(f1, 4),
    "note": "Pretrained inference only. No training curves applicable."
}
with open(os.path.join(RESULTS_DIR, 'evaluation_metrics.json'), 'w') as f:
    json.dump(metrics, f, indent=2)
print("Metrics saved -> results/evaluation_metrics.json")

# Also save evaluation_metrics.csv
df_metrics = pd.DataFrame([metrics])
df_metrics.to_csv(os.path.join(RESULTS_DIR, 'evaluation_metrics.csv'), index=False)
print("Metrics CSV saved -> results/evaluation_metrics.csv")

# -- Confusion matrix -------------------------------------------
cm = confusion_matrix(actuals, predicted, labels=labels)
fig, ax = plt.subplots(figsize=(max(6, len(labels)), max(5, len(labels))))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
            xticklabels=labels, yticklabels=labels, ax=ax)
ax.set_xlabel("Predicted")
ax.set_ylabel("Actual")
ax.set_title("ATTENDRIX - Confusion Matrix (FaceNet)")
plt.tight_layout()
cm_path = os.path.join(RESULTS_DIR, 'confusion_matrix.png')
plt.savefig(cm_path, dpi=150)
plt.close()
print("Confusion matrix saved -> results/confusion_matrix.png")

# -- Summary ----------------------------------------------------
summary = f"""
ATTENDRIX - Evaluation Summary
================================
Date         : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Model        : FaceNet (pretrained via DeepFace, 128-dim embeddings)
Threshold    : Cosine distance <= {THRESHOLD}
Samples      : {len(actuals)}

Accuracy     : {accuracy:.4f}
Precision    : {precision:.4f} (weighted)
Recall       : {recall:.4f} (weighted)
F1-Score     : {f1:.4f} (weighted)

IMPORTANT NOTE:
FaceNet is used as a pretrained feature extractor.
No training was performed; therefore, training loss/accuracy curves
are NOT applicable and have NOT been fabricated.

Files produced:
  results/predictions.csv
  results/evaluation_metrics.csv
  results/evaluation_metrics.json
  results/confusion_matrix.png
"""
print(summary)
with open(os.path.join(RESULTS_DIR, 'evaluation_summary.txt'), 'w') as f:
    f.write(summary)
print("Summary saved -> results/evaluation_summary.txt")

