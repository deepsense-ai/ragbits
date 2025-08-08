export function isURL(input: string): boolean {
  if (isAbsoluteURL(input)) {
    return true;
  }

  return looksLikeRelativeURL(input) && isRelativeURL(input);
}

export function isAbsoluteURL(str: string): boolean {
  try {
    new URL(str);
    return true;
  } catch {
    return false;
  }
}

export function isRelativeURL(str: string): boolean {
  try {
    const DUMMY_BASE_URL = "http://base.local";
    new URL(str, DUMMY_BASE_URL);
    return true;
  } catch {
    return false;
  }
}

export function looksLikeRelativeURL(str: string): boolean {
  // Reject emojis, spaces, and unrelated strings.
  return /^[./~\w%-][\w./~%-]*$/.test(str);
}
