export const siteConfig = {
	name: "LLM Reliability + EvalOps Platform",
	shortName: "LLM EvalOps",
	description:
		"A full-stack reference implementation for measuring LLM quality, cost, and latency across versioned prompts, datasets, and graders.",
	url:
		process.env.NEXT_PUBLIC_SITE_URL ??
		"https://llm-evalops-platform.vercel.app",
} as const;
