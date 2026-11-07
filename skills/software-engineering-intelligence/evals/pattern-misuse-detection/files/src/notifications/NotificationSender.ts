export interface NotificationSender {
  send(to: string, subject: string, body: string): Promise<void>;
}
