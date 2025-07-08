type JSONPrimitive = string | number | boolean | null;
type JSONValue = JSONPrimitive | JSONObject | JSONArray;
interface JSONObject {
  [key: string]: JSONValue;
}
type JSONArray = Array<JSONValue>;

type JSONSafe = JSONValue | { [key: string]: JSONSafe } | JSONSafe[];

// Helper to stringify keys from Map, etc.
function safeKey(key: unknown): string {
  return typeof key === "string" ? key : `map:${String(key)}`;
}

export function toJSONSafe(value: unknown, seen = new WeakSet()): JSONSafe {
  if (value === null || typeof value !== "object") {
    if (typeof value === "bigint") {
      return value.toString();
    }
    if (typeof value === "undefined" || typeof value === "function") {
      return undefined as unknown as JSONSafe;
    }
    return value as JSONPrimitive;
  }

  if (seen.has(value)) {
    return "[Circular]";
  }
  seen.add(value);

  if (value instanceof Date) {
    return value.toISOString();
  }

  if (value instanceof Map) {
    const obj: JSONObject = {};
    for (const [k, v] of value.entries()) {
      obj[safeKey(k)] = toJSONSafe(v, seen);
    }
    return obj;
  }

  if (value instanceof Set) {
    return Array.from(value).map((v) => toJSONSafe(v, seen));
  }

  if (Array.isArray(value)) {
    return value.map((v) => toJSONSafe(v, seen));
  }

  const result: JSONObject = {};
  for (const key in value as Record<string, unknown>) {
    if (Object.prototype.hasOwnProperty.call(value, key)) {
      const safeVal = toJSONSafe((value as Record<string, unknown>)[key], seen);
      if (safeVal !== undefined) {
        result[key] = safeVal;
      }
    }
  }

  return result;
}
