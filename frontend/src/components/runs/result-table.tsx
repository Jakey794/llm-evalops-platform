import type { EvalResult, GraderResult } from "@/lib/types";
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
			<table className="min-w-[1300px] divide-y divide-slate-800 text-left text-sm">
				<thead className="bg-slate-900/60 text-xs uppercase tracking-wide text-slate-500">
					<tr>
						<Header>Test case</Header>
						<Header>Final score</Header>
						<Header>Judge score</Header>
						<Header>Outcome</Header>
						<Header>Failure modes</Header>
						<Header>Latency</Header>
						<Header>Input tokens</Header>
						<Header>Output tokens</Header>
						<Header>Cost</Header>
						<Header>Error</Header>
						<Header>Grader details</Header>
						<Header>Model output</Header>
					</tr>
				</thead>
				<tbody className="divide-y divide-slate-800">
					{results.map((result) => (
						<ResultRow key={result.id} result={result} />
					))}
				</tbody>
			</table>
		</div>
	);
}

function ResultRow({ result }: { result: EvalResult }) {
	const judgeResult = result.grader_results.find(
		(grader) => grader.grader_name === "llm_judge",
	);
	return (
		<tr className="align-top hover:bg-slate-900/50">
			<td className="px-4 py-4">
				<code
					className="block max-w-44 truncate text-xs text-slate-400"
					title={result.test_case_id}
				>
					{result.test_case_id}
				</code>
			</td>
			<Metric value={formatScore(result.score)} />
			<Metric value={formatScore(judgeResult?.score ?? null)} />
			<td className="px-4 py-4">
				<OutcomeBadge passed={result.passed} />
			</td>
			<td className="max-w-72 px-4 py-4">
				<FailureModeBadges modes={result.failure_modes} />
			</td>
			<Metric value={formatLatency(result.latency_ms)} />
			<Metric value={formatInteger(result.input_tokens)} />
			<Metric value={formatInteger(result.output_tokens)} />
			<Metric value={formatCost(result.estimated_cost_usd)} />
			<td className="max-w-64 px-4 py-4 text-xs">
				{result.error ? (
					<span className="line-clamp-3 text-rose-300" title={result.error}>
						{result.error}
					</span>
				) : (
					<span className="text-slate-600">—</span>
				)}
			</td>
			<td className="max-w-80 px-4 py-4 text-xs">
				<details>
					<summary className="cursor-pointer font-medium text-cyan-400 hover:text-cyan-300">
						View grader details
					</summary>
					<GraderDetail result={result} />
				</details>
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
	const deterministicResults = result.grader_results.filter(
		(grader) => grader.grader_type === "deterministic",
	);
	const judgeResult = result.grader_results.find(
		(grader) => grader.grader_name === "llm_judge",
	);

	return (
		<div className="mt-3 w-80 space-y-4 border-l border-slate-700 pl-3 text-slate-400">
			<p className="whitespace-pre-wrap leading-5">{result.grader_feedback}</p>
			<GraderScoreList graders={deterministicResults} />
			{judgeResult ? <JudgeDetail judge={judgeResult} /> : null}
		</div>
	);
}

function GraderScoreList({ graders }: { graders: GraderResult[] }) {
	if (graders.length === 0) {
		return <p>No deterministic grader rows recorded.</p>;
	}
	return (
		<div>
			<p className="mb-2 font-medium text-slate-300">Deterministic graders</p>
			<ul className="space-y-1 font-mono">
				{graders.map((grader) => (
					<li className="flex justify-between gap-4" key={grader.id}>
						<span>{formatLabel(grader.grader_name)}</span>
						<span>{formatScore(grader.score)}</span>
					</li>
				))}
			</ul>
		</div>
	);
}

function JudgeDetail({ judge }: { judge: GraderResult }) {
	const rubricEntries = Object.entries(judge.rubric_scores);
	return (
		<div className="space-y-2">
			<p className="font-medium text-slate-300">
				LLM judge: <span className="font-mono">{formatScore(judge.score)}</span>
			</p>
			<p className="leading-5">
				{judge.feedback ?? "No judge reason available."}
			</p>
			{rubricEntries.length > 0 ? (
				<ul className="space-y-1 font-mono">
					{rubricEntries.map(([name, score]) => (
						<li className="flex justify-between gap-4" key={name}>
							<span>{formatLabel(name)}</span>
							<span>{formatScore(score)}</span>
						</li>
					))}
				</ul>
			) : null}
			{judge.error ? <p className="text-rose-300">{judge.error}</p> : null}
		</div>
	);
}

function FailureModeBadges({ modes }: { modes: string[] }) {
	if (modes.length === 0) {
		return <span className="text-xs text-slate-600">None</span>;
	}
	return (
		<div className="flex flex-wrap gap-1.5">
			{modes.map((mode) => (
				<span
					className="rounded-full bg-rose-950 px-2 py-0.5 text-xs text-rose-300"
					key={mode}
				>
					{formatLabel(mode)}
				</span>
			))}
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

function formatLabel(value: string): string {
	return value.replaceAll("_", " ");
}

function formatScore(value: number | null): string {
	return value === null ? "—" : value.toFixed(3);
}
