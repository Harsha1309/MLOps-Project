# India Tourism Recommender API

An ML-powered FastAPI service that recommends **which Indian destinations to
visit in which month**, based on climate (temperature, rainfall), category
(hill station, beach, heritage, wildlife, spiritual, backwaters, desert,
city), and budget.

## How it works

1. **Dataset** (`build_dataset.py` → `data/india_tourism.csv`)
   56 popular Indian destinations × 12 months = **672 rows**. Each row has:
   `place, state, category, region, month, avg_temp_c, avg_rainfall_mm,
   cost_tier, is_best_month, suitability_score`.
   Temperature/rainfall are generated from realistic seasonal curves per
   region (monsoon June–Sep, winter peak Jan, summer peak May/June, cold
   high-altitude baselines for Himalayan places, etc.), and
   `suitability_score` (0–10) is a heuristic label combining temperature
   comfort, rainfall penalty, and known best-season boosts.

2. **Training** (`train.py` → `models/tourism_model.joblib`)
   A `RandomForestRegressor` inside a `scikit-learn` `Pipeline`
   (one-hot encoding for `category`/`region` + passthrough numeric features)
   learns to predict `suitability_score` from
   `avg_temp_c, avg_rainfall_mm, cost_tier, month_num, category, region`.
   Achieves **R² ≈ 0.96 / MAE ≈ 0.26** on a held-out 20% test split.

3. **API** (`main.py`) serves the trained model plus a lookup table of all
   place/month combinations, so it can score and rank real destinations for
   whatever month/filters the user asks for.

## Project structure

```
india_tourism_api/
├── build_dataset.py     # generates data/india_tourism.csv
├── train.py              # trains model -> models/tourism_model.joblib
├── main.py                # FastAPI app
├── test_api.py            # smoke tests (no server needed)
├── requirements.txt
├── data/
│   └── india_tourism.csv
└── models/
    ├── tourism_model.joblib
    ├── lookup_table.pkl
    └── metrics.json
```

## Setup

```bash
pip install -r requirements.txt

# 1. Build the dataset
python build_dataset.py

# 2. Train the model
python train.py

# 3. Run the API
uvicorn main:app --reload --port 8000
```

Open interactive docs at **http://127.0.0.1:8000/docs**.

## Endpoints

| Method | Path         | Purpose                                              |
|--------|--------------|-------------------------------------------------------|
| GET    | `/`          | Service info                                          |
| GET    | `/health`    | Health check (model loaded? row count)                |
| GET    | `/months`    | List valid month names                                |
| GET    | `/places`    | List destinations (optional `category`, `state` filter)|
| POST   | `/predict`   | Suitability score for one `place` + `month`            |
| POST   | `/recommend` | Top-N destinations for a `month`, given filters         |

### Example: `/predict`

```bash
curl -X POST http://127.0.0.1:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"place": "Manali", "month": "June"}'
```

### Example: `/recommend` — "beach destinations in December, 15–30°C"

```bash
curl -X POST http://127.0.0.1:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{
        "month": "December",
        "category": "Beach",
        "min_temp_c": 15,
        "max_temp_c": 30,
        "max_cost_tier": 2,
        "top_n": 5
      }'
```

### Example: `/recommend` — "cool hill stations in May"

```bash
curl -X POST http://127.0.0.1:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{"month": "May", "category": "Hill Station", "max_temp_c": 25, "top_n": 5}'
```

## Testing

```bash
python test_api.py
```

Runs end-to-end checks (health, predict, recommend, validation errors) using
FastAPI's `TestClient` — no running server required.

## Notes / possible extensions

- Climate values are realistic approximations for demo purposes, not
  official IMD records — swap `build_dataset.py`'s `PLACES` table for a
  real climate CSV to make it production-grade.
- `cost_tier` (1=budget, 2=mid-range, 3=premium) is a simple proxy; a real
  version could plug in live hotel/flight price APIs.
- The model is retrained by simply re-running `train.py` after editing the
  dataset — no code changes needed elsewhere.
