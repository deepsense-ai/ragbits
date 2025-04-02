import axios from "axios";
import { ChatResponse } from "../../types/api";

export const createEventSource = (
  url: string,
  onMessage: (data: ChatResponse) => void,
  onError: () => void,
  config: {
    method: "GET" | "POST";
    body?: Record<string, unknown>;
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

  if (method === "GET") {
    const eventSource = new EventSource(url);

    eventSource.onmessage = (event) => {
      const { data } = event;
      onMessage(data);
    };

    eventSource.onerror = (error) => {
      console.error("EventSource failed:", error);
      eventSource.close();
      onError();
    };

    return () => {
      eventSource.close();
    };
  }

  if (method === "POST") {
    let isCancelled = false;

    axiosClient
      .post(url, message)
      .then(async (response) => {
        const stream = response.data;
        const reader: ReadableStreamDefaultReader<string> = stream
          .pipeThrough(new TextDecoderStream())
          .getReader();

        while (true) {
          const { value, done } = await reader.read();
          if (done || isCancelled) break;

          if (!value) {
            console.error("Received empty message");
            onError();
            return;
          }

          try {
            // Parse the value
            const jsonData = value.split("data: ")[1];
            if (!jsonData) {
              console.error("Invalid message format");
              onError();
              return;
            }

            const parsedValue = JSON.parse(jsonData);
            onMessage(parsedValue);
          } catch (error) {
            console.error("Error parsing JSON:", error);
            onError();
          }
        }
      })
      .catch((error) => {
        console.error("Error in createEventSource:", error);
        onError();
      });

    return () => {
      isCancelled = true;
    };
  }

  throw new Error("Invalid method. Use GET or POST.");
};
