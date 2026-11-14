#!/usr/bin/env python3
"""Offline Sony BPK decryptor.

Reconstructs what NodeRuntimePrivilege.AppInstallerCore does at install time:
  1. parse the EAIP package header (big-endian): magic, version(256),
     header_size, optional inline key, ex-headers (type 1 = RSA-wrapped AES key,
     type 2 = JSON metadata, 0xffff = end)
  2. RSA public-key operation (PKCS1 type-1 recovery) on each wrapped-key
     candidate -> 48 bytes = 32-byte AES-256 key + 16-byte MD5 of the body
  3. verify MD5 of body[header_size:]
  4. AES-256-CBC (ZERO IV) + PKCS5 decrypt body -> .tgz

Usage: bpk_decrypt.py <pkg-file> <public-key.pem> <out.tgz>
Deps: python3 stdlib + openssl CLI (for the AES step).
"""
import sys, os, subprocess, tempfile

def be(b):
    return int.from_bytes(b, "big")

def parse_header(f):
    f.seek(0)
    magic = f.read(4)
    assert magic == b"EAIP", "bad magic %r" % magic
    version = be(f.read(4))
    assert version == 256, "bad version %d" % version
    header_size = be(f.read(2))
    key_size = be(f.read(2))
    keys = []
    if key_size > 0:
        keys.append(f.read(key_size))
    metas = []
    end = (header_size == 0)
    while not end:
        pos = f.tell()
        if header_size and pos >= header_size:
            break
        etype = be(f.read(2))
        if etype == 0:
            size = be(f.read(2))
            f.seek(size, 1)
            continue
        f.seek(2, 1)                     # reserve
        size = be(f.read(4))
        if etype == 1:                   # SGINDECKEY: wrapped AES key
            keys.append(f.read(size))
        elif etype == 2:                 # metadata (JSON string)
            ln = f.read(2)               # readString: ushort length prefix
            metas.append(f.read(be(ln)))
        elif etype == 0xffff:
            end = True
        else:
            f.seek(size, 1)
    if header_size == 0:
        header_size = f.tell()
    return header_size, keys, metas

def rsa_public_recover(pubkey_pem, block):
    """RSA/ECB/PKCS1 'decrypt' with a public key = c^e mod n + strip type-1 padding."""
    mod_out = subprocess.run(["openssl", "rsa", "-pubin", "-in", pubkey_pem,
                             "-modulus", "-noout"],
                            capture_output=True, text=True).stdout
    n = int(mod_out.split("=")[1].replace(":", "").strip(), 16)
    e = 65537
    m = pow(int.from_bytes(block, "big"), e, n).to_bytes(len(block), "big")
    # strip PKCS1 type-1: 00 01 FF..FF 00 <payload>
    if m[0] != 0 or m[1] not in (1, 2):
        return None
    i = 2
    while i < len(m) and m[i] != 0:
        i += 1
    return m[i + 1:]

def main():
    pkg, pem, out = sys.argv[1], sys.argv[2], sys.argv[3]
    with open(pkg, "rb") as f:
        header_size, keys, metas = parse_header(f)
        f.seek(header_size)
        body = f.read()
    print(f"header: {header_size} bytes, {len(keys)} key candidates, "
          f"{len(metas)} metadata entries, body: {len(body)} bytes")
    for m in metas[:3]:
        print("meta:", m[:120].decode("utf-8", "replace"))
    for i, k in enumerate(keys):
        rec = rsa_public_recover(pem, k)
        if rec is None:
            print(f"key[{i}]: RSA recover failed ({len(k)} bytes)")
            continue
        print(f"key[{i}]: recovered {len(rec)} bytes "
              f"({'key+md5' if len(rec) == 48 else 'key only' if len(rec) == 32 else '?'})")
        if len(rec) != 48:
            continue
        aes_key, md5 = rec[:32], rec[32:]
        digest = subprocess.run(["openssl", "dgst", "-md5", "-binary"],
                                input=body, capture_output=True).stdout
        print("  md5:", "OK" if digest == md5 else "MISMATCH")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as tf:
            tf.write(body)
            bodyf = tf.name
        r = subprocess.run(["openssl", "enc", "-d", "-aes-256-cbc",
                            "-K", aes_key.hex(),
                            "-iv", "00" * 16,
                            "-in", bodyf, "-out", out],
                           capture_output=True, text=True)
        os.unlink(bodyf)
        if r.returncode != 0:
            print("  openssl AES failed:", r.stderr.strip())
            return 1
        print(f"  wrote {out} ({os.path.getsize(out)} bytes)")
        ft = subprocess.run(["file", out], capture_output=True, text=True).stdout
        print("  file:", ft.strip())
        return 0
    print("no usable key recovered")
    return 1

if __name__ == "__main__":
    sys.exit(main())
