import { gatewayReady } from "@/lib/server/apiProxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  return gatewayReady();
}
