from shiny import ui, render, reactive
import enerhabitat as eh
import pandas as pd


def sc_server(input, output, session, dia_promedio_dataframe, soluciones_dataframe, sistemas):
    
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

