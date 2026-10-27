import { useQuery } from "@tanstack/react-query"
import { RefreshCw } from "lucide-react"
import { client } from "@/client/client.gen"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

export function OutboxTailPanel() {
  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ["outbox-tail"],
    queryFn: async () => {
      const res = await client.get({
        url: "/api/v1/integration/outbox-tail?limit=25",
      })
      return res.data as { items: any[] }
    },
    refetchInterval: 5000,
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold tracking-tight">
            Transactional Outbox Event Stream
          </h2>
          <p className="text-sm text-muted-foreground">
            Immutable stream of regulatory domain events written in the same
            database transaction as business entities.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => refetch()}
          disabled={isFetching}
          className="gap-2 text-xs"
        >
          <RefreshCw
            className={`h-3.5 w-3.5 ${isFetching ? "animate-spin" : ""}`}
          />
          Refresh Stream
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Event ID</TableHead>
                <TableHead>Event Type</TableHead>
                <TableHead>Aggregate</TableHead>
                <TableHead>Timestamp</TableHead>
                <TableHead>Payload Preview</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell
                    colSpan={5}
                    className="text-center py-6 text-muted-foreground"
                  >
                    Streaming events...
                  </TableCell>
                </TableRow>
              ) : !data?.items || data.items.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={5}
                    className="text-center py-6 text-muted-foreground"
                  >
                    No outbox events recorded yet.
                  </TableCell>
                </TableRow>
              ) : (
                data.items.map((event) => (
                  <TableRow key={event.id}>
                    <TableCell>
                      <code className="text-[11px] font-mono bg-muted px-1.5 py-0.5 rounded border">
                        {event.id.slice(0, 8)}...
                      </code>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant="outline"
                        className="font-mono text-xs font-semibold"
                      >
                        {event.event_type}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      <span className="capitalize">{event.aggregate_type}</span>
                      :{" "}
                      <span className="font-mono">
                        {event.aggregate_id.slice(0, 8)}
                      </span>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                      {new Date(event.created_at).toLocaleTimeString()}
                    </TableCell>
                    <TableCell className="font-mono text-[11px] text-muted-foreground max-w-[320px] truncate">
                      {JSON.stringify(event.payload)}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
