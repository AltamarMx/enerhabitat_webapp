from shiny import ui, render, reactive
import pandas as pd
from shiny import ui, reactive


def capa_server(input, output, session, sistemas):
    # Mantener sincronizado el estado guardado con los valores de entrada
    @reactive.Effect
    def _sync_state():
        state = sistemas.get().copy()
        num_sc = input.num_sc()
        for sc_id in range(1, num_sc + 1):
            sc = state.setdefault(
                sc_id,
                {
                    "absortancia": 0.8,
                    "capas": {1: {"material": None, "ancho": 0.1}},
                    "capas_activas": [1],
                },
            )
            sc["absortancia"] = input[f"absortancia_{sc_id}"]()
            for c_id in sc.get("capas_activas", []):
                sc["capas"][c_id] = {
                    "material": input[f"material_capa_{sc_id}_{c_id}"](),
                    "ancho": input[f"ancho_capa_{sc_id}_{c_id}"](),
                }
            state[sc_id] = sc
        sistemas.set(state)

    # Restaurar valores almacenados cuando cambie la UI
    @reactive.Effect
    def _restore_inputs():
        state = sistemas.get()
        num_sc = input.num_sc()
        for sc_id in range(1, num_sc + 1):
            sc_info = state.get(sc_id, {})
            ui.update_numeric(
                f"absortancia_{sc_id}", value=sc_info.get("absortancia", 0.8)
            )
            capas_info = sc_info.get("capas", {})
            for c_id in sc_info.get("capas_activas", []):
                capa_info = capas_info.get(c_id, {})
                ui.update_select(
                    f"material_capa_{sc_id}_{c_id}",
                    selected=capa_info.get("material"),
                )
                ui.update_numeric(
                    f"ancho_capa_{sc_id}_{c_id}", value=capa_info.get("ancho", 0.1)
                )
            try:
                open_panel = str(input[f"capas_accordion_{sc_id}"]()[0])
                ui.update_accordion(id=f"capas_accordion_{sc_id}", show=open_panel)
            except Exception:
                return

