function dependencies(body = "") {
  const match = body.match(/<!--\s*depends-on:\s*([\d,\s]*)-->/);
  return match ? [...new Set((match[1].match(/\d+/g) || []).map(Number))] : [];
}

function completed(number, issues, visiting = new Set()) {
  const issue = issues.get(number);
  if (!issue || visiting.has(number) || issue.state !== "closed" || issue.state_reason !== "completed") return false;
  const next = new Set(visiting).add(number);
  return dependencies(issue.body).every(id => completed(id, issues, next));
}

async function synchronize({ github, context }) {
  const repo = context.repo;
  const rows = await github.paginate(github.rest.issues.listForRepo, {
    ...repo, state: "all", labels: "roadmap", per_page: 100,
  });
  const issues = new Map(rows.filter(i => !i.pull_request).map(i => [i.number, i]));
  for (const issue of issues.values()) {
    const blockers = dependencies(issue.body).filter(id => !completed(id, issues));
    if (issue.state === "closed" && blockers.length) {
      await github.rest.issues.update({ ...repo, issue_number: issue.number, state: "open" });
      await github.rest.issues.createComment({
        ...repo, issue_number: issue.number,
        body: `🔒 Ön koşullar tamamlanmadığı için görev yeniden açıldı: ${blockers.map(n => `#${n}`).join(", ")}.\nÖnce bu görevleri tamamlayın, ardından bu görevi kapatın.`,
      });
      issue.state = "open";
    }
    const desired = blockers.length ? "status:blocked"
      : issue.state === "closed" ? "status:done"
      : issue.assignees.length ? "status:in-progress" : "status:ready";
    const existing = issue.labels.map(l => l.name);
    for (const name of existing.filter(n => n.startsWith("status:") && n !== desired)) {
      await github.rest.issues.removeLabel({ ...repo, issue_number: issue.number, name });
    }
    if (!existing.includes(desired)) {
      await github.rest.issues.addLabels({ ...repo, issue_number: issue.number, labels: [desired] });
    }
  }
}

async function checkPullRequest({ github, context, core }) {
  const pr = context.payload.pull_request;
  const numbers = [...new Set([...((pr.body || "").matchAll(/\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#(\d+)/gi))].map(m => Number(m[1])))];
  if (!numbers.length) {
    core.setFailed("PR açıklamasına 'Closes #GÖREV_NUMARASI' ekleyin.");
    return;
  }
  const issues = new Map();
  async function load(number) {
    if (issues.has(number)) return;
    const { data } = await github.rest.issues.get({ ...context.repo, issue_number: number });
    if (data.pull_request) throw new Error(`#${number} bir görev değil, pull request.`);
    issues.set(number, data);
    for (const id of dependencies(data.body)) await load(id);
  }
  for (const number of numbers) await load(number);
  const blockers = [...new Set(numbers.flatMap(n => dependencies(issues.get(n).body))
    .filter(n => !completed(n, issues)))];
  if (blockers.length) core.setFailed(`Önce tamamlanması gereken görevler: ${blockers.map(n => `#${n}`).join(", ")}`);
  else core.info("Görev bağlantıları ve ön koşullar uygun.");
}

module.exports = { dependencies, completed, synchronize, checkPullRequest };
