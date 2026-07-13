"use client";

import { Fragment, useState } from "react";
import type { FailedExample } from "@/lib/types";

export function FailedExampleTable({
	examples,
}: {
	examples: FailedExample[];
}) {
	const [difficulty, setDifficulty] = useState("all");
	const [failureMode, setFailureMode] = useState("all");
	const [expandedId, setExpandedId] = useState<string | null>(null);
	const difficulties = [
		...new Set(examples.map((example) => example.difficulty)),
	].sort();
	const failureModes = [
		...new Set(examples.flatMap((example) => example.failure_modes)),
	].sort();
	const filteredExamples = examples.filter(
		(example) =>
			(difficulty === "all" || example.difficulty === difficulty) &&
			(failureMode === "all" || example.failure_modes.includes(failureMode)),
	);

	if (examples.length === 0) {
		return (
			<div className="rounded-lg border border-dashed border-emerald-900/60 bg-emerald-950/20 p-10 text-center">
				<p className="text-sm font-medium text-emerald-300">
					No failed examples
				</p>
				<p className="mt-1 text-sm text-slate-500">
					Every graded case in this run met its pass threshold.
				</p>
			</div>
		);
	}

	return (
		<div className="space-y-3">
			<div className="flex flex-wrap gap-3 rounded-lg border border-slate-800 bg-slate-950 p-3">
				<FilterSelect
					label="Difficulty"
					onChange={setDifficulty}
					options={difficulties}
					value={difficulty}
				/>
				<FilterSelect
					label="Failure mode"
					onChange={setFailureMode}
					options={failureModes}
					value={failureMode}
				/>
				<p className="self-end pb-2 text-xs text-slate-500">
					Showing {filteredExamples.length} of {examples.length}
				</p>
			</div>

			{filteredExamples.length === 0 ? (
				<div className="rounded-lg border border-dashed border-slate-800 bg-slate-950 p-8 text-center text-sm text-slate-500">
					No failed examples match these filters.
				</div>
			) : (
				<div className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-950 shadow-sm shadow-black/20">
					<table className="min-w-[1050px] divide-y divide-slate-800 text-left text-sm">
						<thead className="bg-slate-900/60 text-xs uppercase tracking-wide text-slate-500">
							<tr>
								<Header>Test case</Header>
								<Header>Workflow</Header>
								<Header>Difficulty</Header>
								<Header>Final score</Header>
								<Header>Judge score</Header>
								<Header>Failure modes</Header>
								<Header>Details</Header>
							</tr>
						</thead>
						<tbody className="divide-y divide-slate-800">
							{filteredExamples.map((example) => {
								const expanded = expandedId === example.id;
								const detailId = `failed-example-${example.id}`;
								return (
									<Fragment key={example.id}>
										<tr className="align-top hover:bg-slate-900/50">
											<td className="px-4 py-4">
												<code
													className="block max-w-40 truncate text-xs text-slate-400"
													title={example.test_case_id}
												>
													{example.test_case_id}
												</code>
											</td>
											<td className="whitespace-nowrap px-4 py-4 text-xs text-slate-400">
												{formatLabel(example.workflow_type)}
											</td>
											<td className="px-4 py-4">
												<span className={difficultyClass(example.difficulty)}>
													{example.difficulty}
												</span>
											</td>
											<ScoreCell value={example.final_score} />
											<ScoreCell value={example.llm_judge_score} />
											<td className="max-w-80 px-4 py-4">
												<FailureModeBadges modes={example.failure_modes} />
											</td>
											<td className="px-4 py-4">
												<button
													aria-controls={detailId}
													aria-expanded={expanded}
													className="text-xs font-medium text-cyan-400 hover:text-cyan-300"
													onClick={() =>
														setExpandedId(expanded ? null : example.id)
													}
													type="button"
												>
													{expanded ? "Hide details" : "View details"}
												</button>
											</td>
										</tr>
										{expanded ? (
											<tr id={detailId}>
												<td className="bg-slate-900/40 p-5" colSpan={7}>
													<FailedExampleDetail example={example} />
												</td>
											</tr>
										) : null}
									</Fragment>
								);
							})}
						</tbody>
					</table>
				</div>
			)}
		</div>
	);
}

function FailedExampleDetail({ example }: { example: FailedExample }) {
	return (
		<div className="space-y-5">
			<div className="grid gap-4 lg:grid-cols-3">
				<JsonPanel label="Input" value={example.input_json} />
				<JsonPanel
					label="Expected output"
					value={example.expected_output_json}
				/>
				<JsonPanel label="Model output" value={example.model_output} />
			</div>
			<div className="grid gap-4 lg:grid-cols-3">
				<ScoreBreakdown example={example} />
				<div className="rounded-md border border-slate-800 bg-slate-950 p-4">
					<h4 className="text-xs font-medium uppercase tracking-wide text-slate-500">
						Judge reason
					</h4>
					<p className="mt-3 text-sm leading-6 text-slate-300">
						{example.judge_reason ?? "No judge reason available."}
					</p>
				</div>
				<RubricScores scores={example.rubric_scores} />
			</div>
			{example.grader_errors.length > 0 ? (
				<div className="rounded-md border border-rose-900/60 bg-rose-950/20 p-4">
					<h4 className="text-xs font-medium uppercase tracking-wide text-rose-300">
						Grader errors
					</h4>
					<ul className="mt-3 space-y-2 text-sm text-rose-200">
						{example.grader_errors.map((error) => (
							<li key={`${error.grader_name}-${error.error}`}>
								<span className="font-medium">
									{formatLabel(error.grader_name)}:
								</span>{" "}
								{error.error}
							</li>
						))}
					</ul>
				</div>
			) : null}
		</div>
	);
}

function ScoreBreakdown({ example }: { example: FailedExample }) {
	return (
		<div className="rounded-md border border-slate-800 bg-slate-950 p-4">
			<h4 className="text-xs font-medium uppercase tracking-wide text-slate-500">
				Score breakdown
			</h4>
			<dl className="mt-3 space-y-2 font-mono text-xs text-slate-300">
				<div className="flex justify-between gap-4">
					<dt>Final</dt>
					<dd>{formatScore(example.final_score)}</dd>
				</div>
				<div className="flex justify-between gap-4">
					<dt>LLM judge</dt>
					<dd>{formatScore(example.llm_judge_score)}</dd>
				</div>
				{Object.entries(example.deterministic_grader_scores).map(
					([name, score]) => (
						<div className="flex justify-between gap-4" key={name}>
							<dt>{formatLabel(name)}</dt>
							<dd>{formatScore(score)}</dd>
						</div>
					),
				)}
			</dl>
		</div>
	);
}

function RubricScores({ scores }: { scores: Record<string, number> }) {
	const entries = Object.entries(scores);
	return (
		<div className="rounded-md border border-slate-800 bg-slate-950 p-4">
			<h4 className="text-xs font-medium uppercase tracking-wide text-slate-500">
				Rubric scores
			</h4>
			{entries.length > 0 ? (
				<dl className="mt-3 space-y-2 font-mono text-xs text-slate-300">
					{entries.map(([name, score]) => (
						<div className="flex justify-between gap-4" key={name}>
							<dt>{formatLabel(name)}</dt>
							<dd>{formatScore(score)}</dd>
						</div>
					))}
				</dl>
			) : (
				<p className="mt-3 text-sm text-slate-500">
					No rubric scores recorded.
				</p>
			)}
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

function JsonPanel({ label, value }: { label: string; value: unknown }) {
	const serialized =
		typeof value === "string" ? value : JSON.stringify(value, null, 2);
	return (
		<div className="min-w-0 rounded-md border border-slate-800 bg-slate-950 p-4">
			<h4 className="text-xs font-medium uppercase tracking-wide text-slate-500">
				{label}
			</h4>
			<pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap break-words font-mono text-xs leading-5 text-slate-300">
				{serialized ?? "—"}
			</pre>
		</div>
	);
}

function ScoreCell({ value }: { value: number | null }) {
	return (
		<td className="whitespace-nowrap px-4 py-4 font-mono text-xs text-slate-300">
			{formatScore(value)}
		</td>
	);
}

function FilterSelect({
	label,
	onChange,
	options,
	value,
}: {
	label: string;
	onChange: (value: string) => void;
	options: string[];
	value: string;
}) {
	return (
		<label className="text-xs text-slate-400">
			<span className="mb-1 block font-medium">{label}</span>
			<select
				className="min-w-44 rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200"
				onChange={(event) => onChange(event.target.value)}
				value={value}
			>
				<option value="all">All</option>
				{options.map((option) => (
					<option key={option} value={option}>
						{formatLabel(option)}
					</option>
				))}
			</select>
		</label>
	);
}

function Header({ children }: { children: React.ReactNode }) {
	return (
		<th className="px-4 py-3 font-medium" scope="col">
			{children}
		</th>
	);
}

function difficultyClass(difficulty: string): string {
	const color =
		difficulty === "easy"
			? "bg-emerald-950 text-emerald-300"
			: difficulty === "medium"
				? "bg-amber-950 text-amber-300"
				: "bg-rose-950 text-rose-300";
	return `inline-flex rounded-full px-2 py-0.5 text-xs font-medium capitalize ${color}`;
}

function formatLabel(value: string): string {
	return value.replaceAll("_", " ");
}

function formatScore(value: number | null): string {
	return value === null ? "—" : value.toFixed(3);
}
