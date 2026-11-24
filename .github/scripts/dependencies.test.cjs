const { test } = require("node:test");
const assert = require("node:assert/strict");
const { dependencies, completed, synchronize, checkPullRequest } = require("./dependencies.cjs");

function issue(number, deps = [], state = "open", reason = null) {
  return { number, body: `<!-- depends-on: ${deps.join(",")} -->`, state,
    state_reason: reason, assignees: [], labels: [{ name: "roadmap" }] };
}

test("only completed prerequisites unlock a chain; cycles and missing issues block", () => {
  assert.deepEqual(dependencies("<!-- depends-on: 1, 2, 1 -->"), [1, 2]);
  const issues = new Map([[1, issue(1, [], "closed", "completed")],
    [2, issue(2, [1], "closed", "completed")]]);
  assert.equal(completed(2, issues), true);
  issues.get(1).state_reason = "not_planned";
  assert.equal(completed(2, issues), false);
  assert.equal(completed(999, issues), false);
  issues.get(1).state_reason = "completed";
  issues.get(1).body = "<!-- depends-on: 2 -->";
  assert.equal(completed(2, issues), false);
});

test("closing a blocked task reopens it and retains blocked status", async () => {
  const rows = [issue(2, [1], "closed", "completed"), issue(1)];
  const calls = [];
  const github = {
    paginate: async () => rows,
    rest: { issues: {
      listForRepo: {},
      update: async args => calls.push(["update", args]),
      createComment: async args => calls.push(["comment", args]),
      removeLabel: async args => calls.push(["remove", args]),
      addLabels: async args => calls.push(["labels", args]),
    } },
  };
  await synchronize({ github, context: { repo: { owner: "test", repo: "test" } } });
  assert.ok(calls.some(([action, args]) => action === "update" && args.issue_number === 2 && args.state === "open"));
  assert.ok(calls.some(([action, args]) => action === "labels" && args.issue_number === 2 && args.labels.includes("status:blocked")));
  assert.ok(calls.some(([action, args]) => action === "labels" && args.issue_number === 1 && args.labels.includes("status:ready")));
});

test("PR requires an issue and blocks incomplete dependencies", async () => {
  const issues = new Map([[1, issue(1)], [2, issue(2, [1])]]);
  const failures = [];
  const args = {
    github: { rest: { issues: { get: async ({ issue_number }) => ({ data: issues.get(issue_number) }) } } },
    context: { repo: { owner: "test", repo: "test" }, payload: { pull_request: { body: "Closes #2" } } },
    core: { setFailed: text => failures.push(text), info: () => {} },
  };
  await checkPullRequest(args);
  assert.equal(failures.length, 1);
  issues.set(1, issue(1, [], "closed", "completed"));
  failures.length = 0;
  await checkPullRequest(args);
  assert.equal(failures.length, 0);
  args.context.payload.pull_request.body = "";
  await checkPullRequest(args);
  assert.equal(failures.length, 1);
});
