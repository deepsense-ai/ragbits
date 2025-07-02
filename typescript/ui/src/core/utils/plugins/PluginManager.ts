import { Plugin } from "../../../types/plugins";

type PluginState = Record<string, { isActivated: boolean; config: Plugin }>;

class PluginManager {
  private plugins: PluginState = {};
  private listeners: Set<() => void> = new Set();

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
    if (plugin.config.onActivate) {
      plugin.config.onActivate();
    }
    this.notify();
  }

  deactivate(name: string) {
    const plugin = this.plugins[name];
    if (!plugin || !plugin.isActivated) {
      return;
    }

    plugin.isActivated = false;
    if (plugin.config.onDeactivate) {
      plugin.config.onDeactivate();
    }
    this.notify();
  }

  isPluginActivated(name: string): boolean {
    const plugin = this.plugins[name];
    return !!plugin && plugin.isActivated;
  }

  getPlugin(name: string): Plugin | null {
    const plugin = this.plugins[name];
    if (!plugin || !plugin.isActivated) {
      return null;
    }
    return plugin.config;
  }

  subscribe(listener: () => void) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private notify() {
    this.listeners.forEach((listener) => listener());
  }
}

export const pluginManager = new PluginManager();
