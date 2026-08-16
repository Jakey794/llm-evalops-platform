import type { DatasetSummary } from "@/lib/types";

type DatasetTableProps = {
	datasets: DatasetSummary[];
	selectedDatasetId: string | null;
	onSelect: (datasetId: string) => void;
};

export function DatasetTable({
	datasets,
	selectedDatasetId,
	onSelect,
}: DatasetTableProps) {
	if (datasets.length === 0) {
		return (
			<div className="rounded-lg border border-dashed border-slate-800 bg-slate-950 p-8 text-center">
				<p className="text-sm font-medium text-slate-300">No datasets found</p>
				<p className="mt-1 text-sm text-slate-500">
					Import or seed a dataset to see it here.
				</p>
			</div>
		);
	}

	return (
		<div className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-950 shadow-sm shadow-black/20">
			<table className="min-w-full divide-y divide-slate-800 text-left text-sm">
				<thead className="bg-slate-900/60 text-xs uppercase tracking-wide text-slate-500">
					<tr>
						<th className="px-4 py-3 font-medium" scope="col">
							Name
						</th>
						<th className="px-4 py-3 font-medium" scope="col">
							Workflow
						</th>
						<th className="px-4 py-3 font-medium" scope="col">
							Cases
						</th>
						<th className="px-4 py-3 font-medium" scope="col">
							Source
						</th>
						<th className="px-4 py-3 font-medium" scope="col">
							Created
						</th>
					</tr>
				</thead>
				<tbody className="divide-y divide-slate-800">
					{datasets.map((dataset) => {
						const isSelected = dataset.id === selectedDatasetId;
						return (
							<tr
								className={
									isSelected ? "bg-cyan-950/30" : "hover:bg-slate-900/50"
								}
								key={dataset.id}
							>
								<td className="px-4 py-3">
									<button
										aria-pressed={isSelected}
										className="font-medium text-slate-100 underline-offset-4 hover:text-cyan-300 hover:underline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-cyan-400"
										onClick={() => onSelect(dataset.id)}
										type="button"
									>
										{dataset.name}
									</button>
								</td>
								<td className="whitespace-nowrap px-4 py-3 text-slate-400">
									{formatLabel(dataset.workflow_type)}
								</td>
								<td className="px-4 py-3 font-mono text-slate-300">
									{dataset.test_case_count}
								</td>
								<td className="max-w-56 truncate px-4 py-3 font-mono text-xs text-slate-500">
									{dataset.source_filename ?? "—"}
								</td>
								<td className="whitespace-nowrap px-4 py-3 text-slate-500">
									{formatDate(dataset.created_at)}
								</td>
							</tr>
						);
					})}
				</tbody>
			</table>
		</div>
	);
}

function formatDate(value: string): string {
	return new Intl.DateTimeFormat("en", {
		dateStyle: "medium",
		timeZone: "UTC",
	}).format(new Date(value));
}

function formatLabel(value: string): string {
	return value.replaceAll("_", " ");
}
