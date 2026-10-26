import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, Link, Outlet, redirect } from "@tanstack/react-router"
import {
  BookOpen,
  Building2,
  Calendar,
  ChevronDown,
  Clock,
  FastForward,
  RotateCcw,
  Scale,
  Shield,
  ShieldCheck,
  UserCheck,
} from "lucide-react"
import { toast } from "sonner"

import { client } from "@/client/client.gen"
import { Footer } from "@/components/Common/Footer"
import AppSidebar from "@/components/Sidebar/AppSidebar"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar"
import useAuth, { isLoggedIn } from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout")({
  component: Layout,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({
        to: "/login",
      })
    }
  },
})

interface SystemMeta {
  env_label: string
  rule_status: string
  commit: string
  built_at: string
}

function DemoBanner() {
  const { data: meta } = useQuery<SystemMeta>({
    queryKey: ["system-meta"],
    queryFn: async () => {
      const res = await fetch("/api/v1/meta")
      if (!res.ok) {
        return {
          env_label: "development",
          rule_status: "DEMO",
          commit: "0456163",
          built_at: "",
        }
      }
      return await res.json()
    },
    staleTime: 1000 * 60 * 60,
  })

  if (
    !meta ||
    (meta.env_label !== "development" && meta.env_label !== "demo")
  ) {
    return null
  }

  return (
    <div className="bg-amber-500/15 border-b border-amber-500/30 text-amber-900 dark:text-amber-200 px-4 py-1.5 text-xs flex items-center justify-between z-20">
      <div className="flex items-center gap-2 truncate">
        <Badge
          variant="outline"
          className="border-amber-600/40 bg-amber-500/20 text-amber-900 dark:text-amber-200 text-[10px] font-bold"
        >
          DEMO
        </Badge>
        <span className="truncate">
          Synthetic data, SIMULATED bank and email, DEMO rule values
        </span>
      </div>
      <div className="flex items-center gap-3 shrink-0">
        <Link
          to="/guide"
          className="hidden sm:inline-flex items-center gap-1 font-medium hover:underline text-[11px] text-amber-900 dark:text-amber-200"
        >
          <BookOpen className="size-3" />
          6-Min Tour
        </Link>
        <Link
          to="/evidence"
          className="underline hover:text-foreground text-[11px]"
        >
          Limits
        </Link>
        <span className="font-mono text-[10px] opacity-75">{meta.commit}</span>
      </div>
    </div>
  )
}

function RegulatoryHeader() {
  const { user, loginMutation } = useAuth()
  const queryClient = useQueryClient()

  const { data: clockData } = useQuery({
    queryKey: ["sim-clock"],
    queryFn: async () => {
      const res = await client.get<any>({ url: "/sim/clock" })
      return res.data
    },
    refetchInterval: 15000,
  })

  const clockMutation = useMutation({
    mutationFn: async (offsetDays: number) => {
      const offset_seconds = offsetDays * 86400
      const res = await client.put<any>({
        url: "/sim/clock",
        body: { offset_seconds },
      })
      return res.data
    },
    onSuccess: (_data, days) => {
      queryClient.invalidateQueries({ queryKey: ["sim-clock"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard-data"] })
      queryClient.invalidateQueries({ queryKey: ["instruments"] })
      toast.success(
        days === 0
          ? "Clock reset to real-world current date"
          : `Simulated clock advanced by +${days} days`,
      )
    },
    onError: (err: any) => {
      toast.error(
        `Failed to adjust clock: ${err?.message || "Forbidden outside dev"}`,
      )
    },
  })

  const simulatedDate = clockData?.now
    ? new Date(clockData.now).toLocaleDateString("en-IN", {
        day: "numeric",
        month: "short",
        year: "numeric",
      })
    : "Today"

  const roleLabel =
    user?.role === "institution"
      ? "Institution"
      : user?.role === "regional"
        ? `Regional Officer (${user?.region || "NR"})`
        : user?.role === "bureau"
          ? "Bureau Approver"
          : user?.role === "auditor"
            ? "Auditor (Read-Only)"
            : "System Admin"

  const roleColor =
    user?.role === "institution"
      ? "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-400"
      : user?.role === "regional"
        ? "border-blue-500/30 bg-blue-500/10 text-blue-700 dark:text-blue-400"
        : user?.role === "bureau"
          ? "border-purple-500/30 bg-purple-500/10 text-purple-700 dark:text-purple-400"
          : "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400"

  const PERSONAS = [
    {
      role: "Institution",
      name: "North Tech",
      email: "inst.north1@example.com",
      scope: "Submits FDR instruments; requests release.",
      color: "text-amber-600",
    },
    {
      role: "Regional Officer",
      name: "Officer North",
      email: "officer.north@example.com",
      scope:
        "Requests bank confirmation, notes, waives flags with reason, verifies release.",
      color: "text-blue-600",
    },
    {
      role: "Regional Checker",
      name: "Checker North",
      email: "checker.north@example.com",
      scope: "Regional inspection officer for North Region.",
      color: "text-purple-600",
    },
    {
      role: "Bureau Head",
      name: "Central Bureau",
      email: "bureau@example.com",
      scope: "Approves releases (checker), nationwide reports, virtual clock.",
      color: "text-purple-600",
    },
    {
      role: "Auditor",
      name: "Reg. Auditor",
      email: "auditor@example.com",
      scope: "Read-only access across all regions, instruments, and audit log.",
      color: "text-slate-600",
    },
  ]

  const switchPersona = async (email: string) => {
    try {
      const demoRes = await fetch("/api/v1/login/demo", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      })
      if (demoRes.ok) {
        const data = await demoRes.json()
        if (data.access_token) {
          localStorage.setItem("access_token", data.access_token)
          window.location.reload()
          return
        }
      }
      const res = await fetch("/api/v1/login/demo-personas")
      if (res.ok) {
        const personas: Array<{ email: string; password?: string }> =
          await res.json()
        const match = personas.find((p) => p.email === email)
        if (match?.password) {
          loginMutation.mutate({
            username: email,
            password: match.password,
          })
        }
      }
    } catch {
      // Demo persona endpoint unavailable
    }
  }

  return (
    <div className="flex flex-1 items-center justify-between gap-4">
      <div className="flex items-center gap-3">
        <SidebarTrigger className="-ml-1 text-muted-foreground hover:text-foreground" />
        <div className="hidden sm:flex items-center gap-2 text-xs text-muted-foreground">
          <Shield className="size-3.5 text-primary" />
          <span className="font-semibold text-foreground">AICTE Portal</span>
          <span>/</span>
          <span className="truncate max-w-[200px]">
            PS 26265 Regulatory System
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2 sm:gap-3">
        {/* Quick link to 6-minute guided tour */}
        <Link to="/guide" className="hidden lg:inline-flex">
          <Button
            variant="ghost"
            size="sm"
            className="h-8 gap-1.5 text-xs text-primary hover:text-primary"
          >
            <BookOpen className="size-3.5" />
            <span>Guided Tour</span>
          </Button>
        </Link>

        {/* PostgreSQL RLS status */}
        <Badge
          variant="outline"
          className="hidden md:inline-flex items-center gap-1.5 border-border/80 bg-background/50 text-[11px] font-normal"
        >
          <div className="size-1.5 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-muted-foreground">DB RLS:</span>
          <span className="font-medium text-foreground">NOSUPERUSER</span>
        </Badge>

        {/* Time machine clock control */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              className="h-8 gap-1.5 text-xs font-normal border-dashed border-primary/40 hover:border-primary/80"
            >
              <Clock className="size-3.5 text-primary" />
              <span className="hidden sm:inline text-muted-foreground">
                Clock:
              </span>
              <span className="font-semibold text-foreground">
                {simulatedDate}
              </span>
              {clockData?.is_simulated && (
                <span className="rounded bg-primary/20 px-1 py-0.2 text-[10px] font-bold text-primary">
                  OFFSET
                </span>
              )}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel className="flex items-center gap-1.5 text-xs">
              <Calendar className="size-3.5 text-primary" />
              Time Machine (CHARTER R14)
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={() => clockMutation.mutate(30)}
              className="flex items-center justify-between text-xs cursor-pointer"
            >
              <span>Advance +30 Days</span>
              <FastForward className="size-3 text-muted-foreground" />
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => clockMutation.mutate(60)}
              className="flex items-center justify-between text-xs cursor-pointer"
            >
              <span>Advance +60 Days</span>
              <FastForward className="size-3 text-muted-foreground" />
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => clockMutation.mutate(90)}
              className="flex items-center justify-between text-xs cursor-pointer"
            >
              <span>Advance +90 Days</span>
              <FastForward className="size-3 text-muted-foreground" />
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={() => clockMutation.mutate(0)}
              className="flex items-center justify-between text-xs text-destructive cursor-pointer"
            >
              <span>Reset to Today</span>
              <RotateCcw className="size-3" />
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Header Persona Switcher (CHARTER G2) */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              className={`h-8 px-2.5 text-xs font-medium flex items-center gap-1.5 shadow-xs cursor-pointer ${roleColor}`}
            >
              {user?.role === "institution" ? (
                <Building2 className="size-3.5" />
              ) : user?.role === "regional" ? (
                <Scale className="size-3.5" />
              ) : user?.role === "bureau" ? (
                <ShieldCheck className="size-3.5" />
              ) : (
                <UserCheck className="size-3.5" />
              )}
              <span className="hidden sm:inline text-muted-foreground">
                Viewing as:
              </span>
              <span>{roleLabel}</span>
              <ChevronDown className="size-3 opacity-60 ml-0.5" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-80">
            <DropdownMenuLabel className="flex items-center justify-between text-xs">
              <span className="flex items-center gap-1.5">
                <UserCheck className="size-3.5 text-primary" />
                Demo Persona Switcher (G2)
              </span>
              <span className="text-[10px] text-muted-foreground font-mono">
                1-Click
              </span>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            {PERSONAS.map((p) => {
              const isCurrent = user?.email === p.email
              return (
                <DropdownMenuItem
                  key={p.email}
                  onClick={() => switchPersona(p.email)}
                  className={`flex flex-col items-start gap-0.5 py-2 cursor-pointer ${
                    isCurrent ? "bg-accent/70 font-semibold" : ""
                  }`}
                >
                  <div className="flex items-center justify-between w-full">
                    <span className="text-xs font-medium flex items-center gap-1.5">
                      <span
                        className={`size-1.5 rounded-full ${p.color.replace("text-", "bg-")}`}
                      />
                      {p.role} ({p.name})
                    </span>
                    {isCurrent && (
                      <Badge
                        variant="outline"
                        className="text-[9px] px-1 py-0 h-4 bg-primary/10 text-primary"
                      >
                        Active
                      </Badge>
                    )}
                  </div>
                  <span className="text-[11px] text-muted-foreground leading-snug">
                    {p.scope}
                  </span>
                </DropdownMenuItem>
              )
            })}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  )
}

function Layout() {
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <DemoBanner />
        <header className="sticky top-0 z-10 flex h-14 shrink-0 items-center border-b bg-background/95 backdrop-blur-md px-4 supports-[backdrop-filter]:bg-background/80">
          <RegulatoryHeader />
        </header>
        <main className="flex-1 p-4 md:p-8">
          <div className="mx-auto max-w-7xl">
            <Outlet />
          </div>
        </main>
        <Footer />
      </SidebarInset>
    </SidebarProvider>
  )
}
export default Layout
