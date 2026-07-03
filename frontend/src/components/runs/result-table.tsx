import type { EvalResult } from "@/lib/types";
import { formatCost, formatLatency } from "./run-table";

export function ResultTable({ results }: { results: EvalResult[] }) {
	if (results.length === 0) {
		return (
			<div className="rounded-lg border border-dashed border-slate-800 bg-slate-950 p-10 text-center">
				<p className="text-sm font-medium text-slate-300">No results stored</p>
				<p className="mt-1 text-sm text-slate-500">
					This run did not persist any test-case results.
				</p>
			</div>
		);
	}

	return (
		<div className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-950 shadow-sm shadow-black/20">
			<table className="min-w-[1100px] divide-y divide-slate-800 text-left text-sm">
				<thead className="bg-slate-900/60 text-xs uppercase tracking-wide text-slate-500">
					<tr>
						<Header>Test case</Header>
						<Header>Latency</Header>
						<Header>Input tokens</Header>
						<Header>Output tokens</Header>
						<Header>Cost</Header>
						<Header>Error</Header>
						<Header>Model output</Header>
					</tr>
				</thead>
				<tbody className="divide-y divide-slate-800">
					{results.map((result) => (
						<tr className="align-top hover:bg-slate-900/50" key={result.id}>
							<td className="px-4 py-4">
								<code
									className="block max-w-44 truncate text-xs text-slate-400"
									title={result.test_case_id}
								>
									{result.test_case_id}
								</code>
							</td>
							<Metric value={formatLatency(result.latency_ms)} />
							<Metric value={formatInteger(result.input_tokens)} />
							<Metric value={formatInteger(result.output_tokens)} />
							<Metric value={formatCost(result.estimated_cost_usd)} />
							<td className="max-w-64 px-4 py-4 text-xs">
								{result.error ? (
									<span
										className="line-clamp-3 text-rose-300"
										title={result.error}
									>
										{result.error}
									</span>
								) : (
									<span className="text-slate-600">—</span>
								)}
							</td>
							<td className="max-w-sm px-4 py-4">
								<p
									className="line-clamp-3 whitespace-pre-wrap break-words text-xs leading-5 text-slate-300"
									title={result.model_output ?? undefined}
								>
									{result.model_output ?? "—"}
								</p>
							</td>
						</tr>
					))}
				</tbody>
			</table>
		</div>
	);
}

function Header({ children }: { children: React.ReactNode }) {
	return (
		<th className="px-4 py-3 font-medium" scope="col">
			{children}
		</th>
	);
}

function Metric({ value }: { value: string }) {
	return (
		<td className="whitespace-nowrap px-4 py-4 font-mono text-xs text-slate-300">
			{value}
		</td>
	);
}

function formatInteger(value: number | null): string {
	return value === null ? "—" : value.toLocaleString("en-US");
}
