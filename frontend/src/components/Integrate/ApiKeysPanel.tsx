import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { AlertTriangle, Check, Copy, Plus, Trash2 } from "lucide-react"
import { useState } from "react"
import { toast } from "sonner"
import { client } from "@/client/client.gen"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
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

export function ApiKeysPanel() {
  const queryClient = useQueryClient()
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [clientName, setClientName] = useState("")
  const [scopes, setScopes] = useState<string[]>(["bank:confirm"])
  const [expiresDays, setExpiresDays] = useState("365")
  const [newKeySecret, setNewKeySecret] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ["integration-keys"],
    queryFn: async () => {
      const res = await client.get({ url: "/api/v1/integration/keys" })
      return res.data as { items: any[] }
    },
  })

  const createMutation = useMutation({
    mutationFn: async () => {
      const days = expiresDays === "never" ? null : parseInt(expiresDays, 10)
      const res = await client.post({
        url: "/api/v1/integration/keys",
        body: {
          client_name: clientName,
          scopes,
          expires_in_days: days,
        },
      })
      return res.data as { raw_key: string; key_id: string }
    },
    onSuccess: (data) => {
      setNewKeySecret(data.raw_key)
      queryClient.invalidateQueries({ queryKey: ["integration-keys"] })
      toast.success("Machine API key created successfully")
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || "Failed to issue API key")
    },
  })

  const revokeMutation = useMutation({
    mutationFn: async (keyId: string) => {
      await client.delete({ url: `/api/v1/integration/keys/${keyId}` })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["integration-keys"] })
      toast.success("API key revoked immediately")
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || "Failed to revoke API key")
    },
  })

  const toggleScope = (scope: string) => {
    setScopes((prev) =>
      prev.includes(scope) ? prev.filter((s) => s !== scope) : [...prev, scope],
    )
  }

  const handleCopySecret = () => {
    if (newKeySecret) {
      navigator.clipboard.writeText(newKeySecret)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const handleCloseDialog = () => {
    setIsCreateOpen(false)
    setNewKeySecret(null)
    setClientName("")
    setScopes(["bank:confirm"])
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold tracking-tight">Machine API Keys</h2>
          <p className="text-sm text-muted-foreground">
            Scoped credentials for Core Banking Adapters, SFMS Integrators, and
            AICTE National Systems.
          </p>
        </div>
        <Button onClick={() => setIsCreateOpen(true)} className="gap-2">
          <Plus className="h-4 w-4" /> Issue New API Key
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Client Name</TableHead>
                <TableHead>Key ID</TableHead>
                <TableHead>Scopes</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Last Used</TableHead>
                <TableHead className="text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell
                    colSpan={7}
                    className="text-center py-6 text-muted-foreground"
                  >
                    Loading credentials...
                  </TableCell>
                </TableRow>
              ) : !data?.items || data.items.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={7}
                    className="text-center py-6 text-muted-foreground"
                  >
                    No machine API keys issued yet. Click "Issue New API Key"
                    above.
                  </TableCell>
                </TableRow>
              ) : (
                data.items.map((k) => (
                  <TableRow key={k.key_id}>
                    <TableCell className="font-semibold text-foreground">
                      {k.client_name}
                    </TableCell>
                    <TableCell>
                      <code className="text-xs bg-muted px-1.5 py-0.5 rounded border">
                        {k.key_id}
                      </code>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {k.scopes.map((s: string) => (
                          <Badge
                            key={s}
                            variant="outline"
                            className="text-[11px] font-mono"
                          >
                            {s}
                          </Badge>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell>
                      {k.active ? (
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
                      {new Date(k.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {k.last_used_at
                        ? new Date(k.last_used_at).toLocaleDateString()
                        : "Never"}
                    </TableCell>
                    <TableCell className="text-right">
                      {k.active && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 text-destructive hover:bg-destructive/10"
                          onClick={() => revokeMutation.mutate(k.key_id)}
                          disabled={revokeMutation.isPending}
                        >
                          <Trash2 className="h-3.5 w-3.5 mr-1" /> Revoke
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Creation & Secret Dialog */}
      <Dialog open={isCreateOpen} onOpenChange={handleCloseDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              {newKeySecret
                ? "Save Your Machine API Key"
                : "Issue Machine Integration Key"}
            </DialogTitle>
            <DialogDescription>
              {newKeySecret
                ? "This secret key will NEVER be displayed again. Store it securely in your secret manager."
                : "Creates a least-privilege credential hashed with SHA-256 in the regulatory database."}
            </DialogDescription>
          </DialogHeader>

          {newKeySecret ? (
            <div className="space-y-4 py-2">
              <Alert
                variant="destructive"
                className="bg-amber-500/10 border-amber-500/30 text-amber-900 dark:text-amber-200"
              >
                <AlertTriangle className="h-4 w-4 text-amber-600" />
                <AlertTitle>Copy Secret Immediately</AlertTitle>
                <AlertDescription className="text-xs">
                  Once you close this window, the raw secret cannot be
                  recovered.
                </AlertDescription>
              </Alert>

              <div className="space-y-2">
                <Label className="text-xs">Generated API Key</Label>
                <div className="flex items-center gap-2">
                  <Input
                    readOnly
                    value={newKeySecret}
                    className="font-mono text-xs bg-muted"
                  />
                  <Button
                    size="sm"
                    onClick={handleCopySecret}
                    className="shrink-0 gap-1.5"
                  >
                    {copied ? (
                      <Check className="h-4 w-4 text-green-500" />
                    ) : (
                      <Copy className="h-4 w-4" />
                    )}
                    {copied ? "Copied" : "Copy"}
                  </Button>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <Label htmlFor="clientName">
                  Client / Integrator Identifier
                </Label>
                <Input
                  id="clientName"
                  placeholder="e.g. State Bank of India CBS Adapter"
                  value={clientName}
                  onChange={(e) => setClientName(e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <Label>Required Permissions (Scopes)</Label>
                <div className="space-y-2 rounded border p-3 bg-muted/20">
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="scope-bank"
                      checked={scopes.includes("bank:confirm")}
                      onCheckedChange={() => toggleScope("bank:confirm")}
                    />
                    <label
                      htmlFor="scope-bank"
                      className="text-sm cursor-pointer"
                    >
                      <span className="font-mono font-semibold">
                        bank:confirm
                      </span>{" "}
                      — Submit confirmations & poll pending
                    </label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="scope-aicte"
                      checked={scopes.includes("aicte:read")}
                      onCheckedChange={() => toggleScope("aicte:read")}
                    />
                    <label
                      htmlFor="scope-aicte"
                      className="text-sm cursor-pointer"
                    >
                      <span className="font-mono font-semibold">
                        aicte:read
                      </span>{" "}
                      — Read institutions, instruments & event stream
                    </label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="scope-webhooks"
                      checked={scopes.includes("aicte:webhooks")}
                      onCheckedChange={() => toggleScope("aicte:webhooks")}
                    />
                    <label
                      htmlFor="scope-webhooks"
                      className="text-sm cursor-pointer"
                    >
                      <span className="font-mono font-semibold">
                        aicte:webhooks
                      </span>{" "}
                      — Manage webhook event subscriptions
                    </label>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="expires">Key Validity</Label>
                <Select value={expiresDays} onValueChange={setExpiresDays}>
                  <SelectTrigger id="expires">
                    <SelectValue placeholder="Select validity" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="30">30 Days</SelectItem>
                    <SelectItem value="90">90 Days</SelectItem>
                    <SelectItem value="365">1 Year (365 Days)</SelectItem>
                    <SelectItem value="never">No Expiration</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}

          <DialogFooter>
            {newKeySecret ? (
              <Button onClick={handleCloseDialog} className="w-full">
                I Have Copied the Key Safely
              </Button>
            ) : (
              <div className="flex justify-end gap-2 w-full">
                <Button variant="outline" onClick={handleCloseDialog}>
                  Cancel
                </Button>
                <Button
                  onClick={() => createMutation.mutate()}
                  disabled={
                    !clientName.trim() ||
                    scopes.length === 0 ||
                    createMutation.isPending
                  }
                >
                  Generate Key
                </Button>
              </div>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
