import asyncio
import aiohttp
import json
import re
import os
from tqdm.asyncio import tqdm_asyncio

MAX_CONCURRENT_REQUESTS = 10
REVERSE_LOOKUP_URL = "https://sns-sdk-proxy.bonfida.workers.dev/reverse-lookup/{}"
RETRY_LIMIT = 3
CACHE_FILE = "domain_cache.json"

semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)


async def fetch_usd_prices():
    url = (
        "https://datapi.jup.ag/v1/assets/search?"
        "query=So11111111111111111111111111111111111111112,"
        "EchesyfXePKdLtoiZSL8pBe8Myagyy8ZRqsACNCFGnvp"
    )

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()

    prices = {}
    for token in data:
        mint = token["id"]
        price = token.get("usdPrice")
        prices[mint] = price

    return prices


def load_listings(path):
    pattern = re.compile(r'"domain": "([^"]+)", "usd_price": ([\d.]+)')
    with open(path, "r", encoding="utf-8") as f:
        return {m.group(1): float(m.group(2)) for m in pattern.finditer(f.read())}


def load_offers(path):
    offers = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                offers.append(eval(line.strip()))
            except:
                continue
    return offers


def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


async def fetch_domain(session, acc):
    async with semaphore:
        for _ in range(RETRY_LIMIT):
            try:
                async with session.get(REVERSE_LOOKUP_URL.format(acc), timeout=10) as resp:
                    data = await resp.json()
                    res = data.get("result")
                    if res and res != "Invalid input":
                        return acc, res
            except:
                pass
            await asyncio.sleep(0.5)
        return acc, None  # cache even failures




async def process_offers(domains, offers, sol_price, fida_price):
    cache = load_cache()
    all_accounts = {offer["domain_account"] for offer in offers}
    unknown = [acc for acc in all_accounts if acc not in cache]

    print(f"🔍 Всего уникальных domain_account: {len(all_accounts)}")
    print(f"🚀 Запросим {len(unknown)} новых из них")

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_domain(session, acc) for acc in unknown]
        for acc, domain in await tqdm_asyncio.gather(*tasks):
            cache[acc] = domain  # save even None

    save_cache(cache)

    matched = 0
    for offer in offers:
        acc = offer["domain_account"]
        domain = cache.get(acc)
        if not domain or domain not in domains:
            continue
        if offer["amount"] == '?':
            continue

        amt = float(offer["amount"])
        if offer.get("mint") == 'So11111111111111111111111111111111111111112':
            amt *= sol_price
        if offer.get("mint") == 'EchesyfXePKdLtoiZSL8pBe8Myagyy8ZRqsACNCFGnvp':
            amt *= fida_price

        lp = domains[domain]
        #print(f"{domain} - offer = {amt:.2f}|{lp:.2f} = listed")
        if amt > lp: print(f"$$$$$$$$$$$$$$$$$   https://v1.sns.id/domain?domain={domain}  $$$$$$$$$$$$$$$$")
        matched += 1

    print(f"\n📊 Всего офферов: {len(offers)}")
    print(f"✅ Офферов на маркетплейсе: {matched}")


async def main():
    domains = load_listings("listings.txt")
    offers = load_offers("offers.txt")

    prices = await fetch_usd_prices()
    sol_price = prices.get("So11111111111111111111111111111111111111112")
    fida_price = prices.get("EchesyfXePKdLtoiZSL8pBe8Myagyy8ZRqsACNCFGnvp")

    print(f"💰 SOL = {sol_price}, FIDA = {fida_price}")

    await process_offers(domains, offers, sol_price, fida_price)



if __name__ == "__main__":
    main()
