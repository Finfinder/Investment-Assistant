"use client";

import { useId, useState } from "react";

interface SectionProps {
  title: string;
  id?: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}

export default function Section({ title, id, defaultOpen = true, children }: Readonly<SectionProps>) {
  const [open, setOpen] = useState(defaultOpen);
  const panelId = useId();

  return (
    <div id={id}>
      <button
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        aria-controls={panelId}
        className="flex w-full items-center justify-between py-2 text-left"
      >
        <h2 className="text-xl font-bold">{title}</h2>
        <span className={`text-muted transition-transform ${open ? "rotate-180" : ""}`}>▼</span>
      </button>
      {open && (
        <section id={panelId} aria-label={title} className="mt-2">
          {children}
        </section>
      )}
    </div>
  );
}
