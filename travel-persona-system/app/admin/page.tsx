import { SiteHeader } from "@/components/site-header"
import { AdminDashboard } from "@/components/admin/admin-dashboard"

export default function AdminPage() {
  return (
    <div className="min-h-screen">
      <SiteHeader active="admin" />
      <AdminDashboard />
    </div>
  )
}
