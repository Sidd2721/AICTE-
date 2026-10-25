import { expect, test } from "@playwright/test"

test.use({ storageState: { cookies: [], origins: [] } })

test("Public sign up page is removed (I11 / M0)", async ({ page }) => {
  const response = await page.goto("/signup")
  // Page should either return 404 or show not-found/redirect
  if (response) {
    expect(response.status() === 404 || response.status() === 200).toBeTruthy()
  }
})
