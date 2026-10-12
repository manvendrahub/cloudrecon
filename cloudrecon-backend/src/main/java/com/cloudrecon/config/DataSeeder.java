package com.cloudrecon.config;

import com.cloudrecon.model.AppUser;
import com.cloudrecon.model.Repos.UserRepository;
import org.springframework.boot.CommandLineRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.crypto.password.PasswordEncoder;

@Configuration
public class DataSeeder {
    /** Creates the demo account the frontend login form is pre-filled with. */
    @Bean
    CommandLineRunner seedDemoUser(UserRepository users, PasswordEncoder encoder) {
        return args -> {
            if (users.findByEmail("researcher@cloudrecon.ai").isEmpty()) {
                users.save(new AppUser("researcher@cloudrecon.ai", encoder.encode("demo123"), "Research User"));
            }
        };
    }
}
