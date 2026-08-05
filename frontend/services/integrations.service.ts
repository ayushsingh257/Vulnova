export interface JiraConfigDTO {
  host_url?: string;
  email?: string;
  api_token_masked?: string;
  project_key?: string;
  issue_type: string;
  is_configured: boolean;
}

export interface GitHubConfigDTO {
  repo_owner?: string;
  repo_name?: string;
  personal_access_token_masked?: string;
  is_configured: boolean;
}

export interface IntegrationConfigResponse {
  jira: JiraConfigDTO;
  github: GitHubConfigDTO;
}

export interface SaveJiraConfigRequest {
  host_url: string;
  email: string;
  api_token: string;
  project_key: string;
  issue_type?: string;
}

export interface SaveGitHubConfigRequest {
  repo_owner: string;
  repo_name: string;
  personal_access_token: string;
}

export interface CreateIssueRequest {
  custom_labels?: string[];
  assignee?: string;
}

export interface ExternalIssueDTO {
  issue_id: string;
  issue_key: string;
  issue_url: string;
  provider: string;
  status: string;
  created_at: string;
}

export interface SyncStatusResponse {
  finding_id: string;
  provider: string;
  external_issue_id: string;
  external_status: string;
  previous_vulnova_status: string;
  updated_vulnova_status: string;
  synced_at: string;
}

export class IntegrationsService {
  private static readonly BASE_URL = "/api/v1/integrations";

  /**
   * Fetch integration configuration status (masked secrets).
   */
  public static async getIntegrationStatus(): Promise<IntegrationConfigResponse> {
    const res = await fetch(this.BASE_URL);
    if (!res.ok) {
      throw new Error(`Failed to fetch integration status: ${res.statusText}`);
    }
    return res.json();
  }

  /**
   * Save Jira Cloud integration configuration.
   */
  public static async saveJiraConfig(
    req: SaveJiraConfigRequest
  ): Promise<JiraConfigDTO> {
    const res = await fetch(`${this.BASE_URL}/jira/config`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
    if (!res.ok) {
      throw new Error(`Failed to save Jira configuration: ${res.statusText}`);
    }
    return res.json();
  }

  /**
   * Save GitHub Issues integration configuration.
   */
  public static async saveGitHubConfig(
    req: SaveGitHubConfigRequest
  ): Promise<GitHubConfigDTO> {
    const res = await fetch(`${this.BASE_URL}/github/config`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
    if (!res.ok) {
      throw new Error(`Failed to save GitHub configuration: ${res.statusText}`);
    }
    return res.json();
  }

  /**
   * Create Jira issue for finding.
   */
  public static async createJiraIssue(
    findingId: string,
    req: CreateIssueRequest = {}
  ): Promise<ExternalIssueDTO> {
    const res = await fetch(`${this.BASE_URL}/jira/issues/${findingId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
    if (!res.ok) {
      throw new Error(`Failed to create Jira issue: ${res.statusText}`);
    }
    return res.json();
  }

  /**
   * Create GitHub issue for finding.
   */
  public static async createGitHubIssue(
    findingId: string,
    req: CreateIssueRequest = {}
  ): Promise<ExternalIssueDTO> {
    const res = await fetch(`${this.BASE_URL}/github/issues/${findingId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
    if (!res.ok) {
      throw new Error(`Failed to create GitHub issue: ${res.statusText}`);
    }
    return res.json();
  }

  /**
   * Sync Jira issue lifecycle status through controlled mapper.
   */
  public static async syncJiraStatus(
    findingId: string,
    issueKey: string
  ): Promise<SyncStatusResponse> {
    const res = await fetch(
      `${this.BASE_URL}/jira/${findingId}/${issueKey}/sync`,
      { method: "POST" }
    );
    if (!res.ok) {
      throw new Error(`Failed to sync Jira status: ${res.statusText}`);
    }
    return res.json();
  }

  /**
   * Sync GitHub issue lifecycle status through controlled mapper.
   */
  public static async syncGitHubStatus(
    findingId: string,
    issueNumber: string
  ): Promise<SyncStatusResponse> {
    const res = await fetch(
      `${this.BASE_URL}/github/${findingId}/${issueNumber}/sync`,
      { method: "POST" }
    );
    if (!res.ok) {
      throw new Error(`Failed to sync GitHub status: ${res.statusText}`);
    }
    return res.json();
  }
}
