// scripts/generate_slide_png.js
// Renders the complete, upgraded, production-grade 1920x1080 Slide 4 for SIH 2026
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const OUT_PATH = path.join(__dirname, '..', 'diagrams', 'png', 'slide4_technical_approach_remade.png');

const htmlContent = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Technical Approach - AICTE FDR Portal</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      width: 1920px;
      height: 1080px;
      background: #f8fafc;
      font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
      color: #0f172a;
      overflow: hidden;
      padding: 36px 48px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }

    /* TOP HEADER */
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 12px;
      border-bottom: 2px solid #e2e8f0;
    }
    .sentinel-pill {
      background: #ffffff;
      border: 1.5px solid #0284c7;
      padding: 6px 18px;
      border-radius: 9999px;
      font-weight: 800;
      font-size: 14px;
      color: #0369a1;
      letter-spacing: 0.5px;
      box-shadow: 0 2px 4px rgba(2, 132, 199, 0.1);
    }
    .title-box {
      text-align: center;
    }
    .main-title {
      font-size: 28px;
      font-weight: 800;
      color: #0f172a;
      letter-spacing: -0.5px;
      text-transform: uppercase;
    }
    .subtitle {
      font-size: 15px;
      font-weight: 600;
      color: #475569;
      margin-top: 2px;
    }
    .sih-badge {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .sih-logo-box {
      background: linear-gradient(135deg, #f97316, #10b981);
      color: white;
      font-weight: 900;
      padding: 6px 14px;
      border-radius: 8px;
      font-size: 14px;
      letter-spacing: 0.5px;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }

    /* SECTION 1: SIX STAGE LIFECYCLE */
    .lifecycle-grid {
      display: grid;
      grid-template-columns: repeat(6, 1fr);
      gap: 14px;
      margin-top: 14px;
    }
    .stage-card {
      background: #ffffff;
      border-radius: 12px;
      padding: 12px 14px;
      border: 1.5px solid #e2e8f0;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
      position: relative;
      display: flex;
      flex-direction: column;
    }
    .stage-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 6px;
    }
    .stage-num {
      width: 26px;
      height: 26px;
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 12px;
      color: #ffffff;
    }
    .stage-title {
      font-size: 14px;
      font-weight: 800;
      color: #1e293b;
    }
    .stage-badge {
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      padding: 2px 6px;
      border-radius: 4px;
      margin-bottom: 6px;
      display: inline-block;
      width: fit-content;
    }
    .stage-body {
      font-size: 11px;
      color: #334155;
      line-height: 1.35;
    }
    .stage-body strong {
      color: #0f172a;
    }
    .sub-engine {
      margin-top: 6px;
      padding-top: 6px;
      border-top: 1px dashed #cbd5e1;
      font-size: 10px;
      font-weight: 700;
    }

    /* STAGE ACCENT COLORS */
    .c-claim .stage-num { background: #2563eb; }
    .c-claim .stage-badge { background: #dbeafe; color: #1d4ed8; }
    .c-claim { border-top: 4px solid #2563eb; }

    .c-confirm .stage-num { background: #dc2626; }
    .c-confirm .stage-badge { background: #fee2e2; color: #b91c1c; }
    .c-confirm { border-top: 4px solid #dc2626; }

    .c-scrutinize .stage-num { background: #d97706; }
    .c-scrutinize .stage-badge { background: #fef3c7; color: #b45309; }
    .c-scrutinize { border-top: 4px solid #d97706; }

    .c-monitor .stage-num { background: #059669; }
    .c-monitor .stage-badge { background: #d1fae5; color: #047857; }
    .c-monitor { border-top: 4px solid #059669; }

    .c-maker .stage-num { background: #7c3aed; }
    .c-maker .stage-badge { background: #ede9fe; color: #6d28d9; }
    .c-maker { border-top: 4px solid #7c3aed; }

    .c-checker .stage-num { background: #0284c7; }
    .c-checker .stage-badge { background: #e0f2fe; color: #0369a1; }
    .c-checker { border-top: 4px solid #0284c7; }

    /* SECTION 2: SYSTEM ARCHITECTURE & RESILIENCE */
    .arch-container {
      background: #ffffff;
      border: 1.5px solid #cbd5e1;
      border-radius: 14px;
      padding: 14px 18px;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
      margin-top: 10px;
    }
    .section-label {
      font-size: 13px;
      font-weight: 800;
      color: #1e293b;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 10px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .arch-flex {
      display: grid;
      grid-template-columns: 1.1fr auto 1.3fr auto 1.4fr auto 1.2fr auto 1.2fr;
      align-items: center;
      gap: 8px;
    }
    .arch-node {
      background: #f8fafc;
      border: 1.5px solid #cbd5e1;
      border-radius: 10px;
      padding: 10px 12px;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.03);
    }
    .arch-node-title {
      font-size: 12px;
      font-weight: 800;
      color: #0f172a;
      display: flex;
      align-items: center;
      gap: 6px;
      margin-bottom: 4px;
    }
    .arch-node-desc {
      font-size: 10px;
      color: #475569;
      line-height: 1.35;
    }
    .arch-node-desc strong {
      color: #1e293b;
    }
    .arrow-divider {
      color: #64748b;
      font-size: 16px;
      font-weight: 900;
      text-align: center;
    }

    /* SECTION 3: INTEGRATIONS & DEFENSE LAB */
    .bottom-grid {
      display: grid;
      grid-template-columns: 2.2fr 1fr;
      gap: 14px;
      margin-top: 10px;
    }
    .integration-box {
      background: #f1f5f9;
      border: 1.5px solid #94a3b8;
      border-radius: 14px;
      padding: 12px 18px;
    }
    .integration-flex {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 12px;
      margin-top: 8px;
    }
    .int-card {
      background: #ffffff;
      border: 1px solid #cbd5e1;
      border-radius: 8px;
      padding: 8px 10px;
      display: flex;
      flex-direction: column;
      justify-content: center;
    }
    .int-title {
      font-size: 11px;
      font-weight: 800;
      color: #1e293b;
    }
    .int-sub {
      font-size: 9.5px;
      color: #64748b;
      margin-top: 2px;
    }
    .fraud-lab-box {
      background: #0f172a;
      color: #f8fafc;
      border-radius: 14px;
      padding: 12px 16px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      border: 1.5px solid #334155;
      box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.2);
    }
    .fraud-title {
      font-size: 12px;
      font-weight: 800;
      color: #38bdf8;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .fraud-desc {
      font-size: 10px;
      color: #94a3b8;
      line-height: 1.35;
      margin: 4px 0;
    }
    .fraud-proof {
      font-family: 'JetBrains Mono', monospace;
      font-size: 9.5px;
      color: #4ade80;
      background: rgba(74, 222, 128, 0.1);
      padding: 4px 8px;
      border-radius: 4px;
      border: 1px solid rgba(74, 222, 128, 0.3);
    }

    /* FOOTER */
    .footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-top: 10px;
      border-top: 1.5px solid #e2e8f0;
      font-size: 11px;
      color: #475569;
    }
    .tech-strip {
      font-weight: 700;
      color: #1e293b;
    }
  </style>
</head>
<body>

  <!-- HEADER -->
  <div class="header">
    <div class="sentinel-pill">Sentinel Hubz</div>
    <div class="title-box">
      <div class="main-title">TECHNICAL APPROACH</div>
      <div class="subtitle">Multi-Tier AICTE FDR Regulatory Architecture with Defense-in-Depth Security</div>
    </div>
    <div class="sih-badge">
      <div class="sih-logo-box">SIH 2026 • PS 26265</div>
    </div>
  </div>

  <!-- ZONE 1: SIX STAGE LIFECYCLE (6 DETAILED CARDS) -->
  <div class="lifecycle-grid">
    
    <!-- 01 CLAIM -->
    <div class="stage-card c-claim">
      <div class="stage-header">
        <div class="stage-num">01</div>
        <div class="stage-title">Claim</div>
      </div>
      <div class="stage-badge">Institution (Maker)</div>
      <div class="stage-body">
        College submits FDR certificate scan, bank IFSC, and tenure. 
        <strong>Sniffs first 8 bytes (%PDF-1.4)</strong> to block disguised malware.
        Calculates statutory coverage in exact <strong>integer Paise</strong>.
      </div>
      <div class="sub-engine" style="color: #1d4ed8;">AES-256-GCM Vault Ingestion</div>
    </div>

    <!-- 02 CONFIRM -->
    <div class="stage-card c-confirm">
      <div class="stage-header">
        <div class="stage-num">02</div>
        <div class="stage-title">Confirm</div>
      </div>
      <div class="stage-badge">Zero-Trust Gate</div>
      <div class="stage-body">
        Validates bank response via <strong>6-Point Cryptographic Gate</strong> (pyHanko).
        Asserts <strong>Entire-File Coverage</strong> (blocks trailing pages) & CCA Root CA 
        (<strong>IT Act 2000 § 3A</strong>). Consumes 14-day anti-replay nonce.
      </div>
      <div class="sub-engine" style="color: #b91c1c;">State: Active 10-Yr Confirmed</div>
    </div>

    <!-- 03 SCRUTINIZE -->
    <div class="stage-card c-scrutinize">
      <div class="stage-header">
        <div class="stage-num">03</div>
        <div class="stage-title">Scrutinize</div>
      </div>
      <div class="stage-badge">Dynamic Rules</div>
      <div class="stage-body">
        Evaluates dated <strong>Table 1.4 APH Slabs</strong> with zero hardcoded code numbers.
        Triages checks <strong>D1–D6</strong> (Amount, Tenure, Lien, Duplicates).
        Critical flags trigger automatic <strong>EoA Holds</strong>.
      </div>
      <div class="sub-engine" style="color: #b45309;">Waiver Governance Subsystem</div>
    </div>

    <!-- 04 MONITOR -->
    <div class="stage-card c-monitor">
      <div class="stage-header">
        <div class="stage-num">04</div>
        <div class="stage-title">Monitor</div>
      </div>
      <div class="stage-badge">Distributed Radar</div>
      <div class="stage-body">
        Daily cron worker runs under <strong>pg_advisory_xact_lock</strong>.
        Scans partial index on 10-year horizon, issuing automated countdown alerts at 
        <strong>T-90, T-60, and T-30 days</strong>. Auto-matures at T-0.
      </div>
      <div class="sub-engine" style="color: #047857;">Maturity Obligation Engine</div>
    </div>

    <!-- 05 MAKER -->
    <div class="stage-card c-maker">
      <div class="stage-header">
        <div class="stage-num">05</div>
        <div class="stage-title">Maker</div>
      </div>
      <div class="stage-badge">Regional Officer</div>
      <div class="stage-body">
        Regional Officer inspects physical college operations and bank lien documents.
        Validates release checklist and records <strong>verified_by = Maker.id</strong>.
        Cannot unilaterally approve release.
      </div>
      <div class="sub-engine" style="color: #6d28d9;">Multi-Point Statutory Audit</div>
    </div>

    <!-- 06 CHECKER -->
    <div class="stage-card c-checker">
      <div class="stage-header">
        <div class="stage-num">06</div>
        <div class="stage-title">Checker</div>
      </div>
      <div class="stage-badge">Bureau Approver</div>
      <div class="stage-body">
        Central Bureau approves release. <strong>PostgreSQL constraint strictly enforces maker_id != checker_id</strong>.
        Issues an offline-verifiable, digitally signed <strong>RS256 Encashment Receipt</strong>.
      </div>
      <div class="sub-engine" style="color: #0369a1;">CVC Anti-Collusion Boundary</div>
    </div>

  </div>

  <!-- ZONE 2: MIDDLE SYSTEM ARCHITECTURE (CONNECTED 5-TIER PIPELINE) -->
  <div class="arch-container">
    <div class="section-label">
      <span>Core Defense-in-Depth System Architecture</span>
      <span style="font-size: 11px; font-weight: 700; color: #0284c7;">ACID TRANSACTION BOUNDARY &bull; SECURE ASYNCHRONOUS PIPELINE</span>
    </div>
    <div class="arch-flex">
      
      <!-- NODE 1 -->
      <div class="arch-node">
        <div class="arch-node-title">
          <span style="color: #2563eb;">&#9632;</span> Frontend SPA
        </div>
        <div class="arch-node-desc">
          <strong>React 19 &bull; TypeScript &bull; Bun</strong><br/>
          5-Persona 1-Click Role Switcher<br/>
          WCAG 2.1 AA Accessible UI Primitives
        </div>
      </div>

      <div class="arrow-divider">&rarr;</div>

      <!-- NODE 2 -->
      <div class="arch-node">
        <div class="arch-node-title">
          <span style="color: #0d9488;">&#9632;</span> FastAPI Gateway
        </div>
        <div class="arch-node-desc">
          <strong>Python 3.14 &bull; Uvicorn (uvloop)</strong><br/>
          Sub-15ms P99 Latency &bull; Pydantic v2<br/>
          Sliding-Window IP Rate Limiting
        </div>
      </div>

      <div class="arrow-divider">&rarr;</div>

      <!-- NODE 3 -->
      <div class="arch-node">
        <div class="arch-node-title">
          <span style="color: #0284c7;">&#9632;</span> PostgreSQL 17 (DB)
        </div>
        <div class="arch-node-desc">
          <strong>8-Region Kernel RLS Isolation</strong><br/>
          CHECK (maker_id != checker_id)<br/>
          Distributed Advisory Lock Concurrency
        </div>
      </div>

      <div class="arrow-divider">&rarr;</div>

      <!-- NODE 4 -->
      <div class="arch-node">
        <div class="arch-node-title">
          <span style="color: #d97706;">&#9632;</span> Encrypted Vault
        </div>
        <div class="arch-node-desc">
          <strong>AES-256-GCM Envelope Cipher</strong><br/>
          %PDF-1.4 Magic-Byte Anti-Malware<br/>
          Private Cloud Bucket (fdr-vault)
        </div>
      </div>

      <div class="arrow-divider">&rarr;</div>

      <!-- NODE 5 -->
      <div class="arch-node">
        <div class="arch-node-title">
          <span style="color: #dc2626;">&#9632;</span> Audit Ledger
        </div>
        <div class="arch-node-desc">
          <strong>SHA-256 Hash Chained Logs</strong><br/>
          Trigger-Blocked UPDATE/DELETE<br/>
          Provable: SELECT audit_verify()
        </div>
      </div>

    </div>
  </div>

  <!-- ZONE 3: INTEGRATION POINTS & BREAK-ME FRAUD LAB -->
  <div class="bottom-grid">
    
    <!-- LEFT: INTEGRATIONS + OUTBOX -->
    <div class="integration-box">
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <span style="font-size: 12px; font-weight: 800; color: #1e293b; text-transform: uppercase;">
          Statutory Integrations via Transactional Outbox (Guaranteed Delivery)
        </span>
        <span style="font-size: 10px; font-weight: 700; color: #64748b;">
          HMAC-SHA256 Webhooks &bull; Exponential Backoff (2^n &times; 15s)
        </span>
      </div>
      <div class="integration-flex">
        <div class="int-card">
          <div class="int-title">Core Banking Systems (CBS)</div>
          <div class="int-sub">SFMS 760COV & Bank API Gateways</div>
        </div>
        <div class="int-card">
          <div class="int-title">NeSL Information Utility (IU)</div>
          <div class="int-sub">National Digital Lien Registry (IBC &sect; 215)</div>
        </div>
        <div class="int-card">
          <div class="int-title">AICTE Central Approval ERP</div>
          <div class="int-sub">Automated Extension of Approval (EoA) Holds</div>
        </div>
      </div>
    </div>

    <!-- RIGHT: BREAK-ME FRAUD LAB -->
    <div class="fraud-lab-box">
      <div>
        <div class="fraud-title">
          <span>&#9733;</span> Break-Me Fraud Lab &amp; Verification
        </div>
        <div class="fraud-desc">
          Synthetically attacked with 6 fraud vectors (appended trailing bytes, forged certificates, replay nonces). 100% rejection rate confirmed.
        </div>
      </div>
      <div class="fraud-proof">
        &check; 192/192 Backend Tests &bull; 0 Biome Errors &bull; 100% Continuity
      </div>
    </div>

  </div>

  <!-- FOOTER -->
  <div class="footer">
    <div class="tech-strip">
      Technology: Python 3.14 &bull; React 19 &bull; FastAPI &bull; PostgreSQL 17 (RLS) &bull; pyHanko (PKCS#7) &bull; AES-256-GCM &bull; Docker
    </div>
    <div style="font-size: 11px; font-weight: 700; color: #0284c7;">
      AICTE PS 26265 &bull; Smart India Hackathon 2026 Presentation
    </div>
  </div>

</body>
</html>`;

async function renderSlide() {
  console.log('Rendering 1920x1080 high-resolution presentation slide...');
  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const page = await browser.newPage({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 2 // 2x Retina presentation quality (3840 x 2160 pixels)
  });

  await page.setContent(htmlContent, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000); // Allow fonts to load cleanly

  await page.screenshot({
    path: OUT_PATH,
    fullPage: true
  });

  await browser.close();
  const stats = fs.statSync(OUT_PATH);
  console.log(`\nSlide successfully rendered to: ${OUT_PATH} (${(stats.size / 1024).toFixed(1)} KB)`);
}

renderSlide().catch((err) => {
  console.error('Fatal rendering error:', err);
  process.exit(1);
});
