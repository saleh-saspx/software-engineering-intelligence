package com.acme.crm;

import jakarta.persistence.*;

@Entity
@Table(name = "customers")
public class Customer {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    @Column(name = "national_id", nullable = false, unique = true, length = 10)
    private String nationalId;
    @Column(name = "full_name", nullable = false)
    private String fullName;
    @Column(name = "middle_name")
    private String middleName;
    @Column(name = "branch_code", length = 4)
    private String branchCode;
}
