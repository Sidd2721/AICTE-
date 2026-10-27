import { createFileRoute } from "@tanstack/react-router"
import {
  Activity,
  KeyRound,
  Network,
  ShieldCheck,
  Terminal,
  Webhook,
} from "lucide-react"
import { useState } from "react"
import { ApiKeysPanel } from "@/components/Integrate/ApiKeysPanel"
import { BankFlowTestPanel } from "@/components/Integrate/BankFlowTestPanel"
import { OutboxTailPanel } from "@/components/Integrate/OutboxTailPanel"
import { QuickstartPanel } from "@/components/Integrate/QuickstartPanel"
import { WebhooksPanel } from "@/components/Integrate/WebhooksPanel"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

export const Route = createFileRoute("/_layout/integrate")({
  component: IntegrateView,
})

function IntegrateView() {
  const [activeTab, setActiveTab] = useState("quickstart")

  return (
    <div className="flex flex-col gap-6 p-6 max-w-7xl mx-auto w-full">
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-2">
          <Network className="h-6 w-6 text-primary" />
          <h1 className="text-2xl font-bold tracking-tight">
            Integration Hub & Regulatory Machine APIs
          </h1>
        </div>
        <p className="text-sm text-muted-foreground">
          Machine-to-machine interfaces for Scheduled Commercial Banks, Core
          Banking Adapters, SFMS Gateways, and AICTE Central IT.
        </p>
      </div>

      <Tabs
        value={activeTab}
        onValueChange={setActiveTab}
        className="space-y-6"
      >
        <TabsList className="grid grid-cols-2 sm:grid-cols-5 w-full max-w-3xl">
          <TabsTrigger value="quickstart" className="gap-1.5 text-xs">
            <Terminal className="h-3.5 w-3.5" /> Quickstart
          </TabsTrigger>
          <TabsTrigger value="keys" className="gap-1.5 text-xs">
            <KeyRound className="h-3.5 w-3.5" /> API Keys
          </TabsTrigger>
          <TabsTrigger value="webhooks" className="gap-1.5 text-xs">
            <Webhook className="h-3.5 w-3.5" /> Webhooks
          </TabsTrigger>
          <TabsTrigger value="bankflow" className="gap-1.5 text-xs">
            <ShieldCheck className="h-3.5 w-3.5" /> Try Bank Flow
          </TabsTrigger>
          <TabsTrigger value="outbox" className="gap-1.5 text-xs">
            <Activity className="h-3.5 w-3.5" /> Event Stream
          </TabsTrigger>
        </TabsList>

        <TabsContent value="quickstart">
          <QuickstartPanel />
        </TabsContent>

        <TabsContent value="keys">
          <ApiKeysPanel />
        </TabsContent>

        <TabsContent value="webhooks">
          <WebhooksPanel />
        </TabsContent>

        <TabsContent value="bankflow">
          <BankFlowTestPanel />
        </TabsContent>

        <TabsContent value="outbox">
          <OutboxTailPanel />
        </TabsContent>
      </Tabs>
    </div>
  )
}
