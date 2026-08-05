import { EmptyState } from "@/components/dashboard/state-banners";
import { getPromptVersions } from "@/lib/api";
import type { PromptVersion } from "@/lib/types";

export default async function PromptsPage() {
	let prompts: PromptVersion[] = [];
	let error: string | null = null;

	try {
		prompts = await getPromptVersions();
	} catch (loadError) {
		error =
			loadError instanceof Error
				? loadError.message
				: "Unable to load prompt versions.";
	}

	return (
		<div className="mx-auto max-w-7xl">
			<header className="border-b border-slate-800 pb-6">
				<p className="text-sm font-medium uppercase text-slate-500">Prompts</p>
				<h2 className="mt-2 text-3xl font-semibold tracking-tight text-white">
					Prompt versions
				</h2>
				<p className="mt-3 max-w-2xl text-sm text-slate-400">
					Baseline and intentionally degraded prompt versions used for
					regression comparisons across workflows.
				</p>
			</header>

			<section className="mt-8">
				{error ? (
					<EmptyState description={error} title="Prompt versions unavailable" />
				) : prompts.length === 0 ? (
					<EmptyState
						description="Seed prompt versions with uv run python -m app.seed.load_seed_data."
						title="No prompt versions yet"
					/>
				) : (
					<div className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-950">
						<table className="min-w-full divide-y divide-slate-800 text-left text-sm">
							<thead className="bg-slate-900/60 text-xs uppercase tracking-wide text-slate-500">
								<tr>
									<th className="px-4 py-3" scope="col">
										Name
									</th>
									<th className="px-4 py-3" scope="col">
										Workflow
									</th>
									<th className="px-4 py-3" scope="col">
										Version
									</th>
									<th className="px-4 py-3" scope="col">
										Created
									</th>
								</tr>
							</thead>
							<tbody className="divide-y divide-slate-800">
								{prompts.map((prompt) => (
									<tr key={prompt.id}>
										<td className="px-4 py-3 text-slate-200">{prompt.name}</td>
										<td className="px-4 py-3 font-mono text-xs text-slate-400">
											{prompt.workflow_type}
										</td>
										<td className="px-4 py-3 font-mono text-xs text-cyan-300">
											{prompt.version_label}
										</td>
										<td className="px-4 py-3 text-xs text-slate-500">
											{new Intl.DateTimeFormat("en-CA", {
												dateStyle: "medium",
												timeStyle: "short",
											}).format(new Date(prompt.created_at))}
										</td>
									</tr>
								))}
							</tbody>
						</table>
					</div>
				)}
			</section>
		</div>
	);
}
