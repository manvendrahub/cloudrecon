package com.cloudrecon.web;

import com.cloudrecon.model.AppUser;
import com.cloudrecon.model.Repos.UserRepository;
import com.cloudrecon.security.JwtService;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/auth")
public class AuthController {
    public record LoginRequest(String email, String password) {}
    public record RegisterRequest(String name, String email, String password) {}
    public record AuthResponse(String token, String email, String name) {}

    private final UserRepository users;
    private final PasswordEncoder encoder;
    private final JwtService jwt;

    public AuthController(UserRepository users, PasswordEncoder encoder, JwtService jwt) {
        this.users = users; this.encoder = encoder; this.jwt = jwt;
    }

    @PostMapping("/login")
    public AuthResponse login(@RequestBody LoginRequest r) {
        AppUser u = users.findByEmail(r.email() == null ? "" : r.email().trim().toLowerCase()).orElse(null);
        if (u == null || r.password() == null || !encoder.matches(r.password(), u.passwordHash)) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Wrong email or password");
        }
        return new AuthResponse(jwt.create(u.email), u.email, u.name);
    }

    @PostMapping("/register")
    public AuthResponse register(@RequestBody RegisterRequest r) {
        if (r.email() == null || !r.email().contains("@") || r.password() == null || r.password().length() < 6) {
            throw new IllegalArgumentException("Enter a valid email and a password of at least 6 characters.");
        }
        String email = r.email().trim().toLowerCase();
        if (users.findByEmail(email).isPresent()) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "An account with this email already exists");
        }
        AppUser u = users.save(new AppUser(email, encoder.encode(r.password()), r.name() == null ? email : r.name()));
        return new AuthResponse(jwt.create(u.email), u.email, u.name);
    }
}
