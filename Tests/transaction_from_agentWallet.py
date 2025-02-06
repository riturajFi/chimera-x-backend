from bip_utils import Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes

seed = "9f5fbdf64339d51a5924391ea05ac8e6300f971f081be33140201a7729ee2d86e38e57f05740b70ad64c97375aca56eb5ce6b443ac4a2c59616295aef2770f43"
seed_bytes = bytes.fromhex(seed)
bip44_ctx = Bip44.FromSeed(seed_bytes, Bip44Coins.ETHEREUM).Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0)
private_key = bip44_ctx.PrivateKey().Raw().ToHex()

print(private_key)
