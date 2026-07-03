import Link from "next/link";
import { ResultTable } from "@/components/runs/result-table";
import { RunSummary } from "@/components/runs/run-summary";
import { getEvalRun, getEvalRunResults } from "@/lib/api";

export default async function RunDetailPage({
	params,
}: {
	params: Promise<{ runId: string }>;
}) {
	const { runId } = await params;
	const [run, results] = await Promise.all([
		getEvalRun(runId),
		getEvalRunResults(runId),
	]);

	return (
		<div className="mx-auto max-w-7xl">
			<header className="border-b border-slate-800 pb-6">
				<Link
					className="text-sm text-cyan-400 hover:text-cyan-300"
					href="/runs"
				>
					← All eval runs
				</Link>
				<p className="mt-5 text-sm font-medium uppercase tracking-wide text-slate-500">
					Run inspection
				</p>
				<h2 className="mt-2 text-3xl font-semibold tracking-tight text-white">
					Eval run detail
				</h2>
				<p className="mt-3 break-all font-mono text-xs text-slate-500">
					{run.id}
				</p>
			</header>

			<section className="mt-8">
				<RunSummary run={run} />
			</section>

			<section className="mt-8">
				<div className="mb-3">
					<h3 className="text-lg font-semibold text-white">Case results</h3>
					<p className="mt-1 text-sm text-slate-500">
						{results.length} {results.length === 1 ? "result" : "results"}
					</p>
				</div>
				<ResultTable results={results} />
			</section>
		</div>
	);
}
