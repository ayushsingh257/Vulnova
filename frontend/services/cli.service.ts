export interface CLITokenDTO {
  id: string;
  name: string;
  token_prefix: string;
  raw_token?: string;
  last_used_at?: string;
  created_at: string;
}

export interface CLITokenCreateRequest {
  name: string;
  expires_in_days?: number;
}

export interface CLIProjectDTO {
  id: string;
  name: string;
  repo_url?: string;
  last_scan_id?: string;
  last_scan_status?: string;
  updated_at: string;
}

export class CLIService {
  private static readonly BASE_URL = "/api/v1/cli";

  /**
   * Fetch all active CLI API tokens for tenant organization.
   */
  public static async getTokens(): Promise<CLITokenDTO[]> {
    const res = await fetch(`${this.BASE_URL}/tokens`);
    if (!res.ok) {
      throw new Error(`Failed to fetch CLI tokens: ${res.statusText}`);
    }
    return res.json();
  }

  /**
   * Create a new CLI API token (raw token returned once).
   */
  public static async createToken(
    req: CLITokenCreateRequest
  ): Promise<CLITokenDTO> {
    const res = await fetch(`${this.BASE_URL}/tokens`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
    if (!res.ok) {
      throw new Error(`Failed to create CLI token: ${res.statusText}`);
    }
    return res.json();
  }

  /**
   * Revoke a CLI API token.
   */
  public static async revokeToken(tokenId: string): Promise<void> {
    const res = await fetch(`${this.BASE_URL}/tokens/${tokenId}`, {
      method: "DELETE",
    });
    if (!res.ok && res.status !== 204) {
      throw new Error(`Failed to revoke CLI token: ${res.statusText}`);
    }
  }

  /**
   * Fetch registered projects/repositories.
   */
  public static async getProjects(): Promise<CLIProjectDTO[]> {
    const res = await fetch(`${this.BASE_URL}/projects`);
    if (!res.ok) {
      throw new Error(`Failed to fetch CLI projects: ${res.statusText}`);
    }
    return res.json();
  }
}
