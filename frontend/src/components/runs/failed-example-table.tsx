"use client";

import { useState } from "react";
import type { FailedExample } from "@/lib/types";

export function FailedExampleTable({
	examples,
}: {
	examples: FailedExample[];
}) {
	const [difficulty, setDifficulty] = useState("all");
	const [failureMode, setFailureMode] = useState("all");
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
					<table className="min-w-[1400px] divide-y divide-slate-800 text-left text-sm">
						<thead className="bg-slate-900/60 text-xs uppercase tracking-wide text-slate-500">
							<tr>
								<Header>Test case</Header>
								<Header>Workflow</Header>
								<Header>Difficulty</Header>
								<Header>Score</Header>
								<Header>Failed grader / mode</Header>
								<Header>Feedback</Header>
								<Header>Expected</Header>
								<Header>Actual</Header>
							</tr>
						</thead>
						<tbody className="divide-y divide-slate-800">
							{filteredExamples.map((example) => (
								<FailedExampleRow example={example} key={example.id} />
							))}
						</tbody>
					</table>
				</div>
			)}
		</div>
	);
}

function FailedExampleRow({ example }: { example: FailedExample }) {
	const failedGraders = (example.grader_breakdown.grader_results ?? [])
		.filter((result) => !result.passed)
		.map((result) => result.grader_name);
	const failureLabel = [...failedGraders, ...example.failure_modes].join(", ");

	return (
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
			<td className="whitespace-nowrap px-4 py-4 font-mono text-xs text-rose-300">
				{example.score.toFixed(3)}
			</td>
			<td className="max-w-64 px-4 py-4 text-xs text-rose-300">
				{failureLabel || "Failed composite threshold"}
			</td>
			<td className="max-w-sm px-4 py-4 text-xs text-slate-300">
				{example.grader_feedback ? (
					<details>
						<summary className="cursor-pointer leading-5">
							{truncate(example.grader_feedback, 110)}
						</summary>
						<Breakdown example={example} />
					</details>
				) : (
					<span className="text-slate-600">No grader feedback available</span>
				)}
			</td>
			<JsonCell value={example.expected_output} />
			<JsonCell value={example.parsed_output ?? example.model_output} />
		</tr>
	);
}

function Breakdown({ example }: { example: FailedExample }) {
	const scores = example.grader_breakdown.breakdown ?? {};
	return (
		<div className="mt-3 space-y-3 border-l border-slate-700 pl-3 text-slate-400">
			<p className="whitespace-pre-wrap leading-5">{example.grader_feedback}</p>
			<p>
				Failure modes: {example.failure_modes.join(", ") || "None recorded"}
			</p>
			{Object.keys(scores).length > 0 ? (
				<ul className="space-y-1 font-mono">
					{Object.entries(scores).map(([name, score]) => (
						<li key={name}>
							{name}: {score.toFixed(3)}
						</li>
					))}
				</ul>
			) : null}
		</div>
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

function JsonCell({ value }: { value: unknown }) {
	const serialized = typeof value === "string" ? value : JSON.stringify(value);
	return (
		<td className="max-w-80 px-4 py-4 font-mono text-xs leading-5 text-slate-400">
			<span className="line-clamp-4 break-words" title={serialized}>
				{serialized ?? "—"}
			</span>
		</td>
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

function truncate(value: string, length: number): string {
	return value.length > length ? `${value.slice(0, length - 1)}…` : value;
}
