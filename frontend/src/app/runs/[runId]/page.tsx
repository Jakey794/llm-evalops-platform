import Link from "next/link";
import { BreakdownTable } from "@/components/dashboard/breakdown-table";
import { MetricCard } from "@/components/dashboard/metric-card";
import { PartialDataBanner } from "@/components/dashboard/state-banners";
import { FailedExampleTable } from "@/components/runs/failed-example-table";
import { ResultTable } from "@/components/runs/result-table";
import { RunSummary } from "@/components/runs/run-summary";
import { formatCost, formatLatency } from "@/components/runs/run-table";
import {
	getEvalRun,
	getEvalRunAnalytics,
	getEvalRunResults,
	getFailedExamples,
} from "@/lib/api";

export default async function RunDetailPage({
	params,
}: {
	params: Promise<{ runId: string }>;
}) {
	const { runId } = await params;
	const [run, results, failedExamples, analytics] = await Promise.all([
		getEvalRun(runId),
		getEvalRunResults(runId),
		getFailedExamples(runId),
		getEvalRunAnalytics(runId),
	]);

	return (
		<div className="mx-auto max-w-7xl">
			<header className="border-b border-slate-800 pb-6">
				<Link
					className="text-sm text-cyan-400 hover:text-cyan-300"
					href="/runs"
				>
					← All eval runs
				</Link>
				<p className="mt-5 text-sm font-medium uppercase tracking-wide text-slate-500">
					Run inspection
				</p>
				<h2 className="mt-2 text-3xl font-semibold tracking-tight text-white">
					{run.prompt_name ?? "Eval run detail"}
				</h2>
				<p className="mt-2 text-sm text-slate-400">
					{[run.dataset_name, run.model_name, run.prompt_version_label]
						.filter(Boolean)
						.join(" · ") || "Prompt / model comparison details"}
				</p>
				<p className="mt-3 break-all font-mono text-xs text-slate-500">
					{run.id}
				</p>
			</header>

			{analytics.has_partial_metrics || analytics.incomplete_cases > 0 ? (
				<div className="mt-8">
					<PartialDataBanner
						message={`Partial metrics detected (${analytics.incomplete_cases} incomplete cases). Breakdowns use available graded results.`}
					/>
				</div>
			) : null}

			<section className="mt-8">
				<div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
					<MetricCard
						helperText="Share of cases meeting the grader threshold"
						label="Pass rate"
						value={formatPassRate(run.pass_rate)}
					/>
					<MetricCard
						helperText="Mean final score after configured grader weighting"
						label="Average score"
						value={formatScore(run.avg_score)}
					/>
					<MetricCard
						helperText="Estimated total model cost"
						label="Cost"
						value={formatCost(run.total_cost_usd)}
					/>
					<MetricCard
						helperText={`P95 ${formatLatency(run.p95_latency_ms)}`}
						label="Avg latency"
						value={formatLatency(run.avg_latency_ms)}
					/>
					<MetricCard
						helperText="Cases below the composite threshold"
						label="Failed cases"
						value={run.failed_count.toLocaleString("en-US")}
					/>
				</div>
			</section>

			<section className="mt-8">
				<RunSummary run={run} />
			</section>

			<section className="mt-8 grid gap-4 xl:grid-cols-3">
				<BreakdownTable
					buckets={analytics.by_workflow}
					description="Pass rate and score by workflow type."
					title="Workflow breakdown"
				/>
				<BreakdownTable
					buckets={analytics.by_difficulty}
					description="Pass rate and score by difficulty."
					title="Difficulty breakdown"
				/>
				<BreakdownTable
					buckets={analytics.by_tag}
					description="Pass rate and score by dataset tags."
					title="Tag breakdown"
				/>
			</section>

			<section className="mt-8">
				<div className="mb-3">
					<h3 className="text-lg font-semibold text-white">Failed examples</h3>
					<p className="mt-1 text-sm text-slate-500">
						Inspect model inputs, deterministic scores, judge feedback, and
						rubric details.
					</p>
				</div>
				<FailedExampleTable examples={failedExamples} />
			</section>

			<section className="mt-8">
				<div className="mb-3">
					<h3 className="text-lg font-semibold text-white">Case results</h3>
					<p className="mt-1 text-sm text-slate-500">
						{results.length} {results.length === 1 ? "result" : "results"} with
						expandable grader details
					</p>
				</div>
				<ResultTable results={results} />
			</section>
		</div>
	);
}

function formatPassRate(value: number | null): string {
	return value === null ? "—" : `${(value * 100).toFixed(1)}%`;
}

function formatScore(value: number | null): string {
	return value === null ? "—" : value.toFixed(3);
}
