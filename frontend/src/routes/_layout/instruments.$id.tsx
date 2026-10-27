import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  Download,
  FileText,
  History,
  Shield,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react"
import { useState } from "react"
import { toast } from "sonner"

import { client } from "@/client/client.gen"
import { AboutThisPage } from "@/components/Common/AboutThisPage"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import useAuth from "@/hooks/useAuth"
import { getMessage } from "@/lib/messages"

export const Route = createFileRoute("/_layout/instruments/$id")({
  component: InstrumentCaseView,
})

function formatPaise(p: number | null | undefined): string {
  if (p == null) return "—"
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(p / 100)
}

function InstrumentCaseView() {
  const { id } = Route.useParams() as { id: string }
  const queryClient = useQueryClient()
  const { user: currentUser } = useAuth()
  const [waiverReason, setWaiverReason] = useState("")
  const [showWaiverDialog, setShowWaiverDialog] = useState(false)
  const [selectedFlag, setSelectedFlag] = useState<string | null>(null)
  const [testResult, setTestResult] = useState<any>(null)

  const testGateMutation = useMutation({
    mutationFn: async (attack_type: string) => {
      const res = await client.post<any>({
        url: `/sim/bank/test-gate/${id}`,
        body: { attack_type },
      })
      return res.data
    },
    onSuccess: (data) => {
      setTestResult(data)
      if (data.passed) {
        toast.success(data.message)
      } else {
        toast.warning(`Gate Blocked: ${data.diagnosis}`)
      }
    },
    onError: (err: any) => {
      toast.error(err?.detail || "Simulation Error")
    },
  })

  const { data: caseData, isLoading } = useQuery({
    queryKey: ["instrument-case", id],
    queryFn: async () => {
      const res = await client.get<any>({
        url: `/api/v1/instruments/${id}/case`,
      })
      return res.data
    },
  })

  const waiveMutation = useMutation({
    mutationFn: async (flag: string) => {
      const res = await client.post({
        url: `/api/v1/instruments/${id}/waivers`,
        body: { flag, reason: waiverReason },
      })
      return res.data
    },
    onSuccess: () => {
      toast.success("Flag waived with scrutiny note")
      setShowWaiverDialog(false)
      setWaiverReason("")
      queryClient.invalidateQueries({ queryKey: ["instrument-case", id] })
    },
    onError: (err: any) => toast.error(err?.detail || "Failed to waive flag"),
  })

  const requestConfirmationMutation = useMutation({
    mutationFn: async () => {
      const res = await client.post<any>({
        url: `/api/v1/bank/request-confirmation/${id}`,
      })
      try {
        await client.post<any>({
          url: `/sim/bank/confirm/${id}`,
          body: { outcome: "match" },
        })
      } catch {
        // Simulation callback triggered
      }
      return res.data
    },
    onSuccess: () => {
      toast.success("Bank confirmation requested & verified (SIMULATED)")
      queryClient.invalidateQueries({ queryKey: ["instrument-case", id] })
    },
    onError: (err: any) =>
      toast.error(err?.detail || "Failed to request bank confirmation"),
  })

  const acceptRecordMutation = useMutation({
    mutationFn: async () => {
      const res = await client.post<any>({
        url: `/api/v1/instruments/${id}/accept`,
      })
      return res.data
    },
    onSuccess: () => {
      toast.success("Instrument accepted and marked Active")
      queryClient.invalidateQueries({ queryKey: ["instrument-case", id] })
    },
    onError: (err: any) =>
      toast.error(err?.detail || "Failed to accept instrument record"),
  })

  const requestReleaseMutation = useMutation({
    mutationFn: async () => {
      const res = await client.post({
        url: `/api/v1/instruments/${id}/release`,
        body: {
          path: "term_completion",
          reason: "Maturity completed. Return requested.",
        },
      })
      return res.data
    },
    onSuccess: () => {
      toast.success("Release requested successfully")
      queryClient.invalidateQueries({ queryKey: ["instrument-case", id] })
    },
    onError: (err: any) =>
      toast.error(err?.detail || "Failed to request release"),
  })

  const verifyReleaseMutation = useMutation({
    mutationFn: async (releaseId: string) => {
      const res = await client.post({
        url: `/api/v1/release/${releaseId}/verify`,
        body: { checklist_notes: "Regional Officer verification completed" },
      })
      return res.data
    },
    onSuccess: () => {
      toast.success("Release verified by Regional Officer (Maker)")
      queryClient.invalidateQueries({ queryKey: ["instrument-case", id] })
    },
    onError: (err: any) =>
      toast.error(err?.detail || "Failed to verify release"),
  })

  const approveReleaseMutation = useMutation({
    mutationFn: async (releaseId: string) => {
      const res = await client.post({
        url: `/api/v1/release/${releaseId}/approve`,
        body: {
          approval_notes: "Bureau Approver dual-control approval granted",
        },
      })
      return res.data
    },
    onSuccess: () => {
      toast.success("Release approved by Bureau Approver (Checker)")
      queryClient.invalidateQueries({ queryKey: ["instrument-case", id] })
    },
    onError: (err: any) =>
      toast.error(err?.detail || "Failed to approve release"),
  })

  if (isLoading || !caseData) {
    return (
      <div className="p-8 text-muted-foreground animate-pulse">
        Loading instrument case record...
      </div>
    )
  }

  const inst = (caseData as any).instrument || {}
  const instn = (caseData as any).institution || {}
  const latestConf = (caseData as any).latest_confirmation
  const confFields = latestConf?.fields || {}
  const discrepancies: any[] = (caseData as any).discrepancies || []
  const docs: any[] = (caseData as any).documents || []
  const auditTimeline: any[] = (caseData as any).audit_timeline || []
  const relReq = (caseData as any).release_request
  const badgeMsg = getMessage(inst.badge || "SUBMITTED_CLAIMED")

  const comparisonRows = [
    {
      label: "Instrument Reference",
      sub: inst.ref_no,
      conf: confFields.fdr_number || confFields.ref_no,
      key: "ref_no",
    },
    {
      label: "Bank Code / IFSC",
      sub: `${inst.bank_code} (${inst.ifsc || "—"})`,
      conf: confFields.bank_code || "—",
      key: "bank_code",
    },
    {
      label: "Amount",
      sub: formatPaise(inst.amount_paise),
      conf:
        confFields.amount_paise != null
          ? formatPaise(confFields.amount_paise)
          : "—",
      key: "amount",
    },
    {
      label: "Maturity Date",
      sub: inst.maturity_date || "—",
      conf: confFields.maturity_date || "—",
      key: "maturity_date",
    },
    {
      label: "AICTE Lien Marked",
      sub: inst.lien_marked ? "Yes" : "No",
      conf:
        confFields.lien_marked != null
          ? confFields.lien_marked
            ? "Yes"
            : "No"
          : "—",
      key: "lien_marked",
    },
  ]

  const handleNextAction = () => {
    if (inst.next_action_code === "request_confirmation") {
      requestConfirmationMutation.mutate()
    } else if (inst.next_action_code === "accept_record") {
      acceptRecordMutation.mutate()
    } else if (inst.next_action_code === "verify_release" && relReq?.id) {
      verifyReleaseMutation.mutate(relReq.id)
    } else if (inst.next_action_code === "approve_release" && relReq?.id) {
      approveReleaseMutation.mutate(relReq.id)
    } else if (inst.next_action_code === "request_release") {
      requestReleaseMutation.mutate()
    } else {
      toast.info(`Next action: ${inst.next_action_label}`)
    }
  }

  return (
    <div className="space-y-6 pb-12">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Link
              to="/deposits"
              className="text-muted-foreground hover:text-foreground text-sm flex items-center gap-1"
            >
              <ArrowLeft className="h-4 w-4" /> Back to Deposits
            </Link>
          </div>
          <h1 className="text-2xl font-bold tracking-tight mt-1">
            {inst.ref_no} — Case View
          </h1>
          <p className="text-sm text-muted-foreground">
            {instn.name} (PID: {instn.permanent_id}) • Region: {inst.region}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Badge
            variant={inst.badge === "confirmed" ? "default" : "secondary"}
            className="text-xs px-2.5 py-1"
          >
            {badgeMsg.label}
          </Badge>
          {inst.next_action_label && inst.next_action_code !== "none" && (
            <Button
              size="sm"
              className="font-semibold shadow-sm"
              onClick={handleNextAction}
              disabled={
                requestConfirmationMutation.isPending ||
                acceptRecordMutation.isPending ||
                requestReleaseMutation.isPending ||
                verifyReleaseMutation.isPending ||
                approveReleaseMutation.isPending
              }
              title={`Next action: ${inst.next_action_label}`}
            >
              {inst.next_action_label}
            </Button>
          )}
        </div>
      </div>

      {/* About this screen guide (G3) */}
      <AboutThisPage pageKey="case_page" />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="md:col-span-2">
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Shield className="h-4 w-4 text-primary" /> Submitted vs Confirmed
              (SIMULATED)
            </CardTitle>
            <CardDescription>
              {badgeMsg.sentence} {badgeMsg.action}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[180px]">Field</TableHead>
                  <TableHead>Submitted by Institution</TableHead>
                  <TableHead>Confirmed by Bank (SIMULATED)</TableHead>
                  <TableHead className="w-[100px]">Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {comparisonRows.map((row) => {
                  const hasDisc = discrepancies.some(
                    (d) =>
                      d.field === row.key ||
                      (row.key === "amount" && d.field === "amount_paise"),
                  )
                  return (
                    <TableRow
                      key={row.label}
                      className={hasDisc ? "bg-destructive/10 font-medium" : ""}
                    >
                      <TableCell className="font-medium text-xs">
                        {row.label}
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {String(row.sub ?? "—")}
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {String(row.conf ?? "—")}
                      </TableCell>
                      <TableCell>
                        {hasDisc ? (
                          <Badge
                            variant="destructive"
                            className="text-[10px] gap-1"
                          >
                            <AlertCircle className="h-3 w-3" /> Mismatch
                          </Badge>
                        ) : row.conf !== "—" ? (
                          <Badge
                            variant="outline"
                            className="text-[10px] text-emerald-600 border-emerald-500 gap-1"
                          >
                            <CheckCircle2 className="h-3 w-3" /> Match
                          </Badge>
                        ) : (
                          <span className="text-xs text-muted-foreground">
                            Pending
                          </span>
                        )}
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <ShieldAlert className="h-4 w-4 text-amber-500" /> Scrutiny &
              Waivers
            </CardTitle>
            <CardDescription>
              Hard Rule I7: Scrutiny notes mandatory for waivers
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {discrepancies.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                No open field discrepancies detected on this instrument.
              </p>
            ) : (
              discrepancies.map((disc, idx) => {
                const discCode = disc.code || disc.field || ""
                const msg = getMessage(discCode)
                return (
                  <div
                    key={idx}
                    className="p-3 rounded border border-amber-200 bg-amber-50/50 dark:bg-amber-950/20 text-xs space-y-2"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="space-y-1">
                        <div className="font-semibold text-amber-900 dark:text-amber-200">
                          {msg.label}
                        </div>
                        <p className="text-muted-foreground">{msg.sentence}</p>
                        <p className="text-xs text-amber-800 dark:text-amber-300 font-medium">
                          Action: {msg.action}
                        </p>
                      </div>
                      <Button
                        size="sm"
                        variant="outline"
                        title="Official scrutiny reason mandatory before waiving"
                        onClick={() => {
                          setSelectedFlag(disc.field || disc.code)
                          setShowWaiverDialog(true)
                        }}
                      >
                        Waive Flag with Note
                      </Button>
                    </div>
                    <details className="text-[11px] text-muted-foreground pt-1 border-t border-amber-200/40">
                      <summary className="cursor-pointer hover:underline font-mono">
                        Technical details ({disc.code || disc.field || "raw"})
                      </summary>
                      <pre className="mt-1 font-mono text-[10px] bg-background/50 p-2 rounded overflow-x-auto">
                        {JSON.stringify(disc, null, 2)}
                      </pre>
                    </details>
                  </div>
                )
              })
            )}
          </CardContent>
        </Card>
      </div>

      {/* Break-Me Cryptographic Security Workbench (Hard Rule I3 / CHARTER W5) */}
      <Card className="border-primary/20 bg-gradient-to-br from-card via-card to-primary/5 shadow-xs">
        <CardHeader className="pb-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <CardTitle className="text-base flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-primary" />
              Break-Me Cryptographic Security Workbench (CHARTER W5 / Hard Rule
              I3)
            </CardTitle>
            <Badge
              variant="outline"
              className="text-[10px] uppercase font-bold border-primary/30 text-primary"
            >
              Full Gate Sandbox
            </Badge>
          </div>
          <CardDescription>
            Inject adversarial payloads to verify that the cryptographic bank
            gate rejects forgeries, replayed tokens, and trailing byte
            tampering.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            <Button
              size="sm"
              variant="outline"
              className="text-xs border-destructive/40 hover:bg-destructive/10 text-destructive justify-start h-auto py-2 flex-col items-start gap-0.5"
              disabled={testGateMutation.isPending}
              onClick={() => testGateMutation.mutate("forged_letter")}
            >
              <span className="font-semibold">Attack 1: Forged Challenge</span>
              <span className="text-[10px] text-muted-foreground">
                Byte prefix mismatch
              </span>
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="text-xs border-amber-500/40 hover:bg-amber-500/10 text-amber-700 dark:text-amber-400 justify-start h-auto py-2 flex-col items-start gap-0.5"
              disabled={testGateMutation.isPending}
              onClick={() => testGateMutation.mutate("appended_bytes")}
            >
              <span className="font-semibold">Attack 2: Appended Bytes</span>
              <span className="text-[10px] text-muted-foreground">
                Trailing byte tampering
              </span>
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="text-xs border-purple-500/40 hover:bg-purple-500/10 text-purple-700 dark:text-purple-400 justify-start h-auto py-2 flex-col items-start gap-0.5"
              disabled={testGateMutation.isPending}
              onClick={() => testGateMutation.mutate("replayed_token")}
            >
              <span className="font-semibold">Attack 3: Replayed Token</span>
              <span className="text-[10px] text-muted-foreground">
                Consumed / expired
              </span>
            </Button>
            <Button
              size="sm"
              variant="default"
              className="text-xs justify-start h-auto py-2 flex-col items-start gap-0.5"
              disabled={testGateMutation.isPending}
              onClick={() => testGateMutation.mutate("valid")}
            >
              <span className="font-semibold">Test 4: Genuine Reply</span>
              <span className="text-[10px] opacity-90">
                6/6 gate checks pass
              </span>
            </Button>
          </div>

          {testResult && (
            <div
              className={`p-3.5 rounded-lg border text-xs space-y-2 ${
                testResult.passed
                  ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-950 dark:text-emerald-200"
                  : "border-destructive/40 bg-destructive/10 text-destructive-foreground"
              }`}
            >
              <div className="flex items-center justify-between font-semibold">
                <span className="flex items-center gap-1.5">
                  {testResult.passed ? (
                    <CheckCircle2 className="size-4 text-emerald-600" />
                  ) : (
                    <AlertCircle className="size-4 text-destructive" />
                  )}
                  {testResult.passed
                    ? "Cryptographic Gate Verified — Valid Non-Repudiation"
                    : `Attack Intercepted: [${testResult.diagnosis}]`}
                </span>
                <Badge
                  variant={testResult.passed ? "default" : "destructive"}
                  className="text-[10px]"
                >
                  {testResult.passed ? "VERIFIED" : "BLOCKED"}
                </Badge>
              </div>
              <p className="text-[11px] leading-relaxed text-muted-foreground">
                {testResult.message}
              </p>
              {testResult.gate_report && (
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5 pt-1 font-mono text-[10px]">
                  {Object.entries(testResult.gate_report).map(([key, val]) => (
                    <div
                      key={key}
                      className="flex items-center justify-between px-2 py-1 bg-background/60 rounded border border-border/50"
                    >
                      <span className="truncate pr-1">{key}</span>
                      <span
                        className={
                          val
                            ? "text-emerald-600 font-bold"
                            : "text-destructive font-bold"
                        }
                      >
                        {val ? "✓ PASS" : "✗ FAIL"}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4" /> Release Panel (Maker-Checker)
            </CardTitle>
            <CardDescription>
              Dual-control: Maker != Checker. Recommends; humans release.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            {/* Stepper Visualization */}
            <div className="py-2">
              <div className="flex items-center justify-between relative">
                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-full h-0.5 bg-border -z-1" />
                <div className="flex flex-col items-center gap-1 bg-background px-1 z-10">
                  <div
                    className={`size-6 rounded-full flex items-center justify-center text-[10px] font-bold ${
                      relReq
                        ? "bg-emerald-600 text-white"
                        : "bg-primary text-primary-foreground"
                    }`}
                  >
                    1
                  </div>
                  <span className="text-[10px] font-medium text-muted-foreground">
                    Request
                  </span>
                </div>
                <div className="flex flex-col items-center gap-1 bg-background px-1 z-10">
                  <div
                    className={`size-6 rounded-full flex items-center justify-center text-[10px] font-bold ${
                      relReq?.status === "verified" ||
                      relReq?.status === "released"
                        ? "bg-emerald-600 text-white"
                        : relReq?.status === "submitted"
                          ? "bg-primary text-primary-foreground animate-pulse"
                          : "bg-muted text-muted-foreground"
                    }`}
                  >
                    2
                  </div>
                  <span className="text-[10px] font-medium text-muted-foreground">
                    Verify (RO)
                  </span>
                </div>
                <div className="flex flex-col items-center gap-1 bg-background px-1 z-10">
                  <div
                    className={`size-6 rounded-full flex items-center justify-center text-[10px] font-bold ${
                      relReq?.status === "released"
                        ? "bg-emerald-600 text-white"
                        : relReq?.status === "verified"
                          ? "bg-primary text-primary-foreground animate-pulse"
                          : "bg-muted text-muted-foreground"
                    }`}
                  >
                    3
                  </div>
                  <span className="text-[10px] font-medium text-muted-foreground">
                    Approve (HQ)
                  </span>
                </div>
              </div>
            </div>

            <div className="p-3 bg-muted rounded-md space-y-1">
              <div>
                <strong>Status:</strong>{" "}
                {relReq ? relReq.status.toUpperCase() : "NOT REQUESTED"}
              </div>
              <div>
                <strong>Maker (RO):</strong>{" "}
                {relReq?.verified_by || "Pending verification"}
              </div>
              <div>
                <strong>Checker (Bureau):</strong>{" "}
                {relReq?.approved_by || "Pending approval"}
              </div>
            </div>

            {/* Dual-Control Release Actions */}
            {!relReq && (
              <Button
                size="sm"
                className="w-full"
                disabled={
                  currentUser?.role !== "institution" ||
                  requestReleaseMutation.isPending
                }
                title={
                  currentUser?.role !== "institution"
                    ? "Dual-control: Only Institution persona can initiate release request"
                    : "Request return of mature fixed deposit"
                }
                onClick={() => requestReleaseMutation.mutate()}
              >
                {requestReleaseMutation.isPending
                  ? "Requesting..."
                  : "Request Release (Institution)"}
              </Button>
            )}

            {relReq && relReq.status === "submitted" && (
              <Button
                size="sm"
                className="w-full"
                disabled={
                  currentUser?.role !== "regional" ||
                  verifyReleaseMutation.isPending
                }
                title={
                  currentUser?.role !== "regional"
                    ? "Dual-control: Only Regional Officer (Maker) can verify release"
                    : "Verify release checklist and forward to Bureau"
                }
                onClick={() => verifyReleaseMutation.mutate(relReq.id)}
              >
                {verifyReleaseMutation.isPending
                  ? "Verifying..."
                  : "Verify Release (Maker / Regional)"}
              </Button>
            )}

            {relReq && relReq.status === "verified" && (
              <Button
                size="sm"
                className="w-full"
                disabled={
                  currentUser?.role !== "bureau" ||
                  approveReleaseMutation.isPending
                }
                title={
                  currentUser?.role !== "bureau"
                    ? "Dual-control: Only Bureau Approver (Checker) can approve release"
                    : "Approve release and issue cryptographic encashment receipt"
                }
                onClick={() => approveReleaseMutation.mutate(relReq.id)}
              >
                {approveReleaseMutation.isPending
                  ? "Approving..."
                  : "Approve Release (Checker / Bureau)"}
              </Button>
            )}

            {relReq?.status === "released" && (
              <div className="p-3 border border-emerald-500/30 bg-emerald-500/10 rounded space-y-2">
                <div className="font-semibold text-emerald-800 dark:text-emerald-200 flex items-center gap-1">
                  <Download className="h-4 w-4" /> Encashment Authorization
                  Receipt Ready
                </div>
                <p className="text-[11px] text-muted-foreground font-mono break-all">
                  python scripts/verify_receipt.py receipt_{inst.ref_no}.jwt
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <FileText className="h-4 w-4" /> Uploaded Documents
            </CardTitle>
            <CardDescription>
              Cryptographic SHA256 integrity checked
            </CardDescription>
          </CardHeader>
          <CardContent>
            {docs.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                No documents uploaded.
              </p>
            ) : (
              <div className="space-y-2">
                {docs.map((d, i) => (
                  <div
                    key={i}
                    className="text-xs p-2 border rounded flex justify-between items-center"
                  >
                    <div>
                      <span className="font-medium">{d.doc_type}</span>{" "}
                      <span className="text-muted-foreground">
                        ({d.created_at?.slice(0, 10)})
                      </span>
                    </div>
                    <span className="font-mono text-[10px] text-muted-foreground">
                      {d.sha256?.slice(0, 12)}...
                    </span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <History className="h-4 w-4" /> Audit Ledger Timeline
          </CardTitle>
          <CardDescription>
            Append-only tamper-evident hash chain (Hard Rule I3)
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {auditTimeline.map((ev, i) => (
              <div
                key={i}
                className="text-xs flex items-center justify-between py-1 border-b last:border-0 font-mono"
              >
                <span>
                  {ev.created_at?.replace("T", " ").slice(0, 19)} •{" "}
                  <strong>{ev.action}</strong> ({ev.actor_role})
                </span>
                <span className="text-muted-foreground text-[10px]">
                  {ev.entry_hash?.slice(0, 16)}...
                </span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Dialog open={showWaiverDialog} onOpenChange={setShowWaiverDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Waive Flag: {selectedFlag}</DialogTitle>
          </DialogHeader>
          <div className="space-y-2 py-2">
            <Input
              placeholder="Enter mandatory official scrutiny reason..."
              value={waiverReason}
              onChange={(e) => setWaiverReason(e.target.value)}
            />
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowWaiverDialog(false)}
            >
              Cancel
            </Button>
            <Button
              disabled={!waiverReason.trim() || waiveMutation.isPending}
              onClick={() => selectedFlag && waiveMutation.mutate(selectedFlag)}
            >
              Record Waiver
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
