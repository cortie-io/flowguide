import Form from "next/form";

import { Input } from "../ui/input";
import { Label } from "../ui/label";

export function AuthForm({
  action,
  children,
  defaultEmail = "",
  defaultName = "",
  mode = "login",
}: {
  action: NonNullable<
    string | ((formData: FormData) => void | Promise<void>) | undefined
  >;
  children: React.ReactNode;
  defaultEmail?: string;
  defaultName?: string;
  mode?: "login" | "register";
}) {
  return (
    <Form action={action} className="flex flex-col gap-4">
      {mode === "register" ? (
        <div className="flex flex-col gap-2">
          <Label className="font-normal text-muted-foreground" htmlFor="name">
            Name
          </Label>
          <Input
            autoComplete="name"
            className="h-10 rounded-lg border-border/50 bg-muted/50 text-sm transition-colors focus:border-foreground/20 focus:bg-muted"
            defaultValue={defaultName}
            id="name"
            name="name"
            placeholder="Your full name"
            required
            type="text"
          />
        </div>
      ) : null}

      <div className="flex flex-col gap-2">
        <Label className="font-normal text-muted-foreground" htmlFor="email">
          Email
        </Label>
        <Input
          autoComplete="email"
          autoFocus={mode !== "register"}
          className="h-10 rounded-lg border-border/50 bg-muted/50 text-sm transition-colors focus:border-foreground/20 focus:bg-muted"
          defaultValue={defaultEmail}
          id="email"
          name="email"
          placeholder="you@someo.ne"
          required
          type="email"
        />
      </div>

      {mode === "register" ? (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-2">
              <Label
                className="font-normal text-muted-foreground"
                htmlFor="company"
              >
                Company
              </Label>
              <Input
                autoComplete="organization"
                className="h-10 rounded-lg border-border/50 bg-muted/50 text-sm transition-colors focus:border-foreground/20 focus:bg-muted"
                id="company"
                name="company"
                placeholder="Optional"
                type="text"
              />
            </div>

            <div className="flex flex-col gap-2">
              <Label
                className="font-normal text-muted-foreground"
                htmlFor="jobTitle"
              >
                Job title
              </Label>
              <Input
                autoComplete="organization-title"
                className="h-10 rounded-lg border-border/50 bg-muted/50 text-sm transition-colors focus:border-foreground/20 focus:bg-muted"
                id="jobTitle"
                name="jobTitle"
                placeholder="Optional"
                type="text"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-2">
              <Label
                className="font-normal text-muted-foreground"
                htmlFor="phone"
              >
                Phone
              </Label>
              <Input
                autoComplete="tel"
                className="h-10 rounded-lg border-border/50 bg-muted/50 text-sm transition-colors focus:border-foreground/20 focus:bg-muted"
                id="phone"
                name="phone"
                placeholder="Optional"
                type="tel"
              />
            </div>

            <div className="flex flex-col gap-2">
              <Label
                className="font-normal text-muted-foreground"
                htmlFor="useCase"
              >
                Primary use case
              </Label>
              <Input
                className="h-10 rounded-lg border-border/50 bg-muted/50 text-sm transition-colors focus:border-foreground/20 focus:bg-muted"
                id="useCase"
                name="useCase"
                placeholder="e.g. Workflow automation"
                type="text"
              />
            </div>
          </div>
        </>
      ) : null}

      <div className="flex flex-col gap-2">
        <Label className="font-normal text-muted-foreground" htmlFor="password">
          Password
        </Label>
        <Input
          className="h-10 rounded-lg border-border/50 bg-muted/50 text-sm transition-colors focus:border-foreground/20 focus:bg-muted"
          id="password"
          name="password"
          placeholder="&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;"
          required
          type="password"
        />
      </div>

      {children}
    </Form>
  );
}
