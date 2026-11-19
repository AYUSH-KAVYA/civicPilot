export function getErrorMessage(error: unknown, fallback: string): string {
  if (typeof error === "object" && error !== null) {
    const candidate = error as {
      message?: unknown;
      response?: { data?: { error?: { message?: unknown } } };
    };
    const apiMessage = candidate.response?.data?.error?.message;
    if (typeof apiMessage === "string" && apiMessage.length > 0) return apiMessage;
    if (typeof candidate.message === "string" && candidate.message.length > 0) return candidate.message;
  }
  return fallback;
}