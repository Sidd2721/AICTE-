/**
 * "About this page" Guide Metadata (CHARTER G3).
 * Single content file providing What this is / What to do here / What to notice.
 */

export interface AboutPageContent {
  title: string
  whatThisIs: string
  whatToDoHere: string
  whatToNotice: string
}

export const ABOUT_PAGES: Record<string, AboutPageContent> = {
  dashboard: {
    title: "Executive Compliance Dashboard",
    whatThisIs:
      "A centralized regulatory cockpit tracking deposit compliance, maturity timelines, and required actions across institutions.",
    whatToDoHere:
      "Review the Coverage Card for deposit shortfalls, inspect the prioritized Needs Action queue, or use the Time Machine to simulate future dates.",
    whatToNotice:
      "The Coverage Card computes statutory requirements dynamically from dated rule JSON; counters re-order automatically as deadlines approach.",
  },
  calculator: {
    title: "Table 1.4 Deposit Calculator (DEMO values)",
    whatThisIs:
      "A transparent calculation engine deriving mandatory security deposits from AICTE Approval Process Handbook (APH) guidelines.",
    whatToDoHere:
      "Select proposed academic programmes and property ownership types to compute statutory deposit requirements before submission.",
    whatToNotice:
      "All calculations are performed server-side using integer paise without hardcoded numeric constants; government institutions receive verified exemptions.",
  },
  case_page: {
    title: "Instrument Custody & Case Dossier",
    whatThisIs:
      "An immutable digital file for an individual FDR instrument, linking documents, bank confirmations, notes, and release workflows.",
    whatToDoHere:
      "Inspect submitted documents, trigger simulated bank confirmation, test defenses in the Break-Me Workbench, or initiate authorized release.",
    whatToNotice:
      "The single primary action button is computed server-side by next_action(); the Trust Badge is computed dynamically from confirmation snapshots.",
  },
  reports: {
    title: "Regulatory Compliance Reports & Exports",
    whatThisIs:
      "Regional and nationwide audit reporting feeds categorized by pending, active, matured, and discrepant instruments.",
    whatToDoHere:
      "Filter institutional portfolios by region or lifecycle state and download formula-injection sanitized CSV audit files.",
    whatToNotice:
      "All CSV exports prepend security escapes to formula-trigger characters (=, +, -, @), protecting spreadsheet users from formula injection attacks.",
  },
  audit: {
    title: "Cryptographic Tamper-Evident Audit Ledger",
    whatThisIs:
      "An append-only SHA-256 hash-chained event ledger tracking every state mutation, user login, and release verification.",
    whatToDoHere:
      "Search the regulatory event trail by actor or entity ID, and run the 'Verify Hash Chain' integrity check.",
    whatToNotice:
      "PostgreSQL database triggers permanently block UPDATE, DELETE, and TRUNCATE operations; any manual row tampering is caught immediately.",
  },
  evidence: {
    title: "Verifiable Evidence Map & System Invariants",
    whatThisIs:
      "A transparent engineering map linking every regulatory claim to reproducible terminal commands and test assertions.",
    whatToDoHere:
      "Inspect the 15 system safety invariants (I1–I15), review mutation testing records, and verify the honest limits of this prototype.",
    whatToNotice:
      "Every number and assertion is computed or generated; zero hand-typed metrics appear in reports or documentation.",
  },
  impact: {
    title: "Regulatory & Economic Impact Dashboard",
    whatThisIs:
      "A live, server-computed metrics portal tracking total regulatory deposit corpus, bank confirmation throughput, and audit integrity under AICTE PS 26265.",
    whatToDoHere:
      "Examine live-computed metrics across protected corpus, joint-lien coverage, and banking integrations, and verify system assurance guarantees.",
    whatToNotice:
      "All metrics are calculated directly from active database state; zero values are hardcoded or simulated static numbers.",
  },
}
