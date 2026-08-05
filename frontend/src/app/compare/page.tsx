"use client";

import Link from "next/link";
import { useEffect, useState, useTransition } from "react";
import { ScatterChart } from "@/components/dashboard/scatter-chart";
import {
	EmptyState,
	PartialDataBanner,
} from "@/components/dashboard/state-banners";
import { compareEvalRuns, getEvalRuns } from "@/lib/api";
import type { CompareRunsResponse, EvalRun } from "@/lib/types";

export default function ComparePage() {
	const [runs, setRuns] = useState<EvalRun[] | null>(null);
	const [selected, setSelected] = useState<string[]>([]);
	const [comparison, setComparison] = useState<CompareRunsResponse | null>(
		null,
	);
	const [error, setError] = useState<string | null>(null);
	const [isPending, startTransition] = useTransition();

	useEffect(() => {
		let cancelled = false;
		startTransition(async () => {
			try {
				const loaded = await getEvalRuns();
				if (cancelled) return;
				setRuns(loaded);
				setSelected(loaded.slice(0, 2).map((run) => run.id));
			} catch (loadError) {
				if (cancelled) return;
				setError(
					loadError instanceof Error
						? loadError.message
						: "Unable to load eval runs.",
				);
				setRuns([]);
			}
		});
		return () => {
			cancelled = true;
		};
	}, []);

	function toggleRun(runId: string) {
		setSelected((current) =>
			current.includes(runId)
				? current.filter((id) => id !== runId)
				: current.length >= 5
					? current
					: [...current, runId],
		);
	}

	function runComparison() {
		if (selected.length < 2) {
			setError("Select at least two runs to compare.");
			return;
		}
		setError(null);
		startTransition(async () => {
			try {
				setComparison(await compareEvalRuns(selected));
			} catch (compareError) {
				setError(
					compareError instanceof Error
						? compareError.message
						: "Comparison failed.",
				);
			}
		});
	}

	return (
		<div className="mx-auto max-w-7xl">
			<header className="border-b border-slate-800 pb-6">
				<p className="text-sm font-medium uppercase text-slate-500">Compare</p>
				<h2 className="mt-2 text-3xl font-semibold tracking-tight text-white">
					Prompt and model comparison
				</h2>
				<p className="mt-3 max-w-2xl text-sm text-slate-400">
					Compare up to five completed runs on pass rate, score, cost, and
					latency.
				</p>
			</header>

			{error ? (
				<div className="mt-6">
					<PartialDataBanner message={error} />
				</div>
			) : null}

			<section className="mt-8">
				{runs === null ? (
					<p className="text-sm text-slate-500">Loading eval runs…</p>
				) : runs.length === 0 ? (
					<EmptyState
						description="Create eval runs first, then return here to compare prompt or model versions."
						title="No runs available"
					/>
				) : (
					<div className="space-y-4">
						<div className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-950">
							<table className="min-w-full divide-y divide-slate-800 text-left text-sm">
								<thead className="bg-slate-900/60 text-xs uppercase tracking-wide text-slate-500">
									<tr>
										<th className="px-4 py-3" scope="col">
											Select
										</th>
										<th className="px-4 py-3" scope="col">
											Run
										</th>
										<th className="px-4 py-3" scope="col">
											Prompt / model
										</th>
										<th className="px-4 py-3" scope="col">
											Pass / score
										</th>
										<th className="px-4 py-3" scope="col">
											Cost / p95
										</th>
									</tr>
								</thead>
								<tbody className="divide-y divide-slate-800">
									{runs.map((run) => (
										<tr key={run.id}>
											<td className="px-4 py-3">
												<input
													aria-label={`Select run ${run.id}`}
													checked={selected.includes(run.id)}
													onChange={() => toggleRun(run.id)}
													type="checkbox"
												/>
											</td>
											<td className="px-4 py-3">
												<Link
													className="font-mono text-xs text-cyan-300 hover:underline"
													href={`/runs/${run.id}`}
												>
													{run.id.slice(0, 8)}…
												</Link>
												<p className="mt-1 text-xs text-slate-500">
													{run.dataset_name ?? run.dataset_id.slice(0, 8)}
												</p>
											</td>
											<td className="px-4 py-3 text-xs text-slate-300">
												<p>{run.prompt_name ?? run.prompt_version_id}</p>
												<p className="mt-1 text-slate-500">
													{run.model_name ?? run.model_config_id}
												</p>
											</td>
											<td className="px-4 py-3 font-mono text-xs text-slate-300">
												{formatPassRate(run.pass_rate)} /{" "}
												{formatScore(run.avg_score)}
											</td>
											<td className="px-4 py-3 font-mono text-xs text-slate-300">
												${Number(run.total_cost_usd).toFixed(6)} /{" "}
												{run.p95_latency_ms?.toFixed(1) ?? "—"} ms
											</td>
										</tr>
									))}
								</tbody>
							</table>
						</div>

						<button
							className="rounded-md border border-cyan-800 bg-cyan-950/40 px-4 py-2 text-sm font-medium text-cyan-200 transition hover:bg-cyan-900/40 disabled:opacity-50"
							disabled={isPending || selected.length < 2}
							onClick={runComparison}
							type="button"
						>
							{isPending ? "Comparing…" : "Compare selected runs"}
						</button>
					</div>
				)}
			</section>

			{comparison ? (
				<section className="mt-8 space-y-6">
					<div className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-950">
						<table className="min-w-full divide-y divide-slate-800 text-left text-sm">
							<thead className="bg-slate-900/60 text-xs uppercase tracking-wide text-slate-500">
								<tr>
									<th className="px-4 py-3" scope="col">
										Label
									</th>
									<th className="px-4 py-3" scope="col">
										Pass rate
									</th>
									<th className="px-4 py-3" scope="col">
										Avg score
									</th>
									<th className="px-4 py-3" scope="col">
										Cost
									</th>
									<th className="px-4 py-3" scope="col">
										Avg / p95 latency
									</th>
								</tr>
							</thead>
							<tbody className="divide-y divide-slate-800">
								{comparison.runs.map((run) => (
									<tr key={run.id}>
										<td className="px-4 py-3 text-slate-200">{run.label}</td>
										<td className="px-4 py-3 font-mono text-slate-300">
											{formatPassRate(run.pass_rate)}
										</td>
										<td className="px-4 py-3 font-mono text-slate-300">
											{formatScore(run.avg_score)}
										</td>
										<td className="px-4 py-3 font-mono text-slate-300">
											${run.total_cost_usd.toFixed(6)}
										</td>
										<td className="px-4 py-3 font-mono text-slate-300">
											{run.avg_latency_ms?.toFixed(1) ?? "—"} /{" "}
											{run.p95_latency_ms?.toFixed(1) ?? "—"} ms
										</td>
									</tr>
								))}
							</tbody>
						</table>
					</div>

					<div className="grid gap-4 xl:grid-cols-2">
						<ScatterChart
							description="Cost-quality tradeoff across selected runs."
							emptyMessage="Selected runs are missing cost or score."
							points={comparison.cost_quality.map((point) => ({
								id: point.id,
								label: point.label,
								x: point.cost,
								y: point.quality,
							}))}
							title="Cost vs quality"
							xLabel="Cost (USD)"
							yLabel="Avg score"
						/>
						<ScatterChart
							description="Latency-quality tradeoff across selected runs."
							emptyMessage="Selected runs are missing latency or score."
							points={comparison.latency_quality.map((point) => ({
								id: point.id,
								label: point.label,
								x: point.latency,
								y: point.quality,
							}))}
							title="Latency vs quality"
							xLabel="Latency (ms)"
							yLabel="Avg score"
						/>
					</div>
				</section>
			) : null}
		</div>
	);
}

function formatPassRate(value: number | null): string {
	return value === null ? "—" : `${(value * 100).toFixed(1)}%`;
}

function formatScore(value: number | null): string {
	return value === null ? "—" : value.toFixed(3);
}
