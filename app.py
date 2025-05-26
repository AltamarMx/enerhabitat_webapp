import plotly.express as px
import enerhabitat as eh
import pandas as pd
import os

from shiny import App, ui, render, reactive
from shinywidgets import output_widget, render_widget

from utils.card import side_card, PRECARGADOS_DIR, materiales

app_ui = ui.page_fluid(
    ui.page_sidebar(
        side_card(),
        ui.navset_card_tab(
            ui.nav_panel(
                "Gráfica",
                output_widget("sol_plot"),
            ),
            ui.nav_panel("DataFrame", ui.output_data_frame("sol_df")),
        ),
    )
)

def server(input, output, session):
    data_frame = reactive.Value(None)
    current_file = reactive.Value(None)

    # Diccionario para mantener el registro de capas por cada sistema constructivo
    capas_activas = reactive.Value({1: [1]})  # {sc_id: [lista de capas]}

    # Actualizar capas_activas cuando cambia el número de SC
    @reactive.Effect
    def _():
        num_sc = input.num_sc()
        current_capas = capas_activas().copy()
        
        updated = False
        # Asegurar que tenemos entradas para todos los SC
        for sc_id in range(1, num_sc + 1):
            if sc_id not in current_capas:
                current_capas[sc_id] = [1]
                updated = True
        
        # Eliminar SC que ya no existen
        to_remove = [sc_id for sc_id in list(current_capas.keys()) if sc_id > num_sc]
        if to_remove:
            for sc_id in to_remove:
                del current_capas[sc_id]
            updated = True
        
        if updated:
            capas_activas.set(current_capas)
    
    @reactive.Effect
    @reactive.event(input.resolver_sc)
    def calculate_solucion():
        # Solo se ejecuta cuando se presiona el botón resolver_sc
        sol_data_list = []
        num_sc = input.num_sc()
        df = data_frame.get()
        sol_data_list.append(df)
        for sc_id in range(1, num_sc + 1):
            
            
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
            
            # Agregar identificador
            sub_sol = sol_data[["Is","Tsa","Ti"]].add_suffix(f"_{sc_id}")
            sol_data_list.append(sub_sol)
            
        # Combinar todos los resultados
        if sol_data_list:
            resultado = pd.concat(sol_data_list)
            data_frame.set(resultado)

    
    def sistemaConstructivo(sc_id):
        return [
            (input[f"material_capa_{sc_id}_{i}"](), input[f"ancho_capa_{sc_id}_{i}"]())
            for i in capas_activas().get(sc_id, [])
        ]
        
    
    # Manejo de EPW's
    @reactive.Effect
    def _():
        # Manejar selección de archivo precargado
        if input.selector_archivo().startswith("precargado_"):
            file_name = input.selector_archivo().replace("precargado_", "", 1)
            file_path = os.path.join(PRECARGADOS_DIR, file_name)
            current_file.set(file_path)

    @reactive.Effect
    def _():
        # Manejar archivo subido
        if input.selector_archivo() == "upload" and input.epw_file() is not None:
            file_info = input.epw_file()[0]
            current_file.set(file_info["datapath"])
    
    @reactive.Effect
    def _():
        if current_file() is not None:
            df = eh.meanDay(epw_file=current_file(), month=input.mes())
            data_frame.set(df)
            
    # Agregar capa
    @reactive.Effect
    def _():
        # Buscar qué botón de agregar capa fue presionado
        for sc_id in range(1, input.num_sc() + 1):
            btn_id = f"add_capa_{sc_id}"
            if btn_id in input and input[btn_id]() > 0:
                current_capas = capas_activas().get(sc_id, [1])
                nueva_capa = max(current_capas) + 1 if current_capas else 1
                
                new_dict = capas_activas().copy()
                new_dict[sc_id] = current_capas + [nueva_capa]
                capas_activas.set(new_dict)
                break

    # Eliminar capa
    @reactive.Effect
    def _():
        for sc_id, capas in capas_activas().items():
            for i in capas:
                btn_id = f"remove_capa_{sc_id}_{i}"
                if btn_id in input and input[btn_id]() > 0:
                    if len(capas) > 1:
                        new_dict = capas_activas().copy()
                        new_dict[sc_id] = [c for c in capas if c != i]
                        capas_activas.set(new_dict)
                    break

    @output
    @render.ui
    def ui_upload():
        # ui para subir archivo
        if input.selector_archivo() == "upload":
            return ui.input_file("epw_file", label="", accept=[".epw"], multiple=False)
        return None

    
    @output 
    @render.ui
    def sc_panels():
        num_sc = input.num_sc()
        panels = []

        for sc_id in range(1, num_sc + 1):
            panel = ui.nav_panel(
                f"SC {sc_id}",
                ui.input_numeric(
                    f"absortancia_{sc_id}", 
                    "Absortancia:", 
                    value=0.8, 
                    min=0, 
                    max=1,
                    step=0.01,
                    update_on="blur"
                ),
                ui.h5("Capas:"),
                help_ui_capas(sc_id),  # Usamos la función local
                ui.input_action_button(
                    f"add_capa_{sc_id}",
                    "Agregar capa",
                    width="100%",
                    class_="btn-secondary"
                )
            )
            panels.append(panel)

        return ui.navset_card_tab(*panels)
    
    def help_ui_capas(sc_id):
        """Función helper para generar la UI de capas para un SC específico"""
        panels = []
        for i in capas_activas().get(sc_id, [1]):
            panels.append(
                ui.accordion_panel(
                    f"Capa {i}",
                    ui.input_select(
                        f"material_capa_{sc_id}_{i}", 
                        "Material:", 
                        materiales
                    ),
                    ui.input_numeric(
                        f"ancho_capa_{sc_id}_{i}", 
                        "Ancho (cm):", 
                        value=0.1, 
                        step=0.01, 
                        min=0.01
                    ),                  
                    ui.input_action_button(
                        f"remove_capa_{sc_id}_{i}",
                        "Eliminar",
                        width="100%",
                        class_="btn-light"
                    ) if len(capas_activas().get(sc_id, [])) > 1 else None
                )
            )
        
        return ui.accordion(
            *panels,
            id=f"capas_accordion_{sc_id}",
            open=f"Capa {max(capas_activas().get(sc_id, [1]))}",
            multiple=False,
        )
    
    @render.data_frame
    def sol_df():
        return render.DataGrid(data_frame.get())

    
    @render_widget
    def sol_plot():
        sol_data = data_frame.get()
        if sol_data is None:
            return None
        
        if "Tsa_1" in sol_data.columns.values:
            solucion_plot = px.scatter(
                data_frame=sol_data,
                x=sol_data.index,
                y=["Ta", "Tsa_1", "Ti_1"]
            )
        else:
            solucion_plot = px.scatter(
                data_frame=sol_data,
                x=sol_data.index,
                y=["Ta"]
            )
        return solucion_plot
        

app = App(app_ui, server)
