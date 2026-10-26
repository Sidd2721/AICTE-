import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Database,
  Gauge,
  Layers,
  Shield,
  ShieldCheck,
  Zap,
} from "lucide-react"
import { useState } from "react"

import { client } from "@/client/client.gen"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"

export const Route = createFileRoute("/_layout/evidence")({
  component: EvidenceView,
})

function EvidenceView() {
  const [activeTab, setActiveTab] = useState("status")

  const { data, isLoading } = useQuery({
    queryKey: ["evidence-summary"],
    queryFn: async () => {
      const res = await client.get({ url: "/api/v1/evidence/summary" })
      return res.data as any
    },
  })

  if (isLoading || !data) {
    return (
      <div className="p-8 text-muted-foreground animate-pulse">
        Loading system evidence and status...
      </div>
    )
  }

  const { status, benchmarks, coverage } = data
  const capabilities: any[] = coverage?.capabilities || []

  return (
    <div className="space-y-6 pb-12">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            System Evidence & Verification
          </h1>
          <p className="text-sm text-muted-foreground">
            Operational status, synthetic benchmarks, and mapped capability test
            evidence (SIH PS 26265).
          </p>
        </div>
        <Badge
          variant="outline"
          className="text-xs border-amber-500/40 text-amber-700 dark:text-amber-300"
        >
          STATUS: DEMO • ALL BANK APIS SIMULATED
        </Badge>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid grid-cols-2 w-full max-w-md">
          <TabsTrigger value="status" className="gap-2 text-xs">
            <Layers className="h-4 w-4" /> System Status & Gates
          </TabsTrigger>
          <TabsTrigger value="coverage" className="gap-2 text-xs">
            <ShieldCheck className="h-4 w-4" /> Capability Coverage
          </TabsTrigger>
        </TabsList>
      </Tabs>

      {activeTab === "status" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                  <Clock className="h-4 w-4 text-primary" /> Virtual Clock (IST)
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-sm font-bold font-mono">
                  {status.virtual_clock_ist}
                </div>
                <p className="text-[11px] text-muted-foreground mt-1">
                  {status.clock_is_simulated
                    ? "Simulated offset active"
                    : "Real-time clock"}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                  <Database className="h-4 w-4 text-primary" /> DB Migration
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-sm font-bold font-mono">
                  {status.migration_version}
                </div>
                <p className="text-[11px] text-emerald-600 mt-1 flex items-center gap-1">
                  <CheckCircle2 className="h-3 w-3" /> Schema at head
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                  <Zap className="h-4 w-4 text-primary" /> Worker Lock
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-sm font-bold">
                  {status.worker_status.split(" ")[0]}
                </div>
                <p className="text-[11px] text-muted-foreground mt-1">
                  xact advisory lock verified
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                  <Shield className="h-4 w-4 text-primary" /> Rule Edition
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-sm font-bold">{status.rule_edition}</div>
                <p className="text-[11px] text-amber-600 mt-1">
                  Hard Rule I5: dated JSON
                </p>
              </CardContent>
            </Card>
          </div>

          <Alert className="border-amber-500/30 bg-amber-50/50 dark:bg-amber-950/20">
            <AlertCircle className="h-4 w-4 text-amber-600" />
            <AlertTitle className="text-amber-900 dark:text-amber-200">
              Prototype Disclaimers & Integrity Constraints
            </AlertTitle>
            <AlertDescription className="text-xs text-amber-800 dark:text-amber-300 mt-2 space-y-1">
              {status.disclaimers.map((d: string, idx: number) => (
                <div key={idx} className="flex items-center gap-2">
                  <span className="font-semibold">•</span>
                  <span>{d}</span>
                </div>
              ))}
            </AlertDescription>
          </Alert>
        </div>
      )}

      {activeTab === "coverage" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs text-muted-foreground">
                  Fraud-Lab Detection
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {benchmarks.fraud_lab.precision}
                </div>
                <div className="flex justify-between items-center text-[11px] text-muted-foreground mt-1">
                  <span>{benchmarks.fraud_lab.mean_latency_ms}ms latency</span>
                  <Badge variant="outline" className="text-[9px]">
                    {benchmarks.fraud_lab.label}
                  </Badge>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs text-muted-foreground">
                  Processing Speedup
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {benchmarks.timing.speedup}
                </div>
                <div className="flex justify-between items-center text-[11px] text-muted-foreground mt-1">
                  <span>
                    {benchmarks.timing.manual_baseline} →{" "}
                    {benchmarks.timing.portal_execution}
                  </span>
                  <Badge variant="outline" className="text-[9px]">
                    {benchmarks.timing.label}
                  </Badge>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs text-muted-foreground">
                  Capability Test Pass Rate
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-emerald-600">
                  {coverage.capabilities_passed}/{coverage.total_capabilities}
                </div>
                <div className="text-[11px] text-muted-foreground mt-1">
                  {coverage.tests_passed}/{coverage.total_tests} pytest
                  scenarios passing
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Gauge className="h-4 w-4 text-primary" /> Capability
                Verification Matrix (gen_coverage.py)
              </CardTitle>
              <CardDescription>
                Live mapping of 10 core problem-statement requirements to
                verified automated tests
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {capabilities.map((cap) => (
                  <div
                    key={cap.id}
                    className="p-3 border rounded-lg text-xs space-y-1.5"
                  >
                    <div className="flex items-center justify-between">
                      <div className="font-semibold flex items-center gap-2">
                        <Badge variant="outline" className="text-[10px]">
                          {cap.id}
                        </Badge>
                        <span>{cap.name}</span>
                      </div>
                      <Badge className="bg-emerald-600 text-[10px] gap-1">
                        <CheckCircle2 className="h-3 w-3" /> {cap.status}
                      </Badge>
                    </div>
                    <p className="text-muted-foreground">{cap.description}</p>
                    <div className="font-mono text-[10px] text-muted-foreground pt-1 border-t space-y-0.5">
                      {cap.tests.map((t: any, i: number) => (
                        <div key={i} className="flex justify-between">
                          <span>{t.test_id}</span>
                          <span className="text-emerald-600 font-semibold">
                            {t.status}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
