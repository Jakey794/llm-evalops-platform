type ScatterPoint = {
	id: string;
	label: string;
	x: number | null;
	y: number | null;
};

export function ScatterChart({
	title,
	description,
	xLabel,
	yLabel,
	points,
	emptyMessage,
}: {
	title: string;
	description: string;
	xLabel: string;
	yLabel: string;
	points: ScatterPoint[];
	emptyMessage: string;
}) {
	const plotted = points.filter(
		(point): point is ScatterPoint & { x: number; y: number } =>
			point.x !== null && point.y !== null,
	);

	if (plotted.length === 0) {
		return (
			<section className="rounded-lg border border-dashed border-slate-800 bg-slate-950 p-6">
				<h3 className="text-lg font-semibold text-white">{title}</h3>
				<p className="mt-2 text-sm text-slate-500">{description}</p>
				<p className="mt-4 text-sm text-slate-500">{emptyMessage}</p>
			</section>
		);
	}

	const xs = plotted.map((point) => point.x);
	const ys = plotted.map((point) => point.y);
	const minX = Math.min(...xs);
	const maxX = Math.max(...xs);
	const minY = Math.min(...ys);
	const maxY = Math.max(...ys);
	const padX =
		maxX === minX ? Math.max(Math.abs(maxX) * 0.1, 1) : (maxX - minX) * 0.1;
	const padY =
		maxY === minY ? Math.max(Math.abs(maxY) * 0.1, 0.05) : (maxY - minY) * 0.1;
	const x0 = minX - padX;
	const x1 = maxX + padX;
	const y0 = Math.max(0, minY - padY);
	const y1 = Math.min(1, maxY + padY);
	const width = 420;
	const height = 240;
	const left = 44;
	const right = 16;
	const top = 16;
	const bottom = 36;
	const plotWidth = width - left - right;
	const plotHeight = height - top - bottom;

	const projectX = (value: number) =>
		left + ((value - x0) / (x1 - x0 || 1)) * plotWidth;
	const projectY = (value: number) =>
		top + (1 - (value - y0) / (y1 - y0 || 1)) * plotHeight;

	return (
		<section className="rounded-lg border border-slate-800 bg-slate-950 p-4">
			<h3 className="text-lg font-semibold text-white">{title}</h3>
			<p className="mt-1 text-sm text-slate-500">{description}</p>
			<svg
				aria-label={title}
				className="mt-4 w-full"
				role="img"
				viewBox={`0 0 ${width} ${height}`}
			>
				<title>{title}</title>
				<line
					className="stroke-slate-700"
					x1={left}
					x2={left}
					y1={top}
					y2={top + plotHeight}
				/>
				<line
					className="stroke-slate-700"
					x1={left}
					x2={left + plotWidth}
					y1={top + plotHeight}
					y2={top + plotHeight}
				/>
				<text
					className="fill-slate-500 text-[10px]"
					textAnchor="middle"
					x={left + plotWidth / 2}
					y={height - 8}
				>
					{xLabel}
				</text>
				<text
					className="fill-slate-500 text-[10px]"
					textAnchor="middle"
					transform={`rotate(-90 ${14} ${top + plotHeight / 2})`}
					x={14}
					y={top + plotHeight / 2}
				>
					{yLabel}
				</text>
				{plotted.map((point, index) => {
					const cx = projectX(point.x);
					const cy = projectY(point.y);
					const color = ["#22d3ee", "#34d399", "#fbbf24", "#f472b6", "#a78bfa"][
						index % 5
					];
					return (
						<g key={point.id}>
							<circle cx={cx} cy={cy} fill={color} r={6}>
								<title>
									{point.label}: {point.x.toFixed(3)} / {point.y.toFixed(3)}
								</title>
							</circle>
							<text className="fill-slate-400 text-[9px]" x={cx + 8} y={cy + 3}>
								{truncate(point.label, 18)}
							</text>
						</g>
					);
				})}
			</svg>
			{points.length !== plotted.length ? (
				<p className="mt-2 text-xs text-amber-300">
					{points.length - plotted.length} run
					{points.length - plotted.length === 1 ? "" : "s"} omitted due to
					missing cost, latency, or score.
				</p>
			) : null}
		</section>
	);
}

function truncate(value: string, max: number): string {
	return value.length > max ? `${value.slice(0, max - 1)}…` : value;
}
