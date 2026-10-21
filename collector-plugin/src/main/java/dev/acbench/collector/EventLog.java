package dev.acbench.collector;

import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.LinkedHashMap;
import java.util.Map;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import org.bukkit.Bukkit;

/** Append-only JSONL log; every line carries the server tick so the analysis can align events. Thread safe. */
final class EventLog implements AutoCloseable {
	private static final Gson GSON = new GsonBuilder().serializeNulls().disableHtmlEscaping().create();

	private final BufferedWriter writer;

	EventLog(Path file) throws IOException {
		Files.createDirectories(file.toAbsolutePath().getParent());
		this.writer = Files.newBufferedWriter(file, StandardCharsets.UTF_8, StandardOpenOption.CREATE, StandardOpenOption.APPEND);
	}

	void write(String type, Map<String, ?> data) {
		Map<String, Object> event = new LinkedHashMap<>();
		event.put("type", type);
		event.put("tick", Bukkit.getCurrentTick());
		event.put("time_ms", System.currentTimeMillis());
		event.putAll(data);
		String line = GSON.toJson(event);
		synchronized (this) {
			try {
				writer.write(line);
				writer.newLine();
				writer.flush();
			} catch (IOException ignored) {
				// Never let logging break the server; a missing line shows up as a gap in the analysis.
			}
		}
	}

	@Override
	public synchronized void close() throws IOException {
		writer.close();
	}
}
