import ProtectedRoute from "@/components/auth/ProtectedRoute";
import DashboardShell from "@/components/dashboard/DashboardShell";
import IntegrationsPage from "@/components/integrations/IntegrationsPage";
import { mcpEndpoint } from "@/lib/integrations";
export const dynamic = "force-dynamic";
export const metadata = { title: "AI Integrations | Relay" };
export default function Page() {
  return (
    <ProtectedRoute>
      <DashboardShell pageTitle="Integrations">
        <IntegrationsPage
          endpoint={mcpEndpoint(process.env.MCP_PUBLIC_ORIGIN)}
        />
      </DashboardShell>
    </ProtectedRoute>
  );
}
