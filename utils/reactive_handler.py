from shiny import ui, render, reactive
import enerhabitat as eh


def reactive_server(input, output, session, current_file, dia_promedio_dataframe, sistemas):

    # Recalcular meanDay cuando cambie el EPW o el mes
    @reactive.Effect
    def _():
        if current_file.get() is not None:
            df = eh.meanDay(epw_file=current_file.get(), month=input.mes())
            dia_promedio_dataframe.set(df)
            
    # Asegurar que existe un sistema para cada SC indicado en la UI
    @reactive.Effect
    def _():
        num_sc = input.num_sc()
        state = sistemas.get().copy()
        updated = False

        for sc_id in range(1, num_sc + 1):
            if sc_id not in state:
                state[sc_id] = {
                    "absortancia": 0.8,
                    "capas": {1: {"material": None, "ancho": 0.1}},
                    "capas_activas": [1],
                }
                updated = True

        # Eliminar SC que ya no existan
        to_remove = [sc_id for sc_id in list(state.keys()) if sc_id > num_sc]
        if to_remove:
            for sc_id in to_remove:
                del state[sc_id]
            updated = True

        if updated:
            sistemas.set(state)

