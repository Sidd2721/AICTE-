/**
 * Plain-language system messages and guidance actions for the FDR Portal (SIH PS 26265).
 * Rule T7: Plain-language messages mapping each code to a sentence with an action.
 * Rule T6: Every message conforms to honesty rules (DEMO/SIMULATED).
 */

export const SYSTEM_MESSAGES: Record<
  string,
  { label: string; sentence: string; action: string }
> = {
  // Discrepancy Codes
  D1_AMOUNT_MISMATCH: {
    label: "Deposit Amount Mismatch",
    sentence:
      "The bank-confirmed amount differs from the institution's submitted amount.",
    action:
      "Request an amended FDR certificate from the bank or submit a regional waiver with mandatory scrutiny rationale.",
  },
  AMOUNT_MISMATCH: {
    label: "Amount Mismatch",
    sentence:
      "The bank-confirmed amount differs from the institution's submitted amount.",
    action:
      "Request an amended FDR certificate from the bank or submit a regional waiver with mandatory scrutiny rationale.",
  },
  D2_MATURITY_MISMATCH: {
    label: "Maturity Date Mismatch",
    sentence:
      "The deposit maturity date confirmed by CBS differs from the submission record.",
    action:
      "Review bank confirmation advice and verify tenure calculation under the relevant handbook edition.",
  },
  MATURITY_MISMATCH: {
    label: "Maturity Date Mismatch",
    sentence:
      "The deposit maturity date confirmed by CBS differs from the submission record.",
    action:
      "Review bank confirmation advice and verify tenure calculation under the relevant handbook edition.",
  },
  D3_REF_MISMATCH: {
    label: "FDR Reference Number Mismatch",
    sentence:
      "The instrument reference number does not match CBS account records.",
    action:
      "Check physical certificate scan hash and re-verify bank deposit account identifier.",
  },
  D4_BANK_MISMATCH: {
    label: "Bank Identifier Mismatch",
    sentence:
      "The bank identifier reported by CBS differs from the institution submission.",
    action:
      "Re-verify branch routing code or IFSC identifier before proceeding.",
  },
  D5_LIEN_NOT_MARKED: {
    label: "AICTE Lien Not Marked",
    sentence:
      "AICTE is not recorded as joint holder with lien marked on the bank confirmation.",
    action:
      "Require institution to obtain an explicit AICTE joint lien endorsement from branch manager.",
  },
  INTEREST_RATE_MISMATCH: {
    label: "Interest Rate Discrepancy",
    sentence:
      "The contracted interest rate differs between institution claim and bank record.",
    action:
      "Reconcile interest rate schedule with the bank's fixed deposit receipt copy.",
  },
  JOINT_NAME_MISSING: {
    label: "Joint AICTE Name Missing",
    sentence:
      "AICTE is not recorded as joint holder with lien marked on the bank confirmation.",
    action:
      "Require institution to obtain an explicit AICTE joint lien endorsement from branch manager.",
  },
  FDR_NUMBER_MISMATCH: {
    label: "FDR Number Mismatch",
    sentence:
      "The instrument reference number does not match CBS account records.",
    action:
      "Check physical certificate scan hash and re-verify bank deposit account identifier.",
  },
  STATUS_MISMATCH: {
    label: "Bank Status Discrepancy",
    sentence:
      "CBS reports the deposit in a different state (e.g., closed/encashed) than active.",
    action:
      "Contact bank branch nodal officer to clarify deposit status before proceeding.",
  },

  // Maker-Checker & Release Codes
  MAKER_CANNOT_BE_CHECKER: {
    label: "Dual-Control Policy Violation",
    sentence: "Maker and checker cannot be the same officer (Hard Rule I7).",
    action:
      "A different authorized officer (Bureau Head checker) must review and approve this release.",
  },
  OBLIGATION_ACTIVE: {
    label: "Active Obligation Lock",
    sentence:
      "The institution has active regulatory security deposit obligations that require this FDR coverage.",
    action:
      "Ensure adequate replacement FDR coverage is submitted before requesting final release.",
  },
  TENURE_NOT_MET: {
    label: "Lock-in Period Active",
    sentence:
      "The regulatory lock-in duration has not concluded under applicable Approval Process Handbook rules.",
    action:
      "Review the original deposit terms or obtain Council special dispensation.",
  },
  CONFIRMATION_MISSING: {
    label: "Bank Confirmation Required",
    sentence:
      "An unconfirmed deposit cannot be released without authoritative bank verification.",
    action:
      "Initiate bank verification protocol to confirm authentic deposit status first.",
  },

  // Badges & Lifecycle States
  SUBMITTED_CLAIMED: {
    label: "Submitted by Institution",
    sentence: "FDR submitted by institution; not yet confirmed by bank.",
    action:
      "Regional Officer should trigger bank confirmation to verify authentic CBS deposit records.",
  },
  CONFIRMED_ACTIVE: {
    label: "Confirmed by Bank (SIMULATED)",
    sentence:
      "Deposit verified authentic through bank verification gate (CBS simulator).",
    action:
      "Regular tracking active; monitor upcoming maturity and annual interest renewal.",
  },
  DISCREPANT: {
    label: "Discrepancy Detected",
    sentence:
      "Field discrepancies exist between institution claim and bank confirmation.",
    action:
      "Investigate flagged discrepancies; RO scrutiny note and waiver required to clear.",
  },
  RELEASE_REQUESTED: {
    label: "Release Requested",
    sentence:
      "Institution has requested release of fixed deposit upon tenure completion.",
    action:
      "Regional Officer must verify fulfillment of all obligations and release checklist.",
  },
  RELEASE_VERIFIED: {
    label: "Release Verified (Maker)",
    sentence:
      "Regional Officer verified release checklist; awaiting dual-control Bureau Head approval.",
    action:
      "Bureau Head checker must review case notes and perform final release approval.",
  },
  RELEASED: {
    label: "Released",
    sentence:
      "Deposit formally released to institution. Encashment authorization receipt generated.",
    action:
      "Verify cryptographic receipt token offline using verify_receipt.py.",
  },
}

export function getMessage(code: string) {
  if (SYSTEM_MESSAGES[code]) return SYSTEM_MESSAGES[code]
  const stripped = code.replace(/^D\d+_/, "")
  if (SYSTEM_MESSAGES[stripped]) return SYSTEM_MESSAGES[stripped]
  const upperField = `${code.toUpperCase()}_MISMATCH`
  if (SYSTEM_MESSAGES[upperField]) return SYSTEM_MESSAGES[upperField]
  return {
    label: code,
    sentence: `System event: ${code}`,
    action: "Review case audit history for further context.",
  }
}
