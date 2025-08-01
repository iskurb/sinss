import asyncio
import GetOffers
import Comparison
import GetListings

async def main():
    await GetListings.main()
    await GetOffers.main()
    await Comparison.main()

if __name__ == "__main__":
    asyncio.run(main())
