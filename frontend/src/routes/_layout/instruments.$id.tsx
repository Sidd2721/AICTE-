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
} from "lucide-react"
import { useState } from "react"
import { toast } from "sonner"

import { client } from "@/client/client.gen"
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
  const [waiverReason, setWaiverReason] = useState("")
  const [showWaiverDialog, setShowWaiverDialog] = useState(false)
  const [selectedFlag, setSelectedFlag] = useState<string | null>(null)

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
            <Button size="sm" className="font-semibold shadow-sm">
              {inst.next_action_label}
            </Button>
          )}
        </div>
      </div>

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
              discrepancies.map((disc, idx) => (
                <div
                  key={idx}
                  className="p-2.5 rounded border border-amber-200 bg-amber-50/50 dark:bg-amber-950/20 text-xs space-y-1"
                >
                  <div className="font-semibold text-amber-900 dark:text-amber-200">
                    {disc.field}: {disc.message}
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setSelectedFlag(disc.field)
                      setShowWaiverDialog(true)
                    }}
                  >
                    Waive Flag with Note
                  </Button>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>

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
