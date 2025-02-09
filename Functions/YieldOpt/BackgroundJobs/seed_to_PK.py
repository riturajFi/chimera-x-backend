from eth_keys import keys
import binascii

hex_seed = "3a5897bf3d7a38b342419cf961846a67b7ba5314d24a3a772b2788d0e47b1b337b532129e2474a2c1f5d39f67bf7220683612b4f8ef29a82518009c8bbbc88cd"
private_key = keys.PrivateKey(bytes.fromhex(hex_seed[:64]))  # Truncate if too long
print("Private Key:", private_key)
print("Public Key:", private_key.public_key)
print("Ethereum Address:", private_key.public_key.to_checksum_address())
