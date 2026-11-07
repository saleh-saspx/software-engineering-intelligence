export interface Entity {
  id: string;
}

/** Shared persistence helpers. The Map stands in for the database driver. */
export abstract class BaseRepository<T extends Entity> {
  protected readonly rows = new Map<string, T>();

  async findById(id: string): Promise<T | undefined> {
    return this.rows.get(id);
  }

  async save(entity: T): Promise<void> {
    this.rows.set(entity.id, structuredClone(entity));
  }

  protected now(): string {
    return new Date().toISOString();
  }
}
