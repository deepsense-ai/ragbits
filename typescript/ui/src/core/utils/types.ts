export function exhaustiveGuard(_value: never): never {
  throw new Error(`Unhandled value: ${JSON.stringify(_value)}`);
}
