/**
 * WebSocket helpers with exponential backoff reconnect per §10b.3.
 * Backoff: 1s, 2s, 4s, 8s cap. Reset on successful open.
 */

import { WS_URL, loadToken } from "./api";

export type WSHandle = {
  send: (data: string | ArrayBufferLike | Blob) => void;
  close: () => void;
};

type Options = {
  onMessage?: (ev: MessageEvent) => void;
  onOpen?: () => void;
  onClose?: () => void;
};

function connect(route: string, sessionId: string, opts: Options): WSHandle {
  let attempt = 0;
  let ws: WebSocket | null = null;
  let closed = false;
  const queue: (string | ArrayBufferLike | Blob)[] = [];

  const url = (() => {
    const token = loadToken(sessionId) ?? "";
    return `${WS_URL}${route}?session_id=${sessionId}&token=${encodeURIComponent(token)}`;
  });

  const open = () => {
    if (closed) return;
    ws = new WebSocket(url());

    ws.onopen = () => {
      attempt = 0;
      while (queue.length && ws?.readyState === WebSocket.OPEN) {
        ws.send(queue.shift()!);
      }
      opts.onOpen?.();
    };
    if (opts.onMessage) ws.onmessage = opts.onMessage;
    ws.onclose = () => {
      opts.onClose?.();
      if (closed) return;
      attempt += 1;
      const delay = Math.min(1000 * 2 ** (attempt - 1), 8000);
      setTimeout(open, delay);
    };
    ws.onerror = () => {
      /* swallow — onclose handles reconnect */
    };
  };

  open();

  return {
    send(data) {
      if (ws?.readyState === WebSocket.OPEN) ws.send(data);
      else queue.push(data);
    },
    close() {
      closed = true;
      ws?.close();
    },
  };
}

export const connectVideo = (sessionId: string, opts: Options = {}) =>
  connect("/video-stream", sessionId, opts);
export const connectAudio = (sessionId: string, opts: Options = {}) =>
  connect("/audio-stream", sessionId, opts);
export const connectFeedback = (sessionId: string, opts: Options = {}) =>
  connect("/realtime-feedback", sessionId, opts);
