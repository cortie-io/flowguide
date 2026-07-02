import { SiteHeader } from "@/components/site-header"
import { TestFlow } from "@/components/test-flow"

export default function TestPage() {
  return (
    <div className="min-h-screen">
      <SiteHeader active="test" />
      <TestFlow />
    </div>
  )
}
