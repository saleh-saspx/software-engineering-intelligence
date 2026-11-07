package com.acme.shop.audit;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;

/** Application-wide audit log. Use AuditLogger.getInstance(). */
public final class AuditLogger {

    private static AuditLogger instance;

    private final List<String> buffer = new ArrayList<>();
    private final Path file = Path.of(System.getProperty("audit.file", "audit.log"));

    private AuditLogger() {
    }

    public static synchronized AuditLogger getInstance() {
        if (instance == null) {
            instance = new AuditLogger();
        }
        return instance;
    }

    public void log(String message) {
        buffer.add(Instant.now() + " " + message);
        if (buffer.size() >= 50) {
            flush();
        }
    }

    public synchronized void flush() {
        try {
            Files.write(file, buffer, StandardOpenOption.CREATE, StandardOpenOption.APPEND);
            buffer.clear();
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    /** For tests. */
    public void clear() {
        buffer.clear();
    }

    public List<String> entries() {
        return List.copyOf(buffer);
    }
}
