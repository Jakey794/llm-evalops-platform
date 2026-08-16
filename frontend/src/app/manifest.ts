import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
	return {
		name: "LLM Reliability + EvalOps Platform",
		short_name: "LLM EvalOps",
		description:
			"Measure LLM quality, cost, and latency across versioned evaluation workflows.",
		start_url: "/",
		display: "standalone",
		background_color: "#020617",
		theme_color: "#020617",
		icons: [{ src: "/favicon.ico", sizes: "any", type: "image/x-icon" }],
	};
}
