package dev.acbench.driver.adapter;

import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import net.fabricmc.loader.api.FabricLoader;

/**
 * Controls Meteor Client through its module/setting API. Uses reflection so the driver builds and runs
 * without Meteor on the classpath; only public, long-standing Meteor API is touched
 * ({@code Modules.get().get(name)}, {@code Module.settings}, {@code Setting.parse}).
 */
public class MeteorAdapter implements CheatClientAdapter {
	private static final String MODULES = "meteordevelopment.meteorclient.systems.modules.Modules";

	@Override
	public String id() {
		return "meteor";
	}

	@Override
	public boolean isPresent() {
		return FabricLoader.getInstance().isModLoaded("meteor-client");
	}

	@Override
	public void resetSettings(String module) throws AdapterException {
		Object settings = field(module(module), "settings");
		call(settings, "reset");
	}

	@Override
	public boolean applySetting(String module, String setting, String value) throws AdapterException {
		Object target = findSetting(module(module), setting);
		if (target == null) throw new AdapterException("module " + module + " has no setting " + setting);
		return (boolean) call(target, "parse", value);
	}

	@Override
	public void setEnabled(String module, boolean enabled) throws AdapterException {
		call(module(module), enabled ? "enable" : "disable");
	}

	@Override
	public Boolean isEnabled(String module) throws AdapterException {
		return (Boolean) call(module(module), "isActive");
	}

	@Override
	public List<Map<String, Object>> describeModules() {
		List<Map<String, Object>> out = new ArrayList<>();
		try {
			Object modules = Class.forName(MODULES).getMethod("get").invoke(null);
			for (Object module : (Collection<?>) call(modules, "getAll")) {
				Map<String, Object> m = new LinkedHashMap<>();
				m.put("name", String.valueOf(field(module, "name")));
				m.put("category", String.valueOf(field(module, "category")));
				m.put("description", String.valueOf(field(module, "description")));
				List<Map<String, Object>> settings = new ArrayList<>();
				for (Object group : (Iterable<?>) field(field(module, "settings"), "groups")) {
					for (Object setting : (Iterable<?>) group) {
						Map<String, Object> s = new LinkedHashMap<>();
						s.put("group", String.valueOf(field(group, "name")));
						s.put("name", String.valueOf(field(setting, "name")));
						s.put("type", setting.getClass().getSimpleName());
						s.put("value", String.valueOf(call(setting, "get")));
						s.put("default", String.valueOf(call(setting, "getDefaultValue")));
						Object suggestions = call(setting, "getSuggestions");
						if (suggestions instanceof Iterable<?> it) {
							List<String> values = new ArrayList<>();
							for (Object v : it) values.add(String.valueOf(v));
							if (!values.isEmpty() && values.size() <= 32) s.put("options", values);
						}
						settings.add(s);
					}
				}
				m.put("settings", settings);
				out.add(m);
			}
		} catch (Exception e) {
			out.add(Map.of("error", e.toString()));
		}
		return out;
	}

	private Object module(String name) throws AdapterException {
		try {
			Object modules = Class.forName(MODULES).getMethod("get").invoke(null);
			Object module = modules.getClass().getMethod("get", String.class).invoke(modules, name);
			if (module == null) throw new AdapterException("Meteor has no module named " + name);
			return module;
		} catch (AdapterException e) {
			throw e;
		} catch (Exception e) {
			throw new AdapterException("Meteor API not reachable", e);
		}
	}

	/** Accepts "setting" (first match in any group) or "group/setting". */
	private Object findSetting(Object module, String key) throws AdapterException {
		String group = null;
		String name = key;
		int slash = key.indexOf('/');
		if (slash >= 0) {
			group = key.substring(0, slash);
			name = key.substring(slash + 1);
		}
		for (Object g : (Iterable<?>) field(field(module, "settings"), "groups")) {
			if (group != null && !group.equalsIgnoreCase((String) field(g, "name"))) continue;
			for (Object s : (Iterable<?>) g) {
				if (name.equalsIgnoreCase((String) field(s, "name"))) return s;
			}
		}
		return null;
	}

	private static Object field(Object target, String name) throws AdapterException {
		try {
			return target.getClass().getField(name).get(target);
		} catch (ReflectiveOperationException e) {
			throw new AdapterException("missing field " + name + " on " + target.getClass().getName(), e);
		}
	}

	private static Object call(Object target, String name, Object... args) throws AdapterException {
		try {
			for (Method m : target.getClass().getMethods()) {
				if (m.getName().equals(name) && m.getParameterCount() == args.length) return m.invoke(target, args);
			}
			throw new AdapterException("missing method " + name + " on " + target.getClass().getName());
		} catch (ReflectiveOperationException e) {
			throw new AdapterException("calling " + name + " failed", e);
		}
	}
}
