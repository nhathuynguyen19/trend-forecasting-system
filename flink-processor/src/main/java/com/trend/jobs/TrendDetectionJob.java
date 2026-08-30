package com.trend.jobs;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.flink.api.common.eventtime.WatermarkStrategy;
import org.apache.flink.connector.kafka.source.KafkaSource;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import com.trend.source.KafkaConfig;
import com.trend.model.EventRecord;

public class TrendDetectionJob {

    public static void main(String[] args) throws Exception {
        // Set up the streaming execution environment
        final StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();

        // Retrieve configuration from environment variables (fallback to local dev defaults)
        String bootstrapServers = System.getenv().getOrDefault("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092");
        String topic = System.getenv().getOrDefault("KAFKA_TOPIC", "social.posts.raw");
        String groupId = System.getenv().getOrDefault("KAFKA_GROUP_ID", "flink-trend-detector");

        // Set up Kafka Source
        KafkaSource<String> kafkaSource = KafkaConfig.createKafkaSource(bootstrapServers, topic, groupId);

        // Read stream from Kafka
        DataStream<String> rawStream = env.fromSource(
                kafkaSource,
                WatermarkStrategy.noWatermarks(),
                "Kafka Source"
        );

        // Parse JSON message into EventRecord POJO
        ObjectMapper objectMapper = new ObjectMapper();
        DataStream<EventRecord> eventStream = rawStream.map(value -> {
            try {
                return objectMapper.readValue(value, EventRecord.class);
            } catch (Exception e) {
                // Return null on parsing errors to filter them out
                return null;
            }
        }).filter(record -> record != null);

        // Print to stdout for quick verification in logs
        eventStream.print("Flink Ingested Record");

        // Run the Flink job
        env.execute("SocialTrendAnalyzer-RealTime-Processor");
    }
}
