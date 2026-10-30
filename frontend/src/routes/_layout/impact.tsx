import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import {
  Activity,
  Award,
  Building2,
  CheckCircle2,
  FileCheck2,
  Landmark,
  ShieldAlert,
  ShieldCheck,
  TrendingUp,
} from "lucide-react"

import { DashboardService } from "@/client/sdk.gen"
import { AboutThisPage } from "@/components/Common/AboutThisPage"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

export const Route = createFileRoute("/_layout/impact")({
  component: ImpactDashboard,
})

interface ImpactMetric {
  id: string
  label: string
  formatted: string
  category: string
  description: string
  value_paise?: number
  count?: number
}

function ImpactDashboard() {
  const { data, isLoading } = useQuery({
    queryKey: ["impact-metrics"],
    queryFn: async () => {
      const res = await DashboardService.getImpactMetrics()
      return res.data as {
        status: string
        metrics: ImpactMetric[]
        scope: {
          institutions_enrolled: number
          instruments_total: number
        }
      }
    },
  })

  if (isLoading || !data) {
    return (
      <div className="p-8 text-muted-foreground animate-pulse">
        Computing live regulatory impact metrics...
      </div>
    )
  }

  const { metrics, scope } = data

  const getMetricIcon = (id: string) => {
    switch (id) {
      case "corpus_protected_inr":
        return <Landmark className="h-6 w-6 text-primary" />
      case "active_lien_paise":
        return (
          <ShieldCheck className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
        )
      case "verified_bank_confirmations":
        return (
          <FileCheck2 className="h-6 w-6 text-blue-600 dark:text-blue-400" />
        )
      case "participating_banks":
        return (
          <Building2 className="h-6 w-6 text-purple-600 dark:text-purple-400" />
        )
      case "immutable_audit_events":
        return (
          <ShieldAlert className="h-6 w-6 text-amber-600 dark:text-amber-400" />
        )
      default:
        return <Activity className="h-6 w-6 text-primary" />
    }
  }

  return (
    <div className="flex flex-col gap-6 p-6 max-w-7xl mx-auto">
      <AboutThisPage pageKey="impact" />

      <div className="flex flex-wrap items-center justify-between gap-4 bg-muted/40 p-4 rounded-lg border border-border">
        <div className="flex items-center gap-3">
          <Award className="h-5 w-5 text-primary" />
          <span className="text-sm font-medium">Evaluation Scope:</span>
          <Badge variant="outline" className="font-mono">
            {scope?.institutions_enrolled ?? 0} Institutions Enrolled
          </Badge>
          <Badge variant="outline" className="font-mono">
            {scope?.instruments_total ?? 0} Active Deposit Records
          </Badge>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <CheckCircle2 className="h-4 w-4 text-emerald-600" />
          <span>
            All values dynamically computed from database state (Rule G2)
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {metrics?.map((metric) => (
          <Card
            key={metric.id}
            className="border border-border/80 shadow-sm flex flex-col justify-between"
          >
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <Badge variant="secondary" className="text-xs font-normal">
                  {metric.category}
                </Badge>
                {getMetricIcon(metric.id)}
              </div>
              <CardTitle className="text-base font-semibold mt-2">
                {metric.label}
              </CardTitle>
              <CardDescription className="text-xs line-clamp-2">
                {metric.description}
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="text-3xl font-bold tracking-tight text-foreground">
                {metric.formatted}
              </div>
              {metric.value_paise !== undefined && (
                <p className="text-xs text-muted-foreground font-mono mt-1">
                  Exact: {metric.value_paise.toLocaleString("en-IN")} paise
                </p>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="border border-border/80 mt-2">
        <CardHeader>
          <div className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-primary" />
            <CardTitle className="text-base font-semibold">
              System Impact Summary & Assurance Guarantees
            </CardTitle>
          </div>
          <CardDescription>
            defense-in-depth architecture safeguards preventing regulatory
            non-compliance and financial leakage.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 text-sm text-muted-foreground">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 rounded-md bg-muted/30 border border-border">
              <h4 className="font-semibold text-foreground mb-1">
                Dual-Custody Protection
              </h4>
              <p className="text-xs leading-relaxed">
                Relational invariant prohibits regional verifier from executing
                bureau release approval. Maker cannot be checker under any
                circumstance.
              </p>
            </div>
            <div className="p-4 rounded-md bg-muted/30 border border-border">
              <h4 className="font-semibold text-foreground mb-1">
                Cryptographic Gate
              </h4>
              <p className="text-xs leading-relaxed">
                6-point byte-level check rejects counterfeit letters,
                non-matching signers, or modified PDFs before ingestion.
              </p>
            </div>
            <div className="p-4 rounded-md bg-muted/30 border border-border">
              <h4 className="font-semibold text-foreground mb-1">
                Zero Discretionary Actions
              </h4>
              <p className="text-xs leading-relaxed">
                Buttons in user interface are fully computed from backend Finite
                State Machine (<code className="text-xs">next_action()</code>).
                No client override.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
