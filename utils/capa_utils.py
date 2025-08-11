from shiny import ui, render, reactive
import pandas as pd

def capa_server(input, output, session, capas_activas, sc_state):
    # Mantener sincronizado el estado guardado con los valores de entrada
    @reactive.Effect
    def _sync_state():
        current_capas = capas_activas.get()
        state = {}
        for sc_id, capas in current_capas.items():
            absort = input[f"absortancia_{sc_id}"]()
            capas_dict = {}
            for c_id in capas:
                capas_dict[c_id] = {
                    "material": input[f"material_capa_{sc_id}_{c_id}"](),
                    "ancho": input[f"ancho_capa_{sc_id}_{c_id}"](),
                }
            state[sc_id] = {"absortancia": absort, "capas": capas_dict}

        sc_state.set(state)

    # Restaurar valores almacenados cuando cambie la UI
    @reactive.Effect
    def _restore_inputs():
        state = sc_state.get()
        capas = capas_activas.get()
        for sc_id, lista_capas in capas.items():
            sc_info = state.get(sc_id, {})
            
            ui.update_numeric(
                f"absortancia_{sc_id}", value=sc_info.get("absortancia", 0.8)
            )
            capas_info = sc_info.get("capas", {})
            for c_id in lista_capas:
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
                ui.update_accordion(
                    id=f"capas_accordion_{sc_id}", show=open_panel)
            except: 
                return