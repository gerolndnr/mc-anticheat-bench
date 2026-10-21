package dev.acbench.driver.adapter;

import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import net.fabricmc.loader.api.FabricLoader;

/**
 * Controls LiquidBounce (Nextgen) through its value system, like its ".value set" command:
 * {@code ModuleManager[name]} toggles a module, {@code value.setByString(string)} changes a setting. Setting names in the client config are value keys relative to the module, e.g.
 * {@code mode} or {@code mode.grim2371.someValue}. Uses reflection so the driver builds without LiquidBounce.
 */
public class LiquidBounceAdapter implements CheatClientAdapter {
	private static final String MODULE_MANAGER = "net.ccbluex.liquidbounce.features.module.ModuleManager";

	@Override
	public String id() {
		return "liquidbounce";
	}

	@Override
	public boolean isPresent() {
		return FabricLoader.getInstance().isModLoaded("liquidbounce");
	}

	@Override
	public void resetSettings(String module) throws AdapterException {
		for (Object value : values(module(module))) {
			String name = String.valueOf(call(value, "getName"));
			if (name.equalsIgnoreCase("Bind") || name.equalsIgnoreCase("Enabled")) continue;
			call(value, "restore");
		}
	}

	@Override
	public boolean applySetting(String module, String setting, String value) throws AdapterException {
		Object owner = module(module);
		String key = call(owner, "getKey") + "." + setting;
		Object target = null;
		// Searched below the module instead of via ConfigSystem.findValueByKey, which misses mode groups.
		for (Object candidate : values(owner)) {
			if (key.equalsIgnoreCase(String.valueOf(call(candidate, "getKey")))) {
				target = candidate;
				break;
			}
		}
		if (target == null) throw new AdapterException("LiquidBounce has no value " + key);
		try {
			call(target, "setByString", value);
			return true;
		} catch (AdapterException e) {
			return false;
		}
	}

	@Override
	public void setEnabled(String module, boolean enabled) throws AdapterException {
		call(module(module), "setEnabled", enabled);
	}

	@Override
	public Boolean isEnabled(String module) throws AdapterException {
		return (Boolean) call(module(module), "getEnabled");
	}

	@Override
	public List<Map<String, Object>> describeModules() {
		List<Map<String, Object>> out = new ArrayList<>();
		try {
			for (Object module : (Iterable<?>) singleton(MODULE_MANAGER)) {
				Map<String, Object> m = new LinkedHashMap<>();
				m.put("name", String.valueOf(call(module, "getName")));
				m.put("category", String.valueOf(call(module, "getCategory")));
				m.put("key", String.valueOf(call(module, "getKey")));
				List<Map<String, Object>> settings = new ArrayList<>();
				for (Object value : values(module)) {
					Map<String, Object> s = new LinkedHashMap<>();
					s.put("key", String.valueOf(call(value, "getKey")));
					s.put("type", value.getClass().getSimpleName());
					s.put("value", describeValue(value));
					List<String> modes = modeNames(value);
					if (!modes.isEmpty()) s.put("options", modes);
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

	private static String describeValue(Object value) {
		try {
			Object active = call(value, "getActiveMode");
			return String.valueOf(call(active, "getName"));
		} catch (AdapterException notAModeGroup) {
			try {
				return String.valueOf(call(value, "get"));
			} catch (AdapterException e) {
				return "?";
			}
		}
	}

	private static List<String> modeNames(Object value) {
		List<String> names = new ArrayList<>();
		try {
			for (Object mode : (Iterable<?>) call(value, "getModes")) names.add(String.valueOf(call(mode, "getName")));
		} catch (AdapterException | ClassCastException ignored) {
			// Not a mode group.
		}
		return names;
	}

	/** All values below the module, recursively (Kotlin Sequence). */
	private static List<Object> values(Object module) throws AdapterException {
		Object sequence = call(module, "collectValuesRecursively", "");
		List<Object> out = new ArrayList<>();
		for (Iterator<?> it = (Iterator<?>) call(sequence, "iterator"); it.hasNext(); ) out.add(it.next());
		return out;
	}

	private static Object module(String name) throws AdapterException {
		Object module = call(singleton(MODULE_MANAGER), "get", name);
		if (module == null) throw new AdapterException("LiquidBounce has no module named " + name);
		return module;
	}

	private static Object singleton(String className) throws AdapterException {
		try {
			return Class.forName(className).getField("INSTANCE").get(null);
		} catch (ReflectiveOperationException e) {
			throw new AdapterException("LiquidBounce API not reachable: " + className, e);
		}
	}

	private static Object call(Object target, String name, Object... args) throws AdapterException {
		try {
			for (Method m : target.getClass().getMethods()) {
				if (!m.getName().equals(name) || m.getParameterCount() != args.length) continue;
				if (args.length == 1 && args[0] instanceof String && m.getParameterTypes()[0] != String.class) continue;
				return m.invoke(target, args);
			}
			throw new AdapterException("missing method " + name + " on " + target.getClass().getName());
		} catch (ReflectiveOperationException e) {
			Throwable cause = e.getCause() != null ? e.getCause() : e;
			throw new AdapterException("calling " + name + " failed: " + cause, cause);
		}
	}
}
