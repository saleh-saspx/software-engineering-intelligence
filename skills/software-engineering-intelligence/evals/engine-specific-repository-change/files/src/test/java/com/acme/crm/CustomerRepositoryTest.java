package com.acme.crm;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.test.context.ActiveProfiles;

@DataJpaTest
@ActiveProfiles("test")
class CustomerRepositoryTest {
    @Autowired CustomerRepository repo;

    @Test
    void upsertInsertsThenUpdates() {
        repo.upsertByNationalId("0012345678", "Sara Rad", "");
        repo.upsertByNationalId("0012345678", "Sara Radmehr", "");
        assertThat(repo.findAll()).hasSize(1);
    }

    @Test
    void findsCustomersWithoutMiddleName() {
        repo.upsertByNationalId("0099999999", "Ali Noori", "");
        assertThat(repo.findWithoutMiddleName()).hasSize(1);
    }
}
