"""
build_dataset.py
-----------------
Builds the dataset used to train the recommender: for ~55 popular Indian
tourist destinations x 12 months, it records the typical climate
(avg temperature, rainfall, humidity) and place attributes (category,
region, avg trip cost tier), plus a hand-derived "suitability_score"
(0-10) for visiting that place in that month.

Climate figures are approximate long-term averages compiled from
publicly known seasonal patterns (IMD-style summaries) for each region.
They are meant for a realistic demo dataset, not survey-grade accuracy.

Run:
    python build_dataset.py
"""

import numpy as np
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

# name, state, category, region_type, base_temp(avg annual °C), temp_amplitude,
# monsoon_intensity(0-1), best_months(list, 1-indexed), cost_tier(1=budget,3=premium)
PLACES = [
    ("Manali", "Himachal Pradesh", "Hill Station", "North Mountains", 12, 14, 0.3, [3,4,5,6,9,10,11], 2),
    ("Shimla", "Himachal Pradesh", "Hill Station", "North Mountains", 13, 12, 0.3, [3,4,5,6,9,10,11], 2),
    ("Leh", "Ladakh", "Hill Station", "North Mountains", 2, 16, 0.05, [5,6,7,8,9], 3),
    ("Darjeeling", "West Bengal", "Hill Station", "East Mountains", 15, 8, 0.6, [3,4,5,10,11], 2),
    ("Ooty", "Tamil Nadu", "Hill Station", "South Mountains", 16, 5, 0.4, [3,4,5,9,10,11], 2),
    ("Munnar", "Kerala", "Hill Station", "South Mountains", 20, 5, 0.6, [9,10,11,12,1,2], 2),
    ("Gangtok", "Sikkim", "Hill Station", "East Mountains", 15, 7, 0.55, [3,4,5,10,11], 2),
    ("Mussoorie", "Uttarakhand", "Hill Station", "North Mountains", 15, 10, 0.4, [3,4,5,6,9,10], 2),
    ("Nainital", "Uttarakhand", "Hill Station", "North Mountains", 16, 10, 0.4, [3,4,5,6,9,10,11], 2),
    ("Coorg", "Karnataka", "Hill Station", "South Mountains", 20, 6, 0.6, [9,10,11,12,1,2,3], 2),

    ("Goa", "Goa", "Beach", "West Coast", 27, 4, 0.55, [11,12,1,2], 2),
    ("Kovalam", "Kerala", "Beach", "South Coast", 28, 3, 0.5, [11,12,1,2,3], 2),
    ("Gokarna", "Karnataka", "Beach", "West Coast", 27, 4, 0.5, [10,11,12,1,2], 1),
    ("Puri", "Odisha", "Beach", "East Coast", 27, 6, 0.4, [10,11,12,1,2], 1),
    ("Andaman Islands", "Andaman & Nicobar", "Beach", "Islands", 27, 3, 0.35, [11,12,1,2,3,4], 3),
    ("Varkala", "Kerala", "Beach", "South Coast", 28, 3, 0.5, [11,12,1,2,3], 2),
    ("Diu", "Daman & Diu", "Beach", "West Coast", 27, 5, 0.4, [10,11,12,1,2,3], 1),
    ("Mahabalipuram", "Tamil Nadu", "Beach", "South Coast", 28, 4, 0.4, [11,12,1,2], 1),

    ("Jaipur", "Rajasthan", "Heritage", "North Plains/Desert", 25, 15, 0.15, [10,11,12,1,2,3], 2),
    ("Udaipur", "Rajasthan", "Heritage", "North Plains/Desert", 25, 13, 0.2, [10,11,12,1,2,3], 2),
    ("Jaisalmer", "Rajasthan", "Heritage", "North Plains/Desert", 26, 16, 0.05, [11,12,1,2], 2),
    ("Jodhpur", "Rajasthan", "Heritage", "North Plains/Desert", 26, 15, 0.1, [10,11,12,1,2,3], 2),
    ("Agra", "Uttar Pradesh", "Heritage", "North Plains", 25, 16, 0.25, [10,11,12,1,2,3], 2),
    ("Varanasi", "Uttar Pradesh", "Heritage", "North Plains", 26, 14, 0.35, [10,11,12,1,2,3], 1),
    ("Hampi", "Karnataka", "Heritage", "South Deccan", 27, 6, 0.25, [10,11,12,1,2], 1),
    ("Khajuraho", "Madhya Pradesh", "Heritage", "Central Plains", 25, 14, 0.3, [10,11,12,1,2,3], 2),
    ("Mysore", "Karnataka", "Heritage", "South Deccan", 24, 5, 0.4, [10,11,12,1,2,9], 1),
    ("Amritsar", "Punjab", "Heritage", "North Plains", 24, 16, 0.3, [10,11,12,2,3], 1),

    ("Rishikesh", "Uttarakhand", "Spiritual/Adventure", "North Mountains", 19, 12, 0.4, [3,4,5,9,10,11], 1),
    ("Haridwar", "Uttarakhand", "Spiritual", "North Plains", 24, 15, 0.4, [10,11,12,2,3], 1),
    ("Pushkar", "Rajasthan", "Spiritual", "North Plains/Desert", 25, 15, 0.1, [10,11,12,1,2], 1),
    ("Tirupati", "Andhra Pradesh", "Spiritual", "South Deccan", 28, 6, 0.35, [10,11,12,1,2], 1),
    ("Bodh Gaya", "Bihar", "Spiritual", "East Plains", 26, 14, 0.4, [10,11,12,1,2], 1),
    ("Amarnath", "Jammu & Kashmir", "Spiritual/Adventure", "North Mountains", 5, 15, 0.25, [7,8], 2),

    ("Ranthambore", "Rajasthan", "Wildlife", "North Plains/Desert", 26, 15, 0.15, [10,11,12,1,2,3], 2),
    ("Jim Corbett", "Uttarakhand", "Wildlife", "North Plains", 23, 14, 0.4, [11,12,1,2,3,4], 2),
    ("Kaziranga", "Assam", "Wildlife", "East Plains", 24, 10, 0.7, [11,12,1,2,3], 2),
    ("Bandhavgarh", "Madhya Pradesh", "Wildlife", "Central Plains", 25, 15, 0.35, [10,11,12,1,2,3], 2),
    ("Periyar", "Kerala", "Wildlife", "South Coast", 23, 5, 0.65, [9,10,11,12,1,2], 2),
    ("Gir Forest", "Gujarat", "Wildlife", "West Plains", 27, 10, 0.25, [11,12,1,2,3], 2),

    ("Mumbai", "Maharashtra", "City/Urban", "West Coast", 27, 4, 0.55, [11,12,1,2], 3),
    ("Delhi", "Delhi", "City/Urban", "North Plains", 25, 18, 0.3, [10,11,2,3], 2),
    ("Bengaluru", "Karnataka", "City/Urban", "South Deccan", 24, 4, 0.4, [9,10,11,12,1,2,3], 2),
    ("Kolkata", "West Bengal", "City/Urban", "East Plains", 27, 8, 0.5, [10,11,12,1,2], 2),
    ("Chennai", "Tamil Nadu", "City/Urban", "South Coast", 29, 4, 0.45, [11,12,1], 2),
    ("Hyderabad", "Telangana", "City/Urban", "South Deccan", 27, 8, 0.35, [10,11,12,1,2], 2),
    ("Pune", "Maharashtra", "City/Urban", "South Deccan", 24, 6, 0.45, [10,11,12,1,2], 2),
    ("Ahmedabad", "Gujarat", "City/Urban", "West Plains", 27, 12, 0.3, [11,12,1,2], 2),

    ("Alleppey", "Kerala", "Backwaters", "South Coast", 27, 3, 0.65, [9,10,11,12,1,2], 2),
    ("Kumarakom", "Kerala", "Backwaters", "South Coast", 27, 3, 0.65, [9,10,11,12,1,2], 2),
    ("Srinagar", "Jammu & Kashmir", "Hill Station", "North Mountains", 13, 15, 0.2, [4,5,6,9,10], 3),
    ("Gulmarg", "Jammu & Kashmir", "Hill Station", "North Mountains", 7, 14, 0.2, [12,1,2,4,5,6], 3),
    ("Auli", "Uttarakhand", "Hill Station", "North Mountains", 8, 14, 0.3, [12,1,2,3,4,5], 2),
    ("Spiti Valley", "Himachal Pradesh", "Hill Station/Adventure", "North Mountains", 2, 16, 0.05, [6,7,8,9], 2),
    ("Rann of Kutch", "Gujarat", "Desert", "West Plains", 27, 15, 0.05, [11,12,1,2], 2),
    ("Lakshadweep", "Lakshadweep", "Beach", "Islands", 28, 3, 0.4, [10,11,12,1,2,3], 3),
]


def monthly_temperature(base_temp, amplitude, month_idx, region_type):
    """Approximate a sinusoidal seasonal temperature curve.
    Peak summer ~ May/June for most of India; peak winter ~ Jan.
    Coastal/tropical places have smaller swings (captured via amplitude)."""
    # month_idx: 0=Jan ... 11=Dec. Peak warmth around month index 5 (June) for most regions,
    # except high-altitude regions which still peak ~June-July but from a much lower base.
    phase_shift = 5  # June peak
    angle = 2 * np.pi * (month_idx - phase_shift) / 12
    seasonal = amplitude * np.cos(angle)
    temp = base_temp + seasonal
    return round(temp, 1)


def monthly_rainfall(monsoon_intensity, month_idx, region_type):
    """India's monsoon runs roughly June-September (idx 5-8), with a
    secondary Oct-Nov spell for the east coast (retreating monsoon)."""
    base = 20  # mm baseline
    monsoon_months = {5, 6, 7, 8}
    retreating_months = {9, 10}
    if month_idx in monsoon_months:
        rain = base + monsoon_intensity * 350
    elif month_idx in retreating_months and "East" in region_type or "South Coast" in region_type:
        rain = base + monsoon_intensity * 180
    else:
        rain = base + monsoon_intensity * 30
    return round(max(rain, 5), 1)


def suitability_score(temp, rainfall, category, month_idx, best_months):
    """Heuristic 0-10 label used as training target:
    rewards comfortable temperature (15-28C sweet spot), penalizes heavy rain,
    and gives a boost if the month is in the place's known best_months list."""
    # temperature comfort component (0-6)
    if 15 <= temp <= 28:
        temp_score = 6
    else:
        temp_score = max(0, 6 - 0.25 * min(abs(temp - 21), 24))

    # rainfall penalty (0-3, higher rainfall = lower score)
    rain_score = max(0, 3 - rainfall / 150)

    # domain knowledge boost (0-1)
    best_boost = 1.0 if (month_idx + 1) in best_months else 0.0

    score = temp_score + rain_score + best_boost
    return round(min(10, max(0, score)), 2)


def build():
    rows = []
    for (name, state, category, region, base_temp, amp, monsoon, best_months, cost) in PLACES:
        for month_idx, month_name in enumerate(MONTHS):
            temp = monthly_temperature(base_temp, amp, month_idx, region)
            rain = monthly_rainfall(monsoon, month_idx, region)
            score = suitability_score(temp, rain, category, month_idx, best_months)
            rows.append(
                {
                    "place": name,
                    "state": state,
                    "category": category,
                    "region": region,
                    "month": month_name,
                    "month_num": month_idx + 1,
                    "avg_temp_c": temp,
                    "avg_rainfall_mm": rain,
                    "cost_tier": cost,
                    "is_best_month": 1 if (month_idx + 1) in best_months else 0,
                    "suitability_score": score,
                }
            )
    df = pd.DataFrame(rows)
    out_path = DATA_DIR / "india_tourism.csv"
    df.to_csv(out_path, index=False)
    print(f"Built dataset with {len(df)} rows ({len(PLACES)} places x 12 months)")
    print(f"Saved to {out_path}")
    return df


if __name__ == "__main__":
    build()
