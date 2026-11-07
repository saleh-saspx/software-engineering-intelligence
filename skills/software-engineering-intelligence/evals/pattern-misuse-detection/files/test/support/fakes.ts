import type { NotificationSender } from '../../src/notifications/NotificationSender';

export class FakeNotificationSender implements NotificationSender {
  readonly sent: { to: string; subject: string; body: string }[] = [];

  async send(to: string, subject: string, body: string): Promise<void> {
    this.sent.push({ to, subject, body });
  }
}
