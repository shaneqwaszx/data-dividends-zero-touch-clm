// @vitest-environment node
import { afterEach, expect, it, vi } from "vitest";
import { AiAssistantError, askAiAssistant, askAiAssistantStreaming, fetchAiAssistantBrief } from "./aiAssistant";
import { configureAuthenticatedTransport } from "./api";

const bytes = (text: string) => new TextEncoder().encode(text);
const streamAsk = (signal?: AbortSignal) => askAiAssistantStreaming("case", "why", [], vi.fn(), signal);
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  configureAuthenticatedTransport({ csrfToken: null, onUnauthorized: null });
});
function source(parts: Uint8Array[], status = 503) {
  const cancel = vi.fn();
  let reads = 0;
  const body = new ReadableStream<Uint8Array>({ pull(controller) {
    if (reads < parts.length) controller.enqueue(parts[reads++]);
    else controller.close();
  }, cancel }, { highWaterMark: 0 });
  vi.stubGlobal("fetch", vi.fn(async () => new Response(body, { status,
    headers: { "Content-Type": "application/json", "Content-Length": "1" } })));
  return { body, cancel, reads: () => reads };
}

it.each(["valid JSON", "unterminated JSON", "many chunks"])("bounds HTTP503 %s before parsing, ignoring Content-Length", async (kind) => {
  const parts = kind === "many chunks" ? Array.from({ length: 3073 }, () => bytes(" ".repeat(1024)))
    : [bytes('{"detail":{"message":"'), ...Array.from({ length: 3073 }, () => bytes("x".repeat(1024))),
      ...(kind === "valid JSON" ? [bytes('"}}')] : [])];
  const s = source(parts);
  const error = await streamAsk().catch((error: unknown) => error) as AiAssistantError;
  expect(error).toBeInstanceOf(AiAssistantError);
  expect(error.status).toBe(503);
  expect(error.message.length).toBeLessThanOrEqual(256);
  expect(s.reads()).toBeLessThanOrEqual(18);
  expect(s.cancel).toHaveBeenCalledTimes(1);
  expect(s.body.locked).toBe(false);
});

it.each(["brief", "chat"])("bounds adjacent successful %s JSON consumption", async (kind) => {
  const s = source([bytes('{"answer":"'), ...Array.from({ length: 3073 }, () => bytes("x".repeat(1024))), bytes('"}')], 200);
  const pending = kind === "brief" ? fetchAiAssistantBrief("case") : askAiAssistant("case", "why", []);
  await expect(pending).rejects.toThrow(/limit/);
  expect(s.reads()).toBeLessThanOrEqual(130);
  expect(s.cancel).toHaveBeenCalledTimes(1);
  expect(s.body.locked).toBe(false);
});

it.each([401, 403, 404, 502, 503])("retains HTTP%s status with a bounded safe fallback", async (status) => {
  source([bytes('{"detail":{"message":"private provider diagnostic"}}')], status);
  const error = await streamAsk().catch((error: unknown) => error) as AiAssistantError;
  expect(error.status).toBe(status);
  expect(error.message).not.toContain("private");
  expect(error.message.length).toBeLessThanOrEqual(256);
});

it.each(["Please sign in again.", "This case was not found.", "Request origin not allowed.",
  "The onboarding app could not be reached.", "The onboarding app could not provide this case.",
  "The onboarding app returned an unreadable reply.", "The onboarding app returned an unexpected reply."])
("preserves trusted small service message: %s", async (message) => {
  const s = source([bytes(JSON.stringify({ detail: { message } }))]);
  await expect(streamAsk()).rejects.toMatchObject({ status: 503, message });
  expect(s.body.locked).toBe(false);
});

it.each([bytes("{broken"), bytes("null"), bytes('[1]'), new Uint8Array([0xc3, 0x28]),
  bytes('{"detail":{"message":4}}'), bytes('{"detail":{"message":"' + "x".repeat(300) + '"}}')])
("contains malformed, invalid UTF8 and unsafe error messages", async (part) => {
  source([part]);
  await expect(streamAsk()).rejects.toMatchObject({ status: 503,
    message: "The AI assistant service is unavailable right now." });
});

it("missing error body retains HTTP status", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(null, { status: 404 })));
  await expect(streamAsk()).rejects.toMatchObject({ status: 404, message: "This case was not found." });
});

it.each(["stalled", "trickle"])("absolute error deadline bounds %s body and releases listeners", async (kind) => {
  vi.useFakeTimers();
  const controller = new AbortController();
  const add = vi.spyOn(controller.signal, "addEventListener");
  const remove = vi.spyOn(controller.signal, "removeEventListener");
  const cancel = vi.fn();
  let reads = 0;
  const body = new ReadableStream<Uint8Array>({
    async pull(c) {
      reads++;
      await new Promise((resolve) => setTimeout(resolve, kind === "trickle" ? 1000 : 6000));
      if (controller.signal.aborted) return;
      try {
        if (kind === "trickle" && reads < 7) c.enqueue(bytes(" "));
        else c.close();
      } catch { /* cancellation closes the synthetic producer */ }
    }, cancel,
  }, { highWaterMark: 0 });
  vi.stubGlobal("fetch", vi.fn(async () => new Response(body, { status: 503 })));
  const pending = streamAsk(controller.signal).catch((error: unknown) => error);
  await vi.advanceTimersByTimeAsync(5001);
  expect(cancel).toHaveBeenCalledTimes(1);
  const error = await pending as AiAssistantError;
  expect(error.status).toBe(503);
  expect(body.locked).toBe(false);
  expect(remove.mock.calls.length).toBe(add.mock.calls.length);
  controller.abort();
  expect(vi.getTimerCount()).toBeLessThanOrEqual(1); // only the finite producer's timer may remain
});

it("abort during error reading cancels the source, releases lock and preserves AbortError", async () => {
  const controller = new AbortController();
  const cancel = vi.fn();
  let ready!: () => void;
  const reading = new Promise<void>((resolve) => { ready = resolve; });
  const body = new ReadableStream<Uint8Array>({ pull() { ready(); }, cancel });
  vi.stubGlobal("fetch", vi.fn(async () => new Response(body, { status: 503 })));
  const pending = streamAsk(controller.signal);
  await reading;
  controller.abort();
  await expect(pending).rejects.toMatchObject({ name: "AbortError" });
  expect(cancel).toHaveBeenCalledTimes(1);
  expect(body.locked).toBe(false);
});

it("current 401 expires session before a stalled error read; old 401 cannot expire replacement", async () => {
  const expired = vi.fn();
  configureAuthenticatedTransport({ csrfToken: null, onUnauthorized: expired });
  source([bytes('{}')], 401);
  await expect(streamAsk()).rejects.toMatchObject({ status: 401 });
  expect(expired).toHaveBeenCalledTimes(1);
  let finish!: (r: Response) => void;
  vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>((resolve) => { finish = resolve; })));
  const old = streamAsk();
  const replacement = vi.fn();
  configureAuthenticatedTransport({ csrfToken: null, onUnauthorized: replacement });
  finish(new Response('{}', { status: 401 }));
  await expect(old).rejects.toMatchObject({ status: 401 });
  expect(replacement).not.toHaveBeenCalled();
  expect(expired).toHaveBeenCalledTimes(1);
});

it("keeps valid brief and explicit chat JSON with fragmented UTF8", async () => {
  const brief = { company: "café", message: "Current case", suggested_questions: [], blocker_count: 0, steps_done: 0, steps_total: 1 };
  source([...bytes(JSON.stringify(brief))].map((b) => new Uint8Array([b])), 200);
  await expect(fetchAiAssistantBrief("case")).resolves.toEqual(brief);
  const answer = { answer: "café 🌍", answered_by: "model", model: "synthetic", notice: null, suggested_questions: [] };
  source([bytes(JSON.stringify(answer))], 200);
  await expect(askAiAssistant("case", "why", [])).resolves.toEqual(answer);
});

it("does not wait for a hostile cancellation promise after the error budget", async () => {
  const body = new ReadableStream<Uint8Array>({
    pull(c) { c.enqueue(bytes("x".repeat(16385))); },
    cancel() { return new Promise<void>(() => undefined); },
  });
  vi.stubGlobal("fetch", vi.fn(async () => new Response(body, { status: 503 })));
  await expect(streamAsk()).rejects.toMatchObject({ status: 503 });
  expect(body.locked).toBe(false);
});

it.each([bytes("{broken"), new Uint8Array([0xc3, 0x28])])("rejects invalid successful JSON safely", async (part) => {
  const s = source([part], 200);
  await expect(fetchAiAssistantBrief("case")).rejects.toMatchObject({
    message: "The AI assistant could not read its answer." });
  expect(s.body.locked).toBe(false);
});

it("aborted signal at headers cancels an error body without reading it", async () => {
  const controller = new AbortController();
  const s = source([bytes("late diagnostic")]);
  controller.abort();
  await expect(streamAsk(controller.signal)).rejects.toMatchObject({ name: "AbortError" });
  expect(s.reads()).toBe(0);
  expect(s.cancel).toHaveBeenCalledTimes(1);
  expect(s.body.locked).toBe(false);
});

it("successful finite JSON deadline cancels a pending body too", async () => {
  vi.useFakeTimers();
  const cancel = vi.fn();
  const body = new ReadableStream<Uint8Array>({ pull() { /* stalls */ }, cancel });
  vi.stubGlobal("fetch", vi.fn(async () => new Response(body)));
  const pending = fetchAiAssistantBrief("case").catch((error: unknown) => error);
  await vi.advanceTimersByTimeAsync(5001);
  expect(await pending).toBeInstanceOf(AiAssistantError);
  expect(cancel).toHaveBeenCalledTimes(1);
  expect(body.locked).toBe(false);
  expect(vi.getTimerCount()).toBe(0);
});
