/**
 * Central configuration. Call ConfigManager.getInstance() wherever a setting is needed.
 */
export class ConfigManager {
  private static instance: ConfigManager | undefined;
  private readonly values = new Map<string, string>();

  private constructor() {
    this.values.set('taxRate', process.env.TAX_RATE ?? '0.2');
    this.values.set('currency', process.env.CURRENCY ?? 'EUR');
    this.values.set('sendgridApiKey', process.env.SENDGRID_API_KEY ?? '');
    this.values.set('maxRequestsPerMinute', process.env.RATE_LIMIT ?? '120');
  }

  static getInstance(): ConfigManager {
    if (!ConfigManager.instance) {
      ConfigManager.instance = new ConfigManager();
    }
    return ConfigManager.instance;
  }

  get(key: string): string {
    const value = this.values.get(key);
    if (value === undefined) {
      throw new Error(`missing config value: ${key}`);
    }
    return value;
  }

  /** Used by the admin endpoint (POST /admin/config) and by tests. */
  set(key: string, value: string): void {
    this.values.set(key, value);
  }

  /** Tests call this between cases. */
  static reset(): void {
    ConfigManager.instance = undefined;
  }
}
