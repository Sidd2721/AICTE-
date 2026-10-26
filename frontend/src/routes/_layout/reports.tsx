import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import {
  AlertCircle,
  Calendar,
  Download,
  FileSpreadsheet,
  FileWarning,
  Hourglass,
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"

export const Route = createFileRoute("/_layout/reports")({
  component: ReportsView,
})

const REPORT_TABS = [
  {
    id: "pending-verifications",
    title: "Pending Verifications",
    icon: Hourglass,
    desc: "Instruments awaiting bank confirmation reply.",
  },
  {
    id: "upcoming-maturities",
    title: "Upcoming Maturities",
    icon: Calendar,
    desc: "Fixed deposits maturing within the 60-day window.",
  },
  {
    id: "missing-documents",
    title: "Missing Documents",
    icon: FileWarning,
    desc: "Instruments lacking mandatory FDR certificate or letter.",
  },
  {
    id: "cases-needing-intervention",
    title: "Cases Needing Intervention",
    icon: AlertCircle,
    desc: "Instruments with open discrepancies or overdue responses.",
  },
]

function formatPaise(p: number | null | undefined): string {
  if (p == null) return "—"
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(p / 100)
}

function ReportsView() {
  const [activeTab, setActiveTab] = useState(REPORT_TABS[0].id)

  const { data, isLoading } = useQuery({
    queryKey: ["report-preview", activeTab],
    queryFn: async () => {
      const res = await client.get({
        url: `/api/v1/reports/${activeTab}/preview`,
      })
      return res.data as { report: string; count: number; items: any[] }
    },
  })

  const downloadCsv = async () => {
    try {
      const token = localStorage.getItem("access_token")
      const response = await fetch(`/api/v1/reports/${activeTab}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (!response.ok) throw new Error("Export failed")
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `${activeTab}_${new Date().toISOString().slice(0, 10)}.csv`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      toast.success("Formula-safe CSV report downloaded")
    } catch {
      toast.error("Failed to download CSV report")
    }
  }

  const items = data?.items || []
  const currentTabMeta =
    REPORT_TABS.find((t) => t.id === activeTab) || REPORT_TABS[0]

  return (
    <div className="space-y-6 pb-12">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Statement Reports
          </h1>
          <p className="text-sm text-muted-foreground">
            Auditable statement reporting with formula-safe CSV exports (Hard
            Rule I13).
          </p>
        </div>
        <Button onClick={downloadCsv} className="gap-2">
          <Download className="h-4 w-4" /> Export Formula-Safe CSV
        </Button>
      </div>

      {/* About this screen guide (G3) */}
      <AboutThisPage pageKey="reports" />

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid grid-cols-2 md:grid-cols-4 w-full">
          {REPORT_TABS.map((tab) => (
            <TabsTrigger key={tab.id} value={tab.id} className="gap-2 text-xs">
              <tab.icon className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">{tab.title}</span>
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      <Card>
        <CardHeader className="pb-3 flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <FileSpreadsheet className="h-4 w-4 text-primary" />{" "}
              {currentTabMeta.title}
            </CardTitle>
            <CardDescription>{currentTabMeta.desc}</CardDescription>
          </div>
          <Badge variant="outline">{items.length} records</Badge>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="p-8 text-center text-muted-foreground text-sm">
              Loading preview table...
            </div>
          ) : items.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground text-sm">
              No records matching report criteria.
            </div>
          ) : (
            <div className="border rounded-md overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Ref No</TableHead>
                    <TableHead>Institution</TableHead>
                    <TableHead>Bank</TableHead>
                    <TableHead>Amount</TableHead>
                    <TableHead>Maturity</TableHead>
                    <TableHead>Lifecycle</TableHead>
                    <TableHead>Detail / Notes</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((row, idx) => (
                    <TableRow key={idx}>
                      <TableCell className="font-mono text-xs font-semibold">
                        {row.ref_no}
                      </TableCell>
                      <TableCell className="text-xs">
                        {row.institution_name || row.institution_id || "—"}
                      </TableCell>
                      <TableCell className="text-xs">
                        {row.bank_code || "—"}
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {formatPaise(row.amount_paise)}
                      </TableCell>
                      <TableCell className="text-xs">
                        {row.maturity_date || "—"}
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary" className="text-[10px]">
                          {row.lifecycle || "active"}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {row.days_to_maturity != null
                          ? `${row.days_to_maturity} days remaining`
                          : row.reason || row.missing || "—"}
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
  )
}
