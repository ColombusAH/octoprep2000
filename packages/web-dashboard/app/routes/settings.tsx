import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Settings as SettingsIcon } from "lucide-react";
import { Label } from "~/components/ui/label";
import { Switch } from "~/components/ui/switch";
import { Separator } from "~/components/ui/separator";
import { Button } from "~/components/ui/button";
import type { Language } from "~/lib/api";
import { getUiLanguage, setUiLanguage } from "~/lib/i18n";

export const Route = createFileRoute("/settings")({ component: SettingsPage });

function LanguageRow() {
  const [lang, setLang] = useState<Language>("en");
  // Cookie isn't available during SSR — read it after mount so this never
  // mismatches the inline <head> script's already-applied lang/dir.
  useEffect(() => {
    setLang(getUiLanguage());
  }, []);

  const choose = (next: Language) => {
    setUiLanguage(next);
    setLang(next);
  };

  return (
    <div className="flex items-center justify-between py-4">
      <div className="flex flex-col gap-1">
        <Label id="ui-language-label" className="text-sm font-semibold text-pearl">
          Interface language
        </Label>
        <span className="text-sm text-muted-foreground">
          Switch the dashboard between English and Hebrew (RTL).
        </span>
      </div>
      <div role="group" aria-labelledby="ui-language-label" className="inline-flex gap-1.5">
        <Button
          type="button"
          size="sm"
          variant={lang === "en" ? "default" : "outline"}
          aria-pressed={lang === "en"}
          onClick={() => choose("en")}
        >
          English
        </Button>
        <Button
          type="button"
          size="sm"
          variant={lang === "he" ? "default" : "outline"}
          aria-pressed={lang === "he"}
          onClick={() => choose("he")}
        >
          עברית
        </Button>
      </div>
    </div>
  );
}

function Row({
  id,
  title,
  desc,
  defaultChecked,
}: {
  id: string;
  title: string;
  desc: string;
  defaultChecked?: boolean;
}) {
  const [checked, setChecked] = useState(!!defaultChecked);
  return (
    <div className="flex items-center justify-between py-4">
      <div className="flex flex-col gap-1">
        <Label htmlFor={id} className="text-sm font-semibold text-pearl">
          {title}
        </Label>
        <span className="text-sm text-muted-foreground">{desc}</span>
      </div>
      <Switch id={id} checked={checked} onCheckedChange={setChecked} />
    </div>
  );
}

function SettingsPage() {
  return (
    <main className="mx-auto w-full max-w-2xl px-8 py-16">
      <p className="font-mono text-xs tracking-[0.2em] text-teal uppercase">Demo</p>
      <h1 className="mt-3 flex items-center gap-3 font-display text-3xl font-bold tracking-tight text-pearl">
        <SettingsIcon className="size-7 text-teal" aria-hidden="true" />
        Settings
      </h1>
      <p className="mt-3 max-w-xl text-sm text-muted-foreground">
        Dial in how OctoPrep coaches you, before your next take.
      </p>

      <div className="mt-8 rounded-xl border border-border bg-card px-6">
        <LanguageRow />
        <Separator />
        <Row
          id="live-tips"
          title="Live coaching tips"
          desc="Show real-time toasts during a recording."
          defaultChecked
        />
        <Separator />
        <Row
          id="sound-fx"
          title="Broadcast sound effects"
          desc="Play a chime when a session ends."
        />
        <Separator />
        <Row
          id="auto-archive"
          title="Auto-archive reports"
          desc="Save every completed session to the Tape Rack."
          defaultChecked
        />
      </div>
    </main>
  );
}
