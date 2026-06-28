import type { DatasetDetail } from "@/lib/types";

export function DatasetDetailCard({ dataset }: { dataset: DatasetDetail }) {
	return (
		<article className="rounded-lg border border-slate-800 bg-slate-950 p-5 shadow-sm shadow-black/20">
			<div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
				<div>
					<p className="text-xs font-medium uppercase tracking-wide text-cyan-400">
						Selected dataset
					</p>
					<h3 className="mt-2 text-xl font-semibold text-white">
						{dataset.name}
					</h3>
					<p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
						{dataset.description ?? "No description provided."}
					</p>
				</div>
				<div className="rounded-md border border-slate-800 bg-slate-900/70 px-4 py-3 text-right">
					<p className="text-xs uppercase tracking-wide text-slate-500">
						Test cases
					</p>
					<p className="mt-1 font-mono text-2xl font-semibold text-slate-100">
						{dataset.test_case_count}
					</p>
				</div>
			</div>

			<dl className="mt-5 grid gap-4 border-t border-slate-800 pt-5 sm:grid-cols-3">
				<Detail label="Workflow" value={formatLabel(dataset.workflow_type)} />
				<Detail
					label="Source file"
					value={dataset.source_filename ?? "—"}
					mono
				/>
				<Detail label="Created" value={formatDate(dataset.created_at)} />
			</dl>
		</article>
	);
}

function Detail({
	label,
	value,
	mono = false,
}: {
	label: string;
	value: string;
	mono?: boolean;
}) {
	return (
		<div>
			<dt className="text-xs uppercase tracking-wide text-slate-500">
				{label}
			</dt>
			<dd
				className={`mt-1 text-sm text-slate-300 ${mono ? "font-mono text-xs" : ""}`}
			>
				{value}
			</dd>
		</div>
	);
}

function formatDate(value: string): string {
	return new Intl.DateTimeFormat("en", {
		dateStyle: "medium",
		timeStyle: "short",
	}).format(new Date(value));
}

function formatLabel(value: string): string {
	return value.replaceAll("_", " ");
}
