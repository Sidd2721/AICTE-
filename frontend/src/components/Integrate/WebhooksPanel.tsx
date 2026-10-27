import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  Activity,
  CheckCircle,
  Plus,
  Send,
  Trash2,
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

export function WebhooksPanel() {
  const queryClient = useQueryClient()
  const [isRegisterOpen, setIsRegisterOpen] = useState(false)
  const [targetUrl, setTargetUrl] = useState("")
  const [eventTypesStr, setEventTypesStr] = useState("*")
  const [secret, setSecret] = useState("")

  const { data, isLoading } = useQuery({
    queryKey: ["integration-webhooks"],
    queryFn: async () => {
      const res = await client.get({ url: "/api/v1/integration/webhooks" })
      return res.data as { items: any[] }
    },
  })

  const registerMutation = useMutation({
    mutationFn: async () => {
      const types = eventTypesStr
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean)
      const res = await client.post({
        url: "/api/v1/integration/webhooks",
        body: {
          target_url: targetUrl,
          event_types: types.length > 0 ? types : ["*"],
          secret: secret.trim() || undefined,
        },
      })
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["integration-webhooks"] })
      toast.success("Webhook subscription registered")
      setIsRegisterOpen(false)
      setTargetUrl("")
      setSecret("")
    },
    onError: (err: any) => {
      toast.error(
        err?.response?.data?.detail ||
          "Failed to register webhook. Verify SSRF rules.",
      )
    },
  })

  const testMutation = useMutation({
    mutationFn: async (id: string) => {
      const res = await client.post({
        url: `/api/v1/integration/webhooks/${id}/test`,
      })
      return res.data as {
        success: boolean
        status_code: number
        latency_ms: number
        error_message?: string
      }
    },
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["integration-webhooks"] })
      if (result.success) {
        toast.success(
          `Ping delivered! HTTP ${result.status_code} in ${result.latency_ms}ms`,
        )
      } else {
        toast.error(
          `Ping failed: ${result.error_message || "Target did not respond with 2xx"}`,
        )
      }
    },
    onError: (err: any) => {
      toast.error(
        err?.response?.data?.detail ||
          "Delivery test encountered network error",
      )
    },
  })

  const revokeMutation = useMutation({
    mutationFn: async (id: string) => {
      await client.delete({ url: `/api/v1/integration/webhooks/${id}` })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["integration-webhooks"] })
      toast.success("Webhook revoked")
    },
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold tracking-tight">
            SSRF-Protected Webhooks
          </h2>
          <p className="text-sm text-muted-foreground">
            Real-time push delivery with HMAC-SHA256 signatures, replay window
            protection, and automated SSRF address defenses.
          </p>
        </div>
        <Button onClick={() => setIsRegisterOpen(true)} className="gap-2">
          <Plus className="h-4 w-4" /> Register Webhook
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Target URL</TableHead>
                <TableHead>Event Filter</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Last Delivered</TableHead>
                <TableHead>Failures</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell
                    colSpan={6}
                    className="text-center py-6 text-muted-foreground"
                  >
                    Loading webhooks...
                  </TableCell>
                </TableRow>
              ) : !data?.items || data.items.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={6}
                    className="text-center py-6 text-muted-foreground"
                  >
                    No webhooks registered yet. Click "Register Webhook" above.
                  </TableCell>
                </TableRow>
              ) : (
                data.items.map((sub) => (
                  <TableRow key={sub.id}>
                    <TableCell
                      className="font-mono text-xs max-w-[280px] truncate"
                      title={sub.target_url}
                    >
                      {sub.target_url}
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {sub.event_types.map((t: string) => (
                          <Badge
                            key={t}
                            variant="secondary"
                            className="text-[10px]"
                          >
                            {t}
                          </Badge>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell>
                      {sub.active ? (
                        <Badge className="bg-green-600/10 text-green-700 dark:text-green-400 border-green-600/20 text-xs">
                          Active
                        </Badge>
                      ) : (
                        <Badge variant="destructive" className="text-xs">
                          Revoked
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {sub.last_delivered_at
                        ? new Date(sub.last_delivered_at).toLocaleTimeString()
                        : "Never"}
                    </TableCell>
                    <TableCell>
                      <span
                        className={
                          sub.failure_count > 0
                            ? "text-destructive font-semibold text-xs"
                            : "text-xs text-muted-foreground"
                        }
                      >
                        {sub.failure_count}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1.5">
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-8 gap-1 text-xs"
                          onClick={() => testMutation.mutate(sub.id)}
                          disabled={testMutation.isPending}
                        >
                          <Send className="h-3 w-3" /> Test Ping
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 text-destructive hover:bg-destructive/10"
                          onClick={() => revokeMutation.mutate(sub.id)}
                          disabled={revokeMutation.isPending}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Webhook Delivery Log Drawer / Summary */}
      {data?.items?.some((s) => s.logs && s.logs.length > 0) && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-primary" />
              <CardTitle className="text-base">
                Recent Webhook Dispatch Logs
              </CardTitle>
            </div>
            <CardDescription className="text-xs">
              Audit trail of outbound HTTP delivery attempts with response
              status codes and latencies.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {data.items.flatMap((s) =>
              (s.logs || []).map((log: any) => (
                <div
                  key={log.id}
                  className="flex items-center justify-between p-3 rounded-md border bg-muted/20 text-xs"
                >
                  <div className="flex items-center gap-2.5">
                    {log.success ? (
                      <CheckCircle className="h-4 w-4 text-green-500 shrink-0" />
                    ) : (
                      <XCircle className="h-4 w-4 text-destructive shrink-0" />
                    )}
                    <div>
                      <span className="font-semibold font-mono">
                        {log.event_type}
                      </span>
                      <span className="text-muted-foreground ml-2">
                        to {s.target_url}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge
                      variant={log.success ? "outline" : "destructive"}
                      className="text-[10px]"
                    >
                      HTTP {log.status_code || "ERR"}
                    </Badge>
                    <span className="text-muted-foreground">
                      {log.latency_ms} ms
                    </span>
                    <span className="text-muted-foreground">
                      {new Date(log.delivered_at).toLocaleTimeString()}
                    </span>
                  </div>
                </div>
              )),
            )}
          </CardContent>
        </Card>
      )}

      {/* Register Dialog */}
      <Dialog open={isRegisterOpen} onOpenChange={setIsRegisterOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Register Webhook Subscription</DialogTitle>
            <DialogDescription>
              Target endpoints receive signed HMAC-SHA256 payloads. Loopback
              (outside dev), RFC 1918 private ranges, and cloud metadata
              (169.254.169.254) are strictly blocked.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="targetUrl">Target HTTPS URL</Label>
              <Input
                id="targetUrl"
                placeholder="https://api.bank.gov.in/aicte/webhooks"
                value={targetUrl}
                onChange={(e) => setTargetUrl(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="events">
                Event Types Filter (comma-separated or * for all)
              </Label>
              <Input
                id="events"
                placeholder="instrument.confirmed, instrument.matured, release.verified"
                value={eventTypesStr}
                onChange={(e) => setEventTypesStr(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="secret">
                HMAC Secret (optional, auto-generated if blank)
              </Label>
              <Input
                id="secret"
                type="password"
                placeholder="Leave empty to generate high-entropy secret"
                value={secret}
                onChange={(e) => setSecret(e.target.value)}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsRegisterOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => registerMutation.mutate()}
              disabled={!targetUrl.trim() || registerMutation.isPending}
            >
              Subscribe
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
