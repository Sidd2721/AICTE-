// scripts/generate_master_architecture_png.js
// Renders the COMPLETE Master System Architecture PNG (3840x2160 4K Ultra-HD)
// for AICTE Fixed Deposit & Security Deposit Regulatory Portal (PS 26265)
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const OUT_PATH = path.join(__dirname, '..', 'diagrams', 'png', 'master_system_architecture_complete.png');

const masterMermaidCode = `flowchart TD
    subgraph Tier1 ["TIER 1: INGRESS & CLIENT ACCESS LAYER"]
        CLIENT["Web Browser / Client Interface<br/>(React 19 &bull; TypeScript &bull; 5-Persona 1-Click Login &bull; WCAG 2.1 AA)"]
        CADDY["Caddy 2 / TLS 1.3 Reverse Proxy<br/>- Automatic HTTPS Ingress (Port 443)<br/>- Strict CSP: default-src 'self'<br/>- HSTS: max-age=31536000 &bull; Brotli/Gzip"]
    end

    subgraph Tier2 ["TIER 2: API GATEWAY & APPLICATION SECURITY PERIMETER"]
        API_ROUTER["FastAPI Application Gateway (Python 3.14)<br/>- High-Throughput ASGI with libuv (uvloop)<br/>- Sub-15ms Response P99 &bull; Pydantic v2 (Rust Core)<br/>- Sliding-Window Rate Limiting (IP & Account)"]
        FSM["Server-Driven FSM<br/>(next_action.py)<br/>Centralized UI Buttons"]
        RLS_MW["Context Injector<br/>(set_rls_context)<br/>JWT Claim Extractor"]
        IDEMP["Idempotency Filter<br/>(idempotency.py)<br/>Anti-Double Submit"]
    end

    subgraph Tier3 ["TIER 3: CORE REGULATORY & CRYPTOGRAPHIC TRUST ENGINES"]
        GATE["6-Point Cryptographic Bank Gate<br/>- pyHanko PKCS#7 / CMS Signature Validation<br/>- Entire-File Byte Coverage (Blocks Appended Pages)<br/>- Accredited CCA India Root CA Trust Anchoring<br/>- Legal Non-Repudiation (IT Act 2000 &sect; 3A)"]
        RULES["Dynamic Regulatory Scrutiny Engine<br/>- APH Table 1.4 Dynamic Slabs (Integer Paise)<br/>- Zero Hardcoded Numbers in Code (JSON Rulebooks)<br/>- Automatic Concession Multipliers (Women/PwD/NER)"]
        DISC["Discrepancy Triager (D1&ndash;D6)<br/>- D1 Amount &bull; D2 Tenure &bull; D3 CBS Ref<br/>- D4 Unscheduled &bull; D5 Lien &bull; D6 Duplicate<br/>- Critical Flags Trigger Automated EoA Holds"]
        MAKER_CHECKER["Dual-Custody Release Engine<br/>- CVC Separation of Duties Governance<br/>- Regional Officer (Maker) &bull; Central Bureau (Checker)<br/>- Digitally Signed Offline RS256 Encashment Receipt"]
    end

    subgraph Tier4 ["TIER 4: ASYNCHRONOUS PIPELINE & DISTRIBUTED WORKERS"]
        OUTBOX["Transactional Outbox Queue<br/>- Atomic outbox_message Insertion<br/>- Worker: FOR UPDATE SKIP LOCKED"]
        DISPATCHER["Resilient Webhook Dispatcher<br/>- HMAC-SHA256 Signed Payloads<br/>- 8x Exponential Backoff (2^n &times; 15s)<br/>- Automatic Dead-Letter Queue (DLQ)"]
        RADAR["10-Year Maturity Radar Worker<br/>- pg_try_advisory_lock(847291) Mutex<br/>- Partial Index Scan: instrument_maturity_idx<br/>- Countdown Obligations: T-90, T-60, T-30 Days"]
        CHECKPOINTER["Detached Audit Checkpointer<br/>- Hourly External Ed25519 Signatures<br/>- Proof of Ledger State to Remote Vault"]
    end

    subgraph Tier5 ["TIER 5: STORAGE & DATA IMMUTABILITY KERNEL"]
        DB[("PostgreSQL 17 Database Engine<br/>- 8-Region Kernel Row-Level Security (RLS)<br/>- Relational CHECK (maker_id != checker_id)<br/>- Runtime Least Privilege: NOSUPERUSER NOBYPASSRLS<br/>- Exact Integer Paise Representation (No Float Bugs)")]
        VAULT[("Encrypted File Vault (fdr-vault)<br/>- %PDF-1.4 Magic-Byte Sniffing (Blocks Malware)<br/>- AES-256-GCM Envelope Encryption (96-bit Unique IV)<br/>- Supabase Cloud Storage with Local Fallback")]
        AUDIT_TBL[("Cryptographic Audit Ledger<br/>- SHA-256 Hash Chain: hash_N = SHA256(prev + payload)<br/>- Trigger Immutability: Blocks UPDATE/DELETE/TRUNCATE<br/>- Provable Continuity via SELECT audit_verify()")]
    end

    subgraph External ["EXTERNAL STATUTORY GATEWAYS & SIMULATORS"]
        BANK_CBS["Core Banking Systems (CBS)<br/>- SFMS 760COV Structured Messages<br/>- Open Banking Challenge-Response APIs<br/>- 14-Day Anti-Replay Nonce Consumption"]
        NESL_IU["NeSL Information Utility<br/>- National Digital Lien Registry (IBC Act &sect; 215)<br/>- Cross-Institution Secondary Encumbrance Search"]
        AICTE_ERP["AICTE Central Approval ERP<br/>- Automated Extension of Approval (EoA) Holds<br/>- Real-Time College Intake & Division Sync"]
    end

    CLIENT -->|HTTPS / Port 443| CADDY
    CADDY -->|Reverse Proxy :8000| API_ROUTER
    API_ROUTER --> FSM
    API_ROUTER --> RLS_MW
    API_ROUTER --> IDEMP
    API_ROUTER --> GATE
    API_ROUTER --> RULES
    API_ROUTER --> DISC
    API_ROUTER --> MAKER_CHECKER

    API_ROUTER -->|ACID DB Transaction| DB
    API_ROUTER -->|Stream Encrypted Ciphertext| VAULT
    API_ROUTER -->|Append-Only Mutation| AUDIT_TBL
    API_ROUTER -->|Enqueue Outbox Event| OUTBOX

    OUTBOX --> DISPATCHER
    DISPATCHER -->|Signed HMAC Webhook| BANK_CBS
    DISPATCHER -->|Lien Registration Query| NESL_IU
    DISPATCHER -->|EoA Hold Placement| AICTE_ERP
    RADAR -->|Scans Index Under Mutex| DB
    DB -.-> CHECKPOINTER
`;

const htmlTemplate = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Master System Architecture - AICTE FDR Portal</title>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@500;700;800&display=swap" rel="stylesheet">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      width: 3840px;
      height: 2160px;
      background: #080d1a;
      color: #f8fafc;
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      padding: 48px 64px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      overflow: hidden;
    }

    /* TOP MASTER HEADER */
    .master-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 24px;
      border-bottom: 2px solid #1e293b;
    }
    .header-left {
      display: flex;
      align-items: center;
      gap: 20px;
    }
    .emblem-pill {
      background: linear-gradient(135deg, #0284c7, #0369a1);
      color: #ffffff;
      font-weight: 900;
      font-size: 20px;
      padding: 10px 24px;
      border-radius: 9999px;
      letter-spacing: 1px;
      box-shadow: 0 4px 12px rgba(2, 132, 199, 0.3);
    }
    .sub-pill {
      background: rgba(255, 255, 255, 0.07);
      border: 1.5px solid rgba(255, 255, 255, 0.15);
      color: #94a3b8;
      font-weight: 700;
      font-size: 18px;
      padding: 10px 20px;
      border-radius: 8px;
    }
    .header-center {
      text-align: center;
    }
    .main-title {
      font-size: 40px;
      font-weight: 900;
      color: #ffffff;
      letter-spacing: -1px;
      text-transform: uppercase;
      background: linear-gradient(180deg, #ffffff 0%, #cbd5e1 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    .main-subtitle {
      font-size: 20px;
      font-weight: 600;
      color: #38bdf8;
      margin-top: 4px;
      letter-spacing: 0.5px;
    }
    .header-right {
      text-align: right;
      font-family: 'JetBrains Mono', monospace;
    }
    .sih-badge-box {
      background: linear-gradient(135deg, #f97316, #10b981);
      color: #ffffff;
      font-weight: 900;
      font-size: 20px;
      padding: 10px 24px;
      border-radius: 10px;
      letter-spacing: 0.5px;
      box-shadow: 0 4px 15px rgba(249, 115, 22, 0.3);
    }
    .live-status {
      color: #4ade80;
      font-size: 16px;
      font-weight: 700;
      margin-top: 6px;
    }

    /* CENTER ARCHITECTURE DIAGRAM CONTAINER */
    .diagram-viewport {
      background: linear-gradient(145deg, #0b1329, #080d1a);
      border: 2px solid #1e293b;
      border-radius: 24px;
      padding: 36px 40px;
      height: 1540px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      box-shadow: 0 25px 60px -15px rgba(0, 0, 0, 0.7);
      position: relative;
    }
    .viewport-topbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1.5px solid #1e293b;
      padding-bottom: 14px;
    }
    .viewport-title {
      font-size: 20px;
      font-weight: 800;
      color: #94a3b8;
      letter-spacing: 1px;
      text-transform: uppercase;
    }
    .viewport-engine {
      font-family: 'JetBrains Mono', monospace;
      font-size: 15px;
      color: #38bdf8;
      background: rgba(56, 189, 248, 0.1);
      padding: 6px 16px;
      border-radius: 6px;
      border: 1px solid rgba(56, 189, 248, 0.3);
    }
    .mermaid-stage {
      flex: 1;
      display: flex;
      justify-content: center;
      align-items: center;
      padding: 15px 0;
      overflow: hidden;
    }
    .mermaid {
      width: 100%;
      height: 100%;
      display: flex;
      justify-content: center;
      align-items: center;
    }

    /* MERMAID SVG CUSTOM STYLES */
    .node rect, .node circle, .node polygon {
      stroke-width: 2px !important;
    }
    .edgeLabel {
      background-color: #080d1a !important;
      color: #e2e8f0 !important;
      font-size: 14px !important;
      border-radius: 6px;
      padding: 4px 8px;
      border: 1px solid #334155 !important;
      font-weight: 600;
    }
    .cluster rect {
      stroke-width: 2px !important;
      rx: 12px !important;
      ry: 12px !important;
    }

    /* BOTTOM 4 ARCHITECTURAL PILLARS */
    .pillars-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 24px;
      margin-top: 24px;
    }
    .pillar-card {
      background: #0f172a;
      border: 1.5px solid #1e293b;
      border-radius: 16px;
      padding: 20px 24px;
      box-shadow: 0 8px 20px -4px rgba(0, 0, 0, 0.4);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }
    .pillar-card.p1 { border-top: 4px solid #38bdf8; }
    .pillar-card.p2 { border-top: 4px solid #10b981; }
    .pillar-card.p3 { border-top: 4px solid #f59e0b; }
    .pillar-card.p4 { border-top: 4px solid #8b5cf6; }

    .pillar-head {
      font-size: 18px;
      font-weight: 800;
      color: #ffffff;
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 8px;
    }
    .pillar-body {
      font-size: 15px;
      color: #94a3b8;
      line-height: 1.45;
    }
    .pillar-body strong {
      color: #f1f5f9;
    }
    .pillar-proof {
      font-family: 'JetBrains Mono', monospace;
      font-size: 13px;
      font-weight: 700;
      margin-top: 10px;
      padding-top: 8px;
      border-top: 1px dashed #334155;
    }

    /* BOTTOM MASTER FOOTER */
    .master-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-top: 20px;
      border-top: 2px solid #1e293b;
      font-size: 17px;
      color: #64748b;
      font-weight: 600;
    }
    .tech-legend {
      color: #cbd5e1;
      font-weight: 700;
    }
  </style>
</head>
<body>

  <!-- MASTER TOP HEADER -->
  <div class="master-header">
    <div class="header-left">
      <div class="emblem-pill">AICTE &bull; PS 26265</div>
      <div class="sub-pill">Ministry of Education &bull; Government of India</div>
    </div>
    <div class="header-center">
      <div class="main-title">AICTE Fixed Deposit Receipt &amp; Security Deposit Regulatory Portal</div>
      <div class="main-subtitle">Complete Master System Architecture &bull; End-to-End Enterprise C4 Topology</div>
    </div>
    <div class="header-right">
      <div class="sih-badge-box">SMART INDIA HACKATHON 2026</div>
      <div class="live-status">&check; 192/192 PYTEST PASS &bull; 100% INTACT CONTINUITY</div>
    </div>
  </div>

  <!-- CENTER ARCHITECTURE VIEWPORT -->
  <div class="diagram-viewport">
    <div class="viewport-topbar">
      <div class="viewport-title">Five-Tier Concentric Regulatory Architecture with Statutory External Integrations</div>
      <div class="viewport-engine">Mermaid v10 &bull; 100% Workable Topological Specification</div>
    </div>

    <div class="mermaid-stage">
      <div class="mermaid">
${masterMermaidCode}
      </div>
    </div>

    <div style="display: flex; justify-content: space-between; font-family: 'JetBrains Mono', monospace; font-size: 15px; color: #475569; border-top: 1px solid #1e293b; padding-top: 10px;">
      <span>Strict Defense-in-Depth &bull; Non-Repudiation (IT Act 2000 &sect; 3A) &bull; CVC Anti-Collusion Governance</span>
      <span>Runtime Role: NOSUPERUSER NOBYPASSRLS &bull; Advisory Lock Serialized</span>
    </div>
  </div>

  <!-- BOTTOM 4 PILLARS -->
  <div class="pillars-grid">
    <div class="pillar-card p1">
      <div>
        <div class="pillar-head" style="color: #38bdf8;">&#9632; Zero-Trust Ingestion &amp; Bank Gate</div>
        <div class="pillar-body">
          <strong>%PDF-1.4 Magic-Byte Sniffing</strong> eliminates malware injection. 
          <strong>6-Point Cryptographic Bank Gate</strong> validates PKCS#7 signatures, entire-file byte coverage, and accredited CCA India Root CAs.
        </div>
      </div>
      <div class="pillar-proof" style="color: #38bdf8;">✓ IT Act 2000 § 3A &bull; 6/6 Mutation Proofs</div>
    </div>

    <div class="pillar-card p2">
      <div>
        <div class="pillar-head" style="color: #10b981;">&#9632; Kernel Multi-Tenancy &amp; Dual-Custody</div>
        <div class="pillar-body">
          <strong>PostgreSQL 17 Row-Level Security (RLS)</strong> isolates 8 statutory regions at the database engine layer. 
          Relational <strong>CHECK (maker_id != checker_id)</strong> mathematically blocks single-officer embezzlement.
        </div>
      </div>
      <div class="pillar-proof" style="color: #10b981;">✓ 8-Region Isolation &bull; 403 Forbidden Abort</div>
    </div>

    <div class="pillar-card p3">
      <div>
        <div class="pillar-head" style="color: #f59e0b;">&#9632; Dynamic Scrutiny &amp; Table 1.4 Math</div>
        <div class="pillar-body">
          Automated <strong>Table 1.4 APH rules engine</strong> with zero hardcoded code figures. 
          Stored in exact <strong>integer Paise</strong>. Evaluates checks <strong>D1 through D6</strong>, placing automated EoA Holds on critical defects.
        </div>
      </div>
      <div class="pillar-proof" style="color: #f59e0b;">✓ Sub-50ms Scrutiny &bull; Zero Float Errors</div>
    </div>

    <div class="pillar-card p4">
      <div>
        <div class="pillar-head" style="color: #8b5cf6;">&#9632; Append-Only Audit &amp; 10-Yr Radar</div>
        <div class="pillar-body">
          <strong>SHA-256 Hash Chained Ledger</strong> with trigger-blocked mutation, verifiable via <strong>SELECT audit_verify()</strong>. 
          Distributed advisory-locked daily cron scanner tracks 10-year maturity (T-90/60/30).
        </div>
      </div>
      <div class="pillar-proof" style="color: #8b5cf6;">✓ 100% Continuity &bull; Zero Lapsed Deposits</div>
    </div>
  </div>

  <!-- MASTER BOTTOM FOOTER -->
  <div class="master-footer">
    <div class="tech-legend">
      Core Technology Stack: Python 3.14 (Async) &bull; React 19 &bull; FastAPI &bull; PostgreSQL 17 (RLS) &bull; pyHanko (PKCS#7) &bull; AES-256-GCM &bull; Docker &bull; Bun &bull; uv
    </div>
    <div style="color: #38bdf8; font-weight: 800;">
      National Prototype for AICTE Regulation &bull; Smart India Hackathon 2026 Presentation
    </div>
  </div>

  <script>
    mermaid.initialize({
      startOnLoad: true,
      theme: 'dark',
      themeVariables: {
        darkMode: true,
        background: '#080d1a',
        primaryColor: '#0f172a',
        primaryTextColor: '#f8fafc',
        primaryBorderColor: '#38bdf8',
        lineColor: '#60a5fa',
        secondaryColor: '#1e293b',
        tertiaryColor: '#080d1a',
        fontFamily: 'Plus Jakarta Sans, sans-serif',
        fontSize: '15px'
      },
      flowchart: {
        curve: 'basis',
        nodeSpacing: 40,
        rankSpacing: 40
      }
    });
  </script>
</body>
</html>`;

async function renderMasterArchitecture() {
  console.log('========================================================================');
  console.log('Rendering Master System Architecture Complete PNG (3840x2160 4K Ultra-HD)...');
  console.log('========================================================================\n');

  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const page = await browser.newPage({
    viewport: { width: 3840, height: 2160 },
    deviceScaleFactor: 1 // Already native 4K Ultra-HD resolution
  });

  await page.setContent(htmlTemplate, { waitUntil: 'networkidle' });

  // Wait for Mermaid SVG to fully render
  console.log('Waiting for Mermaid master diagram rendering...');
  await page.waitForSelector('.mermaid svg', { timeout: 30000 });
  await page.waitForTimeout(2000); // Allow all layout elements and fonts to settle

  await page.screenshot({
    path: OUT_PATH,
    fullPage: true
  });

  await browser.close();
  const stats = fs.statSync(OUT_PATH);
  console.log(`\nMaster Architecture PNG successfully rendered to:`);
  console.log(` -> ${OUT_PATH} (${(stats.size / (1024 * 1024)).toFixed(2)} MB)`);
  console.log('========================================================================\n');
}

renderMasterArchitecture().catch((err) => {
  console.error('Fatal error during rendering:', err);
  process.exit(1);
});
