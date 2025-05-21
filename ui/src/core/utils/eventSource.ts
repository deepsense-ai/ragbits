import axios, { AxiosInstance, AxiosResponse, isAxiosError } from "axios";
import { ChatResponse, ChatResponseType, RequestConfig } from "../../types/api";
import { isChatResponse } from "./api";

// TODO: Change this messages to some generic error messages
const SERVER_ERROR_MESSAGE =
  "There was an error processing your request. Please try resending your message shortly.";
const CONNECTION_ERROR_MESSAGE =
  "There was an error connecting to the server. Please check your internet connection and try sending your message again.";

async function handleError(
  error: unknown,
  onError: (error?: string) => void | Promise<void>,
): Promise<void> {
  if (!isAxiosError(error)) {
    await onError(CONNECTION_ERROR_MESSAGE);
    return;
  }
  if (error.response) {
    console.error("Error response:", error.response.data);
    await onError(SERVER_ERROR_MESSAGE);
    return;
  }
  if (error.request) {
    console.error("Error request:", error.request);
    await onError(CONNECTION_ERROR_MESSAGE);
    return;
  }
}

export async function* chunkMessage(
  response: ChatResponse,
): AsyncGenerator<ChatResponse> {
  // When response is too long, chunk it into smaller parts to simulate streaming
  if (response.type !== ChatResponseType.TEXT) {
    yield response;
    return;
  }

  const chunkSize = 15;
  const text = response.content;

  const totalChunks = Math.ceil(text.length / chunkSize);

  if (totalChunks === 1) {
    yield response;
    return;
  }

  for (let i = 0; i < totalChunks; i++) {
    const start = i * chunkSize;
    const end = Math.min(start + chunkSize, text.length);
    const chunk = text.slice(start, end);

    yield {
      content: chunk,
      type: ChatResponseType.TEXT,
    };

    // Random delay between 30ms and 50ms to simulate streaming
    const delay = Math.floor(Math.random() * 20) + 30;
    await new Promise((resolve) => setTimeout(resolve, delay));
  }
}

async function handleStream(
  response: AxiosResponse<ReadableStream>,
  onMessage: (data: ChatResponse) => void | Promise<void>,
  onError: (error?: string) => void | Promise<void>,
  onClose?: () => void | Promise<void>,
  isCancelledRef?: { value: boolean },
): Promise<void> {
  const stream = response.data;
  const reader = stream.pipeThrough(new TextDecoderStream()).getReader();

  async function processChunk({
    value,
    done,
  }: ReadableStreamReadResult<string>): Promise<void> {
    if (done || isCancelledRef?.value) {
      await onClose?.();
      return;
    }

    const lines = value.split("\n");
    if (!lines.length) {
      console.error("Received empty message");
      await onError(SERVER_ERROR_MESSAGE);
      return;
    }

    for (const line of lines) {
      if (!line.startsWith("data: ")) {
        continue;
      }
      try {
        const jsonString = line.replace("data: ", "").trim();
        const parsedValue = JSON.parse(jsonString) as unknown;
        if (!isChatResponse(parsedValue)) {
          console.error("Invalid data format:", parsedValue);
          await onError(SERVER_ERROR_MESSAGE);
          return;
        }

        const chunks = chunkMessage(parsedValue);
        for await (const chunk of chunks) {
          if (isCancelledRef?.value) {
            await onClose?.();
            return;
          }

          await onMessage(chunk);
        }
      } catch (parseError) {
        console.error("Error parsing JSON:", parseError);
        await onError(SERVER_ERROR_MESSAGE);
        return;
      }
    }

    try {
      const nextChunk = await reader.read();
      await processChunk(nextChunk);
    } catch (readError) {
      await handleError(readError, onError);
    }
  }

  try {
    const initialChunk = await reader.read();
    await processChunk(initialChunk);
  } catch (streamError) {
    await handleError(streamError, onError);
  }
}

export function createEventSource<T extends object>(
  url: string,
  onMessage: (data: ChatResponse) => void | Promise<void>,
  onError: (error?: string) => void | Promise<void>,
  onClose?: () => void | Promise<void>,
  config: RequestConfig<T> = { method: "GET" },
): () => void {
  const axiosClient = createAxiosStreamingClient();
  const { method, body } = config;
  const message = body ? JSON.stringify(body) : null;
  const isCancelledRef = { value: false };

  const request = async () => {
    try {
      let response: AxiosResponse<ReadableStream>;
      if (method === "GET") {
        response = await axiosClient.get(url);
      } else if (method === "POST") {
        response = await axiosClient.post(url, message);
      } else {
        throw new Error("Invalid method. Use GET or POST.");
      }

      await handleStream(response, onMessage, onError, onClose, isCancelledRef);
    } catch (err) {
      await handleError(err, onError);
    }
  };

  void request();

  return () => {
    isCancelledRef.value = true;
  };
}

function createAxiosStreamingClient(): AxiosInstance {
  return axios.create({
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    responseType: "stream",
    adapter: "fetch",
  });
}
