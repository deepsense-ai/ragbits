import axios, { AxiosError, AxiosRequestConfig, Method } from "axios";

interface RequestOptions<Req = Record<string, unknown>> {
  url: string;
  method: Method;
  body?: Req;
  headers?: Record<string, string>;
}

const axiosWrapper = async <Res, Req = Record<string, unknown>>({
  url,
  method,
  body,
  headers,
}: RequestOptions<Req>): Promise<[Res, null] | [null, Error | AxiosError]> => {
  const config: AxiosRequestConfig = {
    url,
    method,
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
    data: body,
  };

  try {
    const response = await axios<Res>(config);
    return [response.data, null];
  } catch (e) {
    const error = e as Error | AxiosError;
    return [null, error];
  }
};

export default axiosWrapper;
