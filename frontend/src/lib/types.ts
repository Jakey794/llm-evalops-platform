export type HealthResponse = {
	status: string;
	service: string;
	version: string;
	database?: string;
};

export type DatasetSummary = {
	id: string;
	name: string;
	workflow_type: string;
	source_filename: string | null;
	created_at: string;
	test_case_count: number;
};

export type DatasetDetail = DatasetSummary & {
	description: string | null;
};

export type TestCase = {
	id: string;
	dataset_id: string;
	external_id: string;
	input: Record<string, unknown>;
	expected_output: Record<string, unknown>;
	required_citations: string[];
	tags: string[];
	difficulty: "easy" | "medium" | "hard";
	workflow_type: string;
	metadata: Record<string, unknown>;
	created_at: string;
};

export type MetricCardProps = {
	label: string;
	value: string;
	helperText: string;
};
