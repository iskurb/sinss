import requests
import base64
import base58
import struct

RPC_URL = "https://mainnet.helius-rpc.com/?api-key=5db9bfe0-c9c1-46b9-a768-b8dfcc70dd01"
SNS_MARKETPLACE_PROGRAM = "85iDfUvr3HJyLM2zcq5BXSiDvUWfw6cSE1FfNBo8Ap29"

TAG_MAP = {
    1: "Make Offer",
    2: "Cancel Offer",
    3: "Accept Offer",
}


def get_program_accounts(program_id, limit=None):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getProgramAccounts",
        "params": [
            program_id,
            {
                "encoding": "base64",
                "commitment": "confirmed"
            }
        ]
    }
    response = requests.post(RPC_URL, json=payload)
    accounts = response.json()["result"]
    if limit:
        accounts = accounts[:limit]
    return accounts


def decode_offer(data_b64):
    data = base64.b64decode(data_b64)
    if len(data) < 138:
        return None
    tag = data[0]
    name_account = base58.b58encode(data[2:34]).decode()
    owner = base58.b58encode(data[34:66]).decode()
    quote_mint = base58.b58encode(data[66:98]).decode()
    offer_amount = struct.unpack_from("<Q", data, 98)[0]
    escrow = base58.b58encode(data[106:138]).decode()
    return {
        "tag": tag,
        "domain_account": name_account,
        "owner": owner,
        "quote_mint": quote_mint,
        "offer_amount": offer_amount,
        "escrow": escrow
    }


def main():
    print("Получаю офферы...")
    offer_accounts = get_program_accounts(SNS_MARKETPLACE_PROGRAM)
    print(f"Всего транзакций в программе: {len(offer_accounts)}")

    pubkey_tags = {}
    all_offers = []

    for acc in offer_accounts:
        data_b64 = acc["account"]["data"][0]
        decoded = decode_offer(data_b64)
        if decoded:
            pubkey = acc["pubkey"]
            decoded["pubkey"] = pubkey
            all_offers.append(decoded)
            if pubkey not in pubkey_tags:
                pubkey_tags[pubkey] = set()
            pubkey_tags[pubkey].add(decoded["tag"])

    valid_make_offers = []
    owners_set = set()

    for offer in all_offers:
        pubkey = offer["pubkey"]
        if offer["tag"] == 1 and pubkey_tags.get(pubkey) == {1}:
            # Только если был только "Make Offer"
            mint = offer["quote_mint"]
            amount = offer["offer_amount"]
            if mint == 'So11111111111111111111111111111111111111112':
                amount = amount / (10 ** 9)
            elif mint == 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v':
                amount = amount / (10 ** 6)
            elif mint == 'EchesyfXePKdLtoiZSL8pBe8Myagyy8ZRqsACNCFGnvp':
                amount = amount / (10 ** 6)
            else:
                amount = amount / (10 ** 6) #usdt

            valid_make_offers.append({
                "tag_name": TAG_MAP[1],
                "domain_account": offer["domain_account"],
                "amount": amount,
                "mint": mint
            })
            owners_set.add(offer["owner"])

    with open("offers.txt", "w", encoding="utf-8") as f:
        for offer in valid_make_offers:
            f.write(f"{offer}\n")

    print(f"Найдено: {len(valid_make_offers)} офферов")


if __name__ == "__main__":
    main()
