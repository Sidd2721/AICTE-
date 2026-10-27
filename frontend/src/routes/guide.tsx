import { createFileRoute, Link } from "@tanstack/react-router"
import {
  ArrowRight,
  BookOpen,
  Check,
  CheckCircle2,
  Circle,
  Copy,
  ExternalLink,
  HelpCircle,
  Info,
  Sparkles,
  Terminal,
  UserCheck,
} from "lucide-react"
import { useEffect, useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import useAuth from "@/hooks/useAuth"
import { GLOSSARY_TERMS } from "@/lib/glossary"

export const Route = createFileRoute("/guide")({
  component: GuidePage,
})

interface GuideStep {
  id: string
  step_number: number
  title: string
  persona: string
  email: string
  route: string
  goal: string
  do: string[]
  expect: string
  why: string
}

const GUIDE_STEPS: GuideStep[] = [
  {
    id: "step-1",
    step_number: 1,
    title: "Institution: coverage card -> calculator -> submit FDR",
    persona: "Institution User (North Tech)",
    email: "inst.north1@example.com",
    route: "/deposits",
    goal: "Check mandatory security deposit requirements, calculate required amount, and submit a new fixed deposit record.",
    do: [
      "Sign in as the Institution persona using the 1-click switcher.",
      "Review the Coverage Card showing required versus confirmed deposits.",
      "Open the calculator to compute required funds based on selected programmes.",
      "Submit a new FDR with reference number, bank code, and 10-year maturity date.",
    ],
    expect:
      "A new instrument record appears with the Claimed badge, pending bank verification.",
    why: "Institutions can see exact required deposits computed directly from handbook rules without manual guesswork.",
  },
  {
    id: "step-2",
    step_number: 2,
    title: "RO requests bank confirmation -> SIMULATED reply -> gate report",
    persona: "Regional Officer (North Region)",
    email: "officer.north@example.com",
    route: "/deposits",
    goal: "Request authoritative bank verification for a submitted deposit and inspect the cryptographic validation report.",
    do: [
      "Switch to the Regional Officer persona.",
      "Open the case page for the submitted instrument.",
      "Click the single primary action button 'Request Bank Confirmation'.",
      "View the full cryptographic verification gate report.",
    ],
    expect:
      "All six checks pass; the status badge turns green to Confirmed (SIMULATED).",
    why: "No deposit is trusted on institution claims alone. Bank verification confirms validity cryptographically.",
  },
  {
    id: "step-3",
    step_number: 3,
    title: "Break the gate: forged letter / appended page / replayed token",
    persona: "Regional Officer (North Region)",
    email: "officer.north@example.com",
    route: "/deposits",
    goal: "Test system defenses by attempting three common fraud attacks against the bank verification gate.",
    do: [
      "In the Break-Me Workbench on the case page, select 'Forged Letter Attack'.",
      "Test an 'Appended Bytes' attack where trailing pages were added.",
      "Test a 'Replayed Token' attack using an already consumed verification challenge.",
    ],
    expect:
      "Every attack is immediately rejected with clear explanations and zero false passes.",
    why: "Standard PDF signers often miss appended pages. The portal enforces byte-prefix and boundary checks.",
  },
  {
    id: "step-4",
    step_number: 4,
    title:
      "Amount mismatch -> flag with plain message -> waiver demands a reason",
    persona: "Regional Officer (North Region)",
    email: "officer.north@example.com",
    route: "/deposits",
    goal: "Detect an amount discrepancy between bank and institution claims and enforce accountability before waiver.",
    do: [
      "Run an amount mismatch test where the bank confirms less than claimed.",
      "Notice the plain-language warning explaining the shortfall.",
      "Try waiving the flag with a blank reason to confirm validation blocks it.",
      "Enter a detailed reason of at least 10 characters to record the waiver.",
    ],
    expect:
      "The waiver is accepted only with a written justification and permanently logged to audit.",
    why: "Officers cannot silently bypass discrepancies without creating an immutable paper trail.",
  },
  {
    id: "step-5",
    step_number: 5,
    title:
      "Bureau advances the clock through rule offsets -> worker -> reminders",
    persona: "Bureau Approver (Central)",
    email: "bureau@example.com",
    route: "/dashboard",
    goal: "Fast-forward the virtual clock to test automated background reminders and escalation notices.",
    do: [
      "Switch to the Bureau Approver persona.",
      "Open the Time Machine dropdown in the header and advance +30 days.",
      "Advance to +60 days to trigger escalation notices.",
      "Advance to +90 days to verify overdue alerts and review emails in Mailpit.",
    ],
    expect:
      "Dashboard categories automatically update and reminder emails appear without manual tracking.",
    why: "Automates tracking for 10-year deposits so renewals and maturities are never forgotten.",
  },
  {
    id: "step-6",
    step_number: 6,
    title: "Renewal: replacement FDR -> chain and coverage-gap check",
    persona: "Institution User (North Tech)",
    email: "inst.north1@example.com",
    route: "/deposits",
    goal: "Submit a replacement FDR linked to an expiring instrument and verify custody continuity.",
    do: [
      "Switch back to Institution persona.",
      "Submit a renewal FDR referencing the original instrument ID.",
      "Open the case page to review the linked predecessor.",
      "Check that coverage continuity is maintained without unmonitored gaps.",
    ],
    expect:
      "The old instrument links to the new one in a complete verifiable renewal chain.",
    why: "Prevents institutions from letting deposits lapse during renewal transitions.",
  },
  {
    id: "step-7",
    step_number: 7,
    title:
      "Release: institution requests -> RO verifies -> same RO approve blocked -> bureau approves -> receipt -> offline verify",
    persona: "Institution & Bureau Personas",
    email: "bureau@example.com",
    route: "/deposits",
    goal: "Perform dual-custody authorized deposit release and verify cryptographic encashment receipt.",
    do: [
      "As Institution, request term completion release.",
      "As Regional Officer, verify the request (maker step).",
      "Confirm that Regional Officer cannot approve (role check blocks it).",
      "As Bureau Approver (checker), approve release and view cryptographic receipt.",
    ],
    expect:
      "Status becomes Released, receipt token is generated, and audit chain passes verification.",
    why: "No single officer can authorize the release of security deposits. Dual-custody stops insider fraud.",
  },
]

function GuidePage() {
  const { loginMutation } = useAuth()
  const [copiedCmd, setCopiedCmd] = useState<string | null>(null)
  const [completedSteps, setCompletedSteps] = useState<Record<string, boolean>>(
    {},
  )

  const handleCopyCmd = (cmd: string) => {
    navigator.clipboard.writeText(cmd)
    setCopiedCmd(cmd)
    setTimeout(() => setCopiedCmd(null), 2000)
  }

  useEffect(() => {
    try {
      const saved = localStorage.getItem("aicte_guide_completed")
      if (saved) {
        setCompletedSteps(JSON.parse(saved))
      }
    } catch {
      // Fallback cleanly if localStorage is restricted
    }
  }, [])

  const toggleStep = (id: string) => {
    setCompletedSteps((prev) => {
      const next = { ...prev, [id]: !prev[id] }
      try {
        localStorage.setItem("aicte_guide_completed", JSON.stringify(next))
      } catch {
        // Safe localStorage write
      }
      return next
    })
  }

  const completedCount = Object.values(completedSteps).filter(Boolean).length
  const progressPercent = Math.round(
    (completedCount / GUIDE_STEPS.length) * 100,
  )

  const handleSwitchPersona = async (email: string) => {
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
          window.location.href = "/"
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
    <div className="min-h-screen bg-background text-foreground py-8 px-4 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-4xl space-y-8">
        {/* Navigation & Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-6 border-b">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="flex size-7 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <BookOpen className="size-4" />
              </span>
              <span className="text-xs font-semibold uppercase tracking-wider text-primary">
                Turnkey Evaluation
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
              6-Minute Interactive Guided Tour
            </h1>
            <p className="text-sm text-muted-foreground">
              Seven verifiable capabilities proving regulatory security,
              dual-custody governance, and cryptographic bank verification.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Link to="/login">
              <Button
                variant="outline"
                size="sm"
                className="h-9 gap-1.5 text-xs"
              >
                Back to Sign In
              </Button>
            </Link>
            <Link to="/">
              <Button size="sm" className="h-9 gap-1.5 text-xs">
                Launch Portal
                <ArrowRight className="size-3.5" />
              </Button>
            </Link>
          </div>
        </div>

        {/* Progress Bar & Honesty Banner */}
        <div className="space-y-4">
          <Card className="border border-border/80 bg-card/60 shadow-xs">
            <CardContent className="p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-foreground">
                    Tour Progress: {completedCount} of {GUIDE_STEPS.length}{" "}
                    Completed
                  </span>
                  <Badge variant="outline" className="text-[10px] font-mono">
                    {progressPercent}%
                  </Badge>
                </div>
                <div className="w-64 sm:w-80 h-2 bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary transition-all duration-300"
                    style={{ width: `${progressPercent}%` }}
                  />
                </div>
              </div>

              <a
                href="#glossary"
                className="text-xs text-primary hover:underline flex items-center gap-1 font-medium"
              >
                <HelpCircle className="size-3.5" />
                Jump to Terms Glossary
              </a>
            </CardContent>
          </Card>

          <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-900 dark:text-amber-300 flex items-start gap-2.5">
            <Info className="size-4 shrink-0 mt-0.5" />
            <div className="space-y-0.5">
              <span className="font-semibold">DEMO Environment Notice:</span>{" "}
              All bank adapters and emails are <strong>SIMULATED</strong>.
              Instrument reference numbers and deposit values are{" "}
              <strong>labelled synthetic data</strong>. Approval guidelines
              reflect DEMO handbook tables.
            </div>
          </div>
        </div>

        {/* Step Cards */}
        <div className="space-y-6">
          {GUIDE_STEPS.map((step) => {
            const isDone = Boolean(completedSteps[step.id])

            return (
              <Card
                key={step.id}
                className={`transition-all border shadow-xs ${
                  isDone
                    ? "border-emerald-500/40 bg-emerald-500/5 dark:bg-emerald-950/10"
                    : "hover:border-primary/40"
                }`}
              >
                <CardHeader className="pb-3">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
                    <div className="flex items-start gap-3">
                      <button
                        type="button"
                        onClick={() => toggleStep(step.id)}
                        className="mt-0.5 text-muted-foreground hover:text-primary transition-colors cursor-pointer"
                        title={isDone ? "Mark incomplete" : "Mark as done"}
                        aria-label={`Toggle completion for Step ${step.step_number}`}
                      >
                        {isDone ? (
                          <CheckCircle2 className="size-5 text-emerald-600 dark:text-emerald-400" />
                        ) : (
                          <Circle className="size-5" />
                        )}
                      </button>

                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                            STEP {step.step_number}
                          </span>
                          <Badge
                            variant="outline"
                            className="text-[10px] bg-background/50"
                          >
                            {step.persona}
                          </Badge>
                        </div>
                        <CardTitle className="text-base sm:text-lg font-semibold mt-0.5">
                          {step.title}
                        </CardTitle>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 pl-8 sm:pl-0">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => handleSwitchPersona(step.email)}
                        disabled={loginMutation.isPending}
                        className="h-7 text-xs gap-1.5 border-dashed"
                      >
                        <UserCheck className="size-3" />
                        Switch to {step.persona.split(" ")[0]}
                      </Button>

                      <Link to={step.route}>
                        <Button
                          size="sm"
                          variant="secondary"
                          className="h-7 text-xs gap-1"
                        >
                          Open Screen
                          <ExternalLink className="size-3" />
                        </Button>
                      </Link>
                    </div>
                  </div>
                  <CardDescription className="text-xs pt-1 pl-8">
                    <strong>Goal:</strong> {step.goal}
                  </CardDescription>
                </CardHeader>

                <CardContent className="pl-8 pt-0 space-y-3 text-xs">
                  <div className="space-y-1.5 bg-background/60 p-3 rounded-lg border border-border/50">
                    <span className="font-semibold text-foreground text-[11px] uppercase tracking-wide">
                      What to do:
                    </span>
                    <ol className="list-decimal pl-4 space-y-1 text-muted-foreground">
                      {step.do.map((item, idx) => (
                        <li key={idx} className="leading-relaxed">
                          {item}
                        </li>
                      ))}
                    </ol>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                    <div className="p-2.5 rounded bg-muted/40 border border-border/40">
                      <span className="font-semibold text-foreground block mb-0.5">
                        What you should see:
                      </span>
                      <p className="text-muted-foreground leading-relaxed">
                        {step.expect}
                      </p>
                    </div>
                    <div className="p-2.5 rounded bg-muted/40 border border-border/40">
                      <span className="font-semibold text-foreground block mb-0.5">
                        Why this matters:
                      </span>
                      <p className="text-muted-foreground leading-relaxed">
                        {step.why}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>

        {/* Section: Regulatory Terms Glossary (G4) */}
        <div id="glossary" className="pt-8 border-t space-y-4">
          <div className="space-y-1">
            <h2 className="text-xl font-bold tracking-tight flex items-center gap-2">
              <Sparkles className="size-5 text-primary" />
              Regulatory & Cryptographic Glossary
            </h2>
            <p className="text-xs text-muted-foreground">
              Plain-language definitions for key banking, governance, and
              cryptographic concepts used across screens.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {Object.values(GLOSSARY_TERMS).map((term) => (
              <Card key={term.id} className="p-3 bg-card/60 shadow-none border">
                <div className="space-y-1">
                  <div className="font-semibold text-xs text-foreground flex items-center gap-1.5">
                    <span className="size-1.5 rounded-full bg-primary" />
                    {term.term}
                  </div>
                  <p className="text-[11px] text-foreground/80 font-medium leading-relaxed">
                    {term.plainSummary}
                  </p>
                  <p className="text-[10px] text-muted-foreground leading-relaxed pt-1 border-t border-border/40">
                    {term.detail}
                  </p>
                </div>
              </Card>
            ))}
          </div>
        </div>

        {/* Section: CLI Demo Data Controls (Requirement 2.3) */}
        <div id="cli-controls" className="pt-8 border-t space-y-4">
          <div className="space-y-1">
            <h2 className="text-xl font-bold tracking-tight flex items-center gap-2">
              <Terminal className="size-5 text-primary" />
              Demo Data & Scenario Controller (CLI)
            </h2>
            <p className="text-xs text-muted-foreground">
              Run deterministic scenarios and database reset commands from your
              terminal. Zero destructive UI actions are exposed in the web
              interface.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {[
              {
                title: "Judge Scenario (7-Step Demo)",
                desc: "5 fixed-UUID instruments mapped directly to presentation steps.",
                cmd: "uv run python scripts/demo_data.py load --scenario judge",
              },
              {
                title: "Rich Seed Scenario",
                desc: "11 institutions across all regions with 18+ diverse instruments.",
                cmd: "uv run python scripts/demo_data.py load --scenario rich",
              },
              {
                title: "Stress Dataset (2,000 Instruments)",
                desc: "Deterministic high-volume dataset for p95 latency verification.",
                cmd: "uv run python scripts/demo_data.py load --scenario stress",
              },
              {
                title: "Empty Database (Users + Rules Only)",
                desc: "0 instruments; verifies clean submission workflows.",
                cmd: "uv run python scripts/demo_data.py load --scenario empty",
              },
              {
                title: "Live Database Table Status",
                desc: "Prints table row counts and detected scenario in terminal.",
                cmd: "uv run python scripts/demo_data.py status",
              },
              {
                title: "Full Database Reset & Re-migration",
                desc: "Pristine database recreate, Alembic head upgrade, and Judge reload.",
                cmd: "uv run python scripts/demo_data.py reset",
              },
            ].map((item, idx) => (
              <Card
                key={idx}
                className="p-3 bg-card/60 border flex flex-col justify-between"
              >
                <div>
                  <div className="font-semibold text-xs text-foreground flex items-center justify-between">
                    <span>{item.title}</span>
                    <Badge variant="outline" className="text-[10px] font-mono">
                      CLI
                    </Badge>
                  </div>
                  <p className="text-[11px] text-muted-foreground mt-1">
                    {item.desc}
                  </p>
                </div>
                <div className="mt-2.5 pt-2 border-t border-border/40 flex items-center justify-between gap-2">
                  <code className="text-[10px] font-mono bg-muted/60 px-1.5 py-0.5 rounded truncate flex-1 text-muted-foreground">
                    {item.cmd}
                  </code>
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-6 text-[10px] gap-1 px-2 shrink-0"
                    onClick={() => handleCopyCmd(item.cmd)}
                  >
                    {copiedCmd === item.cmd ? (
                      <>
                        <Check className="size-3 text-emerald-600" /> Copied
                      </>
                    ) : (
                      <>
                        <Copy className="size-3" /> Copy
                      </>
                    )}
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="pt-6 border-t text-center text-xs text-muted-foreground">
          AICTE PS 26265 Prototype • Synthetic Demonstration Dataset • Single
          source of truth: <code>docs/guide.json</code>
        </div>
      </div>
    </div>
  )
}
