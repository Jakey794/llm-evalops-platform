import { RunTable } from "@/components/runs/run-table";
import { getEvalRuns } from "@/lib/api";

export default async function RunsPage() {
	const runs = await getEvalRuns();

	return (
		<div className="mx-auto max-w-7xl">
			<header className="border-b border-slate-800 pb-6">
				<p className="text-sm font-medium uppercase tracking-wide text-slate-500">
					Evaluation history
				</p>
				<h2 className="mt-2 text-3xl font-semibold tracking-tight text-white">
					Eval runs
				</h2>
				<p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">
					Inspect synchronous evaluation runs, execution cost, and latency.
				</p>
			</header>

			<section className="mt-8">
				<div className="mb-3 flex items-end justify-between gap-4">
					<div>
						<h3 className="text-lg font-semibold text-white">Recent runs</h3>
						<p className="mt-1 text-sm text-slate-500">
							{runs.length} {runs.length === 1 ? "run" : "runs"}
						</p>
					</div>
				</div>
				<RunTable runs={runs} />
			</section>
		</div>
	);
}
