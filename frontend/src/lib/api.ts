import type {
	CompareRunsResponse,
	DashboardOverview,
	DatasetDetail,
	DatasetSummary,
	EvalResult,
	EvalRun,
	FailedExample,
	HealthResponse,
	PromptVersion,
	RunAnalytics,
	TestCase,
} from "@/lib/types";

const API_BASE_URL =
	process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

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

export async function getPromptVersions(): Promise<PromptVersion[]> {
	return fetchApi<PromptVersion[]>("/prompt-versions");
}

async function fetchApi<T>(path: string): Promise<T> {
	const url = `${API_BASE_URL}${path}`;
	const response = await fetch(url, { cache: "no-store" });

	if (!response.ok) {
		throw new Error(
			`Request failed (${response.status} ${response.statusText})`,
		);
	}

	return response.json() as Promise<T>;
}
