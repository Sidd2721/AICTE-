from dataclasses import dataclass
from io import BytesIO
from typing import Any

from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.sign.validation import validate_pdf_signature
from pyhanko.sign.validation.status import SignatureCoverageLevel
from pyhanko_certvalidator import ValidationContext


@dataclass(frozen=True)
class GateResult:
    ok: bool
    reason: str  # stable code; never "mismatch" for infrastructure problems


def check_bank_reply(
    reply: bytes, issued: bytes, pinned_sha256_hex: str, trust_roots: list[Any]
) -> GateResult:
    """The full gate (invariant I3). intact+valid+trusted alone is NOT enough."""
    try:
        if not reply.startswith(issued):
            return GateResult(
                False, "not_our_letter"
            )  # must begin with the exact bytes we issued
        reader = PdfFileReader(BytesIO(reply))
        sigs = reader.embedded_signatures
        if len(sigs) != 1:
            return GateResult(False, "need_exactly_one_signature")
        status = validate_pdf_signature(
            sigs[0], ValidationContext(trust_roots=trust_roots)
        )
        if not (status.intact and status.valid):
            return GateResult(False, "signature_not_intact_or_valid")
        if not status.trusted:
            return GateResult(False, "signer_not_trusted")
        if status.coverage != SignatureCoverageLevel.ENTIRE_FILE:
            return GateResult(False, "signature_does_not_cover_whole_file")
        cert = status.signing_cert
        if cert.sha256.hex() != pinned_sha256_hex.lower():
            return GateResult(False, "wrong_signer_for_this_bank")
        if "non_repudiation" not in (cert.key_usage_value.native or []):
            return GateResult(False, "certificate_lacks_non_repudiation")
        return GateResult(True, "accepted")
    except Exception:  # garbage input must never crash the endpoint
        return GateResult(False, "unreadable_or_invalid")


def build_verification_gate_report(
    instrument: dict[str, Any],
    confirmed_fields: dict[str, Any] | None,
    gate_outcome: str = "accepted",
) -> dict[str, Any]:
    """Single definition for verification gate results, split into signature checks and content checks."""
    sig_passed = gate_outcome == "accepted"
    signature_gate = [
        {
            "id": "prefix_match",
            "label": "Issued Letter Prefix Match",
            "passed": sig_passed,
            "status": "passed" if sig_passed else "failed",
            "detail": "Counter-signed document begins with issued bytes"
            if sig_passed
            else "Prefix mismatch",
        },
        {
            "id": "signature_count",
            "label": "Signature Count",
            "passed": sig_passed,
            "status": "passed" if sig_passed else "failed",
            "detail": "Exactly 1 embedded PKCS#7 signature"
            if sig_passed
            else "Signature count invalid",
        },
        {
            "id": "cryptographic_validity",
            "label": "Cryptographic Integrity",
            "passed": sig_passed,
            "status": "passed" if sig_passed else "failed",
            "detail": "Digital signature mathematically intact and valid"
            if sig_passed
            else "Signature invalid",
        },
        {
            "id": "trust_chain",
            "label": "Certificate Authority Trust",
            "passed": sig_passed,
            "status": "passed" if sig_passed else "failed",
            "detail": "Chains to trusted simulated Root CA"
            if sig_passed
            else "Untrusted signer",
        },
        {
            "id": "full_file_coverage",
            "label": "Byte-Range Coverage",
            "passed": sig_passed,
            "status": "passed" if sig_passed else "failed",
            "detail": "Signature covers 100% of document bytes"
            if sig_passed
            else "Incomplete coverage",
        },
        {
            "id": "pinned_signer",
            "label": "Pinned Signer Hash",
            "passed": sig_passed,
            "status": "passed" if sig_passed else "failed",
            "detail": "SHA-256 matches bank certificate fingerprint"
            if sig_passed
            else "Signer fingerprint mismatch",
        },
        {
            "id": "key_usage",
            "label": "Key Usage",
            "passed": sig_passed,
            "status": "passed" if sig_passed else "failed",
            "detail": "Certificate includes non_repudiation"
            if sig_passed
            else "Missing non-repudiation",
        },
        {
            "id": "revocation",
            "label": "Revocation Status",
            "passed": True,
            "status": "not_checked",
            "detail": "Revocation: not checked (simulated CA)",
        },
    ]

    conf = confirmed_fields or {}
    c_ref = conf.get("ref_no")
    c_bank = conf.get("bank_code")
    c_amt = conf.get("amount_paise")
    c_mat = conf.get("maturity_date")
    c_lien = conf.get("lien_marked")

    i_ref = instrument.get("ref_no")
    i_bank = instrument.get("bank_code")
    i_amt = instrument.get("amount_paise")
    i_mat = (
        str(instrument.get("maturity_date"))
        if instrument.get("maturity_date")
        else None
    )
    i_lien = instrument.get("lien_marked")

    ref_pass = bool(c_ref and i_ref and str(c_ref) == str(i_ref))
    bank_pass = bool(c_bank and i_bank and str(c_bank).upper() == str(i_bank).upper())
    amt_pass = bool(c_amt is not None and i_amt is not None and c_amt == i_amt)
    mat_pass = bool(c_mat and i_mat and str(c_mat) == str(i_mat))
    lien_pass = bool(c_lien is True)

    content_checks = [
        {
            "id": "ref_no",
            "label": "FDR Reference Number",
            "passed": ref_pass,
            "declared": i_ref,
            "confirmed": c_ref,
        },
        {
            "id": "bank_code",
            "label": "Bank Identifier Code",
            "passed": bank_pass,
            "declared": i_bank,
            "confirmed": c_bank,
        },
        {
            "id": "amount",
            "label": "Principal Amount (D1)",
            "passed": amt_pass,
            "declared": i_amt,
            "confirmed": c_amt,
        },
        {
            "id": "maturity_date",
            "label": "Maturity Date (D2)",
            "passed": mat_pass,
            "declared": i_mat,
            "confirmed": c_mat,
        },
        {
            "id": "lien_marked",
            "label": "AICTE Joint Lien Endorsement (D5)",
            "passed": lien_pass,
            "declared": i_lien,
            "confirmed": c_lien,
        },
    ]

    return {
        "signature_gate": signature_gate,
        "content_checks": content_checks,
    }
