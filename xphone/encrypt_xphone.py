"""
XPhone Code Encryptor & Obfuscation Packager
Mengenkripsi source code Python XPhone Manager menjadi modul terlindungi (Encrypted Bytecode + Anti-Tamper Loader).
"""
import os
import sys
import zlib
import base64
import hashlib
import py_compile

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def encrypt_file(source_file: str, output_file: str, key_seed: str = "XPHONE_APPDOCKHUB_ENCRYPT_2026"):
    """Mengenkripsi file Python dengan kompresi zlib, XOR dynamic key, dan Base64 packaging."""
    with open(source_file, "r", encoding="utf-8") as f:
        plain_code = f.read()

    # Hitung checksum keaslian kode
    code_hash = hashlib.sha256(plain_code.encode('utf-8')).hexdigest()

    # Kompresi dengan zlib level 9
    compressed = zlib.compress(plain_code.encode('utf-8'), level=9)

    # Obfuscation XOR
    key_bytes = key_seed.encode('utf-8')
    obfuscated = bytearray(len(compressed))
    for i in range(len(compressed)):
        obfuscated[i] = compressed[i] ^ key_bytes[i % len(key_bytes)]

    encoded = base64.b64encode(obfuscated).decode('ascii')

    # Buat runtime loader
    loader_template = f'''# -*- coding: utf-8 -*-
"""
Protected & Encrypted Executable Module - XPhone Manager
Appdockhub.com (C) 2026. All rights reserved.
Tampering or unauthorized reverse-engineering is strictly prohibited.
"""
import zlib
import base64
import hashlib
import sys

_EXPECTED_HASH = "{code_hash}"
_KEY = "{key_seed}".encode('utf-8')
_PAYLOAD = """{encoded}"""

def _run():
    raw_b64 = base64.b64decode(_PAYLOAD.strip())
    decompressed_bytes = bytearray(len(raw_b64))
    for i in range(len(raw_b64)):
        decompressed_bytes[i] = raw_b64[i] ^ _KEY[i % len(_KEY)]
    
    code_str = zlib.decompress(bytes(decompressed_bytes)).decode('utf-8')
    
    # Verifikasi Integritas Anti-Tamper
    if hashlib.sha256(code_str.encode('utf-8')).hexdigest() != _EXPECTED_HASH:
        print("[CRITICAL] Integritas aplikasi rusak / terdeteksi modifikasi tidak sah!")
        sys.exit(1)
        
    exec(code_str, globals())

if __name__ == "__main__":
    _run()
'''
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(loader_template)

    # Kompilasi juga ke .pyc bytecode
    py_compile.compile(output_file, cfile=output_file + "c", doraise=True)
    print(f"Berhasil mengenkripsi {os.path.basename(source_file)} -> {os.path.basename(output_file)} dan .pyc!")

if __name__ == "__main__":
    src = os.path.join(BASE_DIR, "XPhone_Manager_App.py")
    out = os.path.join(BASE_DIR, "XPhone_Manager_Encrypted.py")
    encrypt_file(src, out)
