import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import vm from 'node:vm';

const html = readFileSync(new URL('../tag-report.html', import.meta.url), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)?.[1];
assert.ok(script, 'the page has an inline script');

const elements = new Map();
const element = id => {
  if (!elements.has(id)) elements.set(id, { addEventListener() {}, value: '' });
  return elements.get(id);
};
const context = {
  document: { getElementById: element },
  window: {},
  URL,
  Intl,
};
vm.runInNewContext(script, context);
const { apiBaseFromSite, buildReport, csvForReport, columns } = context.window.TagReport;

test('site URLs map to the API v3 hosts', () => {
  assert.equal(apiBaseFromSite('https://stackoverflowteams.com/c/engineering').base,
    'https://api.stackoverflowteams.com/v3/teams/engineering');
  assert.equal(apiBaseFromSite('https://example.stackenterprise.co').base,
    'https://example.stackenterprise.co/api/v3');
  assert.throws(() => apiBaseFromSite('http://example.stackenterprise.co'));
});

test('v3 data produces report metrics and an all-time Last Used date', () => {
  const data = {
    tags: [{ id: 1, name: 'python', watcherCount: 3,
      creationDate: '2026-01-01T00:00:00Z',
      smes: { users: [{ id: 2 }], userGroups: [{ users: [{ id: 3 }] }] } }],
    questions: [{ id: 10, tags: [{ id: 1, name: 'python' }], owner: { id: 1, name: 'Asker' },
      creationDate: '2026-01-01T00:00:00Z', score: 2, viewCount: 10,
      comments: [
        { ownerUserId: 4, ownerDisplayName: 'Commenter', creationDate: '2026-01-01T03:00:00Z' },
        { ownerUserId: 1, ownerDisplayName: 'Asker', creationDate: '2026-01-01T01:00:00Z' },
      ],
      answers: [
        { owner: { id: 2 }, creationDate: '2026-01-01T02:00:00Z', score: 3,
          isAccepted: true, comments: [{ ownerUserId: 5, ownerDisplayName: 'Editor' }] },
        { owner: { id: 1 }, creationDate: '2026-01-01T01:00:00Z', score: 1,
          isAccepted: false, comments: [] },
      ] }],
    articles: [{ tags: [{ id: 1, name: 'python' }], owner: { id: 3 },
      creationDate: '2026-01-02T00:00:00Z', score: 4, viewCount: 5, commentCount: 2 }],
  };

  const row = buildReport(data, null)[0];
  assert.equal(row.question_count, 1);
  assert.equal(row.answer_count, 2);
  assert.equal(row.article_count, 1);
  assert.equal(row.total_page_views, 15);
  assert.equal(row.question_score, 2);
  assert.equal(row.answer_score, 4);
  assert.equal(row.article_score, 4);
  assert.equal(row.total_smes, 2);
  assert.equal(row.sme_answers, 1);
  assert.equal(row.questions_self_answered, 1);
  assert.equal(row.total_unique_contributors, 5);
  assert.equal(row.median_time_to_first_answer_hours, 2);
  assert.equal(row.median_time_to_first_response_hours, 2);
  assert.equal(row.last_used, '2026-01-02');

  const recent = buildReport(data, 1)[0];
  assert.equal(recent.question_count, 0);
  assert.equal(recent.last_used, '2026-01-02');
});

test('CSV includes all metrics and neutralizes spreadsheet formulas', () => {
  const row = Object.fromEntries(columns.map(([key]) => [key, 0]));
  row.tag_name = '=HYPERLINK("https://example.com")';
  row.question_score = -3;
  const csv = csvForReport([row]);
  assert.equal(columns.length, 27);
  assert.ok(csv.startsWith('\ufeff'));
  assert.ok(csv.includes('"\'=HYPERLINK(""https://example.com"")"'));
  assert.ok(csv.includes('"-3"'));
});

test('the page collects nested v3 resources and clears the token field', async () => {
  const nodes = new Map();
  function makeNode() {
    const node = {
      children: [], value: '', textContent: '', style: {}, hidden: false,
      handlers: new Map(),
      addEventListener(type, handler) { this.handlers.set(type, handler); },
      append(child) { child.parent = this; this.children.push(child); },
      replaceChildren(...children) { this.children = children; },
      remove() { this.parent.children = this.parent.children.filter(item => item !== this); },
      setAttribute() {},
      get firstElementChild() { return this.children[0]; },
    };
    return node;
  }
  function getNode(id) {
    if (!nodes.has(id)) nodes.set(id, makeNode());
    return nodes.get(id);
  }
  const requests = [];
  const responses = {
    '/tags': { items: [{ id: 1, name: 'python', watcherCount: 0,
      creationDate: '2026-01-01T00:00:00Z', subjectMatterExpertCount: 0 }], totalPages: 1 },
    '/articles': { items: [], totalPages: 1 },
    '/questions': { items: [{ id: 10, tags: [{ id: 1, name: 'python' }],
      owner: { id: 1 }, creationDate: '2026-01-01T00:00:00Z',
      answerCount: 1, commentCount: 1, viewCount: 2, score: 1 }], totalPages: 1 },
    '/questions/10/comments': [{ ownerUserId: 2, ownerDisplayName: 'Responder',
      creationDate: '2026-01-01T01:00:00Z' }],
    '/questions/10/answers': { items: [{ id: 20, owner: { id: 2 },
      creationDate: '2026-01-01T02:00:00Z', commentCount: 1,
      isAccepted: false, score: 1 }], totalPages: 1 },
    '/questions/10/answers/20/comments': [{ ownerUserId: 3, ownerDisplayName: 'Reviewer' }],
  };
  const page = {
    document: {
      getElementById: getNode,
      querySelector: () => makeNode(),
      createElement: () => makeNode(),
      body: makeNode(),
    },
    window: {}, URL, Intl, AbortController, DOMException, setTimeout, clearTimeout,
    fetch: async (url, options) => {
      requests.push({ path: url.pathname, params: url.searchParams, authorization: options.headers.Authorization });
      return { ok: true, status: 200, headers: { get: () => null }, json: async () => responses[url.pathname.replace('/v3/teams/engineering', '')] };
    },
  };
  vm.runInNewContext(script, page);
  getNode('site-url').value = 'https://stackoverflowteams.com/c/engineering';
  getNode('token').value = 'private-test-token';

  await getNode('report-form').handlers.get('submit')({ preventDefault() {} });

  assert.equal(getNode('token').value, '');
  assert.equal(getNode('status-badge').textContent, 'Done');
  assert.equal(getNode('results').hidden, false);
  assert.deepEqual(requests.map(request => request.path.replace('/v3/teams/engineering', '')), [
    '/tags', '/articles', '/questions', '/questions/10/comments',
    '/questions/10/answers', '/questions/10/answers/20/comments',
  ]);
  assert.ok(requests.every(request => request.authorization === 'Bearer private-test-token'));
  assert.equal(requests[0].params.get('pageSize'), '100');
});
