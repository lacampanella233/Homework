// AI-assisted offline check of the installed client; no account access.
import assert from "node:assert/strict";
import { Learn2018Helper } from "@robertying/thu-learn-lib";
import { cookieJarConfig } from "@robertying/thu-learn-lib/cookies";

const helper = new Learn2018Helper(cookieJarConfig());
for (const method of ["getCurrentSemester", "getCourseList", "getHomeworkList"]) {
  assert.equal(typeof helper[method], "function", `Missing client method: ${method}`);
}

console.log("Client loaded and initialized; no login or course requests performed.");
