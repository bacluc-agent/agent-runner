export type Label = { name: string };
export type Issue = {
  number: number;
  title: string;
  body: string;
  labels: Label[];
  html_url?: string;
};
export type PullRequest = Issue & {
  head: { ref: string };
  html_url: string;
  repository_url?: string;
};
export type ReviewComment = {
  id: number;
  body: string;
  user?: { login: string };
  created_at?: string;
};
export type IssueComment = {
  id: number;
  body: string;
  user?: { login: string };
  created_at?: string;
};

type Page<T> = { data: T; next?: string };

export class GitHubClient {
  private readonly token: string;
  private readonly apiBase: string;

  constructor(token: string, apiBase = "https://api.github.com") {
    this.token = token;
    this.apiBase = apiBase;
  }

  async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    return (await this.requestPage<T>(path, init)).data;
  }

  private async requestPage<T>(
    path: string,
    init: RequestInit = {},
  ): Promise<Page<T>> {
    const url = path.startsWith("http")
      ? path
      : `${this.apiBase}/${path.replace(/^\//, "")}`;
    const response = await fetch(url, {
      ...init,
      headers: {
        Accept: "application/vnd.github+json",
        Authorization: `Bearer ${this.token}`,
        "X-GitHub-Api-Version": "2022-11-28",
        ...(init.headers ?? {}),
      },
    });
    const body = await response.text();
    if (!response.ok) throw new Error(`GitHub ${response.status}: ${body}`);
    const next = response.headers
      .get("link")
      ?.split(",")
      .map((link) => link.match(/<([^>]+)>;\s*rel="next"/))
      .find(Boolean)?.[1];
    return { data: body ? (JSON.parse(body) as T) : (undefined as T), next };
  }

  async searchIssues(query: string): Promise<Issue[]> {
    return this.searchPages<Issue>(query);
  }

  private async searchPages<T>(query: string): Promise<T[]> {
    const items: T[] = [];
    let path: string | undefined =
      `search/issues?q=${encodeURIComponent(query)}&per_page=100&page=1`;
    while (path) {
      const page = await this.requestPage<{ items: T[] }>(path);
      items.push(...page.data.items);
      path = page.next;
    }
    return items;
  }

  currentUser(): Promise<{ login: string }> {
    return this.request<{ login: string }>("user");
  }

  issues(query: string): Promise<Issue[]> {
    return this.searchIssues(query);
  }

  getIssue(repository: string, number: number): Promise<Issue> {
    return this.request<Issue>(`repos/${repository}/issues/${number}`);
  }

  issue(repository: string, number: number): Promise<Issue> {
    return this.getIssue(repository, number);
  }

  async editIssue(
    repository: string,
    number: number,
    options:
      | {
          body?: string;
          expectedBody?: string;
          addLabels?: string[];
          removeLabels?: string[];
        }
      | string,
    body?: string,
    label?: string,
  ): Promise<void> {
    if (typeof options === "string")
      options = {
        expectedBody: options,
        body,
        addLabels: label ? [label] : [],
      };
    const current = await this.getIssue(repository, number);
    if (
      options.expectedBody !== undefined &&
      current.body !== options.expectedBody
    )
      throw new Error(`issue #${number} changed while it was being edited`);
    const removed = new Set(options.removeLabels ?? []);
    const labels = [
      ...new Set(
        current.labels
          .map((label) => label.name)
          .filter((name) => !removed.has(name))
          .concat(options.addLabels ?? []),
      ),
    ];
    await this.request(`repos/${repository}/issues/${number}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...(options.body === undefined ? {} : { body: options.body }),
        labels,
      }),
    });
  }

  ensureLabel(repository: string, name: string): Promise<void> {
    return this.request(`repos/${repository}/labels`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    }).then(() => undefined);
  }

  async searchPullRequests(query: string): Promise<PullRequest[]> {
    return (await this.searchPages<PullRequest>(query)).map((item) => ({
      ...item,
      repository:
        item.repository ??
        item.repository_url?.replace("https://api.github.com/repos/", ""),
      html_url: item.html_url,
    }));
  }

  async pullRequests(
    query: string,
  ): Promise<
    Array<{ number: number; title: string; url: string; repository: string }>
  > {
    return (await this.searchPullRequests(query)).map((pr) => ({
      number: pr.number,
      title: pr.title,
      url: pr.html_url,
      repository: pr.repository,
    }));
  }

  getPullRequest(repository: string, number: number): Promise<PullRequest> {
    return this.request<PullRequest>(`repos/${repository}/pulls/${number}`);
  }

  listReviewComments(
    repository: string,
    number: number,
  ): Promise<ReviewComment[]> {
    return this.request<ReviewComment[]>(
      `repos/${repository}/pulls/${number}/comments`,
    );
  }

  listIssueComments(
    repository: string,
    number: number,
  ): Promise<IssueComment[]> {
    return this.request<IssueComment[]>(
      `repos/${repository}/issues/${number}/comments`,
    );
  }

  async upsertComment(
    repository: string,
    number: number,
    body: string,
  ): Promise<IssueComment> {
    const comments = await this.listIssueComments(repository, number);
    const existing = comments.find((comment) =>
      comment.body.includes("<!-- agent-progress -->"),
    );
    const path = existing
      ? `repos/${repository}/issues/comments/${existing.id}`
      : `repos/${repository}/issues/${number}/comments`;
    return this.request<IssueComment>(path, {
      method: existing ? "PATCH" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ body }),
    });
  }
}
