import IntegrationAnnouncement from "@/components/integrations/IntegrationAnnouncement";
import { mcpEndpoint } from "@/lib/integrations";
export const dynamic = "force-dynamic";
import ProtectedRoute from "@/components/auth/ProtectedRoute";
import DashboardShell from "@/components/dashboard/DashboardShell";
import DashboardOverview from "@/components/dashboard/DashboardOverview";

export const metadata = {
  title: "Dashboard",
  description: "Relay workflow automation workspace dashboard.",
};

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <DashboardShell pageTitle="Overview">
        <DashboardOverview />
        <IntegrationAnnouncement
          enabled={Boolean(mcpEndpoint(process.env.MCP_PUBLIC_ORIGIN))}
        />
      </DashboardShell>
    </ProtectedRoute>
  );
}
