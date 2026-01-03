class GnostPlugin:
    """
    Base interface for GNOST plugins.

    Plugins extend GNOST behavior without modifying core logic.
    They receive a shared context (scan, graph, flow, etc.)
    and may generate additional insights or outputs.

    Plugin system is experimental and not yet public.
    """

    name = "base"

    def run(self, context):
        raise NotImplementedError
