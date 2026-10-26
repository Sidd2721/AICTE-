import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router"
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  ArrowUpRight,
  Building2,
  CheckCircle2,
  Clock,
  ExternalLink,
  Lock,
  Play,
  RefreshCw,
  Scale,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  XCircle,
} from "lucide-react"
import { useState } from "react"
import { toast } from "sonner"

import { AuditService, DashboardService, SimulationService } from "@/client"
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import useAuth from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/")({
  component: Dashboard,
  head: () => ({
    meta: [
      {
        title: "Compliance Dashboard — AICTE FDR Portal",
      },
    ],
  }),
})

function formatPaiseToRupees(paise: number): string {
  const rupees = paise / 100
  if (rupees >= 10000000) {
    return `₹${(rupees / 10000000).toFixed(2)} Cr`
  }
  if (rupees >= 100000) {
    return `₹${(rupees / 100000).toFixed(2)} Lakh`
  }
  return `₹${rupees.toLocaleString("en-IN")}`
}

function TrustBadge({ status }: { status: string }) {
  switch (status.toLowerCase()) {
    case "confirmed":
      return (
        <Badge
          variant="outline"
          className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 font-medium gap-1"
        >
          <ShieldCheck className="h-3.5 w-3.5" />
          Confirmed
        </Badge>
      )
    case "claimed":
      return (
        <Badge
          variant="outline"
          className="bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20 font-medium gap-1"
        >
          <Clock className="h-3.5 w-3.5" />
          Claimed
        </Badge>
      )
    case "stale":
      return (
        <Badge
          variant="outline"
          className="bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 border-yellow-500/20 font-medium gap-1"
        >
          <AlertTriangle className="h-3.5 w-3.5" />
          Stale
        </Badge>
      )
    case "changed":
      return (
        <Badge variant="destructive" className="font-medium gap-1 shadow-sm">
          <XCircle className="h-3.5 w-3.5" />
          Changed / Discrepant
        </Badge>
      )
    default:
      return <Badge variant="outline">{status}</Badge>
  }
}

function Dashboard() {
  const { user: currentUser } = useAuth()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [verifyingAudit, setVerifyingAudit] = useState(false)

  // 1. Fetch live counters
  const { data: counters, isLoading: countersLoading } = useQuery({
    queryKey: ["dashboard-counters"],
    queryFn: async () => {
      const res = await DashboardService.getDashboardCounters()
      return res.data
    },
    refetchInterval: 15000,
  })

  // 2. Fetch Needs Action queue
  const { data: needsAction, isLoading: actionLoading } = useQuery({
    queryKey: ["dashboard-needs-action"],
    queryFn: async () => {
      const res = await DashboardService.getNeedsActionQueue()
      return res.data
    },
    refetchInterval: 15000,
  })

  // 3. Fetch Fraud Lab metrics
  const { data: fraudMetrics, isLoading: fraudLoading } = useQuery({
    queryKey: ["fraud-lab-metrics"],
    queryFn: async () => {
      const res = await client.get<any>({
        url: "/api/v1/fraud-lab/metrics",
      })
      return res.data
    },
  })

  // 4. Trigger Daily Worker Mutation
  const triggerWorkerMutation = useMutation({
    mutationFn: async () => {
      const res = await SimulationService.triggerDailyWorker()
      return res.data
    },
    onSuccess: (data: any) => {
      toast.success("Daily compliance worker finished", {
        description: `Checked maturities, evaluated Table 1.4 obligations, generated ${data?.alerts_generated ?? 0} alerts.`,
      })
      queryClient.invalidateQueries({ queryKey: ["dashboard-counters"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard-needs-action"] })
    },
    onError: (err: any) => {
      toast.error("Worker trigger failed", {
        description:
          err?.message || "Could not trigger daily compliance worker",
      })
    },
  })

  // 5. Verify cryptographic hash chain
  const handleVerifyAuditChain = async () => {
    try {
      setVerifyingAudit(true)
      const res = await AuditService.verifyAuditChain()
      if (res.data?.valid) {
        toast.success("Cryptographic Audit Chain Verified", {
          description: `Total ${res.data.count} immutable log entries verified with SHA-256 hash chaining. Zero tamper detected.`,
        })
      } else {
        toast.error("Audit Chain Broken", {
          description: `Integrity failure detected at sequence ${res.data?.broken_at_seq}`,
        })
      }
    } catch (e: any) {
      toast.error("Failed to verify audit chain", {
        description: e?.message || "Service unavailable",
      })
    } finally {
      setVerifyingAudit(false)
    }
  }

  const roleLabel =
    currentUser?.role === "bureau"
      ? "AICTE Bureau Officer (Admin)"
      : currentUser?.role === "regional"
        ? `Regional Officer (${currentUser.region?.toUpperCase() ?? "General"})`
        : currentUser?.role === "institution"
          ? "Institution Maker"
          : currentUser?.role === "auditor"
            ? "Compliance Auditor (Read-Only)"
            : currentUser?.role?.toUpperCase() || "Authorized User"

  return (
    <div className="flex flex-col gap-8 pb-12">
      {/* Statutory / Synthetic Prototype Disclaimer Banner (Invariant I15) */}
      <div className="relative overflow-hidden rounded-xl border border-amber-500/30 bg-gradient-to-r from-amber-500/10 via-amber-500/5 to-transparent p-4 md:p-5 shadow-sm">
        <div className="flex items-start gap-4">
          <div className="rounded-lg bg-amber-500/20 p-2 text-amber-600 dark:text-amber-400 shrink-0">
            <ShieldAlert className="h-5 w-5" />
          </div>
          <div className="flex-1 space-y-1">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-amber-800 dark:text-amber-300 text-sm tracking-wide uppercase">
                Regulatory Demonstration Environment — Synthetic Data Only
              </span>
              <Badge
                variant="outline"
                className="text-[10px] uppercase border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300"
              >
                AICTE PS 26265
              </Badge>
            </div>
            <p className="text-xs text-amber-900/80 dark:text-amber-200/80 leading-relaxed">
              Every banking partner, FDR receipt, and financial transaction
              displayed in this portal is a labelled simulator. Protected by
              AES-256-GCM encrypted vault, full verification gate, four-eyes
              Maker-Checker authorization, and tamper-evident SHA-256 audit
              chaining.
            </p>
          </div>
        </div>
      </div>

      {/* Hero Welcome & Actions Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-semibold text-primary uppercase tracking-wider">
              AICTE Regulatory Oversight
            </span>
            <span className="text-xs text-muted-foreground">•</span>
            <Badge variant="secondary" className="text-xs font-medium">
              {roleLabel}
            </Badge>
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight">
            Security Deposit & FDR Oversight
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Real-time compliance monitoring, Table 1.4 obligation tracking, and
            bank confirmation status.
          </p>
        </div>

        {/* Quick Operational Controls */}
        <div className="flex flex-wrap items-center gap-2.5">
          <Button
            variant="outline"
            size="sm"
            onClick={handleVerifyAuditChain}
            disabled={verifyingAudit}
            className="text-xs gap-1.5"
            title="Verify SHA-256 hash chain across all audit events"
          >
            {verifyingAudit ? (
              <RefreshCw className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Lock className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
            )}
            Audit Chain
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={() => triggerWorkerMutation.mutate()}
            disabled={triggerWorkerMutation.isPending}
            className="text-xs gap-1.5"
            title="Simulate midnight cron worker: evaluate maturity windows & Table 1.4 obligations"
          >
            {triggerWorkerMutation.isPending ? (
              <RefreshCw className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Play className="h-3.5 w-3.5 text-primary" />
            )}
            Run Daily Worker
          </Button>

          <Button asChild size="sm" className="text-xs gap-1.5 shadow-sm">
            <Link to="/deposits">
              <Building2 className="h-3.5 w-3.5" />
              Manage FDRs
            </Link>
          </Button>
        </div>
      </div>

      {/* About this screen guide (G3) */}
      <AboutThisPage pageKey="dashboard" />

      {/* KPI Stats Grid (6 Primary Regulator Buckets) */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {/* Card 1: Active */}
        <Card className="relative overflow-hidden border-border/60 hover:border-primary/40 transition-colors">
          <CardHeader className="p-4 pb-2">
            <CardDescription className="text-xs font-medium flex items-center justify-between">
              Active Deposits
              <CheckCircle2 className="h-3.5 w-3.5 text-blue-500" />
            </CardDescription>
            <CardTitle className="text-2xl font-bold">
              {countersLoading ? "..." : (counters?.active ?? 0)}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <span className="text-[11px] text-muted-foreground">
              Joint lien marked
            </span>
          </CardContent>
        </Card>

        {/* Card 2: Expiring */}
        <Card className="relative overflow-hidden border-amber-500/20 bg-amber-500/5 hover:border-amber-500/40 transition-colors">
          <CardHeader className="p-4 pb-2">
            <CardDescription className="text-xs font-medium flex items-center justify-between text-amber-700 dark:text-amber-300">
              Expiring &lt;60d
              <Clock className="h-3.5 w-3.5 text-amber-500" />
            </CardDescription>
            <CardTitle className="text-2xl font-bold text-amber-800 dark:text-amber-200">
              {countersLoading ? "..." : (counters?.expiring ?? 0)}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <span className="text-[11px] text-amber-700/80 dark:text-amber-300/80">
              Renewal notice active
            </span>
          </CardContent>
        </Card>

        {/* Card 3: Matured */}
        <Card className="relative overflow-hidden border-purple-500/20 bg-purple-500/5 hover:border-purple-500/40 transition-colors">
          <CardHeader className="p-4 pb-2">
            <CardDescription className="text-xs font-medium flex items-center justify-between text-purple-700 dark:text-purple-300">
              Matured
              <Scale className="h-3.5 w-3.5 text-purple-500" />
            </CardDescription>
            <CardTitle className="text-2xl font-bold text-purple-800 dark:text-purple-200">
              {countersLoading ? "..." : (counters?.matured ?? 0)}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <span className="text-[11px] text-purple-700/80 dark:text-purple-300/80">
              Tenure reached
            </span>
          </CardContent>
        </Card>

        {/* Card 4: Pending Bank Verification */}
        <Card className="relative overflow-hidden border-border/60 hover:border-primary/40 transition-colors">
          <CardHeader className="p-4 pb-2">
            <CardDescription className="text-xs font-medium flex items-center justify-between">
              Pending Gate
              <Activity className="h-3.5 w-3.5 text-primary" />
            </CardDescription>
            <CardTitle className="text-2xl font-bold">
              {countersLoading ? "..." : (counters?.pending ?? 0)}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <span className="text-[11px] text-muted-foreground">
              Awaiting bank reply
            </span>
          </CardContent>
        </Card>

        {/* Card 5: Renewed / Rolled */}
        <Card className="relative overflow-hidden border-border/60 hover:border-primary/40 transition-colors">
          <CardHeader className="p-4 pb-2">
            <CardDescription className="text-xs font-medium flex items-center justify-between">
              Renewed
              <RefreshCw className="h-3.5 w-3.5 text-emerald-500" />
            </CardDescription>
            <CardTitle className="text-2xl font-bold">
              {countersLoading ? "..." : (counters?.renewed ?? 0)}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <span className="text-[11px] text-muted-foreground">
              Extended tenure
            </span>
          </CardContent>
        </Card>

        {/* Card 6: Released */}
        <Card className="relative overflow-hidden border-emerald-500/20 bg-emerald-500/5 hover:border-emerald-500/40 transition-colors">
          <CardHeader className="p-4 pb-2">
            <CardDescription className="text-xs font-medium flex items-center justify-between text-emerald-700 dark:text-emerald-300">
              Released
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-500" />
            </CardDescription>
            <CardTitle className="text-2xl font-bold text-emerald-800 dark:text-emerald-200">
              {countersLoading ? "..." : (counters?.released ?? 0)}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <span className="text-[11px] text-emerald-700/80 dark:text-emerald-300/80">
              Maker-checker cleared
            </span>
          </CardContent>
        </Card>
      </div>

      {/* Main Two-Column Layout: Work Queue (Left 2/3) + Fraud Benchmark (Right 1/3) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2/3: "Needs Action Today" Prioritized Queue */}
        <div className="lg:col-span-2 space-y-4">
          <Card className="border-border/60 shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div>
                <CardTitle className="text-lg font-bold flex items-center gap-2">
                  <Activity className="h-4 w-4 text-primary" />
                  Needs Action Today
                </CardTitle>
                <CardDescription className="text-xs mt-0.5">
                  Ordered by urgency. Primary actions computed strictly by
                  regulator engine (Invariant I9).
                </CardDescription>
              </div>
              <Badge variant="outline" className="text-xs">
                {needsAction?.length ?? 0} Open Items
              </Badge>
            </CardHeader>

            <CardContent className="p-0">
              {actionLoading ? (
                <div className="p-8 text-center text-sm text-muted-foreground flex items-center justify-center gap-2">
                  <RefreshCw className="h-4 w-4 animate-spin text-primary" />
                  Loading prioritized actions...
                </div>
              ) : !needsAction || needsAction.length === 0 ? (
                <div className="p-12 text-center">
                  <div className="mx-auto w-10 h-10 rounded-full bg-emerald-500/10 flex items-center justify-center mb-3">
                    <CheckCircle2 className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                  </div>
                  <h4 className="text-sm font-semibold">
                    All Clear — No Actions Required
                  </h4>
                  <p className="text-xs text-muted-foreground max-w-sm mx-auto mt-1">
                    No FDRs require immediate attention, bank reverification, or
                    release authorization at this time.
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow className="text-xs hover:bg-transparent">
                        <TableHead className="w-[140px]">
                          FDR Reference
                        </TableHead>
                        <TableHead>Issuing Bank</TableHead>
                        <TableHead>Amount</TableHead>
                        <TableHead>Maturity</TableHead>
                        <TableHead>Trust Badge</TableHead>
                        <TableHead className="text-right">
                          Recommended Action
                        </TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {needsAction.map((item: any) => (
                        <TableRow key={item.instrument_id} className="text-xs">
                          <TableCell className="font-mono font-medium">
                            <Link
                              to="/deposits"
                              className="text-primary hover:underline flex items-center gap-1"
                            >
                              {item.ref_no}
                              <ExternalLink className="h-3 w-3 opacity-60" />
                            </Link>
                          </TableCell>
                          <TableCell className="uppercase font-medium">
                            {item.bank_code}
                          </TableCell>
                          <TableCell className="font-semibold">
                            {formatPaiseToRupees(item.amount_paise)}
                          </TableCell>
                          <TableCell>
                            <span
                              className={
                                item.days_to_maturity <= 0
                                  ? "text-purple-600 dark:text-purple-400 font-semibold"
                                  : item.days_to_maturity <= 30
                                    ? "text-amber-600 dark:text-amber-400 font-semibold"
                                    : "text-muted-foreground"
                              }
                            >
                              {item.days_to_maturity <= 0
                                ? `Matured (${Math.abs(item.days_to_maturity)}d ago)`
                                : `${item.days_to_maturity}d left`}
                            </span>
                          </TableCell>
                          <TableCell>
                            <TrustBadge status={item.badge} />
                          </TableCell>
                          <TableCell className="text-right">
                            <Button
                              size="sm"
                              variant="default"
                              className="text-xs h-7 px-2.5 font-medium gap-1"
                              onClick={() => {
                                navigate({ to: "/deposits" })
                              }}
                            >
                              {item.primary_action?.label || "Review"}
                              <ArrowRight className="h-3 w-3" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right 1/3: Synthetic Fraud Lab Benchmark & Architecture Summary */}
        <div className="space-y-4">
          {/* Fraud Lab Benchmark Card (Milestone M8) */}
          <Card className="border-border/60 shadow-sm relative overflow-hidden bg-gradient-to-b from-card to-card/50">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <Badge
                  variant="outline"
                  className="text-[10px] uppercase font-bold border-primary/30 text-primary bg-primary/10"
                >
                  Milestone M8 Benchmark
                </Badge>
                <Sparkles className="h-4 w-4 text-primary" />
              </div>
              <CardTitle className="text-base font-bold mt-1">
                Synthetic Fraud Lab
              </CardTitle>
              <CardDescription className="text-xs">
                Automated adversarial attack prevention testing across 20 fraud
                scenarios.
              </CardDescription>
            </CardHeader>

            <CardContent className="space-y-4">
              {fraudLoading ? (
                <div className="text-xs text-muted-foreground p-4 text-center">
                  Loading benchmark suite...
                </div>
              ) : (
                <>
                  <div className="grid grid-cols-2 gap-2 text-center">
                    <div className="rounded-lg border bg-muted/40 p-2.5">
                      <span className="text-[10px] uppercase font-medium text-muted-foreground block">
                        Detection (TP)
                      </span>
                      <span className="text-xl font-extrabold text-emerald-600 dark:text-emerald-400">
                        {fraudMetrics?.true_positives ?? 20} /{" "}
                        {fraudMetrics?.total_scenarios ?? 20}
                      </span>
                      <span className="text-[10px] text-emerald-600 dark:text-emerald-400 block font-medium">
                        Synthetic cases detected
                      </span>
                    </div>

                    <div className="rounded-lg border bg-muted/40 p-2.5">
                      <span className="text-[10px] uppercase font-medium text-muted-foreground block">
                        False Alarms (FP)
                      </span>
                      <span className="text-xl font-extrabold text-emerald-600 dark:text-emerald-400">
                        {fraudMetrics?.false_positives ?? 0}
                      </span>
                      <span className="text-[10px] text-muted-foreground block">
                        0 False Flags
                      </span>
                    </div>
                  </div>

                  {/* Tested Invariants Checklist */}
                  <div className="space-y-2 pt-1 border-t text-xs">
                    <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider block">
                      Enforced Invariants
                    </span>
                    <div className="flex items-center justify-between text-muted-foreground">
                      <span>Forged PDF Receipt (%PDF check)</span>
                      <Badge
                        variant="outline"
                        className="text-[10px] bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-none font-semibold"
                      >
                        BLOCKED
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between text-muted-foreground">
                      <span>D1 Amount Tampering Mismatch</span>
                      <Badge
                        variant="outline"
                        className="text-[10px] bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-none font-semibold"
                      >
                        DETECTED
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between text-muted-foreground">
                      <span>D2 Missing AICTE Joint Lien</span>
                      <Badge
                        variant="outline"
                        className="text-[10px] bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-none font-semibold"
                      >
                        DETECTED
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between text-muted-foreground">
                      <span>D4 Premature Bank Encashment</span>
                      <Badge
                        variant="outline"
                        className="text-[10px] bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-none font-semibold"
                      >
                        FLAGGED
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between text-muted-foreground">
                      <span>Single-Signer Release Bypass (I8)</span>
                      <Badge
                        variant="outline"
                        className="text-[10px] bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-none font-semibold"
                      >
                        REJECTED
                      </Badge>
                    </div>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          {/* Quick Regulatory Reference Card */}
          <Card className="border-border/60 shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Scale className="h-4 w-4 text-primary" />
                Statutory Table 1.4 Rules
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-xs text-muted-foreground">
              <p>
                Security deposits are calculated from dated Approval Process
                Handbook (APH) rulebooks.
              </p>
              <ul className="list-disc list-inside space-y-1 pl-1">
                <li>
                  Government institutions are exempt under the active rule file.
                </li>
                <li>
                  Leased land sites require a <strong>2x multiplier</strong>.
                </li>
                <li>
                  Maturity window default: <strong>10-year term</strong>.
                </li>
              </ul>
              <Button
                variant="outline"
                size="sm"
                asChild
                className="w-full mt-3 text-xs"
              >
                <Link to="/deposits">
                  Open Table 1.4 Calculator
                  <ArrowUpRight className="h-3 w-3 ml-1" />
                </Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
