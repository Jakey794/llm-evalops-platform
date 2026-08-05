export function EmptyState({
	title,
	description,
}: {
	title: string;
	description: string;
}) {
	return (
		<div className="rounded-lg border border-dashed border-slate-800 bg-slate-950 p-10 text-center">
			<p className="text-sm font-medium text-slate-300">{title}</p>
			<p className="mt-1 text-sm text-slate-500">{description}</p>
		</div>
	);
}

export function PartialDataBanner({ message }: { message: string }) {
	return (
		<div className="rounded-lg border border-amber-900/60 bg-amber-950/20 px-4 py-3 text-sm text-amber-200">
			{message}
		</div>
	);
}
