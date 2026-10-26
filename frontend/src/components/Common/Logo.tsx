import { Link } from "@tanstack/react-router"
import { ShieldCheck } from "lucide-react"

import { cn } from "@/lib/utils"

interface LogoProps {
  variant?: "full" | "icon" | "responsive"
  className?: string
  asLink?: boolean
}

export function Logo({
  variant = "full",
  className,
  asLink = true,
}: LogoProps) {
  const Emblem = (
    <div className="flex items-center justify-center size-8 rounded-lg bg-gradient-to-br from-amber-600 via-orange-600 to-indigo-700 text-white shadow-sm ring-1 ring-white/20">
      <ShieldCheck className="size-5 text-white" />
    </div>
  )

  const Typography = (
    <div className="flex flex-col text-left leading-tight">
      <div className="flex items-center gap-1.5">
        <span className="font-bold text-sm tracking-tight text-foreground font-sans">
          AICTE
        </span>
        <span className="rounded-sm bg-primary/10 px-1 py-0.2 text-[10px] font-semibold text-primary uppercase tracking-wider">
          FDR Portal
        </span>
      </div>
      <span className="text-[10px] text-muted-foreground font-medium truncate max-w-[150px]">
        Security Deposit System
      </span>
    </div>
  )

  const content =
    variant === "responsive" ? (
      <div className={cn("flex items-center gap-2.5", className)}>
        {Emblem}
        <div className="group-data-[collapsible=icon]:hidden">{Typography}</div>
      </div>
    ) : variant === "icon" ? (
      <div className={className}>{Emblem}</div>
    ) : (
      <div className={cn("flex items-center gap-2.5", className)}>
        {Emblem}
        {Typography}
      </div>
    )

  if (!asLink) {
    return content
  }

  return (
    <Link
      to="/"
      className="inline-flex items-center outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-md"
    >
      {content}
    </Link>
  )
}
