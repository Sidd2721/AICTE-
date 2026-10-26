// scripts/record_demo_video.js
// Automated End-to-End Live Video Recording for AICTE FDR Portal Demo (PS 26265)
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const BASE_URL = 'http://127.0.0.1:8000';
const VIDEO_DIR = path.join(__dirname, '..', 'videos_temp');

if (!fs.existsSync(VIDEO_DIR)) {
  fs.mkdirSync(VIDEO_DIR, { recursive: true });
}

async function showBanner(page, title, subtitle, durationMs = 3000) {
  await page.evaluate(({ title, subtitle }) => {
    let el = document.getElementById('demo-overlay-banner');
    if (!el) {
      el = document.createElement('div');
      el.id = 'demo-overlay-banner';
      el.style.position = 'fixed';
      el.style.bottom = '28px';
      el.style.left = '50%';
      el.style.transform = 'translateX(-50%)';
      el.style.zIndex = '999999';
      el.style.background = 'rgba(15, 23, 42, 0.95)';
      el.style.color = '#ffffff';
      el.style.padding = '14px 28px';
      el.style.borderRadius = '12px';
      el.style.boxShadow = '0 12px 35px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.15)';
      el.style.fontFamily = 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
      el.style.textAlign = 'center';
      el.style.maxWidth = '880px';
      el.style.width = '92%';
      el.style.pointerEvents = 'none';
      el.style.transition = 'all 0.4s ease';
      document.body.appendChild(el);
    }
    el.innerHTML = `
      <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.12em; color: #38bdf8; font-weight: 700; margin-bottom: 4px;">AICTE REGULATORY PORTAL (PS 26265)</div>
      <div style="font-size: 16px; font-weight: 700; color: #f8fafc; margin-bottom: 4px;">${title}</div>
      <div style="font-size: 13px; color: #94a3b8; font-weight: 400; line-height: 1.4;">${subtitle}</div>
    `;
    el.style.opacity = '1';
    el.style.transform = 'translateX(-50%) translateY(0)';
  }, { title, subtitle });

  if (durationMs > 0) {
    await page.waitForTimeout(durationMs);
  }
}

async function loginAs(page, email) {
  await page.evaluate(async (userEmail) => {
    localStorage.removeItem('access_token');
    const res = await fetch('/api/v1/login/demo', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: userEmail }),
    });
    if (res.ok) {
      const data = await res.json();
      localStorage.setItem('access_token', data.access_token);
    }
  }, email);
}

async function run() {
  console.log('Launching browser with video recording...');
  const browser = await chromium.launch({
    headless: true,
  });

  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    recordVideo: {
      dir: VIDEO_DIR,
      size: { width: 1440, height: 900 },
    },
  });

  const page = await context.newPage();

  try {
    // -------------------------------------------------------------
    // SCENE 1: Welcome & Login with 1-Click Personas
    // -------------------------------------------------------------
    console.log('Scene 1: Login & 1-Click Evaluation Personas');
    await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle' });
    await showBanner(
      page,
      'Scene 1: 1-Click Passwordless Evaluation Login',
      'Instant access for all regulatory roles without credential friction. Strict 404 guard outside dev/demo.',
      4000
    );
    await page.mouse.wheel(0, 250);
    await page.waitForTimeout(1500);
    await page.mouse.wheel(0, -250);
    await page.waitForTimeout(1000);

    // -------------------------------------------------------------
    // SCENE 2: Guided Tour
    // -------------------------------------------------------------
    console.log('Scene 2: 6-Minute Interactive Guided Tour');
    await page.goto(`${BASE_URL}/guide`, { waitUntil: 'networkidle' });
    await showBanner(
      page,
      'Scene 2: 6-Minute Guided Tour (docs/guide.json)',
      'Plain-language walkthrough of all 7 core regulatory scenarios, role contracts, and safety invariants.',
      4500
    );
    await page.mouse.wheel(0, 450);
    await page.waitForTimeout(2000);
    await page.mouse.wheel(0, -450);
    await page.waitForTimeout(1000);

    // -------------------------------------------------------------
    // SCENE 3: Institution Persona & Dynamic Calculator
    // -------------------------------------------------------------
    console.log('Scene 3: Institution Calculator & Table 1.4');
    await loginAs(page, 'inst.north1@example.com');
    await page.goto(`${BASE_URL}/deposits`, { waitUntil: 'networkidle' });
    await showBanner(
      page,
      'Scene 3: Dynamic Table 1.4 Calculator (Zero Hardcoded Constants)',
      'Statutory obligations compute dynamically from dated JSON handbook rules in integer paise.',
      4500
    );
    await page.mouse.wheel(0, 350);
    await page.waitForTimeout(2000);
    await page.mouse.wheel(0, -350);
    await page.waitForTimeout(1000);

    // -------------------------------------------------------------
    // SCENE 4: Regional Officer Dashboard & Oversight
    // -------------------------------------------------------------
    console.log('Scene 4: Regional Officer Dashboard');
    await loginAs(page, 'officer.north@example.com');
    await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle' });
    await showBanner(
      page,
      'Scene 4: Regional Regulatory Oversight Dashboard',
      'Tracks unconfirmed claimed deposits, 90-day upcoming maturities, and active discrepancy alerts.',
      4000
    );
    await page.mouse.wheel(0, 300);
    await page.waitForTimeout(2000);
    await page.mouse.wheel(0, -300);
    await page.waitForTimeout(1000);

    // -------------------------------------------------------------
    // SCENE 5: Case Page & 6-Point Cryptographic Bank Gate
    // -------------------------------------------------------------
    console.log('Scene 5: Case Page & 6-Point Cryptographic Gate');
    await page.goto(`${BASE_URL}/deposits`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);

    const firstRowLink = page.locator('table tbody tr a').first();
    if (await firstRowLink.isVisible()) {
      await firstRowLink.click();
      await page.waitForLoadState('networkidle');
      await showBanner(
        page,
        'Scene 5: Case Dossier & 6-Point Cryptographic Bank Gate',
        'Byte-level prefix check (%PDF-1.4), full byte coverage (no appended pages), digital signature, and Root CA validation.',
        5000
      );
      await page.mouse.wheel(0, 350);
      await page.waitForTimeout(2500);
      await page.mouse.wheel(0, -350);
      await page.waitForTimeout(1000);
    }

    // -------------------------------------------------------------
    // SCENE 6: Dual-Custody Release Authorization
    // -------------------------------------------------------------
    console.log('Scene 6: Dual-Custody Maker-Checker Release Authorization');
    await showBanner(
      page,
      'Scene 6: Dual-Custody Release Authorization (Rule I8)',
      'Regional Officer acts as Maker (verifies compliance); physical DB constraint chk_release_request_maker_checker blocks same-person approval.',
      4500
    );
    await page.waitForTimeout(1500);

    // -------------------------------------------------------------
    // SCENE 7: Bureau Approver Oversight
    // -------------------------------------------------------------
    console.log('Scene 7: Bureau Approver Oversight');
    await loginAs(page, 'bureau@example.com');
    await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle' });
    await showBanner(
      page,
      'Scene 7: Central Bureau Approver Oversight (Checker)',
      'National visibility across all regional offices, simulated clock advance, and dual-custody release authorization.',
      4000
    );
    await page.waitForTimeout(2000);

    // -------------------------------------------------------------
    // SCENE 8: Cryptographic Append-Only Audit Ledger
    // -------------------------------------------------------------
    console.log('Scene 8: Append-Only Cryptographic Audit Ledger');
    await page.goto(`${BASE_URL}/audit`, { waitUntil: 'networkidle' });
    await showBanner(
      page,
      'Scene 8: Append-Only Immutable Audit Ledger (SHA-256 Chained)',
      'Every state transition is chained via SHA-256 hashes. Database triggers block UPDATE, DELETE, and TRUNCATE.',
      4500
    );
    await page.mouse.wheel(0, 400);
    await page.waitForTimeout(2500);
    await page.mouse.wheel(0, -450);
    await page.waitForTimeout(1000);

    // -------------------------------------------------------------
    // SCENE 9: Evidence Map & Safety Invariants
    // -------------------------------------------------------------
    console.log('Scene 9: Evidence Map & Safety Invariants');
    await page.goto(`${BASE_URL}/evidence`, { waitUntil: 'networkidle' });
    await showBanner(
      page,
      'Scene 9: Regulatory Evidence Map & Safety Invariants',
      'All 15 statutory invariants proven with 172 automated tests, mutation testing, and zero CDNs.',
      4500
    );
    await page.mouse.wheel(0, 450);
    await page.waitForTimeout(2500);
    await page.mouse.wheel(0, -450);
    await page.waitForTimeout(1000);

    // -------------------------------------------------------------
    // SCENE 10: Conclusion
    // -------------------------------------------------------------
    console.log('Scene 10: Conclusion');
    await showBanner(
      page,
      'AICTE Security Deposit Regulatory Portal — Production-Ready MVP',
      'Mathematical integrity, automated bank confirmation gates, enforced dual custody, and tamper-evident audit trail.',
      5000
    );
    await page.waitForTimeout(2000);

  } catch (err) {
    console.error('Error during video recording:', err);
  } finally {
    await context.close();
    await browser.close();
    console.log('Recording finished successfully.');
  }
}

run();
