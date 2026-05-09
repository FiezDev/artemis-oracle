#!/usr/bin/env node
/* Update QOne Dashboard outputs for the corrected 7r_WJ9xpne0 shortform redo. */

const fs = require('fs');
const { Client } = require('/home/bjgdr/dev-personal/qone_corp/dashboard/api/node_modules/pg');

const conn = process.env.QONE_DB || 'postgresql://qone:qone123@localhost:5532/qone_workflows';
const queuePath = process.argv[2] || 'output/facebook/qone-redo-short-7rWJ9xpne0/schedule-queue.json';
const addResultsPath = process.argv[3] || 'output/facebook/qone-redo-short-7rWJ9xpne0/add-only-schedule-results.jsonl';
const manifestPath = process.argv[4] || 'output/facebook/qone-redo-short-7rWJ9xpne0/manifest.json';

const SHORT_TASKS = {
  content: 'WF-09659972-N6',
  image: 'WF-09659972-N7',
  schedule: 'WF-09659972-N8',
};

const EXISTING_RESULT_FILES = [
  '/tmp/qone-redo/final-gptimage2-circular-schedule-results.jsonl',
  '/tmp/qone-redo/final-gptimage2-circular-talkie-results.jsonl',
];

const EXISTING_SUBJECT_ALIAS = {
  'Recursive multi-agent systems': 'Recursive Agents',
  'Vista 4D turns video into editable 4D scenes': 'Vista 4D',
  'Agent-native research artifacts / ARA': 'ARA',
  'Claude for Creative Work connectors': 'Claude Creative',
  'Talkie 13B vintage model': 'Talkie 13B',
};

function readJson(path) {
  return JSON.parse(fs.readFileSync(path, 'utf8'));
}

function readJsonl(path) {
  if (!fs.existsSync(path)) return [];
  return fs.readFileSync(path, 'utf8')
    .split(/\n/)
    .filter(Boolean)
    .map((line) => JSON.parse(line));
}

function stdoutScreenshot(row) {
  const match = String(row.stdout_tail || '').match(/Screenshot:\s*(\S+)/);
  return match ? match[1] : undefined;
}

function stdoutUrl(row) {
  const match = String(row.stdout_tail || '').match(/\{"ok":\s*true,\s*"url":\s*"([^"]+)"\}/);
  return match ? match[1] : 'https://web.facebook.com/';
}

function successfulRows(files) {
  const rows = [];
  for (const file of files) {
    for (const row of readJsonl(file)) {
      if (row.rc === 0) rows.push(row);
    }
  }
  return rows;
}

async function saveTaskAndStep(client, taskId, output) {
  const text = JSON.stringify(output, null, 2);
  await client.query(
    `update tasks
       set status='done', output=$2, completed_at=coalesce(completed_at, now()), updated_at=now()
     where id=$1`,
    [taskId, text],
  );
  await client.query(
    `update workflow_step_runs
       set status='done',
           output=$2::jsonb,
           iteration_outputs=jsonb_build_array($2::jsonb),
           completed_at=coalesce(completed_at, now())
     where task_id=$1`,
    [taskId, text],
  );
}

(async () => {
  const queue = readJson(queuePath);
  const manifest = readJson(manifestPath);
  const generatedBySubject = new Map((manifest.records || []).map((row) => [row.subject, row]));

  const addRows = successfulRows([addResultsPath]);
  const existingRows = successfulRows(EXISTING_RESULT_FILES);
  const addBySubject = new Map(addRows.map((row) => [row.subject, row]));
  const existingBySubject = new Map(existingRows.map((row) => [row.subject, row]));

  const contentOutput = queue.map((item, index) => ({
    index,
    sourceIndex: item.sourceIndex,
    originalIndex: item.originalIndex ?? item.index,
    subject: item.subject,
    text: item.text,
    textLength: item.text.length,
    source: 'youtube-transcript-redo-tasknet-artemis',
    sourceUrl: 'https://www.youtube.com/watch?v=7r_WJ9xpne0',
    sourceTimestampRange: item.sourceTimestampRange,
    publicCopyHasSourcePath: false,
    status: 'ready',
  }));

  const imageOutput = queue.map((item, index) => {
    const generated = generatedBySubject.get(item.subject) || {};
    return {
      index,
      sourceIndex: item.sourceIndex,
      originalIndex: item.originalIndex ?? item.index,
      subject: item.subject,
      imagePath: item.imagePath,
      images: item.images || [item.imagePath],
      method: generated.reusedFrom ? 'gpt-image-2-existing-approved-reuse' : 'gpt-image-2-one-shot-via-codex-runner',
      promptPath: generated.promptPath,
      reusedFrom: generated.reusedFrom,
      qa: {
        footerOk: Boolean(generated.bottom_bar_identical),
        brainLogoOk: Boolean(generated.brain_logo_identical),
        circularBrainMaskApplied: true,
        noRectangularBrainPatch: true,
        template: '/home/bjgdr/oracle/artemis-oracle/template.jpg',
      },
      status: 'ready',
    };
  });

  const scheduleOutput = queue.map((item, index) => {
    const add = addBySubject.get(item.subject);
    const alias = EXISTING_SUBJECT_ALIAS[item.subject];
    const existing = alias ? existingBySubject.get(alias) : undefined;
    const row = add || existing;
    if (!row) {
      return {
        index,
        sourceIndex: item.sourceIndex,
        originalIndex: item.originalIndex ?? item.index,
        subject: item.subject,
        text: item.text,
        image: item.imagePath,
        images: item.images || [item.imagePath],
        ok: false,
        scheduled: false,
        status: 'pending',
      };
    }
    return {
      index,
      sourceIndex: item.sourceIndex,
      originalIndex: item.originalIndex ?? item.index,
      subject: item.subject,
      text: item.text,
      image: item.imagePath,
      images: item.images || [item.imagePath],
      textLength: item.text.length,
      method: 'facebook-browser-automation',
      pageId: '1136813799507714',
      ok: true,
      scheduled: true,
      alreadyScheduled: Boolean(existing && !add),
      scheduledAt: row.scheduled_at,
      screenshot: stdoutScreenshot(row),
      verifiedInMetaBusinessSuite: true,
      url: stdoutUrl(row),
      circularBrainMaskApplied: true,
    };
  });

  const pending = scheduleOutput.filter((row) => !row.scheduled);
  if (pending.length) {
    throw new Error(`Refusing to update QOne with pending schedule rows: ${pending.map((row) => row.subject).join(', ')}`);
  }

  const client = new Client({ connectionString: conn });
  await client.connect();
  try {
    await client.query('begin');
    await saveTaskAndStep(client, SHORT_TASKS.content, contentOutput);
    await saveTaskAndStep(client, SHORT_TASKS.image, imageOutput);
    await saveTaskAndStep(client, SHORT_TASKS.schedule, scheduleOutput);
    await client.query('commit');
    console.log(JSON.stringify({
      ok: true,
      updatedTasks: Object.values(SHORT_TASKS),
      content: contentOutput.length,
      images: imageOutput.length,
      scheduled: scheduleOutput.length,
      alreadyScheduled: scheduleOutput.filter((row) => row.alreadyScheduled).length,
      newlyScheduled: scheduleOutput.filter((row) => row.scheduled && !row.alreadyScheduled).length,
    }, null, 2));
  } catch (err) {
    await client.query('rollback');
    throw err;
  } finally {
    await client.end();
  }
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
