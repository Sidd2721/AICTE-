import datetime
import io
from asn1crypto import x509 as asn1x509
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.sign import signers
import pytest
from reportlab.pdfgen import canvas

from app.domain.bank_gate import check_bank_reply


def make_identity(cn: str, non_repudiation: bool = True):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=non_repudiation,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(key, hashes.SHA256())
    )
    key_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    cert_der = cert.public_bytes(serialization.Encoding.DER)
    return key_pem, cert_der


def pdf(text: str) -> bytes:
    b = io.BytesIO()
    c = canvas.Canvas(b)
    c.drawString(72, 750, text)
    c.save()
    return b.getvalue()


def sign(pdf_bytes: bytes, key_pem: bytes, cert_der: bytes, tmp_path) -> bytes:
    kp, cp = tmp_path / "k.pem", tmp_path / "c.pem"
    kp.write_bytes(key_pem)
    cp.write_bytes(
        x509.load_der_x509_certificate(cert_der).public_bytes(
            serialization.Encoding.PEM
        )
    )
    signer = signers.SimpleSigner.load(str(kp), str(cp))
    w = IncrementalPdfFileWriter(io.BytesIO(pdf_bytes))
    return signers.sign_pdf(
        w, signers.PdfSignatureMetadata(field_name="Sig1"), signer=signer
    ).getvalue()


def asn1(cert_der: bytes):
    return asn1x509.Certificate.load(cert_der)


def fp(cert_der: bytes) -> str:
    return asn1(cert_der).sha256.hex()


@pytest.fixture
def ctx(tmp_path):
    bank = make_identity("Bank A")
    other = make_identity("Bank B")
    stranger = make_identity("Stranger")
    issued = pdf("FDR 1234 Rs 1000000. Please confirm. Ref ABC123")
    return dict(
        bank=bank,
        other=other,
        stranger=stranger,
        issued=issued,
        tmp=tmp_path,
        roots=[asn1(bank[1]), asn1(other[1])],
        pinned=fp(bank[1]),
    )


def run(c: dict, reply: bytes):
    return check_bank_reply(reply, c["issued"], c["pinned"], c["roots"])


def test_1_valid_accepted(ctx) -> None:
    r = run(ctx, sign(ctx["issued"], *ctx["bank"], ctx["tmp"]))
    assert (r.ok, r.reason) == (True, "accepted")


def test_2a_tampered_inside_issued_part_rejected(ctx) -> None:
    s = bytearray(sign(ctx["issued"], *ctx["bank"], ctx["tmp"]))
    s[200] ^= 0x01
    r = run(ctx, bytes(s))
    assert (r.ok, r.reason) == (False, "not_our_letter")


def test_2b_tampered_inside_signed_update_rejected(ctx) -> None:
    s = bytearray(sign(ctx["issued"], *ctx["bank"], ctx["tmp"]))
    s[len(ctx["issued"]) + 30] ^= 0x01
    r = run(ctx, bytes(s))
    assert not r.ok and r.reason != "accepted"


def test_3_other_document_signed_by_trusted_key_rejected(ctx) -> None:
    evil = sign(pdf("Totally different letter"), *ctx["bank"], ctx["tmp"])
    r = run(ctx, evil)
    assert (r.ok, r.reason) == (False, "not_our_letter")


def test_4_untrusted_signer_rejected(ctx) -> None:
    r = run(ctx, sign(ctx["issued"], *ctx["stranger"], ctx["tmp"]))
    assert (r.ok, r.reason) == (False, "signer_not_trusted")


def test_5_trusted_but_wrong_pinned_signer_rejected(ctx) -> None:
    r = run(ctx, sign(ctx["issued"], *ctx["other"], ctx["tmp"]))
    assert (r.ok, r.reason) == (False, "wrong_signer_for_this_bank")


def test_6_bytes_appended_after_signing_rejected(ctx) -> None:
    r = run(
        ctx,
        sign(ctx["issued"], *ctx["bank"], ctx["tmp"]) + b"\n%appended junk\n",
    )
    assert not r.ok


def test_7_unsigned_rejected(ctx) -> None:
    r = run(ctx, ctx["issued"])
    assert (r.ok, r.reason) == (False, "need_exactly_one_signature")


def test_8_garbage_rejected_without_crash(ctx) -> None:
    r = run(ctx, b"not a pdf")
    assert (r.ok, r.reason) == (False, "not_our_letter")


def test_9_cert_without_non_repudiation_rejected(ctx) -> None:
    weak = make_identity("Bank A weak", non_repudiation=False)
    c = dict(ctx, roots=[asn1(weak[1])], pinned=fp(weak[1]))
    r = run(c, sign(ctx["issued"], *weak, ctx["tmp"]))
    assert (r.ok, r.reason) == (False, "certificate_lacks_non_repudiation")
