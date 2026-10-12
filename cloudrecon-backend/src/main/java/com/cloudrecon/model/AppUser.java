package com.cloudrecon.model;

import jakarta.persistence.*;

@Entity
@Table(name = "users")
public class AppUser {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    public Long id;
    @Column(unique = true, nullable = false)
    public String email;
    @Column(nullable = false)
    public String passwordHash;
    public String name;

    protected AppUser() {}
    public AppUser(String email, String passwordHash, String name) {
        this.email = email; this.passwordHash = passwordHash; this.name = name;
    }
}
