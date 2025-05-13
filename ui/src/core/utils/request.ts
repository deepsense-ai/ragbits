import axios, { AxiosInstance, AxiosResponse } from "axios";
import { useState, useEffect } from "react";
import { RequestConfig } from "../../types/api";

const DEFAULT_CONFIG: RequestConfig = { method: "GET" };

function createAxiosClient(): AxiosInstance {
  return axios.create({
    headers: {
      "Content-Type": "application/json",
    },
    responseType: "json",
    adapter: "fetch",
  });
}

export function createRequest<Res = unknown, Req = unknown>(
  url: string,
  config: RequestConfig<Req>,
): () => Promise<AxiosResponse<Res>> {
  const axiosClient = createAxiosClient();
  const { method, body } = config;
  const message = body ? JSON.stringify(body) : null;

  return async () => {
    if (method === "GET") {
      return await axiosClient.get(url);
    } else if (method === "POST") {
      return await axiosClient.post(url, message);
    } else {
      throw new Error("Invalid method. Use GET or POST.");
    }
  };
}

// TODO: We might want to use TanStackQuery in the future or some other fetching library
export function useRequest<Res = unknown, Req = unknown>(
  url: string,
  config?: RequestConfig<Req>,
): {
  data: AxiosResponse<Res> | null;
  error: Error | null;
  isLoading: boolean;
} {
  const [data, setData] = useState<AxiosResponse | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    let isCancelled = false;
    const fetchData = async () => {
      setIsLoading(true);
      try {
        const response = await createRequest(url, config ?? DEFAULT_CONFIG)();
        if (isCancelled) return;
        setData(response);
      } catch (err) {
        if (isCancelled) return;
        setError(err as Error);
      } finally {
        if (!isCancelled) {
          setIsLoading(false);
        }
      }
    };

    void fetchData();
    return () => {
      isCancelled = true;
    };
  }, [config, url]);

  return { data, error, isLoading };
}
