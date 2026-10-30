import { createFileRoute, Link } from "@tanstack/react-router"
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Copy,
  KeyRound,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  XCircle,
} from "lucide-react"
import { useCallback, useEffect, useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

export const Route = createFileRoute("/verify-receipt")({
  component: VerifyReceiptPage,
})

interface VerifyClaims {
  receipt_id?: string
  instrument_hash?: string
  path?: string
  iat?: number
  release_id?: string
  kid?: string
  [key: string]: unknown
}

interface VerifyResult {
  valid: boolean
  reason: string | null
  claims: VerifyClaims | null
  kid: string | null
  algorithm: string | null
  issued_at: string | null
}

function VerifyReceiptPage() {
  const [tokenInput, setTokenInput] = useState("")
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<VerifyResult | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const verifyToken = useCallback(async (tok: string) => {
    const cleanTok = tok.trim()
    if (!cleanTok) {
      setErrorMsg("Please paste a receipt token to verify.")
      setResult(null)
      return
    }

    setLoading(true)
    setErrorMsg(null)
    try {
      const res = await fetch("/api/v1/receipts/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: cleanTok }),
      })

      if (!res.ok) {
        if (res.status === 413) {
          setErrorMsg("Token exceeds maximum payload size (4 KB limit).")
        } else if (res.status === 429) {
          setErrorMsg("Rate limit exceeded. Please wait a minute and retry.")
        } else {
          setErrorMsg(`Verification service returned status ${res.status}.`)
        }
        setResult(null)
        return
      }

      const data: VerifyResult = await res.json()
      setResult(data)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      setErrorMsg(`Network or server error: ${msg}`)
      setResult(null)
    } finally {
      setLoading(false)
    }
  }, [])

  // Auto-verify if URL hash has #t=<token>
  useEffect(() => {
    const hash = window.location.hash
    if (hash.startsWith("#t=")) {
      const initialToken = hash.slice(3).trim()
      if (initialToken) {
        setTokenInput(initialToken)
        verifyToken(initialToken)
      }
    }
  }, [verifyToken])

  const handleTamperToken = () => {
    if (!tokenInput) return
    const parts = tokenInput.trim().split(".")
    if (parts.length === 3) {
      // Flip a character at index 10 of signature to corrupt signature while preserving valid base64url padding
      const sig = parts[2]
      if (sig.length > 10) {
        const flippedChar = sig[10] === "A" ? "B" : "A"
        const tamperedSig = sig.slice(0, 10) + flippedChar + sig.slice(11)
        const tampered = `${parts[0]}.${parts[1]}.${tamperedSig}`
        setTokenInput(tampered)
        verifyToken(tampered)
        return
      }
    }
    // Fallback: flip last character
    const tampered = `${tokenInput.slice(0, -1)}X`
    setTokenInput(tampered)
    verifyToken(tampered)
  }

  const handleLoadSample = async () => {
    setLoading(true)
    setErrorMsg(null)
    try {
      const res = await fetch("/api/v1/demo/sample-receipt?format=token")
      if (res.ok) {
        const data = await res.json()
        if (data.token) {
          setTokenInput(data.token)
          verifyToken(data.token)
          return
        }
      }
      setErrorMsg("Sample receipt route is only available in demo mode.")
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      setErrorMsg(`Failed to load demo sample token: ${msg}`)
    } finally {
      setLoading(false)
    }
  }

  const handleCopy = () => {
    if (!tokenInput) return
    navigator.clipboard.writeText(tokenInput)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 flex flex-col">
      {/* Prototype Header Notice */}
      <div className="bg-amber-500/10 border-b border-amber-500/20 text-amber-800 dark:text-amber-200 text-xs px-4 py-2 text-center">
        Synthetic data, SIMULATED bank and email, DEMO rule values. Not an
        official document.
      </div>

      {/* Top Navbar */}
      <header className="border-b border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 backdrop-blur sticky top-0 z-10 px-4 sm:px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link
            to="/login"
            className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Portal</span>
          </Link>
          <div className="h-4 w-px bg-slate-200 dark:bg-slate-800" />
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
            <span className="font-semibold text-sm">
              AICTE FDR Portal (PS 26265)
            </span>
            <Badge variant="outline" className="text-xs font-mono">
              Public Verifier
            </Badge>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" asChild>
            <Link to="/guide">Walkthrough Guide</Link>
          </Button>
          <Button variant="outline" size="sm" asChild>
            <Link to="/login">Sign In</Link>
          </Button>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-4xl w-full mx-auto p-4 sm:p-6 lg:p-8 space-y-6">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
            Release Receipt Public Verification
          </h1>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
            Independently verify fixed deposit release receipts signed by
            AICTE's portal key (RS256).
          </p>
        </div>

        {/* Input Card */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center justify-between">
              <span>Receipt Signature Token</span>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleLoadSample}
                  disabled={loading}
                  className="text-xs h-7"
                >
                  Load Sample Token
                </Button>
                {tokenInput && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleCopy}
                    className="text-xs h-7"
                  >
                    <Copy className="h-3 w-3 mr-1" />
                    {copied ? "Copied" : "Copy"}
                  </Button>
                )}
              </div>
            </CardTitle>
            <CardDescription className="text-xs">
              Paste the RS256 JWT token printed on the release receipt PDF or
              loaded from the QR code.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <textarea
              value={tokenInput}
              onChange={(e) => setTokenInput(e.target.value)}
              placeholder="eyJhbGciOiJSUzI1NiIsImtpZCI6IjAwZTU0MDdh... Paste receipt JWT token here"
              rows={4}
              className="w-full rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-slate-900 dark:focus:ring-slate-100"
            />

            <div className="flex flex-wrap items-center gap-2">
              <Button
                onClick={() => verifyToken(tokenInput)}
                disabled={loading || !tokenInput.trim()}
                className="gap-2"
              >
                {loading ? (
                  <RefreshCw className="h-4 w-4 animate-spin" />
                ) : (
                  <KeyRound className="h-4 w-4" />
                )}
                Verify Signature
              </Button>

              {tokenInput && (
                <Button
                  variant="outline"
                  onClick={handleTamperToken}
                  disabled={loading}
                  title="Tamper one character to see cryptographic verification rejection"
                  className="gap-1.5 text-amber-700 dark:text-amber-300 border-amber-300 dark:border-amber-700/50"
                >
                  <AlertTriangle className="h-3.5 w-3.5" />
                  Tamper 1 Character
                </Button>
              )}

              {tokenInput && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setTokenInput("")
                    setResult(null)
                    setErrorMsg(null)
                  }}
                  className="text-xs text-slate-500"
                >
                  Clear
                </Button>
              )}
            </div>

            {errorMsg && (
              <div className="rounded-md border border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950/40 p-3 text-xs text-red-800 dark:text-red-200">
                {errorMsg}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Verification Result Display */}
        {result && (
          <Card
            className={
              result.valid
                ? "border-emerald-500/50 bg-emerald-50/20 dark:bg-emerald-950/20"
                : "border-red-500/50 bg-red-50/20 dark:bg-red-950/20"
            }
          >
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {result.valid ? (
                    <CheckCircle2 className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
                  ) : (
                    <XCircle className="h-6 w-6 text-red-600 dark:text-red-400" />
                  )}
                  <div>
                    <CardTitle className="text-lg">
                      {result.valid
                        ? "Cryptographically Valid Release Receipt"
                        : "Verification Failed"}
                    </CardTitle>
                    <CardDescription className="text-xs">
                      {result.valid
                        ? "Signature verified against AICTE's portal RS256 public key."
                        : "The signature did not match or the token is corrupted."}
                    </CardDescription>
                  </div>
                </div>

                <Badge
                  className={
                    result.valid
                      ? "bg-emerald-600 hover:bg-emerald-600 text-white font-mono text-sm px-3 py-1"
                      : "bg-red-600 hover:bg-red-600 text-white font-mono text-sm px-3 py-1"
                  }
                >
                  {result.valid ? "VALID" : "INVALID"}
                </Badge>
              </div>
            </CardHeader>

            <CardContent className="space-y-4 pt-2">
              {!result.valid && result.reason && (
                <div className="rounded border border-red-200 dark:border-red-900/60 bg-red-100/50 dark:bg-red-900/20 p-3 text-xs text-red-800 dark:text-red-300 font-mono">
                  <b>Reason:</b> {result.reason}
                </div>
              )}

              {result.valid && result.claims && (
                <div className="space-y-3">
                  <div className="text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
                    Verified Claims (Covered by Signature)
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                    <div className="p-2.5 rounded bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
                      <div className="text-slate-500 font-medium">
                        Receipt ID
                      </div>
                      <div className="font-mono mt-0.5 break-all">
                        {result.claims.receipt_id || "—"}
                      </div>
                    </div>

                    <div className="p-2.5 rounded bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
                      <div className="text-slate-500 font-medium">
                        Instrument Hash
                      </div>
                      <div className="font-mono mt-0.5 break-all">
                        {result.claims.instrument_hash || "—"}
                      </div>
                    </div>

                    <div className="p-2.5 rounded bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
                      <div className="text-slate-500 font-medium">
                        Release Path
                      </div>
                      <div className="font-semibold mt-0.5">
                        {result.claims.path || "—"}
                      </div>
                    </div>

                    <div className="p-2.5 rounded bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
                      <div className="text-slate-500 font-medium">
                        Issued At
                      </div>
                      <div className="mt-0.5">{result.issued_at || "—"}</div>
                    </div>

                    <div className="p-2.5 rounded bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 sm:col-span-2">
                      <div className="text-slate-500 font-medium">
                        Key ID (kid) &amp; Algorithm
                      </div>
                      <div className="font-mono mt-0.5 flex items-center gap-2">
                        <span>{result.kid || "—"}</span>
                        <Badge
                          variant="outline"
                          className="text-[10px] font-mono"
                        >
                          {result.algorithm || "RS256"}
                        </Badge>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* What this proves / what this does not prove */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card className="border-emerald-200 dark:border-emerald-950/60">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2 text-emerald-700 dark:text-emerald-400">
                <ShieldCheck className="h-4 w-4" />
                What this proves
              </CardTitle>
            </CardHeader>
            <CardContent className="text-xs text-slate-600 dark:text-slate-400 space-y-2">
              <p>
                <b>Portal Origin:</b> The token was generated by AICTE's release
                approval workflow and signed with the portal's RS256 private
                key.
              </p>
              <p>
                <b>Content Integrity:</b> The signed fields (receipt ID,
                instrument SHA-256 hash, release path, and issuance timestamp)
                have not been modified since issuance.
              </p>
              <p>
                <b>Maker-Checker Approval:</b> The release was reviewed and
                authorized in accordance with the regulatory release checklist.
              </p>
            </CardContent>
          </Card>

          <Card className="border-slate-200 dark:border-slate-800">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2 text-slate-700 dark:text-slate-300">
                <ShieldAlert className="h-4 w-4 text-amber-500" />
                What this does not prove
              </CardTitle>
            </CardHeader>
            <CardContent className="text-xs text-slate-600 dark:text-slate-400 space-y-2">
              <p>
                <b>No Funds Moved:</b> This is a synthetic prototype for
                demonstration; no actual bank funds or money transfers occur.
              </p>
              <p>
                <b>Not a Bank Instrument:</b> This receipt does not constitute a
                bank guarantee, fixed deposit certificate, or negotiable
                instrument.
              </p>
              <p>
                <b>Unsigned Context:</b> Contextual fields on printouts (such as
                deposit amount or bank code) are for human review and are not
                separately attested by the signature.
              </p>
            </CardContent>
          </Card>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 dark:border-slate-800 py-4 px-6 text-center text-xs text-slate-500">
        AICTE Security Deposit Portal (PS 26265) &bull; Synthetic Demo System
      </footer>
    </div>
  )
}
