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

export type EvalRunStatus = "pending" | "running" | "completed" | "failed";

export type EvalRun = {
	id: string;
	dataset_id: string;
	prompt_version_id: string;
	model_config_id: string;
	model_name?: string | null;
	status: EvalRunStatus;
	created_at: string;
	started_at: string | null;
	completed_at: string | null;
	total_cases: number;
	completed_cases: number;
	pass_rate: number | null;
	avg_score: number | null;
	total_cost_usd: string;
	avg_latency_ms: number | null;
	p95_latency_ms: number | null;
	error_count: number;
};

export type EvalResult = {
	id: string;
	eval_run_id: string;
	test_case_id: string;
	model_output: string | null;
	parsed_output: Record<string, unknown> | unknown[] | null;
	raw_response: Record<string, unknown> | null;
	latency_ms: number | null;
	input_tokens: number | null;
	output_tokens: number | null;
	estimated_cost_usd: string | null;
	error: string | null;
	created_at: string;
};
