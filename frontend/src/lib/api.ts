import type {
	CompareRunsResponse,
	DashboardOverview,
	DatasetDetail,
	DatasetSummary,
	EvalResult,
	EvalRun,
	EvalRunCreateRequest,
	FailedExample,
	HealthResponse,
	ModelConfig,
	PromptVersion,
	RunAnalytics,
	TestCase,
} from "@/lib/types";

export class ApiError extends Error {
	readonly status: number;
	readonly detail: string;

	constructor(status: number, statusText: string, detail: string) {
		super(detail || `Request failed (${status} ${statusText})`);
		this.name = "ApiError";
		this.status = status;
		this.detail = detail || statusText;
	}
}

export async function getBackendHealth(): Promise<HealthResponse> {
	return fetchApi<HealthResponse>("/health");
}

export async function getDatasets(): Promise<DatasetSummary[]> {
	return fetchApi<DatasetSummary[]>("/datasets");
}

export async function getDataset(datasetId: string): Promise<DatasetDetail> {
	return fetchApi<DatasetDetail>(`/datasets/${encodeURIComponent(datasetId)}`);
}

export async function getDatasetTestCases(
	datasetId: string,
): Promise<TestCase[]> {
	return fetchApi<TestCase[]>(
		`/datasets/${encodeURIComponent(datasetId)}/test-cases`,
	);
}

export async function getEvalRuns(): Promise<EvalRun[]> {
	return fetchApi<EvalRun[]>("/eval-runs");
}

export async function getDashboardOverview(): Promise<DashboardOverview> {
	return fetchApi<DashboardOverview>("/eval-runs/overview");
}

export async function getEvalRun(runId: string): Promise<EvalRun> {
	return fetchApi<EvalRun>(`/eval-runs/${encodeURIComponent(runId)}`);
}

export async function getEvalRunAnalytics(
	runId: string,
): Promise<RunAnalytics> {
	return fetchApi<RunAnalytics>(
		`/eval-runs/${encodeURIComponent(runId)}/analytics`,
	);
}

export async function getEvalRunResults(runId: string): Promise<EvalResult[]> {
	return fetchApi<EvalResult[]>(
		`/eval-runs/${encodeURIComponent(runId)}/results`,
	);
}

export async function getFailedExamples(
	runId: string,
): Promise<FailedExample[]> {
	return fetchApi<FailedExample[]>(
		`/eval-runs/${encodeURIComponent(runId)}/failed-examples`,
	);
}

export async function compareEvalRuns(
	runIds: string[],
): Promise<CompareRunsResponse> {
	const params = new URLSearchParams();
	for (const runId of runIds) {
		params.append("run_ids", runId);
	}
	return fetchApi<CompareRunsResponse>(`/eval-runs/compare?${params}`);
}

export async function createEvalRun(
	payload: EvalRunCreateRequest,
): Promise<EvalRun> {
	return fetchApi<EvalRun>("/eval-runs", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(payload),
	});
}

export async function getPromptVersions(): Promise<PromptVersion[]> {
	return fetchApi<PromptVersion[]>("/prompt-versions");
}

export async function getModelConfigs(): Promise<ModelConfig[]> {
	return fetchApi<ModelConfig[]>("/model-configs");
}

async function fetchApi<T>(path: string, init?: RequestInit): Promise<T> {
	const isServer = typeof window === "undefined";
	const url = isServer
		? `${getServerApiBaseUrl()}${path}`
		: `/api/backend${path}`;
	const headers = new Headers(init?.headers);
	if (isServer && path !== "/health") {
		const viewerToken = process.env.BACKEND_VIEWER_TOKEN;
		if (viewerToken) headers.set("Authorization", `Bearer ${viewerToken}`);
	}
	const response = await fetch(url, {
		cache: "no-store",
		...init,
		headers,
	});

	if (!response.ok) {
		let detail = "";
		try {
			const body = (await response.json()) as { detail?: unknown };
			if (typeof body.detail === "string") {
				detail = body.detail;
			} else if (body.detail != null) {
				detail = JSON.stringify(body.detail);
			}
		} catch {
			detail = "";
		}
		throw new ApiError(response.status, response.statusText, detail);
	}

	return response.json() as Promise<T>;
}

function getServerApiBaseUrl(): string {
	return (
		process.env.BACKEND_API_BASE_URL ??
		process.env.NEXT_PUBLIC_API_BASE_URL ??
		"http://localhost:8000"
	).replace(/\/$/, "");
}
