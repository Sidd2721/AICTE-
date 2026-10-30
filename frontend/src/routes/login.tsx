import { zodResolver } from "@hookform/resolvers/zod"
import { useQuery } from "@tanstack/react-query"
import {
  createFileRoute,
  Link as RouterLink,
  redirect,
} from "@tanstack/react-router"
import { useEffect, useRef, useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"
import type { Body_login_login_access_token as AccessToken } from "@/client"
import { AuthLayout } from "@/components/Common/AuthLayout"
import { Button } from "@/components/ui/button"
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { LoadingButton } from "@/components/ui/loading-button"
import { PasswordInput } from "@/components/ui/password-input"
import useAuth, { isLoggedIn } from "@/hooks/useAuth"

interface DemoPersona {
  role: string
  name: string
  email: string
  badge: string
  color: string
  password: string
}

const DEFAULT_PERSONAS: DemoPersona[] = [
  {
    role: "Technical Institution",
    name: "North Tech Institute",
    email: "inst.north1@example.com",
    badge: "Institute",
    color: "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/30",
    password: "AdminSecure2026!",
  },
  {
    role: "Regional Officer",
    name: "RO North (Maker)",
    email: "officer.north@example.com",
    badge: "Maker",
    color:
      "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/30",
    password: "AdminSecure2026!",
  },
  {
    role: "Scrutiny Checker",
    name: "Checker North",
    email: "checker.north@example.com",
    badge: "Checker",
    color:
      "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30",
    password: "AdminSecure2026!",
  },
  {
    role: "Bureau Approver",
    name: "Central Bureau (Key 2)",
    email: "bureau@example.com",
    badge: "Approver",
    color:
      "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30",
    password: "AdminSecure2026!",
  },
  {
    role: "Compliance Auditor",
    name: "CAG / Auditor",
    email: "auditor@example.com",
    badge: "Read-Only",
    color:
      "bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/30",
    password: "AdminSecure2026!",
  },
]

const ROLE_DESCRIPTIONS: Record<string, string> = {
  "Technical Institution":
    "Submit FDR records, view required coverage & dynamic calculator",
  "Regional Officer":
    "Maker: initiate verification & inspect cryptographic bank gate report",
  "Scrutiny Checker":
    "Checker: scrutinize discrepancies (D1–D6) & recommend release",
  "Bureau Approver":
    "Approver: dual-custody release authorization & master simulator controls",
  "Compliance Auditor":
    "Read-only auditor: inspect tamper-evident SHA-256 audit ledger",
}

const fetchDemoPersonas = async (): Promise<DemoPersona[]> => {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 12000)
  try {
    const res = await fetch("/api/v1/login/demo-personas", {
      signal: controller.signal,
    })
    clearTimeout(timeoutId)
    if (!res.ok) return DEFAULT_PERSONAS
    const data = await res.json()
    return Array.isArray(data) && data.length > 0 ? data : DEFAULT_PERSONAS
  } catch {
    clearTimeout(timeoutId)
    return DEFAULT_PERSONAS
  }
}

const formSchema = z.object({
  username: z.email({ message: "Invalid email address" }),
  password: z.string().min(1, { message: "Password is required" }),
}) satisfies z.ZodType<AccessToken>

type FormData = z.infer<typeof formSchema>

interface LoginSearch {
  redirect?: string
}

export const Route = createFileRoute("/login")({
  validateSearch: (search: Record<string, unknown>): LoginSearch => ({
    redirect: typeof search.redirect === "string" ? search.redirect : undefined,
  }),
  component: Login,
  beforeLoad: async () => {
    if (isLoggedIn()) {
      throw redirect({
        to: "/",
      })
    }
  },
  head: () => ({
    meta: [
      {
        title: "Log In — AICTE FDR Portal",
      },
    ],
  }),
})

function getSafeRedirect(redirectParam: string | undefined): string {
  if (!redirectParam) return "/"
  if (
    redirectParam.startsWith("/") &&
    !redirectParam.startsWith("//") &&
    !redirectParam.startsWith("/\\")
  ) {
    const cleanPath = redirectParam.split("?")[0].split("#")[0]
    if (cleanPath !== "/login" && cleanPath !== "") {
      return redirectParam
    }
  }
  return "/"
}

function Login() {
  const search = Route.useSearch()
  const redirectTarget = getSafeRedirect(search.redirect)

  const { loginMutation } = useAuth()
  const [activePersonaEmail, setActivePersonaEmail] = useState<string | null>(
    null,
  )
  const [wakingNotice, setWakingNotice] = useState<string | null>(null)
  const [loginError, setLoginError] = useState<string | null>(null)
  const [failedPersona, setFailedPersona] = useState<DemoPersona | null>(null)

  const wakeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    return () => {
      if (wakeTimerRef.current) clearTimeout(wakeTimerRef.current)
      if (retryTimerRef.current) clearTimeout(retryTimerRef.current)
    }
  }, [])

  const {
    data: demoPersonas = DEFAULT_PERSONAS,
    isFetching: isPersonasLoading,
  } = useQuery({
    queryKey: ["demo-personas"],
    queryFn: fetchDemoPersonas,
    staleTime: 1000 * 60 * 60,
  })

  // Watch for server waking state during initial persona load
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | null = null
    if (isPersonasLoading) {
      timer = setTimeout(() => {
        setWakingNotice("Waking the demo server, this can take up to a minute")
      }, 4000)
    } else {
      setWakingNotice(null)
    }
    return () => {
      if (timer) clearTimeout(timer)
    }
  }, [isPersonasLoading])

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      username: "",
      password: "",
    },
  })

  const onSubmit = (data: FormData) => {
    if (loginMutation.isPending || activePersonaEmail) return
    loginMutation.mutate(data)
  }

  const instantLogin = async (persona: DemoPersona, isRetry = false) => {
    setActivePersonaEmail(persona.email)
    setLoginError(null)

    if (wakeTimerRef.current) {
      clearTimeout(wakeTimerRef.current)
    }
    wakeTimerRef.current = setTimeout(() => {
      setWakingNotice("Waking the demo server, this can take up to a minute")
    }, 4000)

    try {
      const res = await fetch("/api/v1/login/demo", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: persona.email }),
      })

      if (wakeTimerRef.current) {
        clearTimeout(wakeTimerRef.current)
        wakeTimerRef.current = null
      }
      setWakingNotice(null)

      if (res.ok) {
        const data = await res.json()
        if (data.access_token) {
          localStorage.setItem("access_token", data.access_token)
          window.location.href = redirectTarget
          return
        }
      }

      // If response not ok and not retry, attempt auto-retry once
      if (!isRetry) {
        setWakingNotice("Waking the demo server, this can take up to a minute")
        if (retryTimerRef.current) clearTimeout(retryTimerRef.current)
        retryTimerRef.current = setTimeout(() => {
          instantLogin(persona, true)
        }, 1500)
        return
      }

      setLoginError("Demo authentication request failed. Please retry.")
      setFailedPersona(persona)
      setActivePersonaEmail(null)
    } catch {
      if (wakeTimerRef.current) {
        clearTimeout(wakeTimerRef.current)
        wakeTimerRef.current = null
      }
      setWakingNotice(null)

      if (!isRetry) {
        setWakingNotice("Waking the demo server, this can take up to a minute")
        if (retryTimerRef.current) clearTimeout(retryTimerRef.current)
        retryTimerRef.current = setTimeout(() => {
          instantLogin(persona, true)
        }, 1500)
        return
      }

      setLoginError("Demo server is taking longer than expected. Please retry.")
      setFailedPersona(persona)
      setActivePersonaEmail(null)
    }
  }

  const fillCredentials = (persona: DemoPersona) => {
    form.setValue("username", persona.email, { shouldValidate: true })
    form.setValue("password", persona.password || "AdminSecure2026!", {
      shouldValidate: true,
    })
  }

  return (
    <AuthLayout>
      <div className="flex flex-col gap-5">
        {/* Header Block */}
        <div className="flex flex-col items-center gap-2 text-center">
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
            AICTE Security Deposit / FDR Portal: interactive demo
          </h1>
          <p className="text-sm text-muted-foreground">
            Pick a role to enter. No password needed.
          </p>
          <div className="mt-1">
            <span className="inline-flex items-center text-[11px] font-medium bg-amber-500/10 text-amber-800 dark:text-amber-300 border border-amber-500/30 px-3 py-1 rounded-full shadow-2xs">
              Synthetic data, simulated bank, demo rule values
            </span>
          </div>
        </div>

        {/* Server Waking State Notice (>4s) */}
        {wakingNotice && (
          <div
            role="status"
            aria-live="polite"
            className="flex items-center gap-2.5 p-3 rounded-lg border border-amber-500/40 bg-amber-500/10 text-amber-800 dark:text-amber-200 text-xs shadow-2xs animate-pulse"
          >
            <span className="inline-block size-2 rounded-full bg-amber-500 animate-ping shrink-0" />
            <span className="font-medium">{wakingNotice}</span>
          </div>
        )}

        {/* Failure Message & Retry */}
        {loginError && (
          <div
            role="alert"
            className="flex items-center justify-between gap-2 p-3 rounded-lg border border-destructive/40 bg-destructive/10 text-destructive text-xs shadow-2xs"
          >
            <span>{loginError}</span>
            {failedPersona && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => instantLogin(failedPersona)}
                className="h-7 text-xs border-destructive/50 text-destructive hover:bg-destructive/20 shrink-0 cursor-pointer min-h-[44px]"
              >
                Retry
              </Button>
            )}
          </div>
        )}

        {/* 1-Click Persona Access Section */}
        <div className="p-3 sm:p-4 rounded-xl border-2 border-primary/30 bg-primary/5 shadow-xs">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-primary flex items-center gap-1.5">
              <span className="inline-block size-2 rounded-full bg-emerald-500 animate-pulse" />
              1-Click Demo Persona Login
            </span>
            <span className="text-[11px] text-muted-foreground font-mono bg-background/80 border px-2 py-0.5 rounded">
              Zero Password Typing
            </span>
          </div>

          <div className="flex flex-col gap-2.5">
            {demoPersonas.map((p) => {
              const isSelected = activePersonaEmail === p.email
              const isStartHere = p.role === "Technical Institution"
              const description =
                ROLE_DESCRIPTIONS[p.role] ||
                "Access portal with role permissions"

              return (
                <button
                  key={p.email}
                  type="button"
                  disabled={loginMutation.isPending || !!activePersonaEmail}
                  onClick={() => instantLogin(p)}
                  aria-label={`Enter as ${p.role}: ${p.name}. ${description}`}
                  className="flex items-center justify-between p-3 rounded-lg border bg-background/90 hover:bg-accent/80 hover:border-primary/50 transition-all cursor-pointer shadow-xs disabled:opacity-60 text-left min-h-[48px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary group"
                >
                  <div className="min-w-0 pr-2">
                    <div className="font-semibold text-xs sm:text-sm text-foreground flex items-center flex-wrap gap-1.5">
                      <span>{p.role}</span>
                      <span className="text-[11px] text-muted-foreground font-normal">
                        ({p.name})
                      </span>
                      {isStartHere && (
                        <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-emerald-600 text-white tracking-wide uppercase">
                          Start here
                        </span>
                      )}
                    </div>
                    <div className="text-[11px] text-muted-foreground mt-0.5 line-clamp-1">
                      {description}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded border font-medium hidden sm:inline-block ${p.color}`}
                    >
                      {p.badge}
                    </span>
                    <span className="text-xs text-primary font-bold group-hover:translate-x-0.5 transition-transform">
                      {isSelected ? "Entering..." : "Enter →"}
                    </span>
                  </div>
                </button>
              )
            })}
          </div>
        </div>

        {/* 6-Minute Tour Link */}
        <RouterLink
          to="/guide"
          className="flex items-center justify-between p-3 rounded-lg border border-primary/30 bg-primary/5 hover:bg-primary/10 transition-all text-xs text-primary font-medium shadow-2xs group min-h-[44px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        >
          <span className="flex items-center gap-2">
            <span className="flex size-5 items-center justify-center rounded-full bg-primary/15 text-primary">
              ✦
            </span>
            Take the 6-minute guided tour
          </span>
          <span className="text-[11px] text-muted-foreground group-hover:text-primary flex items-center gap-0.5">
            Start Tour →
          </span>
        </RouterLink>

        {/* Collapsed Standard Email & Password Sign-in */}
        <details className="group border-t pt-4">
          <summary className="flex items-center justify-between cursor-pointer py-2 text-xs font-medium text-muted-foreground hover:text-foreground list-none select-none outline-none focus-visible:ring-2 focus-visible:ring-primary rounded min-h-[44px]">
            <span className="flex items-center gap-1.5 font-semibold">
              Sign in with email
            </span>
            <span className="text-[11px] text-muted-foreground group-open:rotate-180 transition-transform">
              ▼
            </span>
          </summary>

          <div className="pt-3 flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">
                Enter your registered credentials
              </span>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() =>
                  fillCredentials(demoPersonas[1] || DEFAULT_PERSONAS[1])
                }
                className="h-7 text-[11px] text-primary hover:text-primary hover:bg-primary/10 px-2 min-h-[36px]"
              >
                Fill Demo Credentials
              </Button>
            </div>

            <Form {...form}>
              <form
                onSubmit={form.handleSubmit(onSubmit)}
                className="flex flex-col gap-4"
              >
                <FormField
                  control={form.control}
                  name="username"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-xs">Email</FormLabel>
                      <FormControl>
                        <Input
                          data-testid="email-input"
                          placeholder="user@example.com"
                          type="email"
                          className="min-h-[44px]"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage className="text-xs" />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="password"
                  render={({ field }) => (
                    <FormItem>
                      <div className="flex items-center justify-between">
                        <FormLabel className="text-xs">Password</FormLabel>
                        <RouterLink
                          to="/recover-password"
                          aria-label="Forgot your password?"
                          className="text-xs text-muted-foreground underline-offset-4 hover:underline"
                        >
                          Forgot password?
                        </RouterLink>
                      </div>
                      <FormControl>
                        <PasswordInput
                          data-testid="password-input"
                          placeholder="Password"
                          className="min-h-[44px]"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage className="text-xs" />
                    </FormItem>
                  )}
                />

                <LoadingButton
                  type="submit"
                  loading={loginMutation.isPending}
                  disabled={loginMutation.isPending || !!activePersonaEmail}
                  className="w-full mt-2 min-h-[44px]"
                >
                  Log In
                </LoadingButton>
              </form>
            </Form>
          </div>
        </details>

        <div className="mt-4 pt-4 border-t border-border/50 flex items-center justify-between text-xs text-muted-foreground">
          <RouterLink
            to="/guide"
            className="hover:text-foreground underline-offset-4 hover:underline"
          >
            Walkthrough Guide &rarr;
          </RouterLink>
          <RouterLink
            to="/verify-receipt"
            className="hover:text-foreground underline-offset-4 hover:underline text-emerald-600 dark:text-emerald-400 font-medium"
          >
            Verify Receipt &rarr;
          </RouterLink>
        </div>
      </div>
    </AuthLayout>
  )
}
