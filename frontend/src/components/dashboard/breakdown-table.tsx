import type { BreakdownBucket } from "@/lib/types";

export function BreakdownTable({
	title,
	description,
	buckets,
}: {
	title: string;
	description: string;
	buckets: BreakdownBucket[];
}) {
	if (buckets.length === 0) {
		return (
			<section className="rounded-lg border border-dashed border-slate-800 bg-slate-950 p-6">
				<h3 className="text-lg font-semibold text-white">{title}</h3>
				<p className="mt-2 text-sm text-slate-500">{description}</p>
				<p className="mt-4 text-sm text-slate-500">No breakdown data yet.</p>
			</section>
		);
	}

	return (
		<section className="overflow-hidden rounded-lg border border-slate-800 bg-slate-950">
			<div className="border-b border-slate-800 px-4 py-3">
				<h3 className="text-lg font-semibold text-white">{title}</h3>
				<p className="mt-1 text-sm text-slate-500">{description}</p>
			</div>
			<div className="overflow-x-auto">
				<table className="min-w-full divide-y divide-slate-800 text-left text-sm">
					<thead className="bg-slate-900/60 text-xs uppercase tracking-wide text-slate-500">
						<tr>
							<th className="px-4 py-3 font-medium" scope="col">
								Key
							</th>
							<th className="px-4 py-3 font-medium" scope="col">
								Pass rate
							</th>
							<th className="px-4 py-3 font-medium" scope="col">
								Avg score
							</th>
							<th className="px-4 py-3 font-medium" scope="col">
								Cases
							</th>
							<th className="px-4 py-3 font-medium" scope="col">
								Avg latency
							</th>
							<th className="px-4 py-3 font-medium" scope="col">
								Cost
							</th>
						</tr>
					</thead>
					<tbody className="divide-y divide-slate-800">
						{buckets.map((bucket) => (
							<tr key={bucket.key}>
								<td className="px-4 py-3 font-medium text-slate-200">
									{bucket.key}
								</td>
								<td className="px-4 py-3 font-mono text-slate-300">
									{formatPassRate(bucket.pass_rate)}
								</td>
								<td className="px-4 py-3 font-mono text-slate-300">
									{formatScore(bucket.avg_score)}
								</td>
								<td className="px-4 py-3 font-mono text-slate-300">
									{bucket.passed_count}/{bucket.total_count}
									{bucket.failed_count > 0 ? (
										<span className="ml-2 text-rose-300">
											{bucket.failed_count} failed
										</span>
									) : null}
								</td>
								<td className="px-4 py-3 font-mono text-slate-300">
									{formatLatency(bucket.avg_latency_ms)}
								</td>
								<td className="px-4 py-3 font-mono text-slate-300">
									${bucket.total_cost_usd.toFixed(6)}
								</td>
							</tr>
						))}
					</tbody>
				</table>
			</div>
		</section>
	);
}

function formatPassRate(value: number | null): string {
	return value === null ? "—" : `${(value * 100).toFixed(1)}%`;
}

function formatScore(value: number | null): string {
	return value === null ? "—" : value.toFixed(3);
}

function formatLatency(value: number | null): string {
	return value === null
		? "—"
		: `${value.toLocaleString("en-US", { maximumFractionDigits: 1 })} ms`;
}
