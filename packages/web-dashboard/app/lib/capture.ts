/**
 * Browser capture per §10b.8:
 *   getUserMedia → OffscreenCanvas (320×240) → JPEG @ 0.7 → WS binary frame
 *   Cadence: 200ms (5fps source)
 *
 * Audio: getUserMedia(mic) → AudioWorklet → PCM 16-bit 16kHz → 2s chunks
 */

export type CaptureHandles = {
  stop: () => void;
};

export async function startVideoCapture(
  videoEl: HTMLVideoElement,
  sendFrame: (bytes: ArrayBuffer) => void,
): Promise<CaptureHandles> {
  const stream = await navigator.mediaDevices.getUserMedia({ video: true });
  videoEl.srcObject = stream;
  await videoEl.play();

  const off = new OffscreenCanvas(320, 240);
  const ctx = off.getContext("2d")!;
  const tick = setInterval(async () => {
    ctx.drawImage(videoEl, 0, 0, 320, 240);
    const blob = await off.convertToBlob({ type: "image/jpeg", quality: 0.7 });
    sendFrame(await blob.arrayBuffer());
  }, 200);

  return {
    stop: () => {
      clearInterval(tick);
      stream.getTracks().forEach((t) => t.stop());
    },
  };
}

export async function startAudioCapture(
  sendChunk: (bytes: ArrayBuffer) => void,
  chunkSeconds = 2,
): Promise<CaptureHandles> {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const AudioContextCtor =
    (window as unknown as { AudioContext?: typeof AudioContext; webkitAudioContext?: typeof AudioContext })
      .AudioContext ??
    (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
  const ctx = new AudioContextCtor({ sampleRate: 16000 });
  const source = ctx.createMediaStreamSource(stream);

  // ScriptProcessor is deprecated but the simplest cross-browser path for a scaffold.
  // Phase 1+: replace with an AudioWorklet for jank-free capture.
  const proc = ctx.createScriptProcessor(4096, 1, 1);
  source.connect(proc);
  proc.connect(ctx.destination);

  const samplesPerChunk = 16000 * chunkSeconds;
  let buf = new Int16Array(samplesPerChunk);
  let written = 0;

  proc.onaudioprocess = (ev) => {
    const input = ev.inputBuffer.getChannelData(0);
    for (let i = 0; i < input.length; i += 1) {
      const s = Math.max(-1, Math.min(1, input[i]));
      buf[written++] = s < 0 ? s * 0x8000 : s * 0x7fff;
      if (written >= samplesPerChunk) {
        sendChunk(buf.buffer);
        buf = new Int16Array(samplesPerChunk);
        written = 0;
      }
    }
  };

  return {
    stop: () => {
      proc.disconnect();
      source.disconnect();
      ctx.close().catch(() => undefined);
      stream.getTracks().forEach((t) => t.stop());
    },
  };
}
