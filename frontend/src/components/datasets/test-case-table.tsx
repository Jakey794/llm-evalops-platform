import type { TestCase } from "@/lib/types";

export function TestCaseTable({ testCases }: { testCases: TestCase[] }) {
	return (
		<div>
			<div className="mb-3">
				<h3 className="text-lg font-semibold text-white">Test case preview</h3>
				<p className="mt-1 text-sm text-slate-500">
					{testCases.length} {testCases.length === 1 ? "case" : "cases"}
				</p>
			</div>

			{testCases.length === 0 ? (
				<div className="rounded-lg border border-dashed border-slate-800 bg-slate-950 p-8 text-center text-sm text-slate-500">
					This dataset has no test cases.
				</div>
			) : (
				<div className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-950 shadow-sm shadow-black/20">
					<table className="min-w-full divide-y divide-slate-800 text-left text-sm">
						<thead className="bg-slate-900/60 text-xs uppercase tracking-wide text-slate-500">
							<tr>
								<th className="px-4 py-3 font-medium" scope="col">
									External ID
								</th>
								<th className="px-4 py-3 font-medium" scope="col">
									Workflow
								</th>
								<th className="px-4 py-3 font-medium" scope="col">
									Difficulty
								</th>
								<th className="px-4 py-3 font-medium" scope="col">
									Tags
								</th>
								<th className="px-4 py-3 font-medium" scope="col">
									Input
								</th>
								<th className="px-4 py-3 font-medium" scope="col">
									Expected output
								</th>
							</tr>
						</thead>
						<tbody className="divide-y divide-slate-800">
							{testCases.map((testCase) => (
								<tr
									className="align-top hover:bg-slate-900/40"
									key={testCase.id}
								>
									<td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-slate-300">
										{testCase.external_id}
									</td>
									<td className="whitespace-nowrap px-4 py-3 text-slate-400">
										{formatLabel(testCase.workflow_type)}
									</td>
									<td className="px-4 py-3">
										<span className={difficultyClass(testCase.difficulty)}>
											{testCase.difficulty}
										</span>
									</td>
									<td className="min-w-44 px-4 py-3">
										<div className="flex flex-wrap gap-1.5">
											{testCase.tags.length > 0 ? (
												testCase.tags.map((tag) => (
													<span
														className="rounded bg-slate-800 px-2 py-0.5 text-xs text-slate-300"
														key={tag}
													>
														{tag}
													</span>
												))
											) : (
												<span className="text-slate-600">—</span>
											)}
										</div>
									</td>
									<td className="max-w-72 px-4 py-3 font-mono text-xs leading-5 text-slate-400">
										<span title={JSON.stringify(testCase.input)}>
											{compactJson(testCase.input)}
										</span>
									</td>
									<td className="max-w-72 px-4 py-3 font-mono text-xs leading-5 text-slate-400">
										<span title={JSON.stringify(testCase.expected_output)}>
											{compactJson(testCase.expected_output)}
										</span>
									</td>
								</tr>
							))}
						</tbody>
					</table>
				</div>
			)}
		</div>
	);
}

function compactJson(value: Record<string, unknown>): string {
	const serialized = JSON.stringify(value);
	return serialized.length > 110 ? `${serialized.slice(0, 107)}…` : serialized;
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
