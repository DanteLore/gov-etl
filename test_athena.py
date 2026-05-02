"""Quick Athena sanity checks for gov-etl tables."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from helpers.aws import query_athena

ATHENA_DATABASE = "incoming"
ATHENA_RESULTS_BUCKET = "dantelore.queryresults"


def q(sql):
    print(f"\n>>> {sql}")
    rows = query_athena(sql, ATHENA_DATABASE, ATHENA_RESULTS_BUCKET)
    for row in rows:
        print(row)
    return rows


q("SELECT year, COUNT(*) as rows FROM traffic_census_aadf GROUP BY year ORDER BY year DESC LIMIT 10")
q("SELECT year, COUNT(*) as rows, MIN(price) as min_price, MAX(price) as max_price FROM house_prices_ppd GROUP BY year ORDER BY year DESC LIMIT 10")
