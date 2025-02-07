from bip_utils import Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes

seed = "3a5897bf3d7a38b342419cf961846a67b7ba5314d24a3a772b2788d0e47b1b337b532129e2474a2c1f5d39f67bf7220683612b4f8ef29a8251809ac8bbbc97cd"
seed_bytes = bytes.fromhex(seed)
bip44_ctx = Bip44.FromSeed(seed_bytes, Bip44Coins.ETHEREUM).Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0)
private_key = bip44_ctx.PrivateKey().Raw().ToHex()

print(private_key)
