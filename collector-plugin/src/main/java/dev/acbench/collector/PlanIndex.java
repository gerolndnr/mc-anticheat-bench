package dev.acbench.collector;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import com.google.gson.FieldNamingPolicy;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;

/** The server's view of the run plan: what each trial id means and how its arena has to be prepared. */
final class PlanIndex {
	private static final Gson GSON = new GsonBuilder().setFieldNamingPolicy(FieldNamingPolicy.LOWER_CASE_WITH_UNDERSCORES).create();

	static final class PlanFile {
		String runId;
		List<TrialInfo> trials = new ArrayList<>();
	}

	static final class TrialInfo {
		String id;
		String scenario;
		String category;
		String variant;
		String phase;
		int rep;
		String arena;
		List<String> loadout = new ArrayList<>();
		List<TargetSpec> targets = new ArrayList<>();
	}

	/** A mob placed relative to the arena spawn: forward along +X, side along +Z. */
	static final class TargetSpec {
		String type = "minecraft:husk";
		String role = "target";
		double forward;
		double side;
		double up;
	}

	private final Map<String, TrialInfo> trials = new HashMap<>();
	final String runId;

	PlanIndex(Path file) throws IOException {
		PlanFile plan = GSON.fromJson(Files.readString(file), PlanFile.class);
		this.runId = plan.runId;
		for (TrialInfo trial : plan.trials) trials.put(trial.id, trial);
	}

	TrialInfo get(String id) {
		return trials.get(id);
	}

	int size() {
		return trials.size();
	}
}
