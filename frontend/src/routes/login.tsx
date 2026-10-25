import { zodResolver } from "@hookform/resolvers/zod"
import {
  createFileRoute,
  Link as RouterLink,
  redirect,
} from "@tanstack/react-router"
import { useForm } from "react-hook-form"
import { z } from "zod"

import type { Body_login_login_access_token as AccessToken } from "@/client"
import { AuthLayout } from "@/components/Common/AuthLayout"
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

const formSchema = z.object({
  username: z.email({ message: "Invalid email address" }),
  password: z
    .string()
    .min(1, { message: "Password is required" })
    .min(8, { message: "Password must be at least 8 characters" }),
}) satisfies z.ZodType<AccessToken>

type FormData = z.infer<typeof formSchema>

export const Route = createFileRoute("/login")({
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

const DEMO_PERSONAS = [
  {
    role: "Institution",
    name: "North Tech Inst.",
    email: "inst.north1@example.com",
    badge: "Maker",
    color: "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/30",
  },
  {
    role: "RO Maker",
    name: "Officer North",
    email: "officer.north@example.com",
    badge: "Regional",
    color:
      "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/30",
  },
  {
    role: "RO Checker",
    name: "Checker North",
    email: "checker.north@example.com",
    badge: "Checker",
    color:
      "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30",
  },
  {
    role: "Bureau Head",
    name: "Central Bureau",
    email: "bureau@example.com",
    badge: "Admin",
    color:
      "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30",
  },
  {
    role: "Auditor",
    name: "Reg. Auditor",
    email: "auditor@example.com",
    badge: "Read-Only",
    color:
      "bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/30",
  },
]

function Login() {
  const { loginMutation } = useAuth()
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
    if (loginMutation.isPending) return
    loginMutation.mutate(data)
  }

  const fillDemoPersona = (email: string) => {
    form.setValue("username", email, { shouldValidate: true })
    form.setValue("password", "changethis", { shouldValidate: true })
    loginMutation.mutate({ username: email, password: "changethis" })
  }

  return (
    <AuthLayout>
      <Form {...form}>
        <form
          onSubmit={form.handleSubmit(onSubmit)}
          className="flex flex-col gap-6"
        >
          <div className="flex flex-col items-center gap-1.5 text-center">
            <h1 className="text-2xl font-bold tracking-tight">
              AICTE Deposit &amp; FDR Portal
            </h1>
            <p className="text-xs text-muted-foreground">
              Statutory verification, bank gate &amp; maker-checker release
            </p>
          </div>

          <div className="grid gap-4">
            <FormField
              control={form.control}
              name="username"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Email</FormLabel>
                  <FormControl>
                    <Input
                      data-testid="email-input"
                      placeholder="user@example.com"
                      type="email"
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
                  <div className="flex items-center">
                    <FormLabel>Password</FormLabel>
                    <RouterLink
                      to="/recover-password"
                      className="ml-auto text-sm underline-offset-4 hover:underline"
                    >
                      Forgot your password?
                    </RouterLink>
                  </div>
                  <FormControl>
                    <PasswordInput
                      data-testid="password-input"
                      placeholder="Password"
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
              className="w-full"
            >
              Log In
            </LoadingButton>
          </div>

          {/* Quick Demo Persona Switcher (Charter Requirement for 6-Minute Turnkey Evaluation) */}
          <div className="mt-2 pt-4 border-t border-dashed">
            <div className="flex items-center justify-between mb-2.5">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                Quick Demo Personas
              </span>
              <span className="text-[10px] text-muted-foreground font-mono">
                pw: changethis
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {DEMO_PERSONAS.map((p) => (
                <button
                  key={p.email}
                  type="button"
                  onClick={() => fillDemoPersona(p.email)}
                  className="flex items-center justify-between p-2 rounded-lg border text-left text-xs hover:bg-accent/60 transition-colors"
                >
                  <div className="truncate pr-1">
                    <div className="font-medium text-foreground">{p.role}</div>
                    <div className="text-[10px] text-muted-foreground truncate">
                      {p.email}
                    </div>
                  </div>
                  <span
                    className={`text-[10px] px-1.5 py-0.5 rounded border shrink-0 font-medium ${p.color}`}
                  >
                    {p.badge}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </form>
      </Form>
    </AuthLayout>
  )
}
