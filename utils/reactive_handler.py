from shiny import ui, render, reactive
import enerhabitat as eh

def reactive_server(input, output, session, current_file, dia_promedio_dataframe, sc_state, capas_activas):

    # Recalcular meanDay cuando cambie el EPW o el mes
    @reactive.Effect
    def _():
        if current_file.get() is not None:
            df = eh.meanDay(epw_file=current_file.get(), month=input.mes())
            dia_promedio_dataframe.set(df)
            
    # Actualizar capas_activas cuando cambia el número de SC
    @reactive.Effect
    def _():
        num_sc = input.num_sc()
        current_capas = capas_activas.get().copy()
        state = sc_state.get().copy()

        updated_capas = False
        updated_state = False

        # Asegurar que tenemos entradas para todos los SC
        for sc_id in range(1, num_sc + 1):
            if sc_id not in current_capas:
                current_capas[sc_id] = [1]
                updated_capas = True
            if sc_id not in state:
                state[sc_id] = {"absortancia": 0.8, "capas": {1: {"material": None, "ancho": 0.1}}}
                updated_state = True

        # Eliminar SC que ya no existen
        to_remove = [sc_id for sc_id in list(current_capas.keys()) if sc_id > num_sc]
        if to_remove:
            for sc_id in to_remove:
                del current_capas[sc_id]
                if sc_id in state:
                    del state[sc_id]
            updated_capas = True
            updated_state = True

        if updated_capas:
            capas_activas.set(current_capas)
        if updated_state:
            sc_state.set(state)
