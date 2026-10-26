import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import {
  AlertTriangle,
  ArrowRight,
  Building2,
  Calculator,
  Check,
  CheckCircle2,
  Clock,
  FileCheck,
  Lock,
  Plus,
  RefreshCw,
  Search,
  Shield,
  ShieldCheck,
  Upload,
  XCircle,
} from "lucide-react"
import { useState } from "react"
import { toast } from "sonner"

import {
  BankService,
  DashboardService,
  DepositsService,
  InstrumentsService,
} from "@/client"
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
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

export const Route = createFileRoute("/_layout/deposits")({
  component: Deposits,
  head: () => ({
    meta: [
      {
        title: "Deposits & FDR Repository — AICTE Portal",
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
  switch (status?.toLowerCase()) {
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
        <Badge variant="destructive" className="font-medium gap-1">
          <XCircle className="h-3.5 w-3.5" />
          Discrepant
        </Badge>
      )
    default:
      return <Badge variant="outline">{status || "Unknown"}</Badge>
  }
}

function LifecycleBadge({ lifecycle }: { lifecycle: string }) {
  const norm = (lifecycle || "").toUpperCase()
  if (norm === "ACTIVE") {
    return (
      <Badge
        variant="outline"
        className="bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20 font-medium"
      >
        ACTIVE
      </Badge>
    )
  }
  if (norm === "PENDING" || norm === "PENDING_VERIFICATION") {
    return (
      <Badge
        variant="outline"
        className="bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20 font-medium"
      >
        PENDING
      </Badge>
    )
  }
  if (norm === "MATURED") {
    return (
      <Badge
        variant="outline"
        className="bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20 font-medium"
      >
        MATURED
      </Badge>
    )
  }
  if (norm === "RELEASED") {
    return (
      <Badge
        variant="outline"
        className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 font-medium"
      >
        RELEASED
      </Badge>
    )
  }
  return <Badge variant="outline">{lifecycle}</Badge>
}

interface SearchResultItem {
  id: string
  ref_no: string
  bank_code: string
  amount_paise: number
  issue_date: string
  maturity_date: string
  region: string
  lifecycle: string
  badge: string
  institution_name: string
}

interface SearchResponse {
  results: SearchResultItem[]
  count: number
}

function Deposits() {
  const queryClient = useQueryClient()

  // Filter state
  const [searchQuery, setSearchQuery] = useState("")
  const [lifecycleFilter, setLifecycleFilter] = useState("all")
  const [badgeFilter, setBadgeFilter] = useState("all")

  // Modal controls
  const [isSubmitModalOpen, setIsSubmitModalOpen] = useState(false)
  const [isCalcModalOpen, setIsCalcModalOpen] = useState(false)
  const [isSimModalOpen, setIsSimModalOpen] = useState(false)
  const [selectedInstForSim, setSelectedInstForSim] = useState<any>(null)
  const [isGateResultModalOpen, setIsGateResultModalOpen] = useState(false)
  const [activeGateReport, setActiveGateReport] = useState<any>(null)
  const [isLoadingGateReport, setIsLoadingGateReport] = useState(false)

  // 1. Fetch Instruments via search
  const { data: searchData, isLoading: instrumentsLoading } =
    useQuery<SearchResponse>({
      queryKey: [
        "instruments-search",
        searchQuery,
        lifecycleFilter,
        badgeFilter,
      ],
      queryFn: async () => {
        const res = await DashboardService.searchInstruments({
          query: {
            q: searchQuery || undefined,
            lifecycle: lifecycleFilter !== "all" ? lifecycleFilter : undefined,
            badge: badgeFilter !== "all" ? badgeFilter : undefined,
          },
        })
        return (
          (res.data as unknown as SearchResponse) || { results: [], count: 0 }
        )
      },
    })

  // Fetch Table 1.4 Programmes from Rule File via API
  const { data: programmesData } = useQuery<{
    programmes: Array<{ name: string; amount_paise: number }>
    deposit_term_years: number
    leased_private_multiplier: number
    government_exempt: boolean
    edition: string
  }>({
    queryKey: ["deposits-programmes"],
    queryFn: async () => {
      const res = await client.get<any>({
        url: "/api/v1/deposits/programmes",
      })
      return res.data
    },
  })

  // S5: Institution Security Deposit Coverage Query
  const { data: coverageData } = useQuery<{
    required_paise: number
    confirmed_active_paise: number
    claimed_only_paise: number
    shortfall_paise: number
    is_compliant: boolean
    multiplier: number
    is_government: boolean
    institution_name?: string
  }>({
    queryKey: ["institution-coverage"],
    queryFn: async () => {
      const res = await client.get<any>({
        url: "/api/v1/deposits/coverage",
      })
      return res.data
    },
  })

  // 2. Submission Form State
  const [submitStep, setSubmitStep] = useState(1)
  const [formProgramme, setFormProgramme] = useState("")
  const [formRefNo, setFormRefNo] = useState("")
  const [formBankCode, setFormBankCode] = useState("SBI")
  const [formIfsc, setFormIfsc] = useState("SBIN0001234")
  const [formAmountRupees, setFormAmountRupees] = useState("3500000") // 35 Lakhs default
  const [formIssueDate, setFormIssueDate] = useState("2024-04-01")
  const [formMaturityDate, setFormMaturityDate] = useState("2034-04-01")
  const [formLienMarked, setFormLienMarked] = useState(true)
  const [uploadedDocId, setUploadedDocId] = useState<string | null>(null)
  const [isUploadingDoc, setIsUploadingDoc] = useState(false)

  // Submit Mutation
  const submitInstrumentMutation = useMutation({
    mutationFn: async () => {
      const amountPaise = Math.round(Number(formAmountRupees) * 100)
      const res = await InstrumentsService.submitInstrument({
        body: {
          ref_no: formRefNo,
          bank_code: formBankCode,
          ifsc: formIfsc,
          amount_paise: amountPaise,
          issue_date: formIssueDate,
          maturity_date: formMaturityDate,
          lien_marked: formLienMarked,
          kind: "fdr",
          document_ids: uploadedDocId ? [uploadedDocId] : [],
        },
      })
      return res.data
    },
    onSuccess: (data: any) => {
      toast.success("FDR Submitted Successfully", {
        description: `Reference: ${data?.ref_no}. Stored in AES-256-GCM vault with pending bank verification.`,
      })
      queryClient.invalidateQueries({ queryKey: ["instruments-search"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard-counters"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard-needs-action"] })
      setIsSubmitModalOpen(false)
      resetSubmitForm()
    },
    onError: (err: any) => {
      toast.error("Submission Failed", {
        description: err?.message || "Failed to submit instrument",
      })
    },
  })

  const resetSubmitForm = () => {
    setSubmitStep(1)
    setFormRefNo("")
    setFormProgramme("")
    setUploadedDocId(null)
  }

  // Handle Mock Vault File Upload with Magic Byte Validation
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setIsUploadingDoc(true)
    try {
      // In-browser magic byte check: PDF starts with %PDF
      const header = await file.slice(0, 4).text()
      if (!header.startsWith("%PDF")) {
        toast.error("Invalid File Format (Invariant I3)", {
          description:
            "Scanned FDR receipt must be a valid PDF document starting with '%PDF' magic header.",
        })
        setIsUploadingDoc(false)
        return
      }

      // Upload to document vault
      const formData = new FormData()
      formData.append("file", file)
      formData.append("kind", "fdr_scan")

      const res = await client.post<any>({
        url: "/api/v1/documents/upload",
        body: formData,
      })

      setUploadedDocId(res.data.id)
      toast.success("Document Encrypted & Vaulted", {
        description: `Stored with AES-256-GCM encryption. SHA-256 Fingerprint: ${res.data.sha256?.substring(0, 16)}...`,
      })
    } catch (err: any) {
      toast.error("Vault Upload Failed", {
        description: err?.message || "Could not upload document",
      })
    } finally {
      setIsUploadingDoc(false)
    }
  }

  // 3. Calculator State
  const [calcProgramme, setCalcProgramme] = useState(
    "Engineering and Technology",
  )
  const [calcOwnership, setCalcOwnership] = useState("owned")
  const [calcType, setCalcType] = useState("private")
  const [calcResult, setCalcResult] = useState<any>(null)
  const [isCalculating, setIsCalculating] = useState(false)

  const handleCalculate = async () => {
    setIsCalculating(true)
    try {
      const res = await DepositsService.calculateDeposit({
        query: {
          programmes: calcProgramme,
          land_ownership: calcOwnership,
          institution_type: calcType,
        },
      })
      setCalcResult(res.data)
      toast.success("Statutory Deposit Calculated", {
        description: `Required: ${formatPaiseToRupees(res.data.required_deposit_paise)} under ${res.data.rule_edition}`,
      })
    } catch (e: any) {
      toast.error("Calculation failed", {
        description: e?.message || "Rule calculation error",
      })
    } finally {
      setIsCalculating(false)
    }
  }

  // 4. Bank Simulator State
  const [simScenario, setSimScenario] = useState("valid")
  const [isSimulating, setIsSimulating] = useState(false)

  const handleInspectGate = async (inst: any) => {
    setIsLoadingGateReport(true)
    try {
      const res = await client.get<any>({
        url: `/api/v1/bank/verification-results/${inst.id}`,
      })
      setActiveGateReport(res.data)
      setIsGateResultModalOpen(true)
    } catch (e: any) {
      toast.error("Failed to load verification report", {
        description: e?.message || "Error fetching gate results",
      })
    } finally {
      setIsLoadingGateReport(false)
    }
  }

  const handleRunBankSimulation = async () => {
    if (!selectedInstForSim) return
    setIsSimulating(true)
    try {
      const res = await BankService.simulateBankConfirmation({
        path: {
          instrument_id: selectedInstForSim.id,
        },
        body: {
          outcome: simScenario,
        },
      })
      const data = res.data as any
      const isConfirmed = data?.status === "confirmed"
      if (isConfirmed) {
        toast.success("Bank Confirmation Passed (Verification Gate)", {
          description: `Bank verified FDR ${selectedInstForSim.ref_no}. Trust badge updated to CONFIRMED.`,
        })
      } else {
        toast.warning("Discrepancy Detected by Gate", {
          description: `Discrepancy ${data?.discrepancy || "Flagged"}: Badge updated to CHANGED / DISCREPANT.`,
        })
      }
      queryClient.invalidateQueries({ queryKey: ["instruments-search"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard-counters"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard-needs-action"] })
      setIsSimModalOpen(false)
      setActiveGateReport({
        ...data,
        ref_no: selectedInstForSim.ref_no,
      })
      setIsGateResultModalOpen(true)
    } catch (e: any) {
      toast.error("Bank simulator request failed", {
        description: e?.message || "Simulator error",
      })
    } finally {
      setIsSimulating(false)
    }
  }

  return (
    <div className="flex flex-col gap-6 pb-12">
      {/* Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-semibold text-primary uppercase tracking-wider">
              Statutory Vault
            </span>
            <span className="text-xs text-muted-foreground">•</span>
            <span className="text-xs text-muted-foreground font-mono">
              AES-256-GCM Encrypted
            </span>
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight">
            Security Deposits & FDR Repository
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Registered Fixed Deposit Receipts held in joint lien with AICTE
            under Table 1.4 regulations.
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-2.5">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setIsCalcModalOpen(true)
              if (!calcResult) handleCalculate()
            }}
            className="text-xs gap-1.5"
          >
            <Calculator className="h-3.5 w-3.5 text-primary" />
            Table 1.4 Calculator
          </Button>

          <Button
            size="sm"
            onClick={() => {
              setFormRefNo(
                `FDR-${formBankCode}-${Date.now().toString().slice(-6)}`,
              )
              setIsSubmitModalOpen(true)
            }}
            className="text-xs gap-1.5 shadow-sm"
          >
            <Plus className="h-3.5 w-3.5" />
            Submit FDR
          </Button>
        </div>
      </div>

      {/* About this screen guide (G3) */}
      <AboutThisPage pageKey="calculator" />

      {/* S5: Institution Coverage Card */}
      {coverageData && (
        <Card className="border-border/60 shadow-sm bg-gradient-to-r from-primary/5 via-card to-card">
          <CardHeader className="pb-3 flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-primary" />
                Table 1.4 Deposit Coverage (DEMO values) —{" "}
                {coverageData.institution_name || "Institution Obligation"}
              </CardTitle>
              <CardDescription className="text-xs">
                Computed per Table 1.4 APH ({coverageData.multiplier}x
                multiplier •{" "}
                {coverageData.is_government
                  ? "Government Exempt"
                  : "Private Institution"}
                )
              </CardDescription>
            </div>
            <Badge
              variant={coverageData.is_compliant ? "default" : "destructive"}
              className="text-xs"
            >
              {coverageData.is_compliant
                ? "Fully Covered (DEMO values)"
                : `Shortfall: ${formatPaiseToRupees(coverageData.shortfall_paise)}`}
            </Badge>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
              <div className="p-2.5 bg-background/80 rounded border">
                <div className="text-muted-foreground text-[11px]">
                  Table 1.4 Required (DEMO)
                </div>
                <div className="text-base font-bold font-mono text-foreground mt-0.5">
                  {formatPaiseToRupees(coverageData.required_paise)}
                </div>
              </div>
              <div className="p-2.5 bg-background/80 rounded border">
                <div className="text-emerald-600 dark:text-emerald-400 text-[11px]">
                  Confirmed Active (CBS)
                </div>
                <div className="text-base font-bold font-mono text-emerald-600 dark:text-emerald-400 mt-0.5">
                  {formatPaiseToRupees(coverageData.confirmed_active_paise)}
                </div>
              </div>
              <div className="p-2.5 bg-background/80 rounded border">
                <div className="text-amber-600 dark:text-amber-400 text-[11px]">
                  Claimed Only (Unverified)
                </div>
                <div className="text-base font-bold font-mono text-amber-600 dark:text-amber-400 mt-0.5">
                  {formatPaiseToRupees(coverageData.claimed_only_paise)}
                </div>
              </div>
              <div className="p-2.5 bg-background/80 rounded border">
                <div className="text-destructive text-[11px]">
                  Statutory Shortfall
                </div>
                <div className="text-base font-bold font-mono text-destructive mt-0.5">
                  {formatPaiseToRupees(coverageData.shortfall_paise)}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Filter Toolbar */}
      <Card className="border-border/60 shadow-sm p-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 items-center">
          {/* Search Query */}
          <div className="relative md:col-span-2">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search by FDR reference or institution name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 text-xs h-9"
            />
          </div>

          {/* Lifecycle Filter */}
          <div>
            <Select value={lifecycleFilter} onValueChange={setLifecycleFilter}>
              <SelectTrigger className="text-xs h-9">
                <SelectValue placeholder="All Lifecycles" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Lifecycles</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="pending">Pending Verification</SelectItem>
                <SelectItem value="matured">Matured</SelectItem>
                <SelectItem value="released">Released</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Trust Badge Filter */}
          <div>
            <Select value={badgeFilter} onValueChange={setBadgeFilter}>
              <SelectTrigger className="text-xs h-9">
                <SelectValue placeholder="All Trust Badges" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Trust Badges</SelectItem>
                <SelectItem value="confirmed">Confirmed (Verified)</SelectItem>
                <SelectItem value="claimed">Claimed (Pending)</SelectItem>
                <SelectItem value="stale">Stale (Overdue)</SelectItem>
                <SelectItem value="changed">Discrepant / Changed</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </Card>

      {/* Instruments Data Table */}
      <Card className="border-border/60 shadow-sm">
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <div>
            <CardTitle className="text-base font-bold flex items-center gap-2">
              <FileCheck className="h-4 w-4 text-primary" />
              Registered Fixed Deposit Receipts
            </CardTitle>
            <CardDescription className="text-xs mt-0.5">
              Row-level security active. Showing {searchData?.count ?? 0}{" "}
              instruments scoped to your regional jurisdiction.
            </CardDescription>
          </div>
          <Badge variant="outline" className="text-xs font-mono">
            {searchData?.count ?? 0} Records
          </Badge>
        </CardHeader>

        <CardContent className="p-0">
          {instrumentsLoading ? (
            <div className="p-12 text-center text-sm text-muted-foreground flex items-center justify-center gap-2">
              <RefreshCw className="h-4 w-4 animate-spin text-primary" />
              Loading FDR repository records...
            </div>
          ) : !searchData?.results || searchData.results.length === 0 ? (
            <div className="p-16 text-center">
              <div className="mx-auto w-12 h-12 rounded-full bg-muted flex items-center justify-center mb-3">
                <Building2 className="h-6 w-6 text-muted-foreground" />
              </div>
              <h3 className="text-base font-semibold">No FDR records found</h3>
              <p className="text-xs text-muted-foreground max-w-sm mx-auto mt-1 mb-4">
                No deposit records match your search criteria. Submit a new FDR
                or reset filters.
              </p>
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  setSearchQuery("")
                  setLifecycleFilter("all")
                  setBadgeFilter("all")
                }}
                className="text-xs"
              >
                Reset Search Filters
              </Button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="text-xs hover:bg-transparent">
                    <TableHead className="w-[160px]">FDR Reference</TableHead>
                    <TableHead>Institution</TableHead>
                    <TableHead>Bank & Region</TableHead>
                    <TableHead>Principal Amount</TableHead>
                    <TableHead>Maturity Date</TableHead>
                    <TableHead>Trust Badge</TableHead>
                    <TableHead>Lifecycle</TableHead>
                    <TableHead className="text-right">Verification</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {searchData.results.map((inst: any) => (
                    <TableRow
                      key={inst.id}
                      className="text-xs hover:bg-muted/40"
                    >
                      <TableCell className="font-mono font-medium">
                        {inst.ref_no}
                      </TableCell>
                      <TableCell className="font-medium max-w-[200px] truncate">
                        {inst.institution_name || "Technical Institute"}
                      </TableCell>
                      <TableCell>
                        <span className="uppercase font-semibold">
                          {inst.bank_code}
                        </span>
                        <span className="text-[10px] text-muted-foreground ml-1.5 uppercase">
                          ({inst.region})
                        </span>
                      </TableCell>
                      <TableCell className="font-semibold">
                        {formatPaiseToRupees(inst.amount_paise)}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {inst.maturity_date}
                      </TableCell>
                      <TableCell>
                        <TrustBadge status={inst.badge} />
                      </TableCell>
                      <TableCell>
                        <LifecycleBadge lifecycle={inst.lifecycle} />
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <Button
                            size="sm"
                            variant="outline"
                            asChild
                            className="text-xs h-7 px-2 font-medium gap-1 text-primary hover:text-primary"
                            title="Open detailed case record, discrepancy analysis & release panel"
                          >
                            <Link
                              to="/instruments/$id"
                              params={{ id: inst.id }}
                            >
                              Case View
                            </Link>
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleInspectGate(inst)}
                            disabled={isLoadingGateReport}
                            className="text-xs h-7 px-2 font-medium gap-1"
                            title="Inspect real cryptographic gate & content checks"
                          >
                            <FileCheck className="h-3 w-3 text-muted-foreground" />
                            Gate Results
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => {
                              setSelectedInstForSim(inst)
                              setIsSimModalOpen(true)
                            }}
                            className="text-xs h-7 px-2 font-medium gap-1"
                            title="Simulate bank verification gate (I3)"
                          >
                            <ShieldCheck className="h-3 w-3 text-primary" />
                            Simulate Gate
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 1. Modal: Submit New FDR (4-Step Flow) */}
      <Dialog open={isSubmitModalOpen} onOpenChange={setIsSubmitModalOpen}>
        <DialogContent className="sm:max-w-[540px]">
          <DialogHeader>
            <div className="flex items-center gap-2">
              <Badge
                variant="outline"
                className="text-[10px] uppercase font-bold border-primary/30 text-primary"
              >
                Step {submitStep} of 4
              </Badge>
              <DialogTitle className="text-lg font-bold">
                Register Fixed Deposit Receipt
              </DialogTitle>
            </div>
            <DialogDescription className="text-xs">
              Direct submission into regulator ledger. Documents are stored in
              an AES-256-GCM encrypted vault.
            </DialogDescription>
          </DialogHeader>

          {/* Step 1: Metadata */}
          {submitStep === 1 && (
            <div className="space-y-3 py-2 text-xs">
              <div className="space-y-1">
                <Label htmlFor="refNo" className="text-xs font-semibold">
                  FDR Reference Number *
                </Label>
                <Input
                  id="refNo"
                  value={formRefNo}
                  onChange={(e) => setFormRefNo(e.target.value)}
                  className="font-mono text-xs h-8"
                  placeholder="e.g. FDR-SBI-102938"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <Label htmlFor="bankCode" className="text-xs font-semibold">
                    Issuing Bank Code *
                  </Label>
                  <Select value={formBankCode} onValueChange={setFormBankCode}>
                    <SelectTrigger id="bankCode" className="text-xs h-8">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="SBI">
                        State Bank of India (SBI)
                      </SelectItem>
                      <SelectItem value="HDFC">HDFC Bank</SelectItem>
                      <SelectItem value="ICICI">ICICI Bank</SelectItem>
                      <SelectItem value="PNB">Punjab National Bank</SelectItem>
                      <SelectItem value="CANARA">Canara Bank</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1">
                  <Label htmlFor="ifsc" className="text-xs font-semibold">
                    Branch IFSC *
                  </Label>
                  <Input
                    id="ifsc"
                    value={formIfsc}
                    onChange={(e) => setFormIfsc(e.target.value.toUpperCase())}
                    className="font-mono text-xs h-8 uppercase"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <Label className="text-xs font-semibold">
                  Select APH Table 1.4 Programme (from Rulebook)
                </Label>
                <Select
                  value={formProgramme}
                  onValueChange={(val) => {
                    setFormProgramme(val)
                    const found = programmesData?.programmes?.find(
                      (p) => p.name === val,
                    )
                    if (found) {
                      setFormAmountRupees((found.amount_paise / 100).toString())
                    }
                  }}
                >
                  <SelectTrigger className="text-xs h-8">
                    <SelectValue placeholder="Select programme to auto-fill amount" />
                  </SelectTrigger>
                  <SelectContent>
                    {programmesData?.programmes?.map((p) => (
                      <SelectItem key={p.name} value={p.name}>
                        {p.name} ({formatPaiseToRupees(p.amount_paise)})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1">
                <Label htmlFor="amount" className="text-xs font-semibold">
                  Principal Amount (in ₹ Rupees) *
                </Label>
                <Input
                  id="amount"
                  type="number"
                  value={formAmountRupees}
                  onChange={(e) => setFormAmountRupees(e.target.value)}
                  className="font-semibold text-xs h-8"
                />
                <span className="text-[10px] text-muted-foreground">
                  Stored as integer paise:{" "}
                  {Math.round(
                    Number(formAmountRupees || 0) * 100,
                  ).toLocaleString("en-IN")}{" "}
                  paise (
                  {formatPaiseToRupees(
                    Math.round(Number(formAmountRupees || 0) * 100),
                  )}
                  )
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <Label htmlFor="issueDate" className="text-xs font-semibold">
                    Issue Date *
                  </Label>
                  <Input
                    id="issueDate"
                    type="date"
                    value={formIssueDate}
                    onChange={(e) => setFormIssueDate(e.target.value)}
                    className="text-xs h-8"
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="matDate" className="text-xs font-semibold">
                    Maturity Date *
                  </Label>
                  <Input
                    id="matDate"
                    type="date"
                    value={formMaturityDate}
                    onChange={(e) => setFormMaturityDate(e.target.value)}
                    className="text-xs h-8"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Step 2: Encrypted Vault Upload */}
          {submitStep === 2 && (
            <div className="space-y-4 py-2 text-xs">
              <div className="rounded-lg border border-primary/20 bg-primary/5 p-3 space-y-1.5">
                <div className="flex items-center gap-1.5 font-semibold text-primary text-xs">
                  <Lock className="h-3.5 w-3.5" />
                  Encrypted Vault Storage (Invariant I3)
                </div>
                <p className="text-[11px] text-muted-foreground leading-relaxed">
                  Scanned FDR certificates must be valid PDF files. Each file is
                  validated for the <code>%PDF</code> magic header, encrypted
                  with <strong>AES-256-GCM</strong> using an envelope key, and
                  fingerprinted with a SHA-256 checksum before persistence.
                </p>
              </div>

              <div className="space-y-2">
                <Label className="text-xs font-semibold">
                  Upload Scanned FDR Receipt (PDF) *
                </Label>
                <div className="border border-dashed rounded-lg p-6 text-center space-y-2">
                  <Upload className="h-8 w-8 mx-auto text-muted-foreground" />
                  <div>
                    <input
                      type="file"
                      id="fdrUpload"
                      accept="application/pdf"
                      onChange={handleFileUpload}
                      className="hidden"
                    />
                    <label
                      htmlFor="fdrUpload"
                      className="cursor-pointer inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
                    >
                      Browse PDF document from disk
                    </label>
                  </div>
                  <p className="text-[10px] text-muted-foreground">
                    Must start with %PDF magic bytes. Max file size: 10 MB.
                  </p>
                </div>
                {isUploadingDoc && (
                  <p className="text-xs text-primary flex items-center justify-center gap-1">
                    <RefreshCw className="h-3 w-3 animate-spin" /> Encrypting
                    and saving to vault...
                  </p>
                )}
                {uploadedDocId && (
                  <div className="flex items-center gap-2 p-2 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 rounded border border-emerald-500/20 text-xs">
                    <CheckCircle2 className="h-4 w-4 shrink-0" />
                    <span className="truncate">
                      Vault Document ID: {uploadedDocId}
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Step 3: Joint Lien Details */}
          {submitStep === 3 && (
            <div className="space-y-4 py-2 text-xs">
              <div className="rounded-lg border p-3 space-y-3">
                <div className="flex items-start gap-2.5">
                  <input
                    type="checkbox"
                    id="lienCheckbox"
                    checked={formLienMarked}
                    onChange={(e) => setFormLienMarked(e.target.checked)}
                    className="mt-0.5 h-4 w-4 rounded border-gray-300 text-primary"
                  />
                  <div className="space-y-0.5">
                    <Label
                      htmlFor="lienCheckbox"
                      className="font-semibold text-xs cursor-pointer"
                    >
                      Lien marked in favor of AICTE (Mandatory)
                    </Label>
                    <p className="text-[11px] text-muted-foreground">
                      The issuing bank has endorsed on the physical receipt:{" "}
                      <em>
                        "Fixed Deposit held in joint name / lien in favor of
                        Member Secretary, AICTE"
                      </em>
                      .
                    </p>
                  </div>
                </div>

                <div className="pt-2 border-t text-[11px] text-muted-foreground space-y-1">
                  <p>
                    <strong>Issuing Branch Manager:</strong> Authorized Bank
                    Officer
                  </p>
                  <p>
                    <strong>Dual Signatures:</strong> Verified on scanned
                    receipt
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Step 4: Review & Submit */}
          {submitStep === 4 && (
            <div className="space-y-3 py-2 text-xs">
              <div className="rounded-lg border bg-muted/40 p-3 space-y-2">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Reference:</span>
                  <span className="font-mono font-bold">{formRefNo}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Bank & IFSC:</span>
                  <span className="font-medium">
                    {formBankCode} ({formIfsc})
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Principal:</span>
                  <span className="font-bold text-emerald-600 dark:text-emerald-400">
                    {formatPaiseToRupees(
                      Math.round(Number(formAmountRupees || 0) * 100),
                    )}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Tenure:</span>
                  <span>
                    {formIssueDate} to {formMaturityDate}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Joint Lien:</span>
                  <span
                    className={
                      formLienMarked
                        ? "text-emerald-600 font-semibold"
                        : "text-amber-600 font-semibold"
                    }
                  >
                    {formLienMarked ? "Marked & Endorsed" : "Not Marked"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Vault Document:</span>
                  <span>{uploadedDocId ? "Encrypted (AES-GCM)" : "None"}</span>
                </div>
              </div>

              <div className="p-2.5 rounded bg-amber-500/10 border border-amber-500/20 text-[11px] text-amber-800 dark:text-amber-300">
                Submitting will trigger an automated audit entry and register
                this FDR with initial trust badge <strong>CLAIMED</strong> until
                verified by bank simulator.
              </div>
            </div>
          )}

          <DialogFooter className="flex justify-between sm:justify-between pt-2">
            {submitStep > 1 ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSubmitStep(submitStep - 1)}
                className="text-xs"
              >
                Previous
              </Button>
            ) : (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsSubmitModalOpen(false)}
                className="text-xs"
              >
                Cancel
              </Button>
            )}

            {submitStep < 4 ? (
              <Button
                size="sm"
                onClick={() => setSubmitStep(submitStep + 1)}
                className="text-xs gap-1"
                disabled={submitStep === 1 && (!formRefNo || !formAmountRupees)}
              >
                Continue
                <ArrowRight className="h-3 w-3" />
              </Button>
            ) : (
              <Button
                size="sm"
                onClick={() => submitInstrumentMutation.mutate()}
                disabled={submitInstrumentMutation.isPending}
                className="text-xs gap-1.5"
              >
                {submitInstrumentMutation.isPending ? (
                  <RefreshCw className="h-3 w-3 animate-spin" />
                ) : (
                  <Check className="h-3 w-3" />
                )}
                Confirm & Submit
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 2. Modal: Table 1.4 Calculator */}
      <Dialog open={isCalcModalOpen} onOpenChange={setIsCalcModalOpen}>
        <DialogContent className="sm:max-w-[480px]">
          <DialogHeader>
            <div className="flex items-center gap-2">
              <Calculator className="h-4 w-4 text-primary" />
              <DialogTitle className="text-base font-bold">
                Table 1.4 Statutory Deposit Calculator
              </DialogTitle>
            </div>
            <DialogDescription className="text-xs">
              Calculates mandated FDR security deposit under the Approval
              Process Handbook (APH).
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 py-2 text-xs">
            <div className="space-y-1">
              <Label className="text-xs font-semibold">
                Technical Programme (Table 1.4 Rulebook)
              </Label>
              <Select value={calcProgramme} onValueChange={setCalcProgramme}>
                <SelectTrigger className="text-xs h-8">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {programmesData?.programmes?.map((p) => (
                    <SelectItem key={p.name} value={p.name}>
                      {p.name} ({formatPaiseToRupees(p.amount_paise)} base)
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label className="text-xs font-semibold">Land Ownership</Label>
                <Select value={calcOwnership} onValueChange={setCalcOwnership}>
                  <SelectTrigger className="text-xs h-8">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="owned">Owned Land (1x)</SelectItem>
                    <SelectItem value="leased">
                      Leased Land (2x Multiplier)
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1">
                <Label className="text-xs font-semibold">
                  Institution Type
                </Label>
                <Select value={calcType} onValueChange={setCalcType}>
                  <SelectTrigger className="text-xs h-8">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="private">
                      Private / Self-Financed
                    </SelectItem>
                    <SelectItem value="government">
                      Government (Rule Exempt)
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <Button
              size="sm"
              onClick={handleCalculate}
              disabled={isCalculating}
              className="w-full text-xs mt-2"
            >
              {isCalculating ? (
                <RefreshCw className="h-3.5 w-3.5 animate-spin" />
              ) : (
                "Re-calculate Obligation"
              )}
            </Button>

            {calcResult && (
              <div className="mt-4 rounded-lg border bg-muted/40 p-3 space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">
                    Required Deposit:
                  </span>
                  <span className="text-lg font-extrabold text-primary">
                    {formatPaiseToRupees(calcResult.required_deposit_paise)}
                  </span>
                </div>
                <div className="flex justify-between text-[11px] text-muted-foreground">
                  <span>Multiplier Applied:</span>
                  <span>{calcResult.multiplier}x</span>
                </div>
                <div className="flex justify-between text-[11px] text-muted-foreground">
                  <span>Government Exemption:</span>
                  <span>{calcResult.exempt ? "YES (0 paise)" : "NO"}</span>
                </div>
                <div className="flex justify-between text-[11px] text-muted-foreground">
                  <span>Rulebook Edition:</span>
                  <span>{calcResult.rule_edition}</span>
                </div>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button
              size="sm"
              variant="outline"
              onClick={() => setIsCalcModalOpen(false)}
              className="text-xs"
            >
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 3. Modal: Bank Simulator (Full Gate Testing) */}
      <Dialog open={isSimModalOpen} onOpenChange={setIsSimModalOpen}>
        <DialogContent className="sm:max-w-[460px]">
          <DialogHeader>
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-primary" />
              <DialogTitle className="text-base font-bold">
                Bank Simulator — Invariant I3 Gate & Testing
              </DialogTitle>
            </div>
            <DialogDescription className="text-xs">
              Simulate electronic bank API response for FDR #
              {selectedInstForSim?.ref_no}. Evaluates signature gate and
              discrepancy detection.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 py-2 text-xs">
            <div className="p-2.5 rounded bg-muted/50 border space-y-1">
              <div className="flex justify-between font-mono">
                <span className="text-muted-foreground">Target FDR:</span>
                <span className="font-semibold">
                  {selectedInstForSim?.ref_no}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Principal:</span>
                <span className="font-semibold">
                  {formatPaiseToRupees(selectedInstForSim?.amount_paise || 0)}
                </span>
              </div>
            </div>

            <div className="space-y-1">
              <Label className="text-xs font-semibold">
                Simulated Bank Confirmation Scenario
              </Label>
              <Select value={simScenario} onValueChange={setSimScenario}>
                <SelectTrigger className="text-xs h-8">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="valid">
                    ✓ Valid Match (All checks pass &rarr; CONFIRMED)
                  </SelectItem>
                  <SelectItem value="d1_amount">
                    ⚠ D1 Amount Mismatch (Bank reports different sum)
                  </SelectItem>
                  <SelectItem value="d2_lien">
                    ⚠ D2 Lien Missing (Bank reports no AICTE lien)
                  </SelectItem>
                  <SelectItem value="d4_premature">
                    ⚠ D4 Premature Encashment (Account liquidated)
                  </SelectItem>
                  <SelectItem value="d5_not_found">
                    ⚠ D5 Account Not Found (Non-existent FDR)
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="rounded p-2 text-[11px] bg-primary/5 border border-primary/20 text-muted-foreground">
              Under <strong>Invariant I3</strong>, a bank reply passes only if
              the signature gate holds and all confirmed fields match the
              declared instrument.
            </div>
          </div>

          <DialogFooter className="pt-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => setIsSimModalOpen(false)}
              className="text-xs"
            >
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={handleRunBankSimulation}
              disabled={isSimulating}
              className="text-xs gap-1"
            >
              {isSimulating ? (
                <RefreshCw className="h-3 w-3 animate-spin" />
              ) : (
                <Shield className="h-3 w-3" />
              )}
              Execute Bank Gate
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 4. Modal: Cryptographic Gate & Content Verification Results */}
      <Dialog
        open={isGateResultModalOpen}
        onOpenChange={setIsGateResultModalOpen}
      >
        <DialogContent className="sm:max-w-[620px] max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-5 w-5 text-primary" />
                <DialogTitle className="text-base font-bold">
                  Verification Gate & Field Matching Report
                </DialogTitle>
              </div>
              {activeGateReport?.trust_badge && (
                <TrustBadge status={activeGateReport.trust_badge} />
              )}
            </div>
            <DialogDescription className="text-xs">
              Live verification gate output for FDR #
              {activeGateReport?.ref_no || selectedInstForSim?.ref_no}.
              Signature gate is evaluated independently from content comparison.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2 text-xs">
            {/* Group 1: Signature Checks (The Gate - 8 checks) */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h4 className="font-semibold text-xs tracking-wide uppercase text-muted-foreground">
                  1. Signature & Cryptographic Gate (8 Checks)
                </h4>
                <span className="text-[11px] text-muted-foreground font-mono">
                  Invariant I3
                </span>
              </div>
              <div className="rounded-md border divide-y bg-card">
                {activeGateReport?.signature_gate?.map((chk: any) => (
                  <div
                    key={chk.id}
                    className="flex items-center justify-between p-2 text-xs"
                  >
                    <div className="space-y-0.5">
                      <div className="font-medium flex items-center gap-1.5">
                        {chk.status === "passed" ? (
                          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                        ) : chk.status === "not_checked" ? (
                          <Clock className="h-3.5 w-3.5 text-amber-500" />
                        ) : (
                          <XCircle className="h-3.5 w-3.5 text-rose-600" />
                        )}
                        <span>{chk.label}</span>
                      </div>
                      <p className="text-[11px] text-muted-foreground">
                        {chk.detail}
                      </p>
                    </div>
                    <div>
                      {chk.status === "passed" ? (
                        <Badge
                          variant="outline"
                          className="text-[10px] bg-emerald-50 text-emerald-700 border-emerald-300 dark:bg-emerald-950/40 dark:text-emerald-300"
                        >
                          PASSED
                        </Badge>
                      ) : chk.status === "not_checked" ? (
                        <Badge
                          variant="outline"
                          className="text-[10px] bg-amber-50 text-amber-700 border-amber-300 dark:bg-amber-950/40 dark:text-amber-300"
                        >
                          NOT CHECKED (Simulated CA)
                        </Badge>
                      ) : (
                        <Badge
                          variant="outline"
                          className="text-[10px] bg-rose-50 text-rose-700 border-rose-300 dark:bg-rose-950/40 dark:text-rose-300"
                        >
                          FAILED
                        </Badge>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Group 2: Content Checks (Claimed vs Bank Confirmed - 5 checks) */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h4 className="font-semibold text-xs tracking-wide uppercase text-muted-foreground">
                  2. Content Discrepancy Checks (Claimed vs Confirmed)
                </h4>
                <span className="text-[11px] text-muted-foreground font-mono">
                  5 Field Checks
                </span>
              </div>
              <div className="rounded-md border overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/50 text-[11px]">
                      <TableHead className="h-7 font-semibold">Field</TableHead>
                      <TableHead className="h-7 font-semibold">
                        Declared
                      </TableHead>
                      <TableHead className="h-7 font-semibold">
                        Bank Confirmed
                      </TableHead>
                      <TableHead className="h-7 font-semibold text-right">
                        Result
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {activeGateReport?.content_checks?.map((chk: any) => {
                      const formatVal = (val: any, id: string) => {
                        if (val === null || val === undefined) return "—"
                        if (id === "amount_paise")
                          return formatPaiseToRupees(Number(val))
                        if (typeof val === "boolean")
                          return val ? "Confirmed (AICTE Lien)" : "No Lien"
                        return String(val)
                      }
                      return (
                        <TableRow key={chk.id} className="text-xs">
                          <TableCell className="font-medium py-2">
                            {chk.label}
                          </TableCell>
                          <TableCell className="font-mono text-[11px] text-muted-foreground py-2">
                            {formatVal(chk.declared, chk.id)}
                          </TableCell>
                          <TableCell className="font-mono text-[11px] font-semibold py-2">
                            {formatVal(chk.confirmed, chk.id)}
                          </TableCell>
                          <TableCell className="text-right py-2">
                            {chk.passed ? (
                              <Badge
                                variant="outline"
                                className="text-[10px] bg-emerald-50 text-emerald-700 border-emerald-300"
                              >
                                MATCH
                              </Badge>
                            ) : (
                              <Badge
                                variant="outline"
                                className="text-[10px] bg-rose-50 text-rose-700 border-rose-300"
                              >
                                MISMATCH
                              </Badge>
                            )}
                          </TableCell>
                        </TableRow>
                      )
                    })}
                  </TableBody>
                </Table>
              </div>
            </div>
          </div>

          <DialogFooter className="pt-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => setIsGateResultModalOpen(false)}
              className="text-xs"
            >
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
