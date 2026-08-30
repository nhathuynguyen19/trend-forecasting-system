package com.trend.model;

import java.io.Serializable;

public class EventRecord implements Serializable {
    private static final long serialVersionUID = 1L;

    private String id;
    private String text;
    private long timestamp;
    private String author;

    // Default constructor required by Flink POJO serialization
    public EventRecord() {
    }

    public EventRecord(String id, String text, long timestamp, String author) {
        this.id = id;
        this.text = text;
        this.timestamp = timestamp;
        this.author = author;
    }

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public String getText() {
        return text;
    }

    public void setText(String text) {
        this.text = text;
    }

    public long getTimestamp() {
        return timestamp;
    }

    public void setTimestamp(long timestamp) {
        this.timestamp = timestamp;
    }

    public String getAuthor() {
        return author;
    }

    public void setAuthor(String author) {
        this.author = author;
    }

    @Override
    public String toString() {
        return "EventRecord{" +
                "id='" + id + '\'' +
                ", text='" + text + '\'' +
                ", timestamp=" + timestamp +
                ", author='" + author + '\'' +
                '}';
    }
}
