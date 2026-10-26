import { ChevronDown, ChevronUp, HelpCircle } from "lucide-react"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { ABOUT_PAGES, type AboutPageContent } from "@/lib/about_pages"

interface AboutThisPageProps {
  pageKey: keyof typeof ABOUT_PAGES
  className?: string
}

export function AboutThisPage({ pageKey, className = "" }: AboutThisPageProps) {
  const [isOpen, setIsOpen] = useState(false)
  const content: AboutPageContent | undefined = ABOUT_PAGES[pageKey]

  if (!content) return null

  return (
    <Card
      className={`border-dashed border-primary/25 bg-primary/5 shadow-none transition-all ${className}`}
    >
      <div className="p-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="flex size-6 items-center justify-center rounded-full bg-primary/10 text-primary">
              <HelpCircle className="size-3.5" />
            </span>
            <div>
              <span className="text-xs font-semibold text-foreground">
                About this screen: {content.title}
              </span>
            </div>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => setIsOpen(!isOpen)}
            className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground"
            aria-expanded={isOpen}
          >
            <span className="mr-1">
              {isOpen ? "Hide details" : "What is this?"}
            </span>
            {isOpen ? (
              <ChevronUp className="size-3" />
            ) : (
              <ChevronDown className="size-3" />
            )}
          </Button>
        </div>

        {isOpen && (
          <CardContent className="px-0 pt-3 pb-1 text-xs text-muted-foreground">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 border-t border-border/50 pt-2.5">
              <div className="space-y-1">
                <div className="font-semibold text-foreground flex items-center gap-1.5 text-[11px] uppercase tracking-wide">
                  <span className="size-1.5 rounded-full bg-blue-500" />
                  What this is
                </div>
                <p className="text-[11px] leading-relaxed">
                  {content.whatThisIs}
                </p>
              </div>

              <div className="space-y-1">
                <div className="font-semibold text-foreground flex items-center gap-1.5 text-[11px] uppercase tracking-wide">
                  <span className="size-1.5 rounded-full bg-purple-500" />
                  What to do here
                </div>
                <p className="text-[11px] leading-relaxed">
                  {content.whatToDoHere}
                </p>
              </div>

              <div className="space-y-1">
                <div className="font-semibold text-foreground flex items-center gap-1.5 text-[11px] uppercase tracking-wide">
                  <span className="size-1.5 rounded-full bg-emerald-500" />
                  What to notice
                </div>
                <p className="text-[11px] leading-relaxed">
                  {content.whatToNotice}
                </p>
              </div>
            </div>
          </CardContent>
        )}
      </div>
    </Card>
  )
}
