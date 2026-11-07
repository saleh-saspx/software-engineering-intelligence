import { BaseRepository, type Entity } from './BaseRepository';

export abstract class CachedRepository<T extends Entity> extends BaseRepository<T> {
  private readonly cache = new Map<string, T>();

  async findById(id: string): Promise<T | undefined> {
    const hit = this.cache.get(id);
    if (hit) {
      return hit;
    }
    const row = await super.findById(id);
    if (row) {
      this.cache.set(id, row);
    }
    return row;
  }

  async save(entity: T): Promise<void> {
    await super.save(entity);
    this.cache.set(entity.id, entity);
  }

  protected evict(id: string): void {
    this.cache.delete(id);
  }
}
