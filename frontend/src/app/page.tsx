import { MetricCard } from "@/components/dashboard/metric-card";
import { getBackendHealth } from "@/lib/api";

export default async function DashboardPage() {
	let backendStatus = "unreachable";
	let backendDetail = "Backend health check failed.";
	let isBackendOnline = false;

	try {
		const health = await getBackendHealth();
		backendStatus = health.status;
		backendDetail = `${health.service} v${health.version}`;
		isBackendOnline = true;
	} catch {
		backendStatus = "offline";
		backendDetail = "Unable to reach the FastAPI /health endpoint.";
	}

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
						Evaluate prompt versions, model choices, datasets, and graders
						before shipping LLM application changes.
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

			<section className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
				<MetricCard
					label="Pass Rate"
					value="N/A"
					helperText="Available after first eval run"
				/>
				<MetricCard
					label="Average Score"
					value="N/A"
					helperText="Composite grader score"
				/>
				<MetricCard
					label="Cost"
					value="N/A"
					helperText="Estimated total model cost"
				/>
				<MetricCard
					label="Latency"
					value="N/A"
					helperText="Average and p95 latency"
				/>
			</section>

			<section className="mt-8 rounded-lg border border-dashed border-slate-800 bg-slate-950 p-6">
				<h3 className="text-lg font-semibold text-white">Run history</h3>
				<p className="mt-2 text-sm text-slate-500">
					Eval runs will appear here once the backend runner is implemented.
				</p>
			</section>
		</div>
	);
}
