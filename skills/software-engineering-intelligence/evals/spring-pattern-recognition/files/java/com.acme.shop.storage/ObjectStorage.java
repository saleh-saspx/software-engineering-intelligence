package com.acme.shop.storage;

import java.net.URI;

/** Minimal client for the S3-compatible object store. */
public class ObjectStorage {

    private final URI endpoint;
    private final String bucket;
    private final String accessKey;
    private final String secretKey;

    ObjectStorage(URI endpoint, String bucket, String accessKey, String secretKey) {
        this.endpoint = endpoint;
        this.bucket = bucket;
        this.accessKey = accessKey;
        this.secretKey = secretKey;
    }

    public void put(String key, byte[] content) {
        // signed PUT to endpoint/bucket/key (omitted)
    }
}
