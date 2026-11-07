import { ConfigManager } from '../config/ConfigManager';
import type { NotificationSender } from './NotificationSender';
import { SendGridEmailSender } from './SendGridEmailSender';

export interface INotificationSenderFactory {
  create(): NotificationSender;
}

export class NotificationSenderFactory implements INotificationSenderFactory {
  create(): NotificationSender {
    const config = ConfigManager.getInstance();
    return new SendGridEmailSender(config.get('sendgridApiKey'), 'orders@shop.example');
  }
}
