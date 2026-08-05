export interface NotificationChannelDTO {
  id: string;
  provider: "slack" | "teams" | string;
  name: string;
  webhook_url_masked: string;
  event_types: string[];
  min_severity: string;
  is_active: boolean;
  created_at: string;
}

export interface CreateChannelRequest {
  provider: "slack" | "teams";
  name: string;
  webhook_url: string;
  event_types?: string[];
  min_severity?: string;
}

export interface UpdateChannelRequest {
  name?: string;
  webhook_url?: string;
  event_types?: string[];
  min_severity?: string;
  is_active?: boolean;
}

export interface NotificationRuleDTO {
  id: string;
  name: string;
  event_types: string[];
  min_severity: string;
  min_risk_score: number;
  is_enabled: boolean;
}

export interface NotificationDeliveryResponse {
  channel_id: string;
  provider: string;
  event_type: string;
  status: "DELIVERED" | "FAILED" | string;
  status_code: number;
  delivered_at: string;
  error_message?: string;
}

export class NotificationsService {
  private static readonly BASE_URL = "/api/v1/notifications";

  /**
   * Fetch all configured notification channels (urls masked).
   */
  public static async getChannels(): Promise<NotificationChannelDTO[]> {
    const res = await fetch(`${this.BASE_URL}/channels`);
    if (!res.ok) {
      throw new Error(`Failed to fetch notification channels: ${res.statusText}`);
    }
    return res.json();
  }

  /**
   * Create a new Slack or Teams webhook channel.
   */
  public static async createChannel(
    req: CreateChannelRequest
  ): Promise<NotificationChannelDTO> {
    const res = await fetch(`${this.BASE_URL}/channels`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
    if (!res.ok) {
      throw new Error(`Failed to create notification channel: ${res.statusText}`);
    }
    return res.json();
  }

  /**
   * Update notification channel configuration.
   */
  public static async updateChannel(
    channelId: string,
    req: UpdateChannelRequest
  ): Promise<NotificationChannelDTO> {
    const res = await fetch(`${this.BASE_URL}/channels/${channelId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
    if (!res.ok) {
      throw new Error(`Failed to update notification channel: ${res.statusText}`);
    }
    return res.json();
  }

  /**
   * Delete notification channel.
   */
  public static async deleteChannel(channelId: string): Promise<void> {
    const res = await fetch(`${this.BASE_URL}/channels/${channelId}`, {
      method: "DELETE",
    });
    if (!res.ok && res.status !== 204) {
      throw new Error(`Failed to delete notification channel: ${res.statusText}`);
    }
  }

  /**
   * Fetch notification routing rules.
   */
  public static async getRules(): Promise<NotificationRuleDTO[]> {
    const res = await fetch(`${this.BASE_URL}/rules`);
    if (!res.ok) {
      throw new Error(`Failed to fetch notification rules: ${res.statusText}`);
    }
    return res.json();
  }

  /**
   * Dispatch a test alert to verify webhook connectivity.
   */
  public static async sendTestNotification(
    channelId: string
  ): Promise<NotificationDeliveryResponse> {
    const res = await fetch(`${this.BASE_URL}/test`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ channel_id: channelId }),
    });
    if (!res.ok) {
      throw new Error(`Failed to send test notification: ${res.statusText}`);
    }
    return res.json();
  }
}
