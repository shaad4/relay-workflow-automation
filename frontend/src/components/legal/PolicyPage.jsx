import Image from "next/image";
import Link from "next/link";
import PolicyLinks from "./PolicyLinks";

export const privacyContact = (
  <a href="mailto:groveworkspace@gmail.com">groveworkspace@gmail.com</a>
);

export default function PolicyPage({ title, introduction, sections }) {
  return (
    <div className="dark min-h-screen bg-[var(--canvas)] text-[var(--text-primary)]">
      <a
        href="#policy"
        className="sr-only focus:not-sr-only focus:block focus:p-4"
      >
        Skip to policy
      </a>
      <header className="border-b border-[var(--border-subtle)]">
        <nav
          aria-label="Public navigation"
          className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-5 sm:px-10"
        >
          <Link href="/" aria-label="Relay home">
            <Image
              src="/brand/relay/relay-light.png"
              alt="Relay"
              width={120}
              height={48}
              priority
            />
          </Link>
          <div className="flex flex-wrap items-center gap-5 text-[var(--text-secondary)]">
            <PolicyLinks />
            <Link
              href="/login"
              className="rounded-md border border-[var(--border-default)] px-4 py-2 text-sm hover:bg-[var(--elevated)]"
            >
              Log in
            </Link>
          </div>
        </nav>
      </header>
      <main
        id="policy"
        className="mx-auto max-w-3xl px-6 py-14 sm:px-10 sm:py-20"
      >
        <p className="mb-4 font-mono text-xs uppercase tracking-widest text-[var(--text-secondary)]">
          Relay / Legal
        </p>
        <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
          {title}
        </h1>
        <p className="mt-5 text-sm text-[var(--text-secondary)]">
          Last updated: <time dateTime="2026-10-30">October 30, 2026</time>
        </p>
        <p className="mt-8 text-base leading-8 text-[var(--text-secondary)]">
          {introduction}
        </p>
        <nav
          aria-label="Policy sections"
          className="my-10 rounded-xl border border-[var(--border-default)] bg-[var(--surface)] p-6"
        >
          <h2 className="mb-4 text-sm font-medium">On this page</h2>
          <ol className="grid gap-3 text-sm text-[var(--text-secondary)] sm:grid-cols-2">
            {sections.map(({ id, title }, index) => (
              <li key={id}>
                <a
                  className="underline-offset-4 hover:underline focus-visible:underline"
                  href={`#${id}`}
                >
                  {index + 1}. {title}
                </a>
              </li>
            ))}
          </ol>
        </nav>
        <div className="space-y-10">
          {sections.map(({ id, title, content }, index) => (
            <section
              id={id}
              key={id}
              aria-labelledby={`${id}-heading`}
              className="scroll-mt-8"
            >
              <h2
                id={`${id}-heading`}
                className="mb-4 text-xl font-semibold tracking-tight"
              >
                {index + 1}. {title}
              </h2>
              <div className="space-y-4 text-[15px] leading-7 text-[var(--text-secondary)] [&_a]:break-words [&_a]:text-[var(--text-primary)] [&_a]:underline [&_a]:underline-offset-4 [&_code]:break-all">
                {content}
              </div>
            </section>
          ))}
        </div>
      </main>
      <footer className="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-5 border-t border-[var(--border-subtle)] px-6 py-8 text-sm text-[var(--text-secondary)] sm:px-10">
        <Link href="/">Relay — Workflow automation</Link>
        <PolicyLinks />
      </footer>
    </div>
  );
}
