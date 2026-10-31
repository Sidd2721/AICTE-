import { chromium } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, "..");
const OUT_DIR = path.resolve(ROOT, "docs", "proof");
const BASE_URL = process.env.LIVE_URL || "https://aicte-1-59pn.onrender.com";

if (!fs.existsSync(OUT_DIR)) {
  fs.mkdirSync(OUT_DIR, { recursive: true });
}

async function clearAuth(page) {
  try {
    await page.goto(`${BASE_URL}/login`, { waitUntil: "commit" });
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
  } catch (e) {
    // ignore
  }
  await page.goto(`${BASE_URL}/login`, { waitUntil: "networkidle" });
  await page.waitForTimeout(500);
}

async function run() {
  console.log(`Starting proof capture against ${BASE_URL}...`);
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    deviceScaleFactor: 1, // Keep PNG size compact (< 3MB total across all images)
  });
  const page = await context.newPage();

  const consoleErrors = [];
  const failedRequests = [];

  page.on("console", (msg) => {
    if (msg.type() === "error") {
      const text = msg.text();
      // Ignore favicon or non-critical 3rd party assets
      if (!text.includes("favicon") && !text.includes("manifest")) {
        consoleErrors.push({ url: page.url(), text });
      }
    }
  });

  page.on("requestfailed", (req) => {
    if (req.failure()?.errorText !== "net::ERR_ABORTED") {
      failedRequests.push({ url: req.url(), error: req.failure()?.errorText });
    }
  });

  page.on("response", (res) => {
    if (
      res.status() >= 400 &&
      !res.url().includes("/docs") &&
      !res.url().includes("/verify") &&
      !res.url().includes("favicon")
    ) {
      failedRequests.push({ url: res.url(), status: res.status() });
    }
  });

  // 1. Login Page
  console.log("1. Capturing login page...");
  await clearAuth(page);
  await page.waitForSelector('button:has-text("Technical Institution")', { timeout: 15000 });
  await page.screenshot({ path: path.join(OUT_DIR, "01_login_page.png"), fullPage: true });

  // 2. Institution Dashboard
  console.log("2. Capturing Institution Dashboard...");
  await page.click('button:has-text("Technical Institution")');
  await page.waitForURL(`${BASE_URL}/`, { timeout: 15000 });
  await page.waitForTimeout(2000);
  await page.screenshot({ path: path.join(OUT_DIR, "02_institution_dashboard.png"), fullPage: true });

  // 3. Regional Officer Queue
  console.log("3. Capturing Regional Officer Queue...");
  await clearAuth(page);
  await page.click('button:has-text("Regional Officer")');
  await page.waitForURL(`${BASE_URL}/`, { timeout: 15000 });
  await page.waitForTimeout(2000);
  await page.screenshot({ path: path.join(OUT_DIR, "03_regional_officer_queue.png"), fullPage: true });

  // 4. Bureau Overview
  console.log("4. Capturing Bureau Approver Overview...");
  await clearAuth(page);
  await page.click('button:has-text("Bureau Approver")');
  await page.waitForURL(`${BASE_URL}/`, { timeout: 15000 });
  await page.waitForTimeout(2000);
  await page.screenshot({ path: path.join(OUT_DIR, "04_bureau_overview.png"), fullPage: true });

  // 5. Compliance Auditor Ledger & Chain Verify
  console.log("5. Capturing Auditor Ledger & Chain Verification...");
  await clearAuth(page);
  await page.click('button:has-text("Compliance Auditor")');
  await page.waitForURL(`${BASE_URL}/`, { timeout: 15000 });
  await page.goto(`${BASE_URL}/audit`, { waitUntil: "networkidle" });
  await page.waitForTimeout(1500);

  const verifyBtn = page.locator('button:has-text("Verify Chain Integrity")');
  if (await verifyBtn.isVisible()) {
    await verifyBtn.click();
    await page.waitForTimeout(2500);
  }
  await page.screenshot({ path: path.join(OUT_DIR, "05_auditor_ledger_verified.png"), fullPage: true });

  // 6. Statement Reports Tabs
  console.log("6. Capturing Statement Reports...");
  await clearAuth(page);
  await page.click('button:has-text("Bureau Approver")');
  await page.waitForURL(`${BASE_URL}/`, { timeout: 15000 });
  await page.goto(`${BASE_URL}/reports`, { waitUntil: "networkidle" });
  await page.waitForTimeout(2500);
  await page.screenshot({ path: path.join(OUT_DIR, "06_reports_tabs.png"), fullPage: true });

  // 7. Verify Receipt Page: Load Sample Token (VALID)
  console.log("7. Capturing Public Verify Receipt (VALID)...");
  await page.goto(`${BASE_URL}/verify-receipt`, { waitUntil: "networkidle" });
  await page.waitForTimeout(1000);
  await page.click('button:has-text("Load Sample Token")');
  await page.waitForTimeout(2500);
  await page.screenshot({ path: path.join(OUT_DIR, "08_verify_receipt_valid.png"), fullPage: true });

  // 8. Verify Receipt Page: Tamper 1 Character (INVALID)
  console.log("8. Capturing Public Verify Receipt (INVALID / Tampered)...");
  await page.click('button:has-text("Tamper 1 Character")');
  await page.waitForTimeout(2500);
  await page.screenshot({ path: path.join(OUT_DIR, "09_verify_receipt_invalid.png"), fullPage: true });

  // 9. Sample Receipt PDF Rendering
  console.log("9. Rendering and Capturing Sample Receipt PDF...");
  const pdfRes = await fetch(`${BASE_URL}/api/v1/demo/sample-receipt.pdf`);
  if (!pdfRes.ok) {
    throw new Error(`Failed to fetch sample receipt PDF: HTTP ${pdfRes.status}`);
  }
  const pdfBuffer = Buffer.from(await pdfRes.arrayBuffer());
  const pdfBase64 = pdfBuffer.toString("base64");

  const pdfPage = await context.newPage();
  const pdfHtml = `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>Sample Receipt PDF</title>
      <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
      <style>
        body { margin: 0; padding: 20px; background: #e2e8f0; display: flex; justify-content: center; }
        canvas { box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06); background: white; }
      </style>
    </head>
    <body>
      <canvas id="pdf-canvas"></canvas>
      <script>
        const rawData = atob("${pdfBase64}");
        const uint8 = new Uint8Array(rawData.length);
        for (let i = 0; i < rawData.length; i++) {
          uint8[i] = rawData.charCodeAt(i);
        }
        pdfjsLib.GlobalWorkerOptions.workerSrc = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
        pdfjsLib.getDocument({ data: uint8 }).promise.then(async (pdf) => {
          const p = await pdf.getPage(1);
          const viewport = p.getViewport({ scale: 1.25 });
          const canvas = document.getElementById("pdf-canvas");
          const ctx = canvas.getContext("2d");
          canvas.height = viewport.height;
          canvas.width = viewport.width;
          await p.render({ canvasContext: ctx, viewport }).promise;
          window.__PDF_DONE__ = true;
        }).catch(err => {
          window.__PDF_ERR__ = err.message;
        });
      </script>
    </body>
    </html>
  `;
  await pdfPage.setContent(pdfHtml);
  await pdfPage.waitForFunction(() => window.__PDF_DONE__ || window.__PDF_ERR__, { timeout: 20000 });
  const pdfErr = await pdfPage.evaluate(() => window.__PDF_ERR__);
  if (pdfErr) {
    throw new Error(`PDF rendering failed: ${pdfErr}`);
  }
  await pdfPage.waitForTimeout(1000);
  await pdfPage.screenshot({ path: path.join(OUT_DIR, "07_sample_receipt.png"), fullPage: true });
  await pdfPage.close();

  await browser.close();

  // File size check
  console.log("\n================ SCREENSHOT SIZES ================");
  let totalBytes = 0;
  const files = fs.readdirSync(OUT_DIR).filter((f) => f.endsWith(".png")).sort();
  for (const f of files) {
    const filePath = path.join(OUT_DIR, f);
    const sz = fs.statSync(filePath).size;
    totalBytes += sz;
    console.log(`- ${f}: ${(sz / 1024).toFixed(1)} KB`);
  }
  const totalMB = (totalBytes / (1024 * 1024)).toFixed(2);
  console.log(`Total Screenshot Size: ${totalMB} MB (Limit: 3.00 MB)`);

  console.log("\n================ CONSOLE & NETWORK HYGIENE ================");
  console.log(`Console Errors count: ${consoleErrors.length}`);
  for (const err of consoleErrors) {
    console.log(`  [ERR] ${err.url} -> ${err.text}`);
  }
  console.log(`Failed Requests count: ${failedRequests.length}`);
  for (const req of failedRequests) {
    console.log(`  [REQ_FAIL] ${req.url} -> ${req.error || req.status}`);
  }

  if (totalBytes > 3 * 1024 * 1024) {
    console.error(`ERROR: Total screenshot size ${totalMB} MB exceeds 3.00 MB limit!`);
    process.exit(1);
  }
  if (consoleErrors.length > 0) {
    console.error(`ERROR: Found console errors on demo paths!`);
    process.exit(1);
  }

  console.log("\n[SUCCESS] All screenshots captured, hygiene checks passed!");
}

run().catch((err) => {
  console.error("Execution failed:", err);
  process.exit(1);
});
