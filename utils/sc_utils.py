from shiny import ui, render, reactive
import enerhabitat as eh
import pandas as pd

def init_sistemas(max_sc: int, max_capas: int) -> dict:
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
                capa_id: {"material": None, "ancho": None}
                for capa_id in range(1, max_capas + 1)
            },
        }
    return sistemas

def sc_server(input, output, session, dia_promedio_dataframe, soluciones_dataframe, capas_activas):
    
    """
    ==================================================
                    Lo que funciona
    ==================================================
    """
    #   << Funciones auxiliares >>
    # Regresa lista de tuplas para el sc_id
    def sistemaConstructivo(sc_id):
        sc_info = sistemas.get().get(sc_id, {})
        capas_ids = sc_info.get("capas_activas", [])
        return [
            (input[f"material_capa_{sc_id}_{i}"](), input[f"ancho_capa_{sc_id}_{i}"]())
            for i in capas_ids
        ]
    
    # Resolver sistemas constructivos
    @reactive.Effect
    @reactive.event(input.resolver_sc)
    def calculate_solucion():
        # Solo se ejecuta cuando se presiona el botón resolver_sc
        num_sc = input.num_sc()
        datos = dia_promedio_dataframe.get()

        sol_data_list = []

        for sc_id in range(1, num_sc + 1):
            df = datos.copy()
            # Crear datos base para cada sistema constructivo
            sol_data = eh.Tsa(
                meanDay_dataframe=df,
                solar_absortance=float(input[f"absortancia_{sc_id}"]()),
                surface_tilt=float(input.tilt()),
                surface_azimuth=float(input.azimuth()),
            )

            # Obtener el sistema constructivo actual
            sc = sistemaConstructivo(sc_id)

            # Resolver para este sistema constructivo
            sol_data = eh.solveCS(sc, sol_data)

            # Agregar Ta e Is solo la primera vez
            if sc_id == 1:
                sol_data_list.append(
                    sol_data[["Tn", "DeltaTn", "Ta", "Ig", "Ib", "Id", "Is"]]
                )

            # Agregar identificador
            sub_sol = sol_data[["Tsa", "Ti"]].add_suffix(f"_{sc_id}")
            sol_data_list.append(sub_sol)

        # Combinar todos los resultados
        if sol_data_list:
            resultado = pd.concat(sol_data_list, axis=1)
            soluciones_dataframe.set(resultado)

