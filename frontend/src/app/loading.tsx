export default function DashboardLoading() {
	return (
		<div className="mx-auto max-w-7xl animate-pulse space-y-6">
			<div className="h-24 rounded-lg bg-slate-900" />
			<div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
				<div className="h-28 rounded-lg bg-slate-900" />
				<div className="h-28 rounded-lg bg-slate-900" />
				<div className="h-28 rounded-lg bg-slate-900" />
				<div className="h-28 rounded-lg bg-slate-900" />
			</div>
			<div className="h-64 rounded-lg bg-slate-900" />
		</div>
	);
}
