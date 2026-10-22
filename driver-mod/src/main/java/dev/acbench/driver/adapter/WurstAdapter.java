package dev.acbench.driver.adapter;

import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import com.google.gson.JsonElement;
import com.google.gson.JsonPrimitive;

import net.fabricmc.loader.api.FabricLoader;

/**
 * Controls Wurst Client through its hack list: {@code WurstClient.INSTANCE.getHax().getHackByName(name)} toggles a hack
 * via {@code setEnabled}, and every setting is changed through {@code fromJson}, the same path Wurst uses to load its
 * settings file. That works for sliders (numbers), checkboxes (true/false) and enum settings (the mode's display name,
 * e.g. "Mini Jump") alike. Setting names are Wurst's, case-insensitive. Uses reflection so the driver builds without
 * Wurst.
 */
public class WurstAdapter implements CheatClientAdapter {
	private static final String WURST = "net.wurstclient.WurstClient";

	@Override
	public String id() {
		return "wurst";
	}

	@Override
	public boolean isPresent() {
		return FabricLoader.getInstance().isModLoaded("wurst");
	}

	@Override
	public void resetSettings(String module) throws AdapterException {
		for (Object setting : settings(hack(module)).values()) call(setting, "resetToDefault");
	}

	@Override
	public boolean applySetting(String module, String setting, String value) throws AdapterException {
		Object target = settings(hack(module)).get(setting.toLowerCase());
		if (target == null) throw new AdapterException("Wurst hack " + module + " has no setting " + setting);
		JsonPrimitive wanted = json(value);
		call(target, "fromJson", wanted);
		// fromJson silently ignores values of the wrong type or out of range; reading back tells whether it took.
		return matches((JsonElement) call(target, "toJson"), wanted);
	}

	@Override
	public void setEnabled(String module, boolean enabled) throws AdapterException {
		Object hack = hack(module);
		call(hack, "setEnabled", enabled);
		// Wurst refuses to enable hacks blocked by its TooManyHax hack; report that instead of measuring nothing.
		if (enabled && !(boolean) call(hack, "isEnabled")) throw new AdapterException("Wurst did not enable " + module);
	}

	@Override
	public Boolean isEnabled(String module) throws AdapterException {
		return (Boolean) call(hack(module), "isEnabled");
	}

	@Override
	public List<Map<String, Object>> describeModules() {
		List<Map<String, Object>> out = new ArrayList<>();
		try {
			for (Object hack : (Collection<?>) call(hax(), "getAllHax")) {
				Map<String, Object> m = new LinkedHashMap<>();
				m.put("name", String.valueOf(call(hack, "getName")));
				m.put("category", String.valueOf(call(hack, "getCategory")));
				m.put("description", String.valueOf(call(hack, "getDescription")));
				List<Map<String, Object>> settings = new ArrayList<>();
				for (Object setting : settings(hack).values()) {
					Map<String, Object> s = new LinkedHashMap<>();
					s.put("name", String.valueOf(call(setting, "getName")));
					s.put("type", setting.getClass().getSimpleName());
					s.put("value", String.valueOf(call(setting, "toJson")));
					Object values = hasMethod(setting, "getValues") ? call(setting, "getValues") : null;
					if (values instanceof Object[] modes) {
						// Enum settings: the display names are what fromJson accepts.
						List<String> options = new ArrayList<>();
						for (Object option : modes) options.add(String.valueOf(option));
						s.put("options", options);
						if (hasMethod(setting, "getDefaultSelected")) s.put("default", String.valueOf(call(setting, "getDefaultSelected")));
					} else if (hasMethod(setting, "getMinimum")) {
						s.put("min", call(setting, "getMinimum"));
						s.put("max", call(setting, "getMaximum"));
						s.put("default", call(setting, "getDefaultValue"));
					} else if (hasMethod(setting, "isCheckedByDefault")) {
						s.put("default", call(setting, "isCheckedByDefault"));
					}
					settings.add(s);
				}
				m.put("settings", settings);
				out.add(m);
			}
		} catch (Exception e) {
			out.add(Map.of("error", e.toString()));
		}
		return out;
	}

	private static JsonPrimitive json(String value) {
		if (value.equalsIgnoreCase("true") || value.equalsIgnoreCase("false")) return new JsonPrimitive(Boolean.parseBoolean(value));
		try {
			return new JsonPrimitive(Double.parseDouble(value));
		} catch (NumberFormatException e) {
			return new JsonPrimitive(value);
		}
	}

	private static boolean matches(JsonElement actual, JsonPrimitive wanted) {
		if (actual == null || !actual.isJsonPrimitive()) return false;
		JsonPrimitive got = actual.getAsJsonPrimitive();
		if (wanted.isNumber() && got.isNumber()) return Math.abs(got.getAsDouble() - wanted.getAsDouble()) < 1e-6;
		if (wanted.isBoolean() && got.isBoolean()) return got.getAsBoolean() == wanted.getAsBoolean();
		return got.getAsString().equalsIgnoreCase(wanted.getAsString());
	}

	private Object hax() throws AdapterException {
		try {
			Object wurst = Class.forName(WURST).getField("INSTANCE").get(null);
			return call(wurst, "getHax");
		} catch (AdapterException e) {
			throw e;
		} catch (Exception e) {
			throw new AdapterException("Wurst API not reachable", e);
		}
	}

	private Object hack(String name) throws AdapterException {
		Object hack = call(hax(), "getHackByName", name);
		if (hack == null) throw new AdapterException("Wurst has no hack named " + name);
		return hack;
	}

	@SuppressWarnings("unchecked")
	private static Map<String, Object> settings(Object hack) throws AdapterException {
		return (Map<String, Object>) call(hack, "getSettings");
	}

	private static boolean hasMethod(Object target, String name) {
		for (Method m : target.getClass().getMethods()) {
			if (m.getName().equals(name) && m.getParameterCount() == 0) return true;
		}
		return false;
	}

	private static Object call(Object target, String name, Object... args) throws AdapterException {
		try {
			for (Method m : target.getClass().getMethods()) {
				if (!m.getName().equals(name) || m.getParameterCount() != args.length) continue;
				if (args.length == 1 && !m.getParameterTypes()[0].isInstance(args[0])
						&& !(m.getParameterTypes()[0] == boolean.class && args[0] instanceof Boolean)) continue;
				return m.invoke(target, args);
			}
			throw new AdapterException("missing method " + name + " on " + target.getClass().getName());
		} catch (ReflectiveOperationException e) {
			throw new AdapterException("calling " + name + " failed", e);
		}
	}
}
