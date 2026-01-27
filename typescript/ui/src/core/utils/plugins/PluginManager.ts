import { transform } from "lodash";
import { Plugin } from "../../types/plugins";

type PluginState = {
  isActivated: boolean;
  config: Plugin;
};
type Plugins = Record<string, PluginState>;

class PluginManager {
  private plugins: Plugins = {};
  /**
   * Calculated based on `plugins`. Used to trigger updates in `useSyncExternalStore`
   */
  private activePlugins: Plugin[] = [];
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

    this.produceActivePlugins();
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

  subscribe(listener: () => void) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
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
