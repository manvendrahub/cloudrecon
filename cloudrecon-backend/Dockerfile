# ---- Stage 1: Build ----
# Use the official Maven image that bundles Maven + Java 21 JDK together
FROM maven:3.9-eclipse-temurin-21-alpine AS build
WORKDIR /app

# Cache dependencies layer separately (re-downloads only if pom.xml changes)
COPY pom.xml .
RUN mvn -q dependency:go-offline -B

# Copy source and build
COPY src ./src
RUN mvn -q package -DskipTests -B

# ---- Stage 2: Runtime ----
FROM eclipse-temurin:21-jre-alpine
WORKDIR /app

# Non-root user for security
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

COPY --from=build /app/target/*.jar app.jar

# Directory for uploaded satellite files
RUN mkdir -p /app/data/files && chown -R appuser:appgroup /app/data
VOLUME /app/data

USER appuser
EXPOSE 8080

ENTRYPOINT ["java", "-jar", "app.jar"]
