import type {
	DatasetDetail,
	DatasetSummary,
	HealthResponse,
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
