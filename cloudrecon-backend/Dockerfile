# ---- Stage 1: Build ----
FROM eclipse-temurin:21-jdk-alpine AS build
WORKDIR /app
COPY pom.xml .
COPY src ./src

# Install Maven and build the fat jar (skip tests for speed)
RUN apk add --no-cache maven \
 && mvn -q package -DskipTests

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
