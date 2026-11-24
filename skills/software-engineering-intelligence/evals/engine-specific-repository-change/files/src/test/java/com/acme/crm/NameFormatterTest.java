package com.acme.crm;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class NameFormatterTest {
    @Test
    void joinsNames() {
        assertThat(String.join(" ", "Sara", "Rad")).isEqualTo("Sara Rad");
    }
}
