MAX_SC = 5
MAX_CAPAS = 10

def init_sistemas(max_sc: int = MAX_SC, max_capas: int = MAX_CAPAS) -> dict:
    """Create base dictionary for all constructive systems.

    Each system contains default solar absorptance and a pool of layers with
    placeholder values. Active layers are tracked per system through the
    ``capas_activas`` list, which starts with only the first layer enabled.

    Parameters
    ----------
    max_sc:
        Maximum number of constructive systems to initialise.
    max_capas:
        Maximum number of layers available for each system.
    """
    sistemas: dict[int, dict] = {}
    for sc_id in range(1, max_sc + 1):
        sistemas[sc_id] = {
            "absortancia": 0.8,
            "capas_activas": [1],
            "capas": {
                capa_id: {"material": None, "ancho": 0.1}
                for capa_id in range(1, max_capas + 1)
            },
        }
    return sistemas
