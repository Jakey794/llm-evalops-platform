"use client";

import { type FormEvent, useState } from "react";

export default function LoginPage() {
	const [error, setError] = useState<string | null>(null);
	const [pending, setPending] = useState(false);

	async function submit(event: FormEvent<HTMLFormElement>) {
		event.preventDefault();
		setError(null);
		setPending(true);
		const form = new FormData(event.currentTarget);
		try {
			const response = await fetch("/api/auth/login", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ password: form.get("password") }),
			});
			if (!response.ok) {
				const body = (await response.json()) as { detail?: string };
				setError(body.detail ?? "Unable to sign in");
				return;
			}
			window.location.assign("/");
		} catch {
			setError("Unable to reach the sign-in service");
		} finally {
			setPending(false);
		}
	}

	return (
		<div className="mx-auto flex min-h-[70vh] max-w-md items-center">
			<div className="w-full rounded-2xl border border-slate-800 bg-slate-900/50 p-7 shadow-2xl">
				<p className="text-sm font-medium uppercase tracking-wide text-cyan-400">
					Protected demo
				</p>
				<h1 className="mt-3 text-3xl font-semibold text-white">
					Sign in to EvalOps
				</h1>
				<p className="mt-3 text-sm leading-6 text-slate-400">
					Use the viewer password for read-only access or the operator password
					to launch evaluations.
				</p>
				<form className="mt-7 space-y-4" onSubmit={submit}>
					<label className="block space-y-2 text-sm font-medium text-slate-200">
						<span>Access password</span>
						<input
							autoComplete="current-password"
							className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2.5 text-white outline-none focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20"
							disabled={pending}
							maxLength={256}
							name="password"
							required
							type="password"
						/>
					</label>
					{error ? (
						<p
							className="rounded-lg border border-rose-900/60 bg-rose-950/30 px-3 py-2 text-sm text-rose-200"
							role="alert"
						>
							{error}
						</p>
					) : null}
					<button
						className="w-full rounded-lg bg-cyan-500 px-4 py-2.5 font-semibold text-slate-950 hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-60"
						disabled={pending}
						type="submit"
					>
						{pending ? "Signing in…" : "Sign in"}
					</button>
				</form>
			</div>
		</div>
	);
}
