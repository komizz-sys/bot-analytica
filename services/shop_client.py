import httpx
import config


class ShopApiError(Exception):
    pass


async def get_revenue(period: str) -> dict:
    """
    period: "today" | "week" | "month" | "all"
    -> {
        "income_by_category": {...}, "income_total": int, "orders_count": int,
        "auto_cost_by_category": {...},  # расход, посчитанный магазином
        "auto_cost_total": int,
        "rent_auto_cost_uzs": int,       # осталось для совместимости
        "premium_unknown": [str],        # тарифы без закупочной цены в прайсе
        "period": str,
    }

    Закупочные цены живут в МАГАЗИНЕ (config + data/prices.json), а не здесь:
    там же лежат и цены продажи, так что менять их в одном месте.
    """
    if not config.SHOP_API_URL or not config.SHOP_API_SECRET:
        raise ShopApiError(
            "Не настроен SHOP_API_URL или SHOP_API_SECRET — заполни .env бота-аналитика"
        )

    url = f"{config.SHOP_API_URL}/internal/stats"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                url,
                params={"period": period},
                headers={"X-Internal-Secret": config.SHOP_API_SECRET},
            )
    except httpx.RequestError as e:
        raise ShopApiError(
            f"Не удалось достучаться до магазина ({url}): {e}. "
            "Проверь, что у сервиса магазина включён публичный домен в Railway."
        )

    if r.status_code == 403:
        raise ShopApiError("Магазин отклонил запрос — SHOP_API_SECRET не совпадает с ANALYTICS_API_SECRET в боте-магазине.")
    if r.status_code != 200:
        raise ShopApiError(f"Магазин ответил ошибкой {r.status_code}: {r.text}")

    return r.json()
