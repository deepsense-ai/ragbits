export const createEventSource = <T>(
  url: string,
  onMessage: (data: T) => void,
  onError: () => void,
) => {
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
};
