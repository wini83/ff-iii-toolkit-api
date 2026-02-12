import os
import sys
from pathlib import Path
from pprint import pprint

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

load_dotenv(Path(__file__).parent.parent / ".env.cli")

from services.allegro.api import AllegroApiClient  # noqa: E402


def main() -> None:
    cookie = os.getenv("ALLEGRO_COOKIE")
    if not cookie:
        raise RuntimeError("Missing ALLEGRO_COOKIE env variable")

    session = requests.Session()
    client = AllegroApiClient(cookie=cookie, session=session)

    print("▶ Fetching user info...")
    user = client.get_user_info()
    pprint(user.login)  # albo user.login, zależnie od struktury

    print("\n▶ Fetching orders...")
    orders_result = client.get_orders()

    print(f"✔ Orders: {len(orders_result.orders)}")
    print(f"✔ Payments: {len(orders_result.payments)}")

    print("\n▶ Payments overview:")
    for payment in orders_result.payments:
        print(payment)
        for order in payment.orders:
            print(f"  - {order.order_id} | {order.seller}")
            print(order.print_offers())
            print()

    print("\n✅ Allegro CLI finished successfully")


if __name__ == "__main__":
    main()
