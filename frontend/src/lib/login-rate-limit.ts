type AttemptWindow = { attempts: number[] };

const windows = new Map<string, AttemptWindow>();
const WINDOW_MS = 15 * 60 * 1000;
const MAX_ATTEMPTS = 5;
const MAX_TRACKED_CLIENTS = 10_000;

export function checkLoginRateLimit(key: string): {
	allowed: boolean;
	retryAfter: number;
} {
	const now = Date.now();
	const cutoff = now - WINDOW_MS;
	const window = windows.get(key) ?? { attempts: [] };
	window.attempts = window.attempts.filter((attempt) => attempt > cutoff);
	if (window.attempts.length >= MAX_ATTEMPTS) {
		return {
			allowed: false,
			retryAfter: Math.max(
				1,
				Math.ceil((window.attempts[0] + WINDOW_MS - now) / 1000),
			),
		};
	}
	window.attempts.push(now);
	windows.set(key, window);
	if (windows.size > MAX_TRACKED_CLIENTS) {
		for (const [client, attempts] of windows) {
			if (attempts.attempts.every((attempt) => attempt <= cutoff))
				windows.delete(client);
			if (windows.size <= MAX_TRACKED_CLIENTS) break;
		}
	}
	return { allowed: true, retryAfter: 0 };
}

export function clearLoginRateLimit(key: string): void {
	windows.delete(key);
}
