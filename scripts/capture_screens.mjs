import { chromium } from "@playwright/test"
import fs from "node:fs"
import path from "node:path"

const OUT_DIR = path.resolve("..", "docs", "screens")
if (!fs.existsSync(OUT_DIR)) {
  fs.mkdirSync(OUT_DIR, { recursive: true })
}

async function capture() {
  const browser = await chromium.launch({ headless: true })
  
  // 1. Desktop context (1440x900)
  const desktopCtx = await browser.newContext({
    viewport: { width: 1440, height: 900 },
  })
  const page = await desktopCtx.newPage()

  console.log("Navigating to login...")
  await page.goto("http://localhost:8000/login", { waitUntil: "networkidle" })
  await page.screenshot({ path: path.join(OUT_DIR, "01_login_desktop.png") })

  // Tour Guide (Public)
  console.log("Navigating to tour guide...")
  await page.goto("http://localhost:8000/guide", { waitUntil: "networkidle" })
  await page.screenshot({ path: path.join(OUT_DIR, "02_guide_tour_desktop.png") })

  // Perform login
  await page.goto("http://localhost:8000/login", { waitUntil: "networkidle" })
  await page.fill('input[type="email"]', "officer.north@example.com")
  await page.fill('input[type="password"]', "changethis")
  await page.click('button[type="submit"]')
  await page.waitForURL("http://localhost:8000/", { timeout: 10000 })
  await page.waitForTimeout(1000)

  // Dashboard
  console.log("Capturing Dashboard...")
  await page.screenshot({ path: path.join(OUT_DIR, "03_dashboard_desktop.png") })

  // Deposits & Calculator
  console.log("Capturing Deposits...")
  await page.goto("http://localhost:8000/deposits", { waitUntil: "networkidle" })
  await page.screenshot({ path: path.join(OUT_DIR, "04_deposits_calculator_desktop.png") })

  // Audit Ledger
  console.log("Capturing Audit Ledger...")
  await page.goto("http://localhost:8000/audit", { waitUntil: "networkidle" })
  await page.screenshot({ path: path.join(OUT_DIR, "05_audit_ledger_desktop.png") })

  // Evidence Map
  console.log("Capturing Evidence Map...")
  await page.goto("http://localhost:8000/evidence", { waitUntil: "networkidle" })
  await page.screenshot({ path: path.join(OUT_DIR, "06_evidence_map_desktop.png") })

  await desktopCtx.close()

  // 2. Mobile Context (390x844 - iPhone 14 / modern smartphone)
  const mobileCtx = await browser.newContext({
    viewport: { width: 390, height: 844 },
    isMobile: true,
  })
  const mobilePage = await mobileCtx.newPage()

  console.log("Capturing Mobile views...")
  await mobilePage.goto("http://localhost:8000/guide", { waitUntil: "networkidle" })
  await mobilePage.screenshot({ path: path.join(OUT_DIR, "07_guide_tour_mobile_390px.png") })

  // Mobile login & dashboard
  await mobilePage.goto("http://localhost:8000/login", { waitUntil: "networkidle" })
  await mobilePage.fill('input[type="email"]', "officer.north@example.com")
  await mobilePage.fill('input[type="password"]', "changethis")
  await mobilePage.click('button[type="submit"]')
  await mobilePage.waitForURL("http://localhost:8000/", { timeout: 10000 })
  await mobilePage.waitForTimeout(1000)

  await mobilePage.screenshot({ path: path.join(OUT_DIR, "08_dashboard_mobile_390px.png") })

  await mobileCtx.close()
  await browser.close()
  console.log("Screenshots saved successfully to:", OUT_DIR)
}

capture().catch((err) => {
  console.error("Screenshot capture failed:", err)
  process.exit(1)
})
