from dataclasses import dataclass
from io import BytesIO

from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.sign.validation import validate_pdf_signature
from pyhanko.sign.validation.status import SignatureCoverageLevel
from pyhanko_certvalidator import ValidationContext


@dataclass(frozen=True)
class GateResult:
    ok: bool
    reason: str  # stable code; never "mismatch" for infrastructure problems


def check_bank_reply(reply: bytes, issued: bytes, pinned_sha256_hex: str, trust_roots: list) -> GateResult:
    """The full gate (invariant I3). intact+valid+trusted alone is NOT enough."""
    try:
        if not reply.startswith(issued):
            return GateResult(False, "not_our_letter")          # must begin with the exact bytes we issued
        reader = PdfFileReader(BytesIO(reply))
        sigs = reader.embedded_signatures
        if len(sigs) != 1:
            return GateResult(False, "need_exactly_one_signature")
        status = validate_pdf_signature(sigs[0], ValidationContext(trust_roots=trust_roots))
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
    except Exception:                                            # garbage input must never crash the endpoint
        return GateResult(False, "unreadable_or_invalid")
