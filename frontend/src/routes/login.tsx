import { zodResolver } from "@hookform/resolvers/zod"
import { useQuery } from "@tanstack/react-query"
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

interface DemoPersona {
  role: string
  name: string
  email: string
  badge: string
  color: string
  password: string
}

const fetchDemoPersonas = async (): Promise<DemoPersona[]> => {
  try {
    const res = await fetch("/api/v1/login/demo-personas")
    if (!res.ok) return []
    return await res.json()
  } catch {
    return []
  }
}

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

function Login() {
  const { loginMutation } = useAuth()
  const { data: demoPersonas = [] } = useQuery({
    queryKey: ["demo-personas"],
    queryFn: fetchDemoPersonas,
    staleTime: 1000 * 60 * 60,
  })

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

  const fillDemoPersona = (persona: DemoPersona) => {
    form.setValue("username", persona.email, { shouldValidate: true })
    form.setValue("password", persona.password, { shouldValidate: true })
    loginMutation.mutate({
      username: persona.email,
      password: persona.password,
    })
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
              Table 1.4 calculator (DEMO values) • SIMULATED bank • dual-custody
              release
            </p>
          </div>

          <RouterLink
            to="/guide"
            className="flex items-center justify-between p-3 rounded-lg border border-primary/30 bg-primary/5 hover:bg-primary/10 transition-all text-xs text-primary font-medium shadow-2xs group"
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

          {/* Quick Demo Persona Switcher (Charter Requirement for Turnkey Evaluation) */}
          {demoPersonas.length > 0 ? (
            <div className="mt-2 pt-4 border-t border-dashed">
              <div className="flex items-center justify-between mb-2.5">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                  <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  1-Click Demo Evaluation Personas
                </span>
                <span className="text-[10px] text-muted-foreground font-mono bg-muted/60 px-2 py-0.5 rounded">
                  Instant Sign-in
                </span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {demoPersonas.map((p) => (
                  <button
                    key={p.email}
                    type="button"
                    disabled={loginMutation.isPending}
                    onClick={() => fillDemoPersona(p)}
                    className="flex items-center justify-between p-2.5 rounded-lg border text-left text-xs hover:bg-accent/80 hover:border-primary/40 transition-all cursor-pointer shadow-xs disabled:opacity-50"
                  >
                    <div className="truncate pr-1">
                      <div className="font-semibold text-foreground flex items-center gap-1">
                        {p.role}
                        <span className="text-[10px] text-muted-foreground font-normal">
                          ({p.name})
                        </span>
                      </div>
                      <div className="text-[10px] text-muted-foreground truncate font-mono">
                        {p.email}
                      </div>
                    </div>
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded border shrink-0 font-medium ${p.color}`}
                    >
                      {p.badge}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          ) : null}
        </form>
      </Form>
    </AuthLayout>
  )
}
