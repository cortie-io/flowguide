"use client"

import ReactMarkdown, { type Components } from "react-markdown"
import remarkGfm from "remark-gfm"

const components: Components = {
  h1: ({ children }) => <h1 className="mt-8 font-serif text-3xl font-bold first:mt-0">{children}</h1>,
  h2: ({ children }) => (
    <h2 className="mt-8 border-t border-border pt-6 font-serif text-2xl font-bold first:mt-0 first:border-0 first:pt-0">
      {children}
    </h2>
  ),
  h3: ({ children }) => <h3 className="mt-6 font-serif text-lg font-bold">{children}</h3>,
  p: ({ children }) => <p className="mt-3 text-pretty leading-relaxed text-foreground/90">{children}</p>,
  a: ({ href, children }) => (
    <a href={href} className="font-medium text-primary underline underline-offset-4 hover:opacity-80">
      {children}
    </a>
  ),
  ul: ({ children }) => <ul className="mt-3 list-disc space-y-1.5 pl-5">{children}</ul>,
  ol: ({ children }) => <ol className="mt-3 list-decimal space-y-1.5 pl-5">{children}</ol>,
  li: ({ children }) => <li className="leading-relaxed text-foreground/90">{children}</li>,
  blockquote: ({ children }) => (
    <blockquote className="mt-4 rounded-r-xl border-l-4 border-primary bg-secondary/40 px-4 py-3 text-muted-foreground">
      {children}
    </blockquote>
  ),
  hr: () => <hr className="my-8 border-border" />,
  code: ({ children, className }) => {
    const isBlock = /language-/.test(className ?? "")
    if (isBlock) {
      return (
        <code className={className}>
          {children}
        </code>
      )
    }
    return <code className="rounded bg-secondary px-1.5 py-0.5 font-mono text-[0.85em]">{children}</code>
  },
  pre: ({ children }) => (
    <pre className="mt-4 overflow-x-auto rounded-xl border border-border bg-secondary/40 p-4 font-mono text-sm">
      {children}
    </pre>
  ),
  table: ({ children }) => (
    <div className="mt-4 overflow-x-auto rounded-xl border border-border">
      <table className="w-full border-collapse text-sm">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-secondary/60">{children}</thead>,
  th: ({ children }) => (
    <th className="border-b border-border px-3 py-2 text-left font-semibold text-foreground">{children}</th>
  ),
  td: ({ children }) => <td className="border-b border-border/60 px-3 py-2 align-top text-foreground/90">{children}</td>,
  strong: ({ children }) => <strong className="font-bold text-foreground">{children}</strong>,
}

export function MarkdownContent({ content }: { content: string }) {
  return (
    <div className="text-sm">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  )
}
