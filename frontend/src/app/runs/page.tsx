import Link from "next/link";
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
				<div className="mt-2 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
					<div>
						<h2 className="text-3xl font-semibold tracking-tight text-white">
							Eval runs
						</h2>
						<p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">
							Inspect synchronous evaluation runs, execution cost, and latency.
						</p>
					</div>
					<Link
						className="rounded-md border border-cyan-800 bg-cyan-950/40 px-4 py-2 text-sm font-medium text-cyan-200 transition hover:bg-cyan-900/40"
						href="/runs/new"
					>
						New evaluation
					</Link>
				</div>
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
