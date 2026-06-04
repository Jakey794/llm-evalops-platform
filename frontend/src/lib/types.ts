export type HealthResponse = {
	status: string;
	service: string;
	version: string;
	database?: string;
};

export type MetricCardProps = {
	label: string;
	value: string;
	helperText: string;
};
