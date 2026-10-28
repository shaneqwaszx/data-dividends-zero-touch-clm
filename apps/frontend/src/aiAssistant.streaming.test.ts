// @vitest-environment node
import { afterEach, expect, it, vi } from "vitest";
import { askAiAssistantStreaming } from "./aiAssistant";

afterEach(() => vi.unstubAllGlobals());

it("rejects an oversized unterminated NDJSON stream and cancels its reader", async () => {
  const cancel = vi.fn();
  let chunks = 0;
  const body = new ReadableStream<Uint8Array>({
    pull(controller) {
      if (++chunks < 1026) controller.enqueue(new TextEncoder().encode("x".repeat(1024)));
      else controller.close();
    }, cancel,
  });
  vi.stubGlobal("fetch", vi.fn(async () => new Response(body, {
    headers: { "Content-Type": "application/x-ndjson" },
  })));
  await expect(askAiAssistantStreaming("case", "why", [], vi.fn())).rejects.toThrow(/limit/i);
  expect(cancel).toHaveBeenCalledTimes(1);
  expect(chunks).toBeLessThan(1026);
});


const answer = { answer: "café 🌍", answered_by: "model", model: "synthetic", notice: null,
  suggested_questions: ["Next?"] };
const done = JSON.stringify({ type: "done", ...answer }) + "\n";

function respond(chunks: Uint8Array[], contentType = "application/x-ndjson") {
  const cancel = vi.fn();
  let reads = 0;
  const body = new ReadableStream<Uint8Array>({ pull(controller) {
    if (reads < chunks.length) controller.enqueue(chunks[reads++]);
    else controller.close();
  }, cancel });
  vi.stubGlobal("fetch", vi.fn(async () => new Response(body, {
    headers: { "Content-Type": contentType },
  })));
  return { cancel, reads: () => reads };
}
const bytes = (text: string) => new TextEncoder().encode(text);

it("preserves fragmented UTF-8, text replacement and done; cancels trailing traffic", async () => {
  const text = JSON.stringify({ type: "text", text: answer.answer }) + "\n";
  const stream = respond([...bytes(text + done)].map((byte) => new Uint8Array([byte]))
    .concat([bytes("unread trailing traffic") ]));
  const onText = vi.fn();
  await expect(askAiAssistantStreaming("case", "why", [], onText)).resolves.toEqual(answer);
  expect(onText.mock.calls).toEqual([[answer.answer]]);
  expect(stream.cancel).toHaveBeenCalledTimes(1);
});

it.each(["{broken}\n", '{"type":"text","text":8}\n', "null\n", done.trimEnd(),
  '{"type":"done","answer":"fake success"}\n'])
("contains malformed/incomplete NDJSON without manufacturing completion: %s", async (body) => {
  const stream = respond([bytes(body)]);
  await expect(askAiAssistantStreaming("case", "why", [], vi.fn())).rejects.toThrow();
  expect(stream.cancel.mock.calls.length).toBeLessThanOrEqual(1);
});

it("bounds many small valid events independently of the line limit", async () => {
  const chunk = bytes(JSON.stringify({ type: "text", text: "x".repeat(1000) }) + "\n");
  const stream = respond([...Array<Uint8Array>(2200).fill(chunk), bytes(done)]);
  await expect(askAiAssistantStreaming("case", "why", [], vi.fn())).rejects.toThrow(/limit/);
  expect(stream.reads()).toBeLessThan(2200);
  expect(stream.cancel).toHaveBeenCalledTimes(1);
});

it("bounds the non-NDJSON compatibility response too", async () => {
  respond([bytes("x".repeat(128 * 1024 + 1))], "text/plain");
  await expect(askAiAssistantStreaming("case", "why", [], vi.fn())).rejects.toThrow(/limit/);
});

it("keeps the bounded non-stream compatibility answer", async () => {
  respond([bytes(JSON.stringify(answer))], "application/json");
  await expect(askAiAssistantStreaming("case", "why", [], vi.fn())).resolves.toEqual(answer);
});

it("abort cancels a pending read and publishes no late text or completion", async () => {
  const controller = new AbortController();
  const cancel = vi.fn();
  let started!: () => void;
  const reading = new Promise<void>((resolve) => { started = resolve; });
  const body = new ReadableStream<Uint8Array>({ pull() { started(); }, cancel });
  vi.stubGlobal("fetch", vi.fn(async () => new Response(body, {
    headers: { "Content-Type": "application/x-ndjson" },
  })));
  const onText = vi.fn();
  const pending = askAiAssistantStreaming("old-case", "why", [], onText, controller.signal);
  await reading;
  controller.abort();
  await expect(pending).rejects.toMatchObject({ name: "AbortError" });
  expect(cancel).toHaveBeenCalledTimes(1);
  expect(onText).not.toHaveBeenCalled();
});

it("abort during text delivery cannot return a queued done for a replacement actor/case", async () => {
  const controller = new AbortController();
  respond([bytes(JSON.stringify({ type: "text", text: "old case" }) + "\n" + done)]);
  const onText = vi.fn(() => controller.abort());
  await expect(askAiAssistantStreaming("old-case", "why", [], onText, controller.signal))
    .rejects.toMatchObject({ name: "AbortError" });
  expect(onText).toHaveBeenCalledTimes(1);
});


it("rejects invalid UTF-8 before a text callback", async () => {
  respond([new Uint8Array([0xc3, 10])]);
  const onText = vi.fn();
  await expect(askAiAssistantStreaming("case", "why", [], onText)).rejects.toThrow(/read/);
  expect(onText).not.toHaveBeenCalled();
});

it("EOF after legitimate text cannot silently become a successful done", async () => {
  const onText = vi.fn();
  respond([bytes(JSON.stringify({ type: "text", text: answer.answer }) + "\n")]);
  await expect(askAiAssistantStreaming("case", "why", [], onText)).rejects.toThrow(/stopped/);
  expect(onText.mock.calls).toEqual([[answer.answer]]);
});

it("reports the reply starting once, before its text, and never after an abort", async () => {
  const order: string[] = [];
  respond([bytes(JSON.stringify({ type: "text", text: "line" }) + "\n" + done)]);
  await askAiAssistantStreaming("case", "why", [], () => order.push("text"), undefined, [], () => order.push("connected"));
  expect(order).toEqual(["connected", "text"]);

  const controller = new AbortController();
  const cancel = vi.fn();
  const body = new ReadableStream<Uint8Array>({ cancel });
  const connected = vi.fn();
  vi.stubGlobal("fetch", vi.fn(async () => {
    controller.abort();
    return new Response(body, { headers: { "Content-Type": "application/x-ndjson" } });
  }));
  await expect(askAiAssistantStreaming("case", "why", [], vi.fn(), controller.signal, [], connected))
    .rejects.toMatchObject({ name: "AbortError" });
  expect(connected).not.toHaveBeenCalled();
  expect(cancel).toHaveBeenCalledTimes(1);
});
