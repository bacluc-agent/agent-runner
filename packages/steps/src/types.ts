import type { GitHubClient } from "@bacluc-agent/github";

export type StepContext = {
  repository: string;
  issueRepository: string;
  token?: string;
  launcher: string;
  agentCommand: string;
  dryRun: boolean;
  model?: string;
  github: GitHubClient;
  runAgent: (prompt: string, agent: string) => Promise<string>;
};
