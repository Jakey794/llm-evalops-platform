import Link from "next/link";
import { NewEvaluationForm } from "@/components/runs/new-evaluation-form";

export default function NewEvaluationPage() {
	return (
		<div className="mx-auto max-w-7xl">
			<header className="border-b border-slate-800 pb-6">
				<p className="text-sm font-medium uppercase tracking-wide text-slate-500">
					New evaluation
				</p>
				<h2 className="mt-2 text-3xl font-semibold tracking-tight text-white">
					Launch an eval run
				</h2>
				<p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">
					Pick a seeded dataset, a workflow-compatible prompt version, and a
					model configuration. The API runs the evaluation synchronously and
					returns completed metrics.
				</p>
				<p className="mt-3 text-sm text-slate-500">
					<Link className="text-cyan-400 hover:text-cyan-300" href="/runs">
						Back to runs
					</Link>
				</p>
			</header>

			<section className="mt-8 rounded-lg border border-slate-800 bg-slate-950/60 p-6">
				<NewEvaluationForm />
			</section>
		</div>
	);
}
