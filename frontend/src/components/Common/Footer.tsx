export function Footer() {
  const currentYear = new Date().getFullYear()

  return (
    <footer className="border-t py-3 px-6 bg-muted/20">
      <div className="flex flex-col items-center justify-between gap-3 text-xs sm:flex-row text-muted-foreground">
        <div>
          <span className="font-semibold text-foreground">
            AICTE Security Deposit / FDR Portal
          </span>{" "}
          &bull; PS 26265 &bull; Prototype for Regulatory Oversight (
          {currentYear})
        </div>
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center rounded-sm bg-yellow-500/10 px-2 py-0.5 text-[11px] font-medium text-yellow-700 dark:text-yellow-400 border border-yellow-500/20">
            Synthetic Data &bull; Labelled Simulators
          </span>
          <span className="text-muted-foreground/50">|</span>
          <a
            href="/docs"
            className="hover:text-foreground transition-colors underline-offset-4 hover:underline"
          >
            API Docs
          </a>
          <span className="text-muted-foreground/50">&bull;</span>
          <span className="text-muted-foreground">
            Strict RLS Context Enabled
          </span>
        </div>
      </div>
    </footer>
  )
}
