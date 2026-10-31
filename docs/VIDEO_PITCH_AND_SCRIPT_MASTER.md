# AICTE Fixed Deposit Receipt (FDR) & Security Deposit Regulatory Portal (PS 26265)
## Master Video Pitch, Voice-Over Script & Broadcast Cues

**Demo Video Asset**: [`docs/demo_video.mp4`](demo_video.mp4)  
**File Size**: 3,474,139 bytes (3.47 MB)  
**SHA-256**: `7B76F19BA6E0B8DA2BAA3D31BE66E15E94FB23E8E9390E0D041498DA039DE255`  
**Playback Player**: [`docs/video_player.html`](video_player.html)  
**Generator Automation**: [`scripts/record_full_demo_video.js`](../scripts/record_full_demo_video.js)  

---

### Voice-Over Script & Scene-by-Scene Timeline

#### Scene 1: Welcome & Instant Persona Access (0:00 - 0:25)
- **Visual Cue**: Browser navigates to `/login`. Interactive persona switcher displays cards for Institution, Regional Officer (Maker), Regional Checker, Bureau Head (Checker), and External Auditor.
- **On-Screen Subtitle**: `SCENE 1: INSTANT EVALUATION LOGIN — Passwordless 1-Click Persona Access`
- **Voice-Over Narration**:  
  *"Welcome to the AICTE Security Deposit and Fixed Deposit Regulatory Portal, engineered for Problem Statement 26265. Evaluating technical regulator portals often requires cumbersome credentials. Here, judges can step into any persona with a single click. Notice our fail-closed security: this demo switcher endpoint automatically yields a 404 in production."*

#### Scene 2: Interactive 6-Minute Guided Tour (0:25 - 0:50)
- **Visual Cue**: Navigation to `/guide`. Smooth scrolling over 7 capability cards with reading time estimates, prerequisite badges, and live links.
- **On-Screen Subtitle**: `SCENE 2: INTERACTIVE 6-MINUTE TOUR — Single Source of Truth (docs/guide.json)`
- **Voice-Over Narration**:  
  *"For first-time evaluators, the built-in 6-minute tour walks through every regulatory capability. All tour steps derive from a single JSON configuration, written at an eighth-grade reading level, completely free of unexplained database codes or technical jargon."*

#### Scene 3: Dynamic Table 1.4 Handbook Calculator (0:50 - 1:20)
- **Visual Cue**: Switched to Institution persona (`inst.north1@example.com`). At `/deposits`, click "Table 1.4 Calculator". Modal pops up showing programme multi-select, land ownership toggle (owned vs leased), and minority status.
- **On-Screen Subtitle**: `SCENE 3: regulatory CALCULATOR — Dynamic Handbook Engine (Integer Paise)`
- **Voice-Over Narration**:  
  *"Institutions submit deposit guarantees based on AICTE Approval Process Handbook regulations. Rather than hardcoding figures in application code, our engine dynamically evaluates dated JSON rule sets. For example, a new Engineering campus on leased private land applies a 2x multiplier, stored accurately in integer paise to eliminate rounding discrepancies."*

#### Scene 4: FDR Submission & Cryptographic Scan Vault (1:20 - 1:50)
- **Visual Cue**: Click "Submit FDR". Form takes instrument reference, issuing bank, term, and PDF certificate upload.
- **On-Screen Subtitle**: `SCENE 4: FDR INTAKE & VAULT — SHA-256 Fingerprint & AES-256-GCM Encryption`
- **Voice-Over Narration**:  
  *"When an institution files an instrument, the portal validates the PDF magic header, computes a cryptographic SHA-256 fingerprint, and stores it in the encrypted vault. The instrument status is initially marked 'Submitted (Claimed)' until verified by the issuing bank."*

#### Scene 5: Bank Confirmation Gate (1:50 - 2:20)
- **Visual Cue**: Switch to Regional Officer (`officer.north@example.com`). Click "Trigger Bank Confirmation" on instrument `FDR-B9-301`. Full 6-stage gate checks byte integrity, PDF signature coverage, certificate chain, and bank records. Trust badge turns green "Confirmed by Bank (SIMULATED)".
- **On-Screen Subtitle**: `SCENE 5: BANK CONFIRMATION GATE — 6-Stage Cryptographic Verification Gate`
- **Voice-Over Narration**:  
  *"Paper letters are vulnerable to fraud. In our workflow, the Regional Officer requests independent verification. The labelled bank simulator runs a rigorous 6-stage cryptographic gate. Only when byte prefix, entire-file signature coverage, and issuing records match does the badge turn green."*

#### Scene 6: Discrepancy Defense & Mandatory Scrutiny (2:20 - 2:50)
- **Visual Cue**: Inspect case with a ₹ 10,00,000 shortfall between claimed and confirmed amount. RO attempts to waive the discrepancy; system requires a mandatory digital scrutiny note.
- **On-Screen Subtitle**: `SCENE 6: DISCREPANCY DEFENSE — Automatic Discrepancy Flags & Scrutiny Notes`
- **Voice-Over Narration**:  
  *"If a bank confirms an amount lower than claimed or a mismatched lien, the engine automatically raises a discrepancy flag. Officers cannot quietly bypass this: waiving a flag requires a mandatory Scrutiny Note with minimum length and justification, creating an auditable trail."*

#### Scene 7: Dual-Custody Release Authorization (2:50 - 3:30)
- **Visual Cue**: Case `FDR-B9-304` (maturity reached). Regional Officer marks verification on the 3-step Stepper. RO attempts to approve release: blocked with HTTP 403 `MAKER_CANNOT_BE_CHECKER`. Switch to Bureau Head (`bureau@example.com`), who approves the release and generates the cryptographic encashment receipt.
- **On-Screen Subtitle**: `SCENE 7: DUAL-CONTROL RELEASE — Maker is Never Checker (I8 Hard Invariant)`
- **Voice-Over Narration**:  
  *"The portal's strongest governance safeguard is dual-custody release. When an FDR reaches maturity, the Regional Officer acts as Maker and verifies compliance. The system strictly forbids the Maker from approving the release. A different Bureau Head must review and authorize the transaction, producing a signed cryptographic release receipt token."*

#### Scene 8: Security Workbench & Replay Defense (3:30 - 3:55)
- **Visual Cue**: At Security Workbench, test invalid certificate, expired validity, and replayed webhook payloads. System immediately rejects invalid signatures with specific failure diagnostics.
- **On-Screen Subtitle**: `SCENE 8: SECURITY WORKBENCH — Active Adversarial Testing & Gate Enforcement`
- **Voice-Over Narration**:  
  *"Judges can verify our defenses live using the Break-Me Workbench. Injecting a replayed bank webhook or a certificate signed with an unauthorized key immediately triggers an integrity violation. Every gate failure is recorded in the immutable audit log."*

#### Scene 9: Tamper-Evident Audit Ledger (3:55 - 4:20)
- **Visual Cue**: Switch to External Auditor (`auditor@example.com`). Open `/audit` and click "Verify Chain Integrity". System calculates SHA-256 hashes from genesis to head; visual indicator displays green "Ledger Intact".
- **On-Screen Subtitle**: `SCENE 9: TAMPER-EVIDENT LEDGER — Append-Only SHA-256 Hash Chain`
- **Voice-Over Narration**:  
  *"All state transitions are etched into an append-only audit ledger. PostgreSQL triggers permanently forbid UPDATE and DELETE operations. Each record stores the SHA-256 hash of its predecessor. Clicking 'Verify Chain Integrity' validates the mathematical continuity of the entire history."*

#### Scene 10: System Evidence & 15 Safety Invariants (4:20 - 4:45)
- **Visual Cue**: Navigate to `/evidence` and `/impact`. Review test suite counts, bundle metrics, and computed dashboard impact metrics.
- **On-Screen Subtitle**: `SCENE 10: EVIDENCE & REGULATORY IMPACT — Zero Assertion Without Proof`
- **Voice-Over Narration**:  
  *"Every claim in this portal is verified by automated test suites: 186 backend tests, 43 end-to-end browser tests, and 4 mutation proofs. With non-superuser database isolation, integer paise precision, and machine-to-machine integration APIs, the AICTE FDR Portal is hackathon-final and prototype-ready."*

---

### Captions File (.vtt specification)
The complete closed-captions track matching `docs/demo_video.mp4` is embedded below and rendered inside [`docs/video_player.html`](video_player.html).
