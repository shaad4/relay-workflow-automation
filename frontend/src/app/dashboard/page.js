import ProtectedRoute from "@/components/auth/ProtectedRoute";
import DashboardShell from "@/components/dashboard/DashboardShell";
import DashboardOverview from "@/components/dashboard/DashboardOverview";

export const metadata = {
  title: "Dashboard - Relay",
  description: "Relay workflow automation workspace dashboard.",
};

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <DashboardShell pageTitle="Overview">
        <DashboardOverview />
      </DashboardShell>
    </ProtectedRoute>
  );
}
