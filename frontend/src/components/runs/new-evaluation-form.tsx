"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
	type FormEvent,
	useEffect,
	useMemo,
	useState,
	useTransition,
} from "react";
import {
	EmptyState,
	PartialDataBanner,
} from "@/components/dashboard/state-banners";
import {
	ApiError,
	createEvalRun,
	getDatasets,
	getModelConfigs,
	getPromptVersions,
} from "@/lib/api";
import type { DatasetSummary, ModelConfig, PromptVersion } from "@/lib/types";

type FormState = {
	datasetId: string;
	promptVersionId: string;
	modelConfigId: string;
};

export function NewEvaluationForm() {
	const router = useRouter();
	const [datasets, setDatasets] = useState<DatasetSummary[] | null>(null);
	const [prompts, setPrompts] = useState<PromptVersion[] | null>(null);
	const [models, setModels] = useState<ModelConfig[] | null>(null);
	const [form, setForm] = useState<FormState>({
		datasetId: "",
		promptVersionId: "",
		modelConfigId: "",
	});
	const [loadError, setLoadError] = useState<string | null>(null);
	const [validationError, setValidationError] = useState<string | null>(null);
	const [submitError, setSubmitError] = useState<string | null>(null);
	const [completedRunId, setCompletedRunId] = useState<string | null>(null);
	const [isPending, startTransition] = useTransition();

	useEffect(() => {
		let cancelled = false;
		startTransition(async () => {
			try {
				const [loadedDatasets, loadedPrompts, loadedModels] = await Promise.all(
					[getDatasets(), getPromptVersions(), getModelConfigs()],
				);
				if (cancelled) return;
				setDatasets(loadedDatasets);
				setPrompts(loadedPrompts);
				setModels(loadedModels);
				setForm({
					datasetId: loadedDatasets[0]?.id ?? "",
					promptVersionId: "",
					modelConfigId: loadedModels[0]?.id ?? "",
				});
			} catch (error) {
				if (cancelled) return;
				setLoadError(
					error instanceof Error
						? error.message
						: "Unable to load evaluation options.",
				);
				setDatasets([]);
				setPrompts([]);
				setModels([]);
			}
		});
		return () => {
			cancelled = true;
		};
	}, []);

	const selectedDataset = useMemo(
		() => datasets?.find((dataset) => dataset.id === form.datasetId) ?? null,
		[datasets, form.datasetId],
	);

	const compatiblePrompts = useMemo(() => {
		if (!prompts || !selectedDataset) return [];
		return prompts.filter(
			(prompt) => prompt.workflow_type === selectedDataset.workflow_type,
		);
	}, [prompts, selectedDataset]);

	const incompatiblePromptCount = useMemo(() => {
		if (!prompts || !selectedDataset) return 0;
		return prompts.length - compatiblePrompts.length;
	}, [compatiblePrompts.length, prompts, selectedDataset]);

	useEffect(() => {
		if (!selectedDataset || compatiblePrompts.length === 0) {
			setForm((current) =>
				current.promptVersionId ? { ...current, promptVersionId: "" } : current,
			);
			return;
		}
		const stillValid = compatiblePrompts.some(
			(prompt) => prompt.id === form.promptVersionId,
		);
		if (!stillValid) {
			setForm((current) => ({
				...current,
				promptVersionId: compatiblePrompts[0].id,
			}));
		}
	}, [compatiblePrompts, form.promptVersionId, selectedDataset]);

	function onSubmit(event: FormEvent<HTMLFormElement>) {
		event.preventDefault();
		setValidationError(null);
		setSubmitError(null);
		setCompletedRunId(null);

		if (!form.datasetId || !form.promptVersionId || !form.modelConfigId) {
			setValidationError(
				"Select a dataset, a compatible prompt version, and a model configuration.",
			);
			return;
		}
		if (!selectedDataset) {
			setValidationError("Selected dataset is no longer available.");
			return;
		}
		const prompt = compatiblePrompts.find(
			(item) => item.id === form.promptVersionId,
		);
		if (!prompt) {
			setValidationError(
				`Prompt must match dataset workflow type (${selectedDataset.workflow_type}).`,
			);
			return;
		}

		startTransition(async () => {
			try {
				const run = await createEvalRun({
					dataset_id: form.datasetId,
					prompt_version_id: form.promptVersionId,
					model_config_id: form.modelConfigId,
				});
				setCompletedRunId(run.id);
				if (run.status === "failed") {
					setSubmitError(
						"Evaluation finished with status failed. Open the run detail page for provider or grader errors.",
					);
					return;
				}
				router.push(`/runs/${run.id}`);
			} catch (error) {
				if (error instanceof ApiError) {
					if (error.status === 404) {
						setValidationError(error.detail);
					} else if (
						error.detail.toLowerCase().includes("provider") ||
						error.detail.toLowerCase().includes("api key")
					) {
						setSubmitError(
							`Provider error: ${error.detail}. Check model keys in the root .env and retry.`,
						);
					} else {
						setSubmitError(error.detail);
					}
					return;
				}
				setSubmitError(
					error instanceof Error
						? error.message
						: "Unable to start evaluation.",
				);
			}
		});
	}

	if (datasets === null || prompts === null || models === null) {
		return (
			<p className="text-sm text-slate-500">Loading evaluation options…</p>
		);
	}

	if (loadError) {
		return (
			<EmptyState description={loadError} title="Unable to load run launcher" />
		);
	}

	if (datasets.length === 0 || prompts.length === 0 || models.length === 0) {
		return (
			<EmptyState
				description="Seed datasets, prompt versions, and model configs with uv run python -m app.seed.load_seed_data, then refresh."
				title="Missing seed resources"
			/>
		);
	}

	return (
		<form className="space-y-6" onSubmit={onSubmit}>
			{validationError ? <PartialDataBanner message={validationError} /> : null}
			{submitError ? (
				<div className="rounded-lg border border-rose-900/60 bg-rose-950/20 px-4 py-3 text-sm text-rose-200">
					{submitError}
				</div>
			) : null}
			{completedRunId ? (
				<p className="text-sm text-slate-400">
					Run created.{" "}
					<Link
						className="text-cyan-400 hover:text-cyan-300"
						href={`/runs/${completedRunId}`}
					>
						Open run detail
					</Link>
				</p>
			) : null}

			<div className="grid gap-5 lg:grid-cols-3">
				<label className="block space-y-2 text-sm">
					<span className="font-medium text-slate-200">Dataset</span>
					<select
						className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100"
						disabled={isPending}
						onChange={(event) =>
							setForm((current) => ({
								...current,
								datasetId: event.target.value,
							}))
						}
						value={form.datasetId}
					>
						{datasets.map((dataset) => (
							<option key={dataset.id} value={dataset.id}>
								{dataset.name} ({dataset.workflow_type})
							</option>
						))}
					</select>
					<span className="block text-xs text-slate-500">
						{selectedDataset
							? `${selectedDataset.test_case_count} cases · ${selectedDataset.workflow_type}`
							: "Choose a seeded dataset"}
					</span>
				</label>

				<label className="block space-y-2 text-sm">
					<span className="font-medium text-slate-200">Prompt version</span>
					<select
						className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100"
						disabled={isPending || compatiblePrompts.length === 0}
						onChange={(event) =>
							setForm((current) => ({
								...current,
								promptVersionId: event.target.value,
							}))
						}
						value={form.promptVersionId}
					>
						{compatiblePrompts.length === 0 ? (
							<option value="">No compatible prompts</option>
						) : (
							compatiblePrompts.map((prompt) => (
								<option key={prompt.id} value={prompt.id}>
									{prompt.name} / {prompt.version_label}
								</option>
							))
						)}
					</select>
					<span className="block text-xs text-slate-500">
						{selectedDataset
							? `Showing prompts for ${selectedDataset.workflow_type}` +
								(incompatiblePromptCount > 0
									? ` · ${incompatiblePromptCount} incompatible hidden`
									: "")
							: "Select a dataset first"}
					</span>
				</label>

				<label className="block space-y-2 text-sm">
					<span className="font-medium text-slate-200">Model config</span>
					<select
						className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100"
						disabled={isPending}
						onChange={(event) =>
							setForm((current) => ({
								...current,
								modelConfigId: event.target.value,
							}))
						}
						value={form.modelConfigId}
					>
						{models.map((model) => (
							<option key={model.id} value={model.id}>
								{model.provider}/{model.model_name}
							</option>
						))}
					</select>
					<span className="block text-xs text-slate-500">
						Requires a configured provider key for live generation.
					</span>
				</label>
			</div>

			<div className="flex flex-wrap items-center gap-3">
				<button
					className="rounded-md border border-cyan-800 bg-cyan-950/40 px-4 py-2 text-sm font-medium text-cyan-200 transition hover:bg-cyan-900/40 disabled:opacity-50"
					disabled={isPending || compatiblePrompts.length === 0}
					type="submit"
				>
					{isPending ? "Running evaluation…" : "Start evaluation"}
				</button>
				<p className="text-xs text-slate-500">
					Runs synchronously. Keep this page open until the run completes.
				</p>
			</div>
		</form>
	);
}
