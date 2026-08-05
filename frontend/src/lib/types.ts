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

export type PromptVersion = {
	id: string;
	name: string;
	workflow_type: string;
	version_label: string;
	created_at: string;
	template?: string;
};

export type ModelConfig = {
	id: string;
	provider: string;
	model_name: string;
	temperature: number | null;
	max_output_tokens: number;
	created_at: string;
	response_format?: Record<string, unknown> | null;
};

export type EvalRunCreateRequest = {
	dataset_id: string;
	prompt_version_id: string;
	model_config_id: string;
};

export type EvalRunStatus = "pending" | "running" | "completed" | "failed";

export type EvalRun = {
	id: string;
	dataset_id: string;
	prompt_version_id: string;
	model_config_id: string;
	model_name?: string | null;
	dataset_name?: string | null;
	prompt_name?: string | null;
	prompt_version_label?: string | null;
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

export type BreakdownBucket = {
	key: string;
	total_count: number;
	passed_count: number;
	failed_count: number;
	pass_rate: number | null;
	avg_score: number | null;
	avg_latency_ms: number | null;
	total_cost_usd: number;
};

export type RunAnalytics = {
	eval_run_id: string;
	by_tag: BreakdownBucket[];
	by_difficulty: BreakdownBucket[];
	by_workflow: BreakdownBucket[];
	incomplete_cases: number;
	has_partial_metrics: boolean;
};

export type CompareRunPoint = {
	id: string;
	label: string;
	status: string;
	dataset_name: string | null;
	prompt_name: string | null;
	prompt_version_label: string | null;
	model_name: string | null;
	pass_rate: number | null;
	avg_score: number | null;
	total_cost_usd: number;
	avg_latency_ms: number | null;
	p95_latency_ms: number | null;
	failed_count: number;
	total_count: number;
};

export type CompareRunsResponse = {
	runs: CompareRunPoint[];
	cost_quality: Array<{
		id: string;
		label: string;
		cost: number | null;
		quality: number | null;
	}>;
	latency_quality: Array<{
		id: string;
		label: string;
		latency: number | null;
		quality: number | null;
	}>;
};

export type DashboardOverview = {
	run_count: number;
	completed_run_count: number;
	pass_rate: number | null;
	avg_score: number | null;
	total_cost_usd: number;
	avg_latency_ms: number | null;
	p95_latency_ms: number | null;
	has_partial_metrics: boolean;
	recent_runs: CompareRunPoint[];
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
