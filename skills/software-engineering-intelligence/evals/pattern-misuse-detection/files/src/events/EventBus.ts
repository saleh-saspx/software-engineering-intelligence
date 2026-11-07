export type Listener<E> = (event: E) => Promise<void> | void;

/** In-process publish/subscribe. Listeners run in the order they were subscribed. */
export class EventBus {
  private readonly listeners = new Map<string, Listener<any>[]>();

  subscribe<E>(type: string, listener: Listener<E>): void {
    const list = this.listeners.get(type) ?? [];
    list.push(listener);
    this.listeners.set(type, list);
  }

  async publish<E>(type: string, event: E): Promise<void> {
    for (const listener of this.listeners.get(type) ?? []) {
      try {
        await listener(event);
      } catch (err) {
        // one failing listener must not break the others
        console.error(`listener for ${type} failed`, err);
      }
    }
  }
}
