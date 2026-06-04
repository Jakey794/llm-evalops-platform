import type { HealthResponse } from "@/lib/types";

const API_BASE_URL =
	process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function getBackendHealth(): Promise<HealthResponse> {
	const healthUrl = `${API_BASE_URL}/health`;
	const response = await fetch(healthUrl, {
		cache: "no-store",
	});

	if (!response.ok) {
		throw new Error(
			`Backend health check failed for ${healthUrl}: ${response.status} ${response.statusText}`,
		);
	}

	return response.json() as Promise<HealthResponse>;
}
