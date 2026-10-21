package dev.acbench.driver.mixin;

import dev.acbench.driver.Driver;
import net.minecraft.client.multiplayer.MultiPlayerGameMode;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.player.Player;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** Counts every attack packet the client sends, no matter whether the driver or a cheat module triggered it. */
@Mixin(MultiPlayerGameMode.class)
public abstract class MultiPlayerGameModeMixin {
	@Inject(method = "attack", at = @At("HEAD"))
	private void acbench$onAttack(Player player, Entity target, CallbackInfo ci) {
		Driver driver = Driver.instance();
		if (driver != null) driver.countAttack();
	}
}
