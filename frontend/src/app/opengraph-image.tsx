import { ImageResponse } from "next/og";

export const alt = "LLM Reliability + EvalOps Platform";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpenGraphImage() {
	return new ImageResponse(
		<div
			style={{
				alignItems: "flex-start",
				background: "#020617",
				color: "#f8fafc",
				display: "flex",
				flexDirection: "column",
				height: "100%",
				justifyContent: "center",
				padding: "88px",
				width: "100%",
			}}
		>
			<div style={{ color: "#22d3ee", fontSize: 28, letterSpacing: 4 }}>
				EVALOPS / LLM RELIABILITY
			</div>
			<div
				style={{
					fontSize: 72,
					fontWeight: 700,
					lineHeight: 1.05,
					marginTop: 28,
				}}
			>
				Measure what your LLMs ship.
			</div>
			<div style={{ color: "#94a3b8", fontSize: 30, marginTop: 30 }}>
				Versioned datasets, deterministic graders, quality gates, and
				cost-latency analytics.
			</div>
		</div>,
		{ ...size },
	);
}
