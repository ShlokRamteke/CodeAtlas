import type {
  HealthResponse,
  Repository,
  InvestigationResponse,
  InvestigationRequest,
} from "@archaeologist/contracts";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchHealth(): Promise<HealthResponse> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/health`, { cache: "no-store" });
    if (!res.ok) {
      return {
        status: "error",
        version: "unknown",
        database: "disconnected",
        timestamp: new Date().toISOString(),
      };
    }
    return await res.json();
  } catch (error) {
    return {
      status: "error",
      version: "offline",
      database: "disconnected",
      timestamp: new Date().toISOString(),
    };
  }
}

export async function fetchRepositories(): Promise<Repository[]> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/repositories/`, { cache: "no-store" });
    if (!res.ok) return [];
    return await res.json();
  } catch (error) {
    return [];
  }
}

export async function createInvestigation(data: InvestigationRequest): Promise<InvestigationResponse | null> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/investigations/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (error) {
    return null;
  }
}
