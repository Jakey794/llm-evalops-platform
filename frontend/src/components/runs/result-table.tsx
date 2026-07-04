import type { EvalResult } from "@/lib/types";
import { formatCost, formatLatency } from "./run-table";

export function ResultTable({ results }: { results: EvalResult[] }) {
	if (results.length === 0) {
		return (
			<div className="rounded-lg border border-dashed border-slate-800 bg-slate-950 p-10 text-center">
				<p className="text-sm font-medium text-slate-300">
					No results for this run yet
				</p>
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
						<Header>Score</Header>
						<Header>Outcome</Header>
						<Header>Latency</Header>
						<Header>Input tokens</Header>
						<Header>Output tokens</Header>
						<Header>Cost</Header>
						<Header>Error</Header>
						<Header>Grader feedback</Header>
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
							<Metric value={result.score.toFixed(3)} />
							<td className="px-4 py-4">
								<OutcomeBadge passed={result.passed} />
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
							<td className="max-w-72 px-4 py-4 text-xs">
								{result.grader_feedback ? (
									<details>
										<summary className="cursor-pointer text-slate-300">
											{truncate(result.grader_feedback, 80)}
										</summary>
										<GraderDetail result={result} />
									</details>
								) : (
									<span className="text-slate-600">
										No grader feedback available
									</span>
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

function OutcomeBadge({ passed }: { passed: boolean }) {
	return (
		<span
			className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
				passed ? "bg-emerald-950 text-emerald-300" : "bg-rose-950 text-rose-300"
			}`}
		>
			{passed ? "Passed" : "Failed"}
		</span>
	);
}

function GraderDetail({ result }: { result: EvalResult }) {
	const components = result.grader_breakdown.grader_results ?? [];
	return (
		<div className="mt-3 space-y-3 border-l border-slate-700 pl-3 text-slate-400">
			<p className="whitespace-pre-wrap leading-5">{result.grader_feedback}</p>
			<p>Failure modes: {result.failure_modes.join(", ") || "None recorded"}</p>
			{components.length > 0 ? (
				<ul className="space-y-1 font-mono">
					{components.map((component) => (
						<li key={component.grader_name}>
							{component.grader_name}: {component.score.toFixed(3)}
						</li>
					))}
				</ul>
			) : null}
		</div>
	);
}

function truncate(value: string, length: number): string {
	return value.length > length ? `${value.slice(0, length - 1)}…` : value;
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
