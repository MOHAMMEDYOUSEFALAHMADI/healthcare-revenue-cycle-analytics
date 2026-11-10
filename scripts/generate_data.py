"""Generate synthetic claims. Usage: python scripts/generate_data.py --months 15 --claims-per-month 2500"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rcm.data import generate_claims  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--start", default="2024-07-01")
    p.add_argument("--months", type=int, default=15)
    p.add_argument("--claims-per-month", type=int, default=2500)
    p.add_argument("--seed", type=int, default=21)
    a = p.parse_args()
    df = generate_claims(a.start, a.months, a.claims_per_month, a.seed)
    (ROOT / "data").mkdir(exist_ok=True)
    df.to_csv(ROOT / "data" / "synthetic_claims.csv", index=False)
    print(f"Wrote {len(df):,} synthetic claims to data/synthetic_claims.csv")


if __name__ == "__main__":
    main()
