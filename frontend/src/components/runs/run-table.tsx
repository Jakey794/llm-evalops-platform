import Link from "next/link";
import type { EvalRun } from "@/lib/types";

export function RunTable({ runs }: { runs: EvalRun[] }) {
	if (runs.length === 0) {
		return (
			<div className="rounded-lg border border-dashed border-slate-800 bg-slate-950 p-10 text-center">
				<p className="text-sm font-medium text-slate-300">No eval runs found</p>
				<p className="mt-1 text-sm text-slate-500">
					Start an evaluation through the API to see it here.
				</p>
			</div>
		);
	}

	return (
		<div className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-950 shadow-sm shadow-black/20">
			<table className="min-w-[1200px] divide-y divide-slate-800 text-left text-sm">
				<thead className="bg-slate-900/60 text-xs uppercase tracking-wide text-slate-500">
					<tr>
						<Header>ID / status</Header>
						<Header>Dataset</Header>
						<Header>Prompt / model</Header>
						<Header>Progress</Header>
						<Header>Cost</Header>
						<Header>Latency avg / p95</Header>
						<Header>Created / started</Header>
					</tr>
				</thead>
				<tbody className="divide-y divide-slate-800">
					{runs.map((run) => (
						<tr className="align-top hover:bg-slate-900/50" key={run.id}>
							<td className="px-4 py-4">
								<Link
									className="block max-w-40 truncate font-mono text-xs text-cyan-300 underline-offset-4 hover:underline"
									href={`/runs/${run.id}`}
									title={run.id}
								>
									{run.id}
								</Link>
								<StatusBadge status={run.status} />
							</td>
							<IdCell value={run.dataset_id} />
							<td className="px-4 py-4">
								<Identifier value={run.prompt_version_id} />
								<p className="mt-2 max-w-44 truncate text-xs text-slate-400">
									{run.model_name ?? "—"}
								</p>
							</td>
							<td className="whitespace-nowrap px-4 py-4 font-mono text-slate-300">
								{run.completed_cases} / {run.total_cases}
								{run.error_count > 0 ? (
									<p className="mt-2 text-xs text-rose-300">
										{run.error_count} errors
									</p>
								) : null}
							</td>
							<td className="whitespace-nowrap px-4 py-4 font-mono text-slate-300">
								{formatCost(run.total_cost_usd)}
							</td>
							<td className="whitespace-nowrap px-4 py-4 font-mono text-xs text-slate-300">
								{formatLatency(run.avg_latency_ms)} /{" "}
								{formatLatency(run.p95_latency_ms)}
							</td>
							<td className="whitespace-nowrap px-4 py-4 text-xs text-slate-400">
								<p>{formatDateTime(run.created_at)}</p>
								<p className="mt-2 text-slate-500">
									{formatDateTime(run.started_at)}
								</p>
							</td>
						</tr>
					))}
				</tbody>
			</table>
		</div>
	);
}

export function StatusBadge({ status }: { status: EvalRun["status"] }) {
	const tone = {
		completed: "border-emerald-900 bg-emerald-950/60 text-emerald-300",
		failed: "border-rose-900 bg-rose-950/60 text-rose-300",
		pending: "border-slate-700 bg-slate-900 text-slate-300",
		running: "border-cyan-900 bg-cyan-950/60 text-cyan-300",
	}[status];

	return (
		<span
			className={`mt-2 inline-flex rounded-full border px-2 py-0.5 text-xs ${tone}`}
		>
			{status}
		</span>
	);
}

export function formatCost(value: string | null): string {
	if (value === null) return "—";
	return `$${Number(value).toLocaleString("en-US", { maximumFractionDigits: 8 })}`;
}

export function formatLatency(value: number | null): string {
	return value === null
		? "—"
		: `${value.toLocaleString("en-US", { maximumFractionDigits: 1 })} ms`;
}

export function formatDateTime(value: string | null): string {
	if (value === null) return "—";
	return new Intl.DateTimeFormat("en-CA", {
		dateStyle: "medium",
		timeStyle: "short",
	}).format(new Date(value));
}

function Header({ children }: { children: React.ReactNode }) {
	return (
		<th className="px-4 py-3 font-medium" scope="col">
			{children}
		</th>
	);
}

function IdCell({ value }: { value: string }) {
	return (
		<td className="px-4 py-4">
			<Identifier value={value} />
		</td>
	);
}

function Identifier({ value }: { value: string }) {
	return (
		<span
			className="block max-w-44 truncate font-mono text-xs text-slate-400"
			title={value}
		>
			{value}
		</span>
	);
}
