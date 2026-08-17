export function hasSameOrigin(request: Request): boolean {
	const origin = request.headers.get("origin");
	if (!origin) return false;
	return origin === getExternalOrigin(request);
}

export function getExternalOrigin(request: Request): string {
	const forwardedHost = request.headers
		.get("x-forwarded-host")
		?.split(",")[0]
		?.trim();
	const host = forwardedHost || request.headers.get("host");
	const forwardedProtocol = request.headers
		.get("x-forwarded-proto")
		?.split(",")[0]
		?.trim();
	const protocol =
		forwardedProtocol === "https" || forwardedProtocol === "http"
			? forwardedProtocol
			: new URL(request.url).protocol.replace(":", "");
	return host ? `${protocol}://${host}` : new URL(request.url).origin;
}
