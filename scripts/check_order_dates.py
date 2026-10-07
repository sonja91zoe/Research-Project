"""Query an order's stored dates, independently of image inference."""
import argparse
import json
from src.evidence.database import verify_dates

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', required=True)
    parser.add_argument('--order-id', required=True)
    parser.add_argument('--purchase-date', required=True)
    parser.add_argument('--request-date', required=True)
    parser.add_argument('--window-days', type=int, default=30)
    args = parser.parse_args()
    print(json.dumps(verify_dates(args.database, args.order_id,
          args.purchase_date, args.request_date, args.window_days), indent=2))
