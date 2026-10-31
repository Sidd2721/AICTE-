#!/usr/bin/env python3
"""Generate an RSA 2048-bit private key PEM for stable release receipt signing.

Prints the private key PEM and exact Render configuration steps to stdout.
Never writes to any repository files.
"""

import hashlib

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def main() -> None:
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    pub_pem = priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    kid = hashlib.sha256(pub_pem.strip()).hexdigest()[:16]

    print("=" * 72)
    print("AICTE SECURITY DEPOSIT PORTAL - RECEIPT SIGNING KEY GENERATOR")
    print("=" * 72)
    print(f"Key ID (thumbprint prefix): {kid}")
    print("Algorithm: RS256 (RSA 2048-bit)")
    print("-" * 72)
    print("RECEIPT_PRIVATE_KEY_PEM (Copy the exact block below):")
    print("-" * 72)
    print(priv_pem.strip())
    print("-" * 72)
    print("\nEXACT RENDER DEPLOYMENT STEPS:")
    print("1. Open Render Dashboard: https://dashboard.render.com")
    print("2. Select your web service ('aicte-fdr-portal')")
    print("3. In the left navigation sidebar, click 'Environment'")
    print("4. Click 'Add Environment Variable'")
    print("   - Key:   RECEIPT_PRIVATE_KEY_PEM")
    print("   - Value: [Paste the complete multiline PEM text above]")
    print("5. Click 'Save Changes'")
    print("6. Render automatically redeploys with the persistent stable key.")
    print("=" * 72)


if __name__ == "__main__":
    main()
