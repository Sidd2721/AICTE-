import { Check, Copy, Terminal } from "lucide-react"
import { useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

export function QuickstartPanel() {
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null)
  const baseUrl =
    typeof window !== "undefined"
      ? window.location.origin
      : "http://localhost:8000"

  const copyToClipboard = (text: string, index: number) => {
    navigator.clipboard.writeText(text)
    setCopiedIndex(index)
    setTimeout(() => setCopiedIndex(null), 2000)
  }

  const snippets = [
    {
      title: "Bank IT: Poll Pending Verification Requests",
      scope: "bank:confirm",
      method: "GET",
      endpoint: "/api/integration/v1/bank/requests/pending",
      desc: "Queried by Core Banking Adapters to retrieve pending inquiries for branch IFSCs.",
      curl: `curl -X GET "${baseUrl}/api/integration/v1/bank/requests/pending?ifsc=SBIN0001234&limit=10" \\
  -H "X-API-Key: fdr_demo_key_secret"`,
    },
    {
      title: "Bank IT: Submit Signed Bank Confirmation",
      scope: "bank:confirm",
      method: "POST",
      endpoint: "/api/integration/v1/bank/confirmations",
      desc: "Executes 6-point cryptographic gate. Requires Idempotency-Key and single-use challenge token.",
      curl: `curl -X POST "${baseUrl}/api/integration/v1/bank/confirmations" \\
  -H "Content-Type: application/json" \\
  -H "Idempotency-Key: $(uuidgen 2>/dev/null || echo '01928a3f-7b01-7102-8a19-123456789abc')" \\
  -H "X-API-Key: fdr_demo_key_secret" \\
  -d '{
    "request_token": "tok_sec_sample981237",
    "signed_letter_base64": "JVBERi0xLjQgU0lNVUxBVEVEIEJBTksgVkVSSUZJQ0FUSU9O...",
    "fields": {
      "ref_no": "FDR-B9-301",
      "bank_code": "SBIN",
      "amount_paise": 350000000,
      "maturity_date": "2034-01-15",
      "lien_marked": true
    }
  }'`,
    },
    {
      title: "Central IT: Query Active Institutions",
      scope: "aicte:read",
      method: "GET",
      endpoint: "/api/integration/v1/institutions",
      desc: "Deterministic cursor pagination for AICTE central approval sync and CAG audit extractors.",
      curl: `curl -X GET "${baseUrl}/api/integration/v1/institutions?region=NR&limit=20" \\
  -H "X-API-Key: fdr_demo_key_secret"`,
    },
    {
      title: "Central IT: Query Fixed Deposit Instruments",
      scope: "aicte:read",
      method: "GET",
      endpoint: "/api/integration/v1/instruments",
      desc: "Filtered by lifecycle state (pending, active, matured) and confirmation badge.",
      curl: `curl -X GET "${baseUrl}/api/integration/v1/instruments?lifecycle=active&badge=confirmed" \\
  -H "X-API-Key: fdr_demo_key_secret"`,
    },
    {
      title: "Central IT: Stream Transactional Outbox Events",
      scope: "aicte:read",
      method: "GET",
      endpoint: "/api/integration/v1/events",
      desc: "Sequential at-least-once lifecycle event stream for national workflow orchestrators.",
      curl: `curl -X GET "${baseUrl}/api/integration/v1/events?limit=50" \\
  -H "X-API-Key: fdr_demo_key_secret"`,
    },
    {
      title: "Public Audit: Detached Signed Checkpoints",
      scope: "public",
      method: "GET",
      endpoint: "/api/v1/audit/checkpoints",
      desc: "Verifiable with standard openssl / minisign using the published Ed25519 public key.",
      curl: `curl -X GET "${baseUrl}/api/v1/audit/checkpoints"`,
    },
  ]

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Terminal className="h-5 w-5 text-primary" />
            <CardTitle>Integration Quickstart & Contract Reference</CardTitle>
          </div>
          <CardDescription>
            Copy-paste curl examples pre-configured for this environment. Every
            endpoint enforces scoped API keys, least-privilege RLS, integer
            paise amounts, and RFC 7807 error envelopes.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 rounded-lg bg-muted/40 text-sm">
            <div>
              <span className="font-semibold text-foreground">
                Base Namespace:
              </span>{" "}
              <code className="bg-background px-1.5 py-0.5 rounded border text-xs">
                /api/integration/v1
              </code>
            </div>
            <div>
              <span className="font-semibold text-foreground">Evolution:</span>{" "}
              <Badge variant="outline" className="text-xs">
                Additive-Only (SemVer 1.0)
              </Badge>
            </div>
            <div>
              <span className="font-semibold text-foreground">
                Rate Limits:
              </span>{" "}
              <span className="text-muted-foreground text-xs">
                100 req/min (Standard Headers)
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="space-y-4">
        {snippets.map((snip, idx) => (
          <Card key={snip.title} className="overflow-hidden">
            <CardHeader className="bg-muted/20 py-3 px-4 border-b">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Badge
                    variant={snip.method === "POST" ? "default" : "secondary"}
                    className="text-xs font-mono font-bold"
                  >
                    {snip.method}
                  </Badge>
                  <span className="font-semibold text-sm">{snip.title}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="text-xs font-mono">
                    Scope: {snip.scope}
                  </Badge>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-8 gap-1.5 text-xs"
                    onClick={() => copyToClipboard(snip.curl, idx)}
                  >
                    {copiedIndex === idx ? (
                      <>
                        <Check className="h-3.5 w-3.5 text-green-500" />
                        <span className="text-green-500">Copied</span>
                      </>
                    ) : (
                      <>
                        <Copy className="h-3.5 w-3.5" />
                        <span>Copy curl</span>
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-4 space-y-2">
              <p className="text-xs text-muted-foreground">{snip.desc}</p>
              <pre className="p-3 bg-muted/60 text-foreground font-mono text-xs rounded-md overflow-x-auto whitespace-pre border">
                {snip.curl}
              </pre>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
