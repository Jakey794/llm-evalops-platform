import Link from "next/link";
import { MetricCard } from "@/components/dashboard/metric-card";
import { ScatterChart } from "@/components/dashboard/scatter-chart";
import {
	EmptyState,
	PartialDataBanner,
} from "@/components/dashboard/state-banners";
import {
	formatCost,
	formatLatency,
	RunTable,
} from "@/components/runs/run-table";
import { getBackendHealth, getDashboardOverview, getEvalRuns } from "@/lib/api";
import type { EvalRun } from "@/lib/types";

export default async function DashboardPage() {
	let backendStatus = "unreachable";
	let backendDetail = "Backend health check failed.";
	let isBackendOnline = false;
	let overviewError: string | null = null;
	let runs: EvalRun[] = [];
	let overview = null;

	try {
		const health = await getBackendHealth();
		backendStatus = health.status;
		backendDetail = `${health.service} v${health.version}`;
		isBackendOnline = true;
	} catch {
		backendStatus = "offline";
		backendDetail = "Unable to reach the FastAPI /health endpoint.";
	}

	if (isBackendOnline) {
		try {
			[overview, runs] = await Promise.all([
				getDashboardOverview(),
				getEvalRuns(),
			]);
		} catch (error) {
			overviewError =
				error instanceof Error ? error.message : "Failed to load overview.";
		}
	}

	const completedRuns = runs.filter((run) => run.status === "completed");

	return (
		<div className="mx-auto max-w-7xl">
			<div className="flex flex-col justify-between gap-4 border-b border-slate-800 pb-6 md:flex-row md:items-end">
				<div>
					<p className="text-sm font-medium uppercase text-slate-500">
						Dashboard
					</p>
					<h2 className="mt-2 text-3xl font-semibold tracking-tight text-white">
						LLM Reliability + EvalOps Platform
					</h2>
					<p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">
						Inspect pass rate, cost, latency, and recent eval history across
						prompt and model versions.
					</p>
				</div>

				<div className="rounded-lg border border-slate-800 bg-slate-950 px-4 py-3">
					<p className="text-xs uppercase text-slate-500">Backend</p>
					<p
						className={`mt-1 text-sm font-semibold ${
							isBackendOnline ? "text-emerald-400" : "text-amber-400"
						}`}
					>
						{backendStatus}
					</p>
					<p className="mt-1 text-xs text-slate-500">{backendDetail}</p>
				</div>
			</div>

			{overviewError ? (
				<div className="mt-8">
					<PartialDataBanner message={overviewError} />
				</div>
			) : null}

			{overview?.has_partial_metrics ? (
				<div className="mt-8">
					<PartialDataBanner message="Some completed runs are missing pass rate, score, or latency. Charts and averages use available data only." />
				</div>
			) : null}

			<section className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
				<MetricCard
					helperText={
						overview
							? `${overview.completed_run_count} completed of ${overview.run_count} recent runs`
							: "Available after first eval run"
					}
					label="Pass Rate"
					value={formatPassRate(overview?.pass_rate ?? null)}
				/>
				<MetricCard
					helperText="Mean composite score across completed runs"
					label="Average Score"
					value={formatScore(overview?.avg_score ?? null)}
				/>
				<MetricCard
					helperText="Estimated total model cost for completed runs"
					label="Cost"
					value={overview ? formatCost(String(overview.total_cost_usd)) : "N/A"}
				/>
				<MetricCard
					helperText={`Avg ${formatLatency(overview?.avg_latency_ms ?? null)} · p95 ${formatLatency(overview?.p95_latency_ms ?? null)}`}
					label="Latency"
					value={formatLatency(overview?.avg_latency_ms ?? null)}
				/>
			</section>

			<section className="mt-8 grid gap-4 xl:grid-cols-2">
				<ScatterChart
					description="Average score versus total run cost for completed evaluations."
					emptyMessage="Run at least one completed evaluation with cost and score to plot cost-quality tradeoffs."
					points={completedRuns.map((run) => ({
						id: run.id,
						label: run.prompt_name ?? run.model_name ?? run.id.slice(0, 8),
						x: Number(run.total_cost_usd),
						y: run.avg_score,
					}))}
					title="Cost vs quality"
					xLabel="Cost (USD)"
					yLabel="Avg score"
				/>
				<ScatterChart
					description="Average score versus p95 latency for completed evaluations."
					emptyMessage="Run at least one completed evaluation with latency and score to plot latency-quality tradeoffs."
					points={completedRuns.map((run) => ({
						id: run.id,
						label: run.prompt_name ?? run.model_name ?? run.id.slice(0, 8),
						x: run.p95_latency_ms ?? run.avg_latency_ms,
						y: run.avg_score,
					}))}
					title="Latency vs quality"
					xLabel="P95 latency (ms)"
					yLabel="Avg score"
				/>
			</section>

			<section className="mt-8">
				<div className="mb-3 flex items-end justify-between gap-4">
					<div>
						<h3 className="text-lg font-semibold text-white">Run history</h3>
						<p className="mt-1 text-sm text-slate-500">
							{runs.length} recent {runs.length === 1 ? "run" : "runs"}
						</p>
					</div>
					<Link
						className="text-sm text-cyan-400 hover:text-cyan-300"
						href="/runs"
					>
						View all runs
					</Link>
				</div>
				{runs.length === 0 ? (
					<EmptyState
						description="Start an evaluation through the API or CI gate to populate history."
						title="No eval runs yet"
					/>
				) : (
					<RunTable runs={runs.slice(0, 8)} />
				)}
			</section>
		</div>
	);
}

function formatPassRate(value: number | null): string {
	return value === null ? "N/A" : `${(value * 100).toFixed(1)}%`;
}

function formatScore(value: number | null): string {
	return value === null ? "N/A" : value.toFixed(3);
}
