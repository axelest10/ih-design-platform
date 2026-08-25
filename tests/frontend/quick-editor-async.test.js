const assert = require("node:assert/strict");
const test = require("node:test");

const { waitForResult } = require("../../frontend/scripts/async-generation.js");

const response = (payload, ok = true) => ({
  ok,
  json: async () => payload,
});

test("resolves the asynchronous quick-design result before preview access", async () => {
  const jobs = [
    { status: "queued", result: null },
    { status: "processing", result: null },
    {
      status: "succeeded",
      result: { preview: { html: "<!doctype html><p>Diseño listo</p>" } },
    },
  ];
  const requestedUrls = [];

  const result = await waitForResult(
    {
      task_id: "quick-design-task",
      status: "processing",
      status_url: "https://example.test/api/v1/tasks/quick-design-task/",
    },
    {
      request: async (url) => {
        requestedUrls.push(url);
        return response(jobs.shift());
      },
      wait: async () => {},
    },
  );

  assert.equal(result.preview.html, "<!doctype html><p>Diseño listo</p>");
  assert.deepEqual(requestedUrls, [
    "https://example.test/api/v1/tasks/quick-design-task/",
    "https://example.test/api/v1/tasks/quick-design-task/",
    "https://example.test/api/v1/tasks/quick-design-task/",
  ]);
});

test("keeps the synchronous quick-design response unchanged", async () => {
  const directResult = { preview: { html: "<!doctype html><p>Directo</p>" } };
  let requests = 0;

  const result = await waitForResult(directResult, {
    request: async () => {
      requests += 1;
      return response({});
    },
  });

  assert.equal(result, directResult);
  assert.equal(requests, 0);
});

test("reports the persisted asynchronous job error", async () => {
  await assert.rejects(
    waitForResult(
      { status: "processing", status_url: "https://example.test/api/v1/tasks/failure/" },
      {
        request: async () => response({ status: "failed", error: "Render inválido." }),
        wait: async () => {},
      },
    ),
    /Render inválido\./,
  );
});
