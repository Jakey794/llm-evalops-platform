import type { EvalRun } from "@/lib/types";
import {
	formatCost,
	formatDateTime,
	formatLatency,
	StatusBadge,
} from "./run-table";

export function RunSummary({ run }: { run: EvalRun }) {
	const items = [
		["Status", <StatusBadge key="status" status={run.status} />],
		["Progress", `${run.completed_cases} / ${run.total_cases}`],
		["Errors", run.error_count.toLocaleString("en-US")],
		["Total cost", formatCost(run.total_cost_usd)],
		["Average latency", formatLatency(run.avg_latency_ms)],
		["P95 latency", formatLatency(run.p95_latency_ms)],
		["Created", formatDateTime(run.created_at)],
		["Started", formatDateTime(run.started_at)],
		["Completed", formatDateTime(run.completed_at)],
	] as const;

	return (
		<div className="overflow-hidden rounded-lg border border-slate-800 bg-slate-950">
			<div className="grid gap-px bg-slate-800 sm:grid-cols-2 lg:grid-cols-3">
				{items.map(([label, value]) => (
					<div className="bg-slate-950 p-4" key={label}>
						<p className="text-xs uppercase tracking-wide text-slate-500">
							{label}
						</p>
						<div className="mt-2 font-mono text-sm text-slate-200">{value}</div>
					</div>
				))}
			</div>

			<div className="grid gap-4 border-t border-slate-800 p-4 lg:grid-cols-3">
				<Reference label="Dataset ID" value={run.dataset_id} />
				<Reference label="Prompt version ID" value={run.prompt_version_id} />
				<Reference
					label="Model"
					value={run.model_name ?? run.model_config_id}
				/>
			</div>
		</div>
	);
}

function Reference({ label, value }: { label: string; value: string }) {
	return (
		<div className="min-w-0">
			<p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
			<p
				className="mt-2 truncate font-mono text-xs text-slate-300"
				title={value}
			>
				{value}
			</p>
		</div>
	);
}
