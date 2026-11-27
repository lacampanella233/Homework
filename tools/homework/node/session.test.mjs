// AI-assisted tests of the installed client's session API, using fake data only.
import assert from "node:assert/strict";
import test from "node:test";
import { FailReason, Learn2018Helper } from "@robertying/thu-learn-lib";
import { CookieJar, cookieJarConfig } from "@robertying/thu-learn-lib/cookies";

function restoredClient() {
  const jar = new CookieJar();
  jar.setCookieSync(
    "JSESSIONID=fake-session; Path=/; Secure; HttpOnly",
    "https://learn.tsinghua.edu.cn",
  );
  const savedJar = JSON.parse(JSON.stringify(jar.serializeSync()));
  const helper = new Learn2018Helper(cookieJarConfig(CookieJar.fromJSON(savedJar)));
  helper.setCSRFToken("fake-csrf");
  return helper;
}

test("restored cookies and CSRF token reach the session probe", async (t) => {
  let calls = 0;
  t.mock.method(globalThis, "fetch", async (input, init) => {
    calls += 1;
    const url = new URL(input);
    assert.equal(url.origin, "https://learn.tsinghua.edu.cn");
    assert.equal(url.searchParams.get("_csrf"), "fake-csrf");
    assert.equal(new Headers(init.headers).get("cookie"), "JSESSIONID=fake-session");
    return Response.json({ message: "success" });
  });

  await restoredClient().ensureSession();

  assert.equal(calls, 1);
});

test("expired sessions stop without attempting credential login", async (t) => {
  let calls = 0;
  t.mock.method(globalThis, "fetch", async () => {
    calls += 1;
    return new Response("", { status: 403 });
  });

  await assert.rejects(
    () => restoredClient().ensureSession(),
    (error) => error.reason === FailReason.NOT_LOGGED_IN,
  );
  assert.equal(calls, 1);
});

test("a missing CSRF token cannot resume a session by cookies alone", async (t) => {
  const helper = restoredClient();
  helper.setCSRFToken("");
  let calls = 0;
  t.mock.method(globalThis, "fetch", async () => {
    calls += 1;
    throw new Error("Unexpected request without a CSRF token");
  });

  await assert.rejects(
    () => helper.ensureSession(),
    (error) => error.reason === FailReason.NO_CREDENTIAL,
  );
  assert.equal(calls, 0);
});
