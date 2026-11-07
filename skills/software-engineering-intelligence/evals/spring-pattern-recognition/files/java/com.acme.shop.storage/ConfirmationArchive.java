package com.acme.shop.storage;

import java.nio.charset.StandardCharsets;
import org.springframework.stereotype.Component;

@Component
public class ConfirmationArchive {

    private final ObjectStorage storage;

    public ConfirmationArchive(ObjectStorage storage) {
        this.storage = storage;
    }

    public void store(long orderId, String confirmationText) {
        storage.put("confirmations/" + orderId + ".txt", confirmationText.getBytes(StandardCharsets.UTF_8));
    }
}
