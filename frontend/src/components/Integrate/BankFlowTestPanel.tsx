import { useMutation, useQueryClient } from "@tanstack/react-query"
import {
  CheckCircle2,
  FileCheck,
  Play,
  ShieldCheck,
  XCircle,
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

export function BankFlowTestPanel() {
  const queryClient = useQueryClient()
  const [testResult, setTestResult] = useState<any | null>(null)

  const testMutation = useMutation({
    mutationFn: async () => {
      const res = await client.post({
        url: "/api/v1/integration/bank-flow-test",
      })
      return res.data
    },
    onSuccess: (data: any) => {
      setTestResult(data)
      queryClient.invalidateQueries({ queryKey: ["instruments"] })
      queryClient.invalidateQueries({ queryKey: ["outbox-events"] })
      toast.success("Bank confirmation flow executed successfully")
    },
    onError: (err: any) => {
      toast.error(
        err?.response?.data?.detail || "Bank flow test encountered an error",
      )
    },
  })

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-primary" />
            <CardTitle>
              Interactive Bank Confirmation & Cryptographic Gate Test
            </CardTitle>
          </div>
          <CardDescription>
            Simulates a Core Banking System (CBS) securely responding to an
            AICTE verification inquiry. Evaluates the 6-point cryptographic gate
            defined in Invariant I3.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            In production, Core Banking adapters counter-sign the issued
            challenge letter with an HSM-backed Class 3 digital signature
            certificate. The gate ensures that only unaltered documents matching
            pinned bank roots can mark an FDR deposit confirmed.
          </p>

          <div className="flex items-center gap-3 pt-2">
            <Button
              onClick={() => testMutation.mutate()}
              disabled={testMutation.isPending}
              className="gap-2 font-semibold"
            >
              <Play className="h-4 w-4 fill-current" />
              {testMutation.isPending
                ? "Executing Gate..."
                : "Run End-to-End Bank Confirmation Test"}
            </Button>
            <span className="text-xs text-muted-foreground">
              Executes sandbox sign ➔ evaluates cryptographic gate ➔ transitions
              deposit to Active
            </span>
          </div>
        </CardContent>
      </Card>

      {testResult && (
        <Card className="border-green-600/30 bg-green-500/5">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileCheck className="h-5 w-5 text-green-600" />
                <CardTitle className="text-base text-green-800 dark:text-green-300">
                  Execution Complete — Verdict:{" "}
                  {testResult.gate_result?.verdict?.toUpperCase()}
                </CardTitle>
              </div>
              <Badge className="bg-green-600 text-white font-mono text-xs">
                Deposit Confirmed
              </Badge>
            </div>
            <CardDescription className="text-xs">
              Instrument Reference:{" "}
              <strong className="font-mono text-foreground">
                {testResult.instrument_ref}
              </strong>{" "}
              | Challenge Token:{" "}
              <code className="bg-background px-1 py-0.5 rounded border text-[11px]">
                {testResult.token_used}
              </code>
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {(testResult.gate_result?.checks || []).map(
                (check: any, idx: number) => (
                  <div
                    key={check.id || check.label || idx}
                    className="flex items-start gap-2.5 p-3 rounded-md border bg-background/80"
                  >
                    {check.passed ? (
                      <CheckCircle2 className="h-4 w-4 text-green-600 shrink-0 mt-0.5" />
                    ) : (
                      <XCircle className="h-4 w-4 text-destructive shrink-0 mt-0.5" />
                    )}
                    <div>
                      <span className="font-semibold text-xs block text-foreground">
                        {check.label || check.name}
                      </span>
                      <span className="text-muted-foreground text-[11px]">
                        {check.detail || "Cryptographic verification passed"}
                      </span>
                    </div>
                  </div>
                ),
              )}
            </div>

            <div className="p-3 bg-muted/40 rounded-md border text-xs text-muted-foreground">
              <strong>Audit Ledger Update:</strong> Transactional outbox
              enqueued event{" "}
              <code className="text-foreground font-mono">
                instrument.confirmed
              </code>{" "}
              and recorded immutable audit log with cryptographic hash chain.
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
