import Link from "next/link";
import { MetricCard } from "@/components/dashboard/metric-card";
import { FailedExampleTable } from "@/components/runs/failed-example-table";
import { ResultTable } from "@/components/runs/result-table";
import { RunSummary } from "@/components/runs/run-summary";
import { getEvalRun, getEvalRunResults, getFailedExamples } from "@/lib/api";

export default async function RunDetailPage({
	params,
}: {
	params: Promise<{ runId: string }>;
}) {
	const { runId } = await params;
	const [run, results, failedExamples] = await Promise.all([
		getEvalRun(runId),
		getEvalRunResults(runId),
		getFailedExamples(runId),
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
					Eval run detail
				</h2>
				<p className="mt-3 break-all font-mono text-xs text-slate-500">
					{run.id}
				</p>
			</header>

			<section className="mt-8">
				<div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
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
						helperText="Cases below the composite threshold"
						label="Failed cases"
						value={run.failed_count.toLocaleString("en-US")}
					/>
					<MetricCard
						helperText="Cases included in this evaluation"
						label="Total cases"
						value={run.total_count.toLocaleString("en-US")}
					/>
				</div>
			</section>

			<section className="mt-8">
				<RunSummary run={run} />
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
						{results.length} {results.length === 1 ? "result" : "results"}
						with expandable grader details
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
