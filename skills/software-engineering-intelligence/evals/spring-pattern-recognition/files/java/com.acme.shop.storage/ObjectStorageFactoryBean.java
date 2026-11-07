package com.acme.shop.storage;

import java.net.URI;
import org.springframework.beans.factory.FactoryBean;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Component;

@Component
public class ObjectStorageFactoryBean implements FactoryBean<ObjectStorage> {

    private final Environment env;

    public ObjectStorageFactoryBean(Environment env) {
        this.env = env;
    }

    @Override
    public ObjectStorage getObject() {
        return new ObjectStorage(URI.create(env.getRequiredProperty("storage.endpoint")),
                env.getRequiredProperty("storage.bucket"),
                env.getRequiredProperty("storage.access-key"),
                env.getRequiredProperty("storage.secret-key"));
    }

    @Override
    public Class<?> getObjectType() {
        return ObjectStorage.class;
    }
}
