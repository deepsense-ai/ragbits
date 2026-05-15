export interface PreSendContribution {
  context?: Record<string, unknown>;
  userMessageExtra?: Record<string, unknown>;
  files?: File[];
}

type Contributor = () => PreSendContribution | null;

const contributors = new Set<Contributor>();

export function registerPreSendContributor(c: Contributor): () => void {
  contributors.add(c);
  return () => {
    contributors.delete(c);
  };
}

export function collectPreSendContext(): PreSendContribution {
  let context: Record<string, unknown> | undefined;
  let userMessageExtra: Record<string, unknown> | undefined;
  const files: File[] = [];
  for (const c of contributors) {
    const r = c();
    if (!r) continue;
    if (r.context) context = { ...(context ?? {}), ...r.context };
    if (r.userMessageExtra) {
      userMessageExtra = { ...(userMessageExtra ?? {}), ...r.userMessageExtra };
    }
    if (r.files && r.files.length > 0) files.push(...r.files);
  }
  return {
    context,
    userMessageExtra,
    files: files.length > 0 ? files : undefined,
  };
}
