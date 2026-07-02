import { Suspense } from "react"
import { SiteHeader } from "@/components/site-header"
import { ResultView } from "@/components/result-view"

export default function ResultPage() {
  return (
    <div className="min-h-screen">
      <SiteHeader />
      <Suspense
        fallback={<div className="flex min-h-[60vh] items-center justify-center text-muted-foreground">불러오는 중…</div>}
      >
        <ResultView />
      </Suspense>
    </div>
  )
}
