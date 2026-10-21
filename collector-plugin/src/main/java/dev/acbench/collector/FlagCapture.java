package dev.acbench.collector;

import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.apache.logging.log4j.Level;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.core.LogEvent;
import org.apache.logging.log4j.core.LoggerContext;
import org.apache.logging.log4j.core.appender.AbstractAppender;
import org.apache.logging.log4j.core.config.Property;
import org.bukkit.Bukkit;
import org.bukkit.event.Event;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.plugin.Plugin;

/**
 * Turns anticheat alerts into {@code flag} events. Two source types, both configured per anticheat:
 * <ul>
 *   <li>{@code log}: a regex with named groups {@code player}, {@code check} and optionally {@code vl},
 *       matched against every console line. Works for almost every anticheat.</li>
 *   <li>{@code event}: a Bukkit event class of the anticheat's API plus getter chains such as
 *       {@code getPlayer.getName}, read via reflection so the collector needs no compile dependency.</li>
 * </ul>
 */
final class FlagCapture {
	private static final Pattern FORMATTING = Pattern.compile("\u001B\\[[0-9;]*[A-Za-z]|§[0-9a-fk-orx]", Pattern.CASE_INSENSITIVE);

	private final EventLog log;
	private final Plugin plugin;
	private final List<Pattern> logPatterns = new ArrayList<>();
	private AbstractAppender appender;

	FlagCapture(EventLog log, Plugin plugin) {
		this.log = log;
		this.plugin = plugin;
	}

	void configure(List<Map<?, ?>> sources) {
		for (Map<?, ?> source : sources) {
			String type = String.valueOf(source.get("type"));
			switch (type) {
				case "log" -> logPatterns.add(Pattern.compile(String.valueOf(source.get("pattern"))));
				case "event" -> registerEventSource(source);
				default -> plugin.getLogger().warning("Unknown flag source type " + type);
			}
		}
		if (!logPatterns.isEmpty()) attachAppender();
	}

	private void attachAppender() {
		appender = new AbstractAppender("AcBenchFlagCapture", null, null, true, Property.EMPTY_ARRAY) {
			@Override
			public void append(LogEvent event) {
				onLogLine(event.getMessage().getFormattedMessage());
			}
		};
		appender.start();
		LoggerContext context = (LoggerContext) LogManager.getContext(false);
		context.getConfiguration().getRootLogger().addAppender(appender, Level.ALL, null);
		context.updateLoggers();
	}

	void detach() {
		if (appender == null) return;
		LoggerContext context = (LoggerContext) LogManager.getContext(false);
		context.getConfiguration().getRootLogger().removeAppender(appender.getName());
		context.updateLoggers();
		appender.stop();
	}

	private void onLogLine(String raw) {
		if (raw == null) return;
		String line = FORMATTING.matcher(raw).replaceAll("");
		for (Pattern pattern : logPatterns) {
			Matcher m = pattern.matcher(line);
			if (!m.find()) continue;
			flag("log", group(m, "player"), group(m, "check"), group(m, "vl"), line);
			return;
		}
	}

	private static String group(Matcher m, String name) {
		try {
			String value = m.group(name);
			return value == null ? null : value.trim();
		} catch (IllegalArgumentException e) {
			return null;
		}
	}

	private void flag(String source, String player, String check, String vl, String raw) {
		Map<String, Object> data = new LinkedHashMap<>();
		data.put("source", source);
		data.put("player", player);
		data.put("check", check);
		data.put("vl", vl);
		data.put("raw", raw);
		log.write("flag", data);
	}

	@SuppressWarnings("unchecked")
	private void registerEventSource(Map<?, ?> source) {
		String className = String.valueOf(source.get("class"));
		String owner = (String) source.get("plugin");
		try {
			Plugin ac = owner == null ? null : Bukkit.getPluginManager().getPlugin(owner);
			ClassLoader loader = ac != null ? ac.getClass().getClassLoader() : plugin.getClass().getClassLoader();
			Class<? extends Event> eventClass = (Class<? extends Event>) Class.forName(className, true, loader);
			String playerPath = (String) source.get("player");
			String checkPath = (String) source.get("check");
			String vlPath = (String) source.get("vl");
			Bukkit.getPluginManager().registerEvent(eventClass, new Listener() {}, EventPriority.MONITOR, (listener, event) -> {
				if (!eventClass.isInstance(event)) return;
				flag("event:" + eventClass.getSimpleName(), str(resolve(event, playerPath)), str(resolve(event, checkPath)), str(resolve(event, vlPath)), null);
			}, plugin, false);
			plugin.getLogger().info("Listening for anticheat event " + className);
		} catch (ClassNotFoundException e) {
			plugin.getLogger().warning("Flag event class not found: " + className);
		}
	}

	/** Follows a dot separated chain of no-arg methods, e.g. "getCheck.getCheckName". */
	private static Object resolve(Object root, String path) {
		if (path == null || path.isBlank()) return null;
		Object current = root;
		for (String name : path.split("\\.")) {
			if (current == null) return null;
			try {
				Method method = current.getClass().getMethod(name);
				method.setAccessible(true);
				current = method.invoke(current);
			} catch (ReflectiveOperationException | RuntimeException e) {
				return null;
			}
		}
		return current;
	}

	private static String str(Object value) {
		return value == null ? null : String.valueOf(value);
	}
}
