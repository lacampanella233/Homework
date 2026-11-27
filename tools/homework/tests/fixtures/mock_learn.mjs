// AI-assisted offline example; no client dependency or network access.
const courseId = process.argv[2];
console.error(`Reading mock homework for ${courseId}`);
process.stdout.write(JSON.stringify([
  {
    id: "student_record_1",
    baseId: "homework_1",
    title: "第一次作业：ε-δ",
    deadline: "2026-11-30T23:59:00+08:00",
  },
]));
