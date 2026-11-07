package com.acme.shop.fx;

import java.math.BigDecimal;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.context.annotation.Primary;
import org.springframework.stereotype.Component;

/** Caches rates for an hour; ECB publishes once a day. */
@Primary
@Component
public class CachingExchangeRateProvider implements ExchangeRateProvider {

    private static final Duration TTL = Duration.ofHours(1);

    private final ExchangeRateProvider delegate;
    private final Clock clock;
    private final Map<String, CachedRate> cache = new ConcurrentHashMap<>();

    public CachingExchangeRateProvider(@Qualifier("ecbExchangeRateProvider") ExchangeRateProvider delegate, Clock clock) {
        this.delegate = delegate;
        this.clock = clock;
    }

    @Override
    public BigDecimal rate(String from, String to) {
        String key = from + "->" + to;
        Instant now = clock.instant();
        CachedRate cached = cache.get(key);
        if (cached != null && cached.fetchedAt().plus(TTL).isAfter(now)) {
            return cached.rate();
        }
        BigDecimal fresh = delegate.rate(from, to);
        cache.put(key, new CachedRate(fresh, now));
        return fresh;
    }

    private record CachedRate(BigDecimal rate, Instant fetchedAt) {
    }
}
