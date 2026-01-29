import { transform } from "lodash";
import { AnyPluginSlot, Plugin } from "../../types/plugins";
import { SlotName, StoredSlot } from "../../types/slots";

type PluginState = {
  isActivated: boolean;
  config: Plugin;
};
type Plugins = Record<string, PluginState>;

// Internal slot filler with plugin reference for cleanup
type RegisteredSlotFiller = StoredSlot & { pluginName: string };

class PluginManager {
  private plugins: Plugins = {};
  private activePlugins: Plugin[] = [];
  private slotFillers: Map<SlotName, RegisteredSlotFiller[]> = new Map();
  private listeners: Set<() => void> = new Set();

  // Caches for useSyncExternalStore (must return stable references)
  private slotFillersCache: Map<SlotName, StoredSlot[]> = new Map();
  private hasSlotFillersCache: Map<SlotName, boolean> = new Map();

  register(plugin: Plugin) {
    this.plugins[plugin.name] = {
      isActivated: false,
      config: plugin,
    };
    this.notify();
  }

  activate(name: string) {
    const plugin = this.plugins[name];

    if (!plugin || plugin.isActivated) {
      return;
    }

    plugin.isActivated = true;

    // Register plugin's slots
    if (plugin.config.slots) {
      for (const slot of plugin.config.slots) {
        this.registerSlot(name, slot);
      }
    }

    // Call custom activation logic
    if (plugin.config.onActivate) {
      plugin.config.onActivate();
    }

    this.produceActivePlugins();
    this.notify();
  }

  deactivate(name: string) {
    const plugin = this.plugins[name];
    if (!plugin || !plugin.isActivated) {
      return;
    }

    plugin.isActivated = false;

    // Unregister plugin's slots
    this.unregisterPluginSlots(name);

    // Call custom deactivation logic
    if (plugin.config.onDeactivate) {
      plugin.config.onDeactivate();
    }

    this.produceActivePlugins();
    this.notify();
  }

  isPluginActivated(name: string): boolean {
    const plugin = this.plugins[name];
    return !!plugin && plugin.isActivated;
  }

  getPlugin(name: string): PluginState | null {
    const plugin = this.plugins[name];
    if (!plugin || !plugin.isActivated) {
      return null;
    }
    return plugin;
  }

  getActivePlugins(): Plugin[] {
    return this.activePlugins;
  }

  // Slot management methods
  getSlotFillers(slot: SlotName): StoredSlot[] {
    const fillers = this.slotFillers.get(slot) ?? [];
    const cached = this.slotFillersCache.get(slot);

    // Return cached if equivalent (for useSyncExternalStore stability)
    if (
      cached &&
      cached.length === fillers.length &&
      cached.every((f, i) => f === fillers[i])
    ) {
      return cached;
    }

    this.slotFillersCache.set(slot, fillers);
    return fillers;
  }

  hasSlotFillers(slot: SlotName): boolean {
    const hasFillers = (this.slotFillers.get(slot)?.length ?? 0) > 0;
    const cached = this.hasSlotFillersCache.get(slot);

    if (cached === hasFillers) {
      return cached;
    }

    this.hasSlotFillersCache.set(slot, hasFillers);
    return hasFillers;
  }

  subscribe(listener: () => void) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private registerSlot(pluginName: string, slot: AnyPluginSlot) {
    const existing = this.slotFillers.get(slot.slot) ?? [];
    // Convert typed slot to stored slot format
    const filler: RegisteredSlotFiller = {
      slot: slot.slot,
      component: slot.component,
      priority: slot.priority,
      condition: slot.condition,
      pluginName,
    };
    existing.push(filler);
    existing.sort((a, b) => (b.priority ?? 0) - (a.priority ?? 0));
    this.slotFillers.set(slot.slot, existing);
  }

  private unregisterPluginSlots(pluginName: string) {
    for (const [slotName, fillers] of this.slotFillers.entries()) {
      const filtered = fillers.filter((f) => f.pluginName !== pluginName);
      this.slotFillers.set(slotName, filtered);
    }
  }

  private notify() {
    this.listeners.forEach((listener) => listener());
  }

  private produceActivePlugins() {
    this.activePlugins = transform<typeof this.plugins, Plugin[]>(
      this.plugins,
      (res, p) => {
        if (!p.isActivated) {
          return;
        }

        res.push(p.config);
      },
      [],
    );
  }
}

export const pluginManager = new PluginManager();
