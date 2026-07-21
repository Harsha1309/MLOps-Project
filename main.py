"""
main.py
-------
FastAPI service for the India Tourism Recommender.

Endpoints:
    GET  /                       -> health/info
    GET  /health                 -> health check
    GET  /places                 -> list all known places (optional filters)
    GET  /months                 -> list valid month names
    POST /predict                -> suitability score for one place+month
    POST /recommend               -> top-N place recommendations for a month
                                      given optional temperature/category/budget filters

Run:
    uvicorn main:app --reload --port 8000
"""

from pathlib import Path
from typing import List, Optional

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).parent
MODEL_PATH = BASE_DIR / "models" / "tourism_model.joblib"
LOOKUP_PATH = BASE_DIR / "models" / "lookup_table.pkl"

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
MONTH_TO_NUM = {m: i + 1 for i, m in enumerate(MONTHS)}

app = FastAPI(
    title="India Tourism Recommender API",
    description=(
        "Predicts how suitable an Indian destination is to visit in a given "
        "month, and recommends the best places based on month, preferred "
        "temperature range, category, and budget."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Load model + lookup table at startup
# ---------------------------------------------------------------------------
_model_bundle = None
_lookup_df: Optional[pd.DataFrame] = None


@app.on_event("startup")
def load_artifacts():
    global _model_bundle, _lookup_df
    if not MODEL_PATH.exists() or not LOOKUP_PATH.exists():
        raise RuntimeError(
            "Model artifacts not found. Run `python build_dataset.py` "
            "then `python train.py` before starting the API."
        )
    _model_bundle = joblib.load(MODEL_PATH)
    _lookup_df = pd.read_pickle(LOOKUP_PATH)
    print(f"Loaded model and lookup table ({len(_lookup_df)} rows).")


def get_pipeline():
    if _model_bundle is None:
        raise HTTPException(status_code=503, detail="Model not loaded yet.")
    return _model_bundle["pipeline"]


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class PredictRequest(BaseModel):
    place: str = Field(..., description="Destination name, e.g. 'Manali'")
    month: str = Field(..., description="Full month name, e.g. 'June'")


class PredictResponse(BaseModel):
    place: str
    state: str
    month: str
    avg_temp_c: float
    avg_rainfall_mm: float
    category: str
    predicted_suitability_score: float


class RecommendRequest(BaseModel):
    month: str = Field(..., description="Full month name, e.g. 'December'")
    min_temp_c: Optional[float] = Field(None, description="Minimum acceptable avg temperature")
    max_temp_c: Optional[float] = Field(None, description="Maximum acceptable avg temperature")
    category: Optional[str] = Field(
        None,
        description="Filter by category, e.g. 'Beach', 'Hill Station', 'Heritage', "
        "'Wildlife', 'Spiritual', 'City/Urban', 'Backwaters', 'Desert'",
    )
    max_cost_tier: Optional[int] = Field(
        None, ge=1, le=3, description="1=budget, 2=mid-range, 3=premium"
    )
    top_n: int = Field(5, ge=1, le=20, description="Number of recommendations to return")


class Recommendation(BaseModel):
    place: str
    state: str
    category: str
    region: str
    month: str
    avg_temp_c: float
    avg_rainfall_mm: float
    cost_tier: int
    predicted_suitability_score: float


class RecommendResponse(BaseModel):
    month: str
    filters_applied: dict
    count: int
    recommendations: List[Recommendation]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/")
def root():
    return {
        "service": "India Tourism Recommender API",
        "status": "running",
        "docs": "/docs",
        "endpoints": ["/health", "/places", "/months", "/predict", "/recommend"],
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_loaded": _model_bundle is not None,
        "rows_in_lookup": int(len(_lookup_df)) if _lookup_df is not None else 0,
    }


@app.get("/months")
def months():
    return {"months": MONTHS}


@app.get("/places")
def list_places(
    category: Optional[str] = Query(None, description="Filter by category"),
    state: Optional[str] = Query(None, description="Filter by state"),
):
    if _lookup_df is None:
        raise HTTPException(status_code=503, detail="Data not loaded yet.")
    df = _lookup_df[["place", "state", "category", "region", "cost_tier"]].drop_duplicates()
    if category:
        df = df[df["category"].str.lower() == category.lower()]
    if state:
        df = df[df["state"].str.lower() == state.lower()]
    return {"count": len(df), "places": df.to_dict(orient="records")}


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    if _lookup_df is None:
        raise HTTPException(status_code=503, detail="Data not loaded yet.")

    month = req.month.strip().title()
    if month not in MONTH_TO_NUM:
        raise HTTPException(status_code=400, detail=f"Invalid month '{req.month}'.")

    row = _lookup_df[
        (_lookup_df["place"].str.lower() == req.place.strip().lower())
        & (_lookup_df["month"] == month)
    ]
    if row.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for place '{req.place}'. Check /places for valid names.",
        )
    row = row.iloc[0]

    pipeline = get_pipeline()
    features = _model_bundle["numeric_features"] + _model_bundle["categorical_features"]
    X = pd.DataFrame([row[features]])
    score = float(pipeline.predict(X)[0])

    return PredictResponse(
        place=row["place"],
        state=row["state"],
        month=month,
        avg_temp_c=float(row["avg_temp_c"]),
        avg_rainfall_mm=float(row["avg_rainfall_mm"]),
        category=row["category"],
        predicted_suitability_score=round(score, 2),
    )


@app.post("/recommend", response_model=RecommendResponse)
def recommend(req: RecommendRequest):
    if _lookup_df is None:
        raise HTTPException(status_code=503, detail="Data not loaded yet.")

    month = req.month.strip().title()
    if month not in MONTH_TO_NUM:
        raise HTTPException(status_code=400, detail=f"Invalid month '{req.month}'.")

    df = _lookup_df[_lookup_df["month"] == month].copy()

    filters_applied = {"month": month}

    if req.min_temp_c is not None:
        df = df[df["avg_temp_c"] >= req.min_temp_c]
        filters_applied["min_temp_c"] = req.min_temp_c
    if req.max_temp_c is not None:
        df = df[df["avg_temp_c"] <= req.max_temp_c]
        filters_applied["max_temp_c"] = req.max_temp_c
    if req.category is not None:
        df = df[df["category"].str.lower().str.contains(req.category.lower())]
        filters_applied["category"] = req.category
    if req.max_cost_tier is not None:
        df = df[df["cost_tier"] <= req.max_cost_tier]
        filters_applied["max_cost_tier"] = req.max_cost_tier

    if df.empty:
        return RecommendResponse(
            month=month, filters_applied=filters_applied, count=0, recommendations=[]
        )

    pipeline = get_pipeline()
    features = _model_bundle["numeric_features"] + _model_bundle["categorical_features"]
    df["predicted_suitability_score"] = pipeline.predict(df[features]).round(2)

    df = df.sort_values("predicted_suitability_score", ascending=False).head(req.top_n)

    recs = [
        Recommendation(
            place=r["place"],
            state=r["state"],
            category=r["category"],
            region=r["region"],
            month=month,
            avg_temp_c=float(r["avg_temp_c"]),
            avg_rainfall_mm=float(r["avg_rainfall_mm"]),
            cost_tier=int(r["cost_tier"]),
            predicted_suitability_score=float(r["predicted_suitability_score"]),
        )
        for _, r in df.iterrows()
    ]

    return RecommendResponse(
        month=month,
        filters_applied=filters_applied,
        count=len(recs),
        recommendations=recs,
    )
