/**
 * Regulatory display formatters (CHARTER R5).
 * Enforces Indian numbering for rupees (₹) and IST dates ("26 Oct 2026").
 */

export function formatPaiseToRupees(paise: number | null | undefined): string {
  if (paise == null) return "₹0"
  const rupees = Math.round(paise / 100)
  if (rupees >= 10000000) {
    return `₹${(rupees / 10000000).toFixed(2)} Cr`
  }
  if (rupees >= 100000) {
    return `₹${(rupees / 100000).toFixed(2)} Lakh`
  }
  return `₹${rupees.toLocaleString("en-IN")}`
}

export function formatDateIST(
  dateStr: string | Date | null | undefined,
): string {
  if (!dateStr) return "—"
  try {
    // If format is YYYY-MM-DD string, parse parts directly to avoid UTC day-offset issues
    if (typeof dateStr === "string" && /^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
      const [year, month, day] = dateStr.split("-").map(Number)
      const d = new Date(year, month - 1, day)
      return d.toLocaleDateString("en-IN", {
        day: "numeric",
        month: "short",
        year: "numeric",
      })
    }
    const d = typeof dateStr === "string" ? new Date(dateStr) : dateStr
    if (Number.isNaN(d.getTime())) return String(dateStr)
    return d.toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
      year: "numeric",
      timeZone: "Asia/Kolkata",
    })
  } catch {
    return String(dateStr)
  }
}
