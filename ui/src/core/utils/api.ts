export const buildApiUrl = (path: string) => {
  const devUrl = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";
  const baseUrl = import.meta.env.DEV ? devUrl : "";
  return `${baseUrl}${path}`;
};
