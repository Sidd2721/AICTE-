from typing import Any


def evaluate_discrepancies(
    instrument: dict[str, Any],
    confirmed: dict[str, Any],
) -> list[dict[str, Any]]:
    """Evaluates D1-D6 discrepancy rules between declared instrument and confirmed bank data."""
    discrepancies: list[dict[str, Any]] = []

    # D1: Amount discrepancy
    inst_amt = instrument.get("amount_paise")
    conf_amt = confirmed.get("amount_paise")
    if inst_amt is not None and conf_amt is not None and inst_amt != conf_amt:
        discrepancies.append(
            {
                "code": "D1_AMOUNT_MISMATCH",
                "label": "Deposit amount does not match bank record",
                "severity": "critical",
                "declared": inst_amt,
                "confirmed": conf_amt,
            }
        )

    # D2: Maturity date discrepancy
    inst_mat = instrument.get("maturity_date")
    conf_mat = confirmed.get("maturity_date")
    if inst_mat and conf_mat and str(inst_mat) != str(conf_mat):
        discrepancies.append(
            {
                "code": "D2_MATURITY_MISMATCH",
                "label": "Maturity date does not match bank confirmation",
                "severity": "critical",
                "declared": str(inst_mat),
                "confirmed": str(conf_mat),
            }
        )

    # D3: Reference number discrepancy
    inst_ref = instrument.get("ref_no")
    conf_ref = confirmed.get("ref_no")
    if inst_ref and conf_ref and inst_ref != conf_ref:
        discrepancies.append(
            {
                "code": "D3_REF_MISMATCH",
                "label": "FDR reference number mismatch",
                "severity": "critical",
                "declared": inst_ref,
                "confirmed": conf_ref,
            }
        )

    # D4: Bank code discrepancy
    inst_bank = instrument.get("bank_code")
    conf_bank = confirmed.get("bank_code")
    if inst_bank and conf_bank and inst_bank.upper() != conf_bank.upper():
        discrepancies.append(
            {
                "code": "D4_BANK_MISMATCH",
                "label": "Bank identifier mismatch",
                "severity": "critical",
                "declared": inst_bank,
                "confirmed": conf_bank,
            }
        )

    # D5: Lien not marked
    inst_lien = bool(instrument.get("lien_marked", False))
    conf_lien = bool(confirmed.get("lien_marked", True))
    if not inst_lien or not conf_lien:
        discrepancies.append(
            {
                "code": "D5_LIEN_NOT_MARKED",
                "label": "Fixed deposit is not marked with lien to AICTE",
                "severity": "critical",
                "declared": inst_lien,
                "confirmed": conf_lien,
            }
        )

    return discrepancies
