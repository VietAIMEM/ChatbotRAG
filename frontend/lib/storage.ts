const CLIENT_ID_KEY = "pgrag_client_id";
const CONVERSATION_ID_KEY = "pgrag_conversation_id";

export function generateUuid(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export function getClientId(): string {
  if (typeof window === "undefined") return "";
  let value = window.localStorage.getItem(CLIENT_ID_KEY);
  if (!value) {
    value = generateUuid();
    window.localStorage.setItem(CLIENT_ID_KEY, value);
  }
  return value;
}

export function getCurrentConversationId(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(CONVERSATION_ID_KEY);
}

export function setCurrentConversationId(value: string | null): void {
  if (typeof window === "undefined") return;
  if (value) {
    window.localStorage.setItem(CONVERSATION_ID_KEY, value);
  } else {
    window.localStorage.removeItem(CONVERSATION_ID_KEY);
  }
}
