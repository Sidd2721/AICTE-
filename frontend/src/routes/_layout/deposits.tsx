import { createFileRoute } from "@tanstack/react-router"
import { Building2 } from "lucide-react"

export const Route = createFileRoute("/_layout/deposits")({
  component: Deposits,
  head: () => ({
    meta: [
      {
        title: "Deposits - FDR Portal",
      },
    ],
  }),
})

function Deposits() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Security Deposits & FDRs
          </h1>
          <p className="text-muted-foreground text-sm">
            AICTE Security Deposit and Fixed Deposit Receipt records.
          </p>
        </div>
      </div>
      <div className="flex flex-col items-center justify-center text-center py-12 rounded-lg border border-dashed">
        <div className="rounded-full bg-muted p-4 mb-4">
          <Building2 className="h-8 w-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold">No deposits registered yet</h3>
        <p className="text-muted-foreground">
          Deposit tracking and management will be enabled in upcoming
          milestones.
        </p>
      </div>
    </div>
  )
}
