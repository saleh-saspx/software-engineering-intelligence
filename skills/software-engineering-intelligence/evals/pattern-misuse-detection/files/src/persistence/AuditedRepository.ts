import { BaseRepository, type Entity } from './BaseRepository';
import { CachedRepository } from './CachedRepository';

export abstract class AuditedRepository<T extends Entity> extends CachedRepository<T> {
  readonly auditLog: string[] = [];

  async save(entity: T): Promise<void> {
    // The cache must not serve a stale copy while the audit entry is written,
    // so bypass CachedRepository.save and write straight to the base store.
    await BaseRepository.prototype.save.call(this, entity);
    this.evict(entity.id);
    this.auditLog.push(`${this.now()} saved ${entity.id}`);
  }
}
