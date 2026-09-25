import ProtectedRoute from "@/components/auth/ProtectedRoute";
import DashboardShell from "@/components/dashboard/DashboardShell";
import DashboardSkeleton from "@/components/dashboard/DashboardSkeleton";

export const metadata = {
  title: "Dashboard - Relay",
  description: "Relay workflow automation workspace dashboard.",
};

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <DashboardShell pageTitle="Dashboard">
        <DashboardSkeleton />
      </DashboardShell>
    </ProtectedRoute>
  );
}
