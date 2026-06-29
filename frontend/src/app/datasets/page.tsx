"use client";

import { useEffect, useState } from "react";
import { DatasetDetailCard } from "@/components/datasets/dataset-detail-card";
import { DatasetTable } from "@/components/datasets/dataset-table";
import { TestCaseTable } from "@/components/datasets/test-case-table";
import { getDataset, getDatasets, getDatasetTestCases } from "@/lib/api";
import type { DatasetDetail, DatasetSummary, TestCase } from "@/lib/types";

export default function DatasetsPage() {
	const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
	const [selectedDatasetId, setSelectedDatasetId] = useState<string | null>(
		null,
	);
	const [datasetDetail, setDatasetDetail] = useState<DatasetDetail | null>(
		null,
	);
	const [testCases, setTestCases] = useState<TestCase[]>([]);
	const [isLoadingDatasets, setIsLoadingDatasets] = useState(true);
	const [isLoadingSelection, setIsLoadingSelection] = useState(false);
	const [datasetsError, setDatasetsError] = useState<string | null>(null);
	const [selectionError, setSelectionError] = useState<string | null>(null);
	const [datasetsRequest, setDatasetsRequest] = useState(0);
	const [selectionRequest, setSelectionRequest] = useState(0);

	// biome-ignore lint/correctness/useExhaustiveDependencies: the request token intentionally triggers retries.
	useEffect(() => {
		let isCurrent = true;
		setIsLoadingDatasets(true);
		setDatasetsError(null);

		void getDatasets()
			.then((nextDatasets) => {
				if (!isCurrent) return;
				setDatasets(nextDatasets);
				setSelectedDatasetId((currentId) => {
					if (currentId && nextDatasets.some(({ id }) => id === currentId)) {
						return currentId;
					}
					return nextDatasets[0]?.id ?? null;
				});
			})
			.catch((error: unknown) => {
				if (!isCurrent) return;
				setDatasetsError(getErrorMessage(error));
			})
			.finally(() => {
				if (isCurrent) setIsLoadingDatasets(false);
			});

		return () => {
			isCurrent = false;
		};
	}, [datasetsRequest]);

	// biome-ignore lint/correctness/useExhaustiveDependencies: the request token intentionally triggers retries.
	useEffect(() => {
		if (!selectedDatasetId) {
			setDatasetDetail(null);
			setTestCases([]);
			setSelectionError(null);
			return;
		}

		let isCurrent = true;
		setIsLoadingSelection(true);
		setSelectionError(null);

		void Promise.all([
			getDataset(selectedDatasetId),
			getDatasetTestCases(selectedDatasetId),
		])
			.then(([detail, cases]) => {
				if (!isCurrent) return;
				setDatasetDetail(detail);
				setTestCases(cases);
			})
			.catch((error: unknown) => {
				if (!isCurrent) return;
				setDatasetDetail(null);
				setTestCases([]);
				setSelectionError(getErrorMessage(error));
			})
			.finally(() => {
				if (isCurrent) setIsLoadingSelection(false);
			});

		return () => {
			isCurrent = false;
		};
	}, [selectedDatasetId, selectionRequest]);

	return (
		<div className="mx-auto max-w-7xl">
			<header className="border-b border-slate-800 pb-6">
				<p className="text-sm font-medium uppercase tracking-wide text-slate-500">
					Eval data
				</p>
				<h2 className="mt-2 text-3xl font-semibold tracking-tight text-white">
					Datasets
				</h2>
				<p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">
					Browse imported evaluation datasets and inspect their test cases.
				</p>
			</header>

			<section className="mt-8">
				<div className="mb-3 flex items-center justify-between">
					<div>
						<h3 className="text-lg font-semibold text-white">
							Dataset library
						</h3>
						<p className="mt-1 text-sm text-slate-500">
							{datasets.length} {datasets.length === 1 ? "dataset" : "datasets"}
						</p>
					</div>
				</div>

				{isLoadingDatasets ? (
					<LoadingPanel message="Loading datasets…" />
				) : datasetsError ? (
					<ErrorPanel
						message={datasetsError}
						onRetry={() => setDatasetsRequest((request) => request + 1)}
					/>
				) : (
					<DatasetTable
						datasets={datasets}
						onSelect={setSelectedDatasetId}
						selectedDatasetId={selectedDatasetId}
					/>
				)}
			</section>

			<section className="mt-8">
				{isLoadingSelection ? (
					<LoadingPanel message="Loading dataset details…" />
				) : selectionError ? (
					<ErrorPanel
						message={selectionError}
						onRetry={() => setSelectionRequest((request) => request + 1)}
					/>
				) : datasetDetail ? (
					<div className="space-y-6">
						<DatasetDetailCard dataset={datasetDetail} />
						<TestCaseTable testCases={testCases} />
					</div>
				) : datasets.length > 0 ? (
					<div className="rounded-lg border border-dashed border-slate-800 bg-slate-950 p-8 text-center text-sm text-slate-500">
						Select a dataset to inspect its test cases.
					</div>
				) : null}
			</section>
		</div>
	);
}

function LoadingPanel({ message }: { message: string }) {
	return (
		<div
			aria-live="polite"
			className="animate-pulse rounded-lg border border-slate-800 bg-slate-950 p-8 text-center text-sm text-slate-400"
		>
			{message}
		</div>
	);
}

function ErrorPanel({
	message,
	onRetry,
}: {
	message: string;
	onRetry: () => void;
}) {
	return (
		<div
			role="alert"
			className="flex flex-col gap-4 rounded-lg border border-rose-950 bg-rose-950/20 p-5 sm:flex-row sm:items-center sm:justify-between"
		>
			<div>
				<p className="text-sm font-semibold text-rose-300">
					Unable to load data
				</p>
				<p className="mt-1 text-sm text-rose-200/70">{message}</p>
			</div>
			<button
				className="rounded-md border border-rose-800 px-3 py-2 text-sm font-medium text-rose-200 transition hover:bg-rose-900/40"
				onClick={onRetry}
				type="button"
			>
				Try again
			</button>
		</div>
	);
}

function getErrorMessage(error: unknown): string {
	return error instanceof Error
		? error.message
		: "An unexpected error occurred.";
}
