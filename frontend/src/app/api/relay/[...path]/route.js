import { proxyRequest } from "@/lib/server/apiProxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const GET = proxyRequest;
export const HEAD = proxyRequest;
export const POST = proxyRequest;
export const PUT = proxyRequest;
export const PATCH = proxyRequest;
export const DELETE = proxyRequest;
export const OPTIONS = proxyRequest;
