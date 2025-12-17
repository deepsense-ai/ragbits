import { Card, CardBody, Chip, ScrollShadow, Select, SelectItem } from "@heroui/react";
import { Icon } from "@iconify/react";
import { useEvalStore } from "../../stores/EvalStoreContext";
import { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ResponseChunk } from "../../types";

interface ResponsesViewProps {
  scenarioName: string | null;
}

// Chunk type configuration for styling
const CHUNK_TYPE_CONFIG: Record<
  string,
  { color: "primary" | "success" | "warning" | "secondary" | "danger" | "default"; icon: string; label: string }
> = {
  text: { color: "primary", icon: "heroicons:document-text", label: "Text" },
  reference: { color: "success", icon: "heroicons:bookmark", label: "Reference" },
  tool_call: { color: "warning", icon: "heroicons:wrench", label: "Tool Call" },
  usage: { color: "secondary", icon: "heroicons:chart-bar", label: "Usage" },
  live_update: { color: "primary", icon: "heroicons:arrow-path", label: "Live Update" },
  state_update: { color: "secondary", icon: "heroicons:cog", label: "State Update" },
  message_id: { color: "default", icon: "heroicons:identification", label: "Message ID" },
  conversation_id: { color: "default", icon: "heroicons:chat-bubble-oval-left", label: "Conversation ID" },
  conversation_summary: { color: "primary", icon: "heroicons:document-text", label: "Summary" },
  followup_messages: { color: "primary", icon: "heroicons:chat-bubble-left-right", label: "Follow-ups" },
  image: { color: "success", icon: "heroicons:photo", label: "Image" },
  chunked_content: { color: "secondary", icon: "heroicons:squares-2x2", label: "Chunked Content" },
  clear_message: { color: "default", icon: "heroicons:x-circle", label: "Clear Message" },
  todo_item: { color: "warning", icon: "heroicons:clipboard-document-list", label: "Todo Item" },
  confirmation_request: { color: "warning", icon: "heroicons:question-mark-circle", label: "Confirmation" },
  error: { color: "danger", icon: "heroicons:exclamation-triangle", label: "Error" },
  unknown: { color: "default", icon: "heroicons:question-mark-circle", label: "Unknown" },
};

function getChunkConfig(chunkType: string) {
  return CHUNK_TYPE_CONFIG[chunkType] || CHUNK_TYPE_CONFIG.unknown;
}

// Custom renderers for different chunk types
interface ChunkRendererProps {
  chunk: ResponseChunk;
}

function TextChunkRenderer({ chunk }: ChunkRendererProps) {
  const text = (chunk.chunk_data as { text?: string }).text || "";
  return (
    <div className="prose prose-sm dark:prose-invert max-w-none">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
    </div>
  );
}

function ReferenceChunkRenderer({ chunk }: ChunkRendererProps) {
  const data = chunk.chunk_data as { title?: string; content?: string; url?: string };
  return (
    <div className="space-y-2">
      <p className="font-medium">{data.title || "Reference"}</p>
      <p className="text-foreground-500 text-sm line-clamp-3">{data.content}</p>
      {data.url && (
        <a
          href={data.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-primary text-xs hover:underline inline-flex items-center gap-1"
        >
          <Icon icon="heroicons:arrow-top-right-on-square" className="text-xs" />
          View Source
        </a>
      )}
    </div>
  );
}

function ToolCallChunkRenderer({ chunk }: ChunkRendererProps) {
  const data = chunk.chunk_data as { name?: string; arguments?: unknown; result?: unknown };
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <span className="font-medium">{data.name || "Unknown Tool"}</span>
      </div>
      <details className="text-xs">
        <summary className="cursor-pointer text-foreground-500 hover:text-foreground">Arguments</summary>
        <pre className="mt-2 p-2 bg-default-100 rounded overflow-auto max-h-32">
          {JSON.stringify(data.arguments, null, 2)}
        </pre>
      </details>
      {data.result !== undefined && (
        <details className="text-xs">
          <summary className="cursor-pointer text-foreground-500 hover:text-foreground">Result</summary>
          <pre className="mt-2 p-2 bg-default-100 rounded overflow-auto max-h-32">
            {JSON.stringify(data.result, null, 2)}
          </pre>
        </details>
      )}
    </div>
  );
}

function UsageChunkRenderer({ chunk }: ChunkRendererProps) {
  const data = chunk.chunk_data as {
    prompt_tokens?: number;
    completion_tokens?: number;
    total_tokens?: number;
    estimated_cost?: number;
    n_requests?: number;
    usage?: Record<string, unknown>;
  };

  // Handle both direct usage and wrapped usage (UsageResponse)
  const usage = data.usage || data;

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs">
      {(usage as { prompt_tokens?: number }).prompt_tokens !== undefined && (
        <div className="p-2 bg-default-100 rounded">
          <span className="text-foreground-500 block">Prompt</span>
          <span className="font-medium">{(usage as { prompt_tokens: number }).prompt_tokens}</span>
        </div>
      )}
      {(usage as { completion_tokens?: number }).completion_tokens !== undefined && (
        <div className="p-2 bg-default-100 rounded">
          <span className="text-foreground-500 block">Completion</span>
          <span className="font-medium">{(usage as { completion_tokens: number }).completion_tokens}</span>
        </div>
      )}
      {(usage as { total_tokens?: number }).total_tokens !== undefined && (
        <div className="p-2 bg-default-100 rounded">
          <span className="text-foreground-500 block">Total</span>
          <span className="font-medium">{(usage as { total_tokens: number }).total_tokens}</span>
        </div>
      )}
      {(usage as { estimated_cost?: number }).estimated_cost !== undefined && (
        <div className="p-2 bg-default-100 rounded">
          <span className="text-foreground-500 block">Cost</span>
          <span className="font-medium">${(usage as { estimated_cost: number }).estimated_cost.toFixed(6)}</span>
        </div>
      )}
    </div>
  );
}

function LiveUpdateChunkRenderer({ chunk }: ChunkRendererProps) {
  const data = chunk.chunk_data as {
    update_id?: string;
    type?: string;
    content?: { label?: string; description?: string };
  };
  return (
    <div className="space-y-1">
      <div className="flex items-center gap-2">
        <Chip size="sm" variant="flat" color={data.type === "START" ? "primary" : "success"}>
          {data.type || "UPDATE"}
        </Chip>
        <span className="font-medium">{data.content?.label || "Live Update"}</span>
      </div>
      {data.content?.description && <p className="text-sm text-foreground-500">{data.content.description}</p>}
    </div>
  );
}

function ImageChunkRenderer({ chunk }: ChunkRendererProps) {
  const data = chunk.chunk_data as { id?: string; url?: string };
  return (
    <div className="space-y-2">
      {data.url ? (
        <img src={data.url} alt={data.id || "Image"} className="max-w-full h-auto rounded max-h-48 object-contain" />
      ) : (
        <p className="text-foreground-500">Image ID: {data.id}</p>
      )}
    </div>
  );
}

function FollowupMessagesChunkRenderer({ chunk }: ChunkRendererProps) {
  const data = chunk.chunk_data as { messages?: string[] };
  return (
    <div className="space-y-1">
      {data.messages?.map((msg, i) => (
        <div key={i} className="text-sm p-2 bg-default-100 rounded">
          {msg}
        </div>
      ))}
    </div>
  );
}

function ErrorChunkRenderer({ chunk }: ChunkRendererProps) {
  const data = chunk.chunk_data as { message?: string };
  return (
    <div className="text-danger">
      <p className="font-medium">Error</p>
      <p className="text-sm">{data.message || "Unknown error"}</p>
    </div>
  );
}

function TodoItemChunkRenderer({ chunk }: ChunkRendererProps) {
  const data = chunk.chunk_data as { task?: { title?: string; description?: string; status?: string } };
  return (
    <div className="space-y-1">
      <p className="font-medium">{data.task?.title || "Task"}</p>
      {data.task?.description && <p className="text-sm text-foreground-500">{data.task.description}</p>}
      {data.task?.status && (
        <Chip size="sm" variant="flat">
          {data.task.status}
        </Chip>
      )}
    </div>
  );
}

function ConfirmationRequestChunkRenderer({ chunk }: ChunkRendererProps) {
  const data = chunk.chunk_data as { confirmation_request?: { message?: string; tool_name?: string } };
  return (
    <div className="space-y-2 p-2 border border-warning rounded">
      <div className="flex items-center gap-2">
        <Icon icon="heroicons:exclamation-triangle" className="text-warning" />
        <span className="font-medium">Confirmation Required</span>
      </div>
      {data.confirmation_request?.tool_name && (
        <p className="text-sm">
          Tool: <span className="font-mono">{data.confirmation_request.tool_name}</span>
        </p>
      )}
      {data.confirmation_request?.message && <p className="text-sm text-foreground-500">{data.confirmation_request.message}</p>}
    </div>
  );
}

function DefaultChunkRenderer({ chunk }: ChunkRendererProps) {
  return (
    <pre className="text-xs p-2 bg-default-100 rounded overflow-auto max-h-48">
      {JSON.stringify(chunk.chunk_data, null, 2)}
    </pre>
  );
}

// Renderer registry - allows for custom renderers per type
const CHUNK_RENDERERS: Record<string, React.FC<ChunkRendererProps>> = {
  text: TextChunkRenderer,
  reference: ReferenceChunkRenderer,
  tool_call: ToolCallChunkRenderer,
  usage: UsageChunkRenderer,
  live_update: LiveUpdateChunkRenderer,
  image: ImageChunkRenderer,
  followup_messages: FollowupMessagesChunkRenderer,
  error: ErrorChunkRenderer,
  todo_item: TodoItemChunkRenderer,
  confirmation_request: ConfirmationRequestChunkRenderer,
};

function ChunkCard({ chunk }: { chunk: ResponseChunk }) {
  const config = getChunkConfig(chunk.chunk_type);
  const Renderer = CHUNK_RENDERERS[chunk.chunk_type] || DefaultChunkRenderer;

  return (
    <Card className="shadow-sm">
      <CardBody className="p-3">
        <div className="flex items-start gap-3">
          {/* Type indicator */}
          <div
            className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 bg-${config.color}/10`}
          >
            <Icon icon={config.icon} className={`text-${config.color} text-lg`} />
          </div>

          <div className="flex-1 min-w-0">
            {/* Header */}
            <div className="flex items-center gap-2 mb-2 flex-wrap">
              <Chip size="sm" color={config.color} variant="flat">
                {config.label}
              </Chip>
              <span className="text-xs text-foreground-500">
                Turn {chunk.turn_index + 1} • Task {chunk.task_index + 1}
              </span>
              <span className="text-xs text-foreground-400">#{chunk.chunk_index}</span>
            </div>

            {/* Content rendered by type-specific renderer */}
            <div className="text-sm">
              <Renderer chunk={chunk} />
            </div>
          </div>
        </div>
      </CardBody>
    </Card>
  );
}

export function ResponsesView({ scenarioName }: ResponsesViewProps) {
  const execution = useEvalStore((s) => (scenarioName ? s.executions[scenarioName] : null));
  const [filterType, setFilterType] = useState<string>("all");

  // Get unique chunk types for filter dropdown
  const uniqueTypes = useMemo(() => {
    if (!execution?.responseChunks) return [];
    const types = new Set(execution.responseChunks.map((c) => c.chunk_type));
    return Array.from(types).sort();
  }, [execution?.responseChunks]);

  // Filter chunks
  const filteredChunks = useMemo(() => {
    if (!execution?.responseChunks) return [];
    if (filterType === "all") return execution.responseChunks;
    return execution.responseChunks.filter((c) => c.chunk_type === filterType);
  }, [execution?.responseChunks, filterType]);

  if (!scenarioName) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-8 text-center">
        <Icon icon="heroicons:squares-2x2" className="text-6xl text-foreground-300 mb-4" />
        <h2 className="text-lg font-medium text-foreground">Select a Scenario</h2>
        <p className="text-sm text-foreground-500 mt-2">Click on a scenario to view its response stream</p>
      </div>
    );
  }

  if (!execution || execution.responseChunks.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-8 text-center">
        <Icon icon="heroicons:clock" className="text-6xl text-foreground-300 mb-4" />
        <h2 className="text-lg font-medium text-foreground">{execution ? "No Response Chunks Yet" : "Not Started"}</h2>
        <p className="text-sm text-foreground-500 mt-2">
          {execution ? "Waiting for response stream..." : "Run the scenario to see response chunks"}
        </p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Filter Controls */}
      <div className="border-b border-divider px-6 py-3">
        <div className="flex items-center gap-4 flex-wrap">
          <span className="text-sm text-foreground-500">Filter by type:</span>
          <Select
            size="sm"
            selectedKeys={[filterType]}
            onSelectionChange={(keys) => setFilterType(Array.from(keys)[0] as string)}
            className="w-48"
            aria-label="Filter chunk type"
            items={[
              { key: "all", label: `All Types (${execution.responseChunks.length})` },
              ...uniqueTypes.map((type) => ({
                key: type,
                label: `${getChunkConfig(type).label} (${execution.responseChunks.filter((c) => c.chunk_type === type).length})`,
              })),
            ]}
          >
            {(item) => <SelectItem key={item.key}>{item.label}</SelectItem>}
          </Select>
          <span className="text-sm text-foreground-500">
            Showing {filteredChunks.length} of {execution.responseChunks.length} chunks
          </span>
        </div>
      </div>

      {/* Chunks List */}
      <ScrollShadow className="flex-1">
        <div className="p-6 space-y-3">
          {filteredChunks.map((chunk) => (
            <ChunkCard key={`${chunk.turn_index}-${chunk.chunk_index}`} chunk={chunk} />
          ))}
        </div>
      </ScrollShadow>
    </div>
  );
}
