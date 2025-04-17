import axios, { AxiosResponse } from "axios";
import { ChatResponse } from "../../types/api";

export const createEventSource = <T extends object>(
  url: string,
  onMessage: (data: ChatResponse) => void,
  onError: () => void,
  onClose?: () => void,
  config: {
    method: "GET" | "POST";
    body?: T;
  } = { method: "GET" },
) => {
  const axiosClient = axios.create({
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    responseType: "stream",
    adapter: "fetch",
  });

  const { method, body } = config;
  const message = body ? JSON.stringify(body) : null;

  let isCancelled = false;
  const handleStream = async (response: AxiosResponse) => {
    const stream = response.data;
    const reader: ReadableStreamDefaultReader<string> = stream
      .pipeThrough(new TextDecoderStream())
      .getReader();

    while (true) {
      const { value, done } = await reader.read();
      if (done || isCancelled) {
        onClose?.();
        return;
      }

      const lines = value.split("\n");

      if (lines.length === 0) {
        console.error("Received empty message");
        onError();
        return;
      }

      for (const line of lines) {
        if (!line.startsWith("data: ")) {
          continue;
        }

        try {
          const jsonString = line.replace("data: ", "").trim();
          const parsedValue = JSON.parse(jsonString);
          onMessage(parsedValue);
        } catch (error) {
          console.error("Error parsing JSON:", error);
          onError();
        }
      }
    }
  };

  const handleError = (error: Error) => {
    console.error("Error in createEventSource:", error);
    onError();
  };

  if (method === "GET") {
    axiosClient.get(url).then(handleStream).catch(handleError);
  } else if (method === "POST") {
    axiosClient.post(url, message).then(handleStream).catch(handleError);
  } else {
    throw new Error("Invalid method. Use GET or POST.");
  }

  return () => {
    isCancelled = true;
  };
};
