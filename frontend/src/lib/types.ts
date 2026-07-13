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
	failed_count: number;
	total_count: number;
};

export type ComponentGraderResult = {
	grader_name: string;
	score: number;
	passed: boolean;
	feedback: string;
	failure_modes: string[];
	metadata: Record<string, unknown>;
};

export type GraderBreakdown = {
	breakdown?: Record<string, number>;
	grader_results?: ComponentGraderResult[];
	pass_threshold?: number;
	weights?: Record<string, number>;
	[key: string]: unknown;
};

export type GraderResult = {
	id: string;
	grader_name: string;
	grader_type: string;
	score: number | null;
	passed: boolean | null;
	feedback: string | null;
	failure_modes: string[];
	rubric_scores: Record<string, number>;
	raw_output: Record<string, unknown> | null;
	error: string | null;
	created_at: string;
};

export type GraderError = {
	grader_name: string;
	error: string;
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
	score: number;
	passed: boolean;
	grader_feedback: string;
	failure_modes: string[];
	grader_breakdown: GraderBreakdown;
	grader_results: GraderResult[];
	created_at: string;
};

export type FailedExample = {
	id: string;
	eval_run_id: string;
	test_case_id: string;
	workflow_type: string;
	difficulty: string;
	tags: string[];
	input_json: Record<string, unknown>;
	expected_output_json: Record<string, unknown>;
	model_output: string | null;
	final_score: number;
	passed: boolean;
	deterministic_grader_scores: Record<string, number>;
	llm_judge_score: number | null;
	judge_reason: string | null;
	failure_modes: string[];
	rubric_scores: Record<string, number>;
	grader_errors: GraderError[];
	grader_results: GraderResult[];
	created_at: string;
};
