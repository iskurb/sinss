import aiohttp
import asyncio
import aiofiles
from tqdm.asyncio import tqdm

API_URL = "https://sns-api.bonfida.com/v2/listings/listings-v3"
OUTPUT_FILE = "listings.txt"

HEADERS = {
    "Content-Type": "application/json"
}

FILTER_PARAMS = {
    "page_size": 100,
    "max_len": 15,
}

TIMEOUT = aiohttp.ClientTimeout(total=90)
MAX_RETRIES = 5
RETRY_DELAY = 2
CONCURRENCY = 20

SEM = asyncio.Semaphore(CONCURRENCY)

async def fetch_page(session, page):
    payload = {"params": {**FILTER_PARAMS, "page": page}}
    async with SEM:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with session.post(API_URL, json=payload, headers=HEADERS, timeout=TIMEOUT) as resp:
                    content_type = resp.headers.get("Content-Type", "")
                    if "application/json" not in content_type:
                        raise ValueError(f"Invalid content type: {content_type}")
                    data = await resp.json()
                    return data
            except Exception as e:
                print(f"❌ Страница {page}, попытка {attempt}/{MAX_RETRIES}: {e}")
                await asyncio.sleep(RETRY_DELAY)
        print(f"🚫 Страница {page} пропущена после {MAX_RETRIES} попыток")
        return None

async def main():
    async with aiohttp.ClientSession() as session:
        first_page = await fetch_page(session, 1)
        if not first_page:
            print("Не удалось получить первую страницу.")
            return

        total_pages = first_page.get("total_pages", 1)
        results = first_page.get("data", [])
        print(f"Получение листингов")
        print(f"Всего страниц: {total_pages}")

        tasks = [fetch_page(session, page) for page in range(2, total_pages + 1)]
        pages = await tqdm.gather(*tasks, desc="Загрузка страниц", total=len(tasks))

        for page_data in pages:
            if page_data and "data" in page_data:
                results.extend(page_data["data"])

        async with aiofiles.open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            for item in results:
                domain = item.get("d")
                usd_price = item.get("up")
                if domain and usd_price is not None:
                    await f.write(f'"domain": "{domain}", "usd_price": {usd_price}\n')

        print(f"Готово! Сохранено {len(results)} доменов")

if __name__ == "__main__":
    asyncio.run(main())
