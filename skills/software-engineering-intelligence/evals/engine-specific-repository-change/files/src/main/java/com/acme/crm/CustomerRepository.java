package com.acme.crm;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface CustomerRepository extends JpaRepository<Customer, Long> {

    @Modifying
    @Query(value = """
        MERGE INTO customers c
        USING (SELECT :nationalId AS national_id, :fullName AS full_name, :middleName AS middle_name FROM dual) s
           ON (c.national_id = s.national_id)
        WHEN MATCHED THEN UPDATE SET c.full_name = s.full_name, c.middle_name = s.middle_name
        WHEN NOT MATCHED THEN INSERT (national_id, full_name, middle_name)
             VALUES (s.national_id, s.full_name, s.middle_name)
        """, nativeQuery = true)
    int upsertByNationalId(@Param("nationalId") String nationalId, @Param("fullName") String fullName,
                           @Param("middleName") String middleName);

    @Query(value = """
        SELECT * FROM (
          SELECT c.*, ROWNUM rn FROM (
            SELECT * FROM customers WHERE branch_code = :branch ORDER BY full_name
          ) c WHERE ROWNUM <= :last
        ) WHERE rn > :first
        """, nativeQuery = true)
    List<Customer> findPageForBranch(@Param("branch") String branch, @Param("first") int first, @Param("last") int last);

    @Query(value = "SELECT * FROM customers WHERE middle_name = ''", nativeQuery = true)
    List<Customer> findWithoutMiddleName();

    @Query(value = "SELECT NVL(middle_name, '-') FROM customers WHERE id = :id", nativeQuery = true)
    String middleNameOrDash(@Param("id") Long id);
}
