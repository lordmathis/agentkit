import os

from agentkit.agent import Agent

class PluginRegistry():
    _registry: dict[str, Agent] = {}

    @classmethod
    def discover_plugins(cls, plugins_dir: str):
        plugin_files = [f for f in os.listdir(plugins_dir) if f.endswith('.py') and not f.startswith('_')]
        for filename in plugin_files:
            path = os.path.join(plugins_dir, filename)
            cls.register_plugin(path)

    @classmethod
    def register_plugin(cls, path: str):
        module_name = os.path.basename(path)[:-3]
        module_path = path.replace('/', '.').removesuffix('.py')
        module = __import__(module_path, fromlist=[''])
        if isinstance(module, Agent):
            cls._registry[module_name] = module

    @classmethod
    def get_plugin(cls, name: str) -> Agent | None:
        return cls._registry.get(name)
    
    @classmethod
    def list_plugins(cls) -> list[str]:
        return list(cls._registry.keys())
    