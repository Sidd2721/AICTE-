import { useMutation, useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import {
  AlertCircle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  History,
  ShieldCheck,
} from "lucide-react"
import { useState } from "react"

import { client } from "@/client/client.gen"
import { AboutThisPage } from "@/components/Common/AboutThisPage"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
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

export const Route = createFileRoute("/_layout/audit")({
  component: AuditLedgerView,
})

const PAGE_SIZE = 15

function AuditLedgerView() {
  const [page, setPage] = useState(0)

  const { data, isLoading } = useQuery({
    queryKey: ["audit-events", page],
    queryFn: async () => {
      const res = await client.get({
        url: "/api/v1/audit/events",
        query: { limit: PAGE_SIZE, offset: page * PAGE_SIZE },
      })
      return res.data as {
        items: any[]
        total: number
        offset: number
        limit: number
      }
    },
  })

  const verifyMutation = useMutation({
    mutationFn: async () => {
      const res = await client.get({ url: "/api/v1/audit/verify" })
      return res.data as {
        status: "clean" | "corrupted"
        tampered_event_id: number | null
        message: string
      }
    },
  })

  const events = data?.items || []
  const total = data?.total || 0
  const maxPage = Math.max(0, Math.ceil(total / PAGE_SIZE) - 1)
  const verifyResult = verifyMutation.data
  const isClean = verifyResult?.status === "clean"

  return (
    <div className="space-y-6 pb-12">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Audit Ledger</h1>
          <p className="text-sm text-muted-foreground">
            Immutable, append-only cryptographic event trail (Hard Rule I3).
          </p>
        </div>
        <Button
          onClick={() => verifyMutation.mutate()}
          disabled={verifyMutation.isPending}
          variant="outline"
          className="gap-2 border-primary/40 hover:bg-primary/5"
        >
          <ShieldCheck className="h-4 w-4 text-primary" />
          {verifyMutation.isPending
            ? "Verifying Hash Chain..."
            : "Verify Chain Integrity"}
        </Button>
      </div>

      {/* About this screen guide (G3) */}
      <AboutThisPage pageKey="audit" />

      {verifyResult && (
        <Alert variant={isClean ? "default" : "destructive"}>
          {isClean ? (
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
          ) : (
            <AlertCircle className="h-4 w-4" />
          )}
          <AlertTitle>
            {isClean ? "Hash Chain Intact" : "Chain Integrity Tampered"}
          </AlertTitle>
          <AlertDescription>
            {isClean
              ? `${verifyResult.message}. All sequential SHA-256 links form a valid, unbroken chain.`
              : `${verifyResult.message}. Hash mismatch violates append-only invariant.`}
          </AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader className="pb-3 flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <History className="h-4 w-4 text-primary" /> Cryptographic Event
              Stream
            </CardTitle>
            <CardDescription>
              Showing {events.length} of {total} total recorded events
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              disabled={page === 0}
              onClick={() => setPage((p) => Math.max(0, p - 1))}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="text-xs text-muted-foreground">
              Page {page + 1} of {Math.max(1, maxPage + 1)}
            </span>
            <Button
              size="sm"
              variant="outline"
              disabled={page >= maxPage}
              onClick={() => setPage((p) => p + 1)}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="p-8 text-center text-muted-foreground text-sm">
              Loading audit events...
            </div>
          ) : events.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground text-sm">
              No audit events recorded yet.
            </div>
          ) : (
            <div className="border rounded-md overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[60px]">Seq</TableHead>
                    <TableHead>Timestamp</TableHead>
                    <TableHead>Action</TableHead>
                    <TableHead>Entity</TableHead>
                    <TableHead>Actor Role</TableHead>
                    <TableHead>Entry Hash (SHA-256)</TableHead>
                    <TableHead>Previous Hash</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {events.map((ev) => (
                    <TableRow key={ev.id}>
                      <TableCell className="font-mono text-xs">
                        {ev.id}
                      </TableCell>
                      <TableCell className="text-xs whitespace-nowrap">
                        {ev.created_at?.replace("T", " ").slice(0, 19)}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className="text-[10px] font-semibold"
                        >
                          {ev.action}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-xs">
                        {ev.entity_type}:{ev.entity_id?.slice(0, 8)}
                      </TableCell>
                      <TableCell className="text-xs font-medium">
                        {ev.actor_role}
                      </TableCell>
                      <TableCell className="font-mono text-[10px] text-muted-foreground">
                        {ev.entry_hash?.slice(0, 16)}...
                      </TableCell>
                      <TableCell className="font-mono text-[10px] text-muted-foreground">
                        {ev.prev_hash
                          ? `${ev.prev_hash.slice(0, 12)}...`
                          : "GENESIS"}
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
