# Stage 1: Build the shadow fat jar
FROM gradle:8.5-jdk21 AS builder
WORKDIR /app
COPY --chown=gradle:gradle . .
RUN gradle shadowJar --no-daemon

# Stage 2: Create the Flink job image for deployment
FROM flink:1.19.0-java17
WORKDIR /opt/flink
# Place the jar in usrlib/ for Flink's Application Mode deployment
COPY --from=builder /app/build/libs/flink-processor-1.0-SNAPSHOT.jar /opt/flink/usrlib/trend-detection-job.jar
