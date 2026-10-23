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
 *   <li>{@code callback}: a listener interface of the anticheat's API (e.g. NoCheatPlus' NCPHook), implemented by a
 *       proxy and registered through a static method, for anticheats without a violation event.</li>
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
				// Registered one tick later: the anticheat's hook registry is only ready once it is enabled.
				case "callback" -> Bukkit.getScheduler().runTask(plugin, () -> registerCallbackSource(source));
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

	/**
	 * For anticheats that report violations through a listener interface instead of a Bukkit event (e.g. NoCheatPlus'
	 * NCPHook): implements {@code interface} with a proxy and passes it to the static method {@code register}
	 * ("pkg.Class.method"). {@code register_args} lists its arguments: "listener" for the proxy, "enum:pkg.Enum.CONSTANT",
	 * or a plain string. On every call of {@code callback}, {@code player}/{@code check}/{@code vl} pick an argument by
	 * index and follow a getter chain, e.g. "1.getName". All other interface methods, and the callback itself, return the
	 * neutral value of their type (false, 0, null; strings "acbench"), so the anticheat's own handling is never changed.
	 */
	private void registerCallbackSource(Map<?, ?> source) {
		String owner = (String) source.get("plugin");
		String interfaceName = String.valueOf(source.get("interface"));
		String register = String.valueOf(source.get("register"));
		String callback = String.valueOf(source.get("callback"));
		try {
			Plugin ac = owner == null ? null : Bukkit.getPluginManager().getPlugin(owner);
			ClassLoader loader = ac != null ? ac.getClass().getClassLoader() : plugin.getClass().getClassLoader();
			Class<?> listenerType = Class.forName(interfaceName, true, loader);
			String playerPath = (String) source.get("player");
			String checkPath = (String) source.get("check");
			String vlPath = (String) source.get("vl");
			Object listener = java.lang.reflect.Proxy.newProxyInstance(loader, new Class<?>[]{listenerType}, (proxy, method, args) -> {
				if (method.getName().equals(callback) && args != null) {
					flag("callback:" + listenerType.getSimpleName(), str(argPath(args, playerPath)), str(argPath(args, checkPath)),
							str(argPath(args, vlPath)), null);
				} else if (method.getName().equals("equals") && args != null && args.length == 1) {
					return proxy == args[0];
				} else if (method.getName().equals("hashCode")) {
					return System.identityHashCode(proxy);
				}
				return neutral(method.getReturnType());
			});
			int split = register.lastIndexOf('.');
			Class<?> registry = Class.forName(register.substring(0, split), true, loader);
			List<?> argSpecs = source.get("register_args") instanceof List<?> l ? l : List.of("listener");
			Object[] args = new Object[argSpecs.size()];
			for (int i = 0; i < args.length; i++) args[i] = registerArg(String.valueOf(argSpecs.get(i)), listener, loader);
			for (Method m : registry.getMethods()) {
				if (!m.getName().equals(register.substring(split + 1)) || m.getParameterCount() != args.length) continue;
				boolean fits = true;
				for (int i = 0; i < args.length; i++) fits &= m.getParameterTypes()[i].isInstance(args[i]);
				if (!fits) continue;
				m.invoke(null, args);
				plugin.getLogger().info("Listening for anticheat callback " + interfaceName + "." + callback);
				return;
			}
			plugin.getLogger().warning("No matching method " + register + " for flag callback");
		} catch (ReflectiveOperationException | RuntimeException e) {
			plugin.getLogger().warning("Flag callback " + interfaceName + " could not be registered: " + e);
		}
	}

	@SuppressWarnings({"unchecked", "rawtypes"})
	private static Object registerArg(String spec, Object listener, ClassLoader loader) throws ClassNotFoundException {
		if (spec.equals("listener")) return listener;
		if (spec.startsWith("enum:")) {
			String path = spec.substring(5);
			int split = path.lastIndexOf('.');
			return Enum.valueOf((Class<? extends Enum>) Class.forName(path.substring(0, split), true, loader), path.substring(split + 1));
		}
		return spec;
	}

	/** "1.getName" = argument 1, then getName(). */
	private static Object argPath(Object[] args, String path) {
		if (path == null || path.isBlank()) return null;
		int dot = path.indexOf('.');
		int index;
		try {
			index = Integer.parseInt(dot < 0 ? path : path.substring(0, dot));
		} catch (NumberFormatException e) {
			return null;
		}
		if (index < 0 || index >= args.length) return null;
		return dot < 0 ? args[index] : resolve(args[index], path.substring(dot + 1));
	}

	private static Object neutral(Class<?> type) {
		if (type == boolean.class) return false;
		if (type == String.class) return "acbench";
		if (type == int.class) return 0;
		if (type == long.class) return 0L;
		if (type == double.class) return 0.0;
		if (type == float.class) return 0f;
		if (type == short.class) return (short) 0;
		if (type == byte.class) return (byte) 0;
		if (type == char.class) return '\0';
		return null;
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
