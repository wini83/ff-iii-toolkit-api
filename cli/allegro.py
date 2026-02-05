import os
from pprint import pprint

import requests

from services.allegro.api import AllegroApiClient


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
