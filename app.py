import plotly.express as px
import enerhabitat as eh
import pandas as pd
import os

from datetime import date
from io import StringIO

from shiny import App, ui, render, reactive
from shinywidgets import output_widget, render_widget

from utils.card import side_card, PRECARGADOS_DIR, materiales


app_ui = ui.page_fluid(
    ui.page_sidebar(
        side_card(),
        ui.navset_card_tab(
            ui.nav_panel(
                "Resultados",
                ui.card(
                    ui.card_header("Temperatura"),
                    output_widget("sol_plot")
                ),
                ui.card(
                    ui.card_header("Irradiancia"),
                    output_widget("irr_plot")
                )
            ),
            ui.nav_panel(
                "Datos día promedio",
                ui.output_data_frame("dia_df"),
                ui.download_button("down_dia","Descargar datos")                  
            ),
            ui.nav_panel(
                "Datos resultados",
                ui.output_data_frame("sol_df"),
                ui.download_button("down_res", "Descargar datos")
            )
        ),
    )
)

def server(input, output, session):
    # Definición de variables "globales" para la app
    dia_promedio_dataframe = reactive.Value(pd.DataFrame())
    soluciones_dataframe = reactive.Value(pd.DataFrame())
    current_file = reactive.Value(None)

    # Diccionario para mantener el registro de capas por cada sistema constructivo
    capas_activas = reactive.Value({1: [1]})  # {sc_id : [capas]}

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

            # Agregar Ta solo la primera vez
            if sc_id == 1:
                sol_data_list.append(sol_data[["Tn", "DeltaTn", "Ta", "Ig", "Ib", "Id"]])

            # Agregar identificador
            sub_sol = sol_data[["Is","Tsa","Ti"]].add_suffix(f"_{sc_id}")
            sol_data_list.append(sub_sol)

        # Combinar todos los resultados
        if sol_data_list:
            resultado = pd.concat(sol_data_list,axis=1)
            soluciones_dataframe.set(resultado)        

    # Manejo de EPW's
    @reactive.Effect
    def _():
        # Manejar selección de archivo precargado
        if input.selector_archivo().startswith("precargado_"):
            file_name = input.selector_archivo().replace("precargado_", "", 1)
            file_path = os.path.join(PRECARGADOS_DIR, file_name)
            current_file.set(file_path)

    # Manejar archivo subido
    @reactive.Effect
    def _():  
        if input.selector_archivo() == "upload" and input.epw_file() is not None:
            file_info = input.epw_file()[0]
            current_file.set(file_info["datapath"])

    # Actualizar capas_activas cuando cambia el número de SC
    @reactive.Effect
    def _():
        num_sc = input.num_sc()
        current_capas = capas_activas.get().copy()

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

    # Recalcular meanDay cuando cambie el EPW o el mes
    @reactive.Effect
    def _():
        if current_file.get() is not None:
            df = eh.meanDay(epw_file=current_file.get(), month=input.mes())
            dia_promedio_dataframe.set(df)

    # Agregar capa
    @reactive.Effect
    def _():
        # Buscar qué botón de agregar capa fue presionado
        for sc_id in capas_activas():
            btn_id = f"add_capa_{sc_id}"
            if btn_id in input and input[btn_id]() > 0:
                current_capas = capas_activas().copy()
                capa_id=max(current_capas[sc_id])+1
                current_capas[sc_id].append(capa_id)
                capas_activas.set(current_capas)
                ui.insert_accordion_panel(
                    f"capas_accordion_{sc_id}",
                    ui.accordion_panel(
                        f"Capa {capa_id}",
                        ui.input_select(
                            f"material_capa_{sc_id}_{capa_id}", "Material:", materiales
                        ),
                        ui.input_numeric(
                            f"ancho_capa_{sc_id}_{capa_id}",
                            "Ancho (cm):",
                            value=0.1,
                            step=0.01,
                            min=0.01,
                        ),
                        ui.input_action_button(
                            f"remove_capa_{sc_id}_{capa_id}",
                            "Eliminar",
                            width="100%",
                            class_="btn-light",
                        ),
                    ),
                )

    # Eliminar capa
    @reactive.Effect
    def _():
        for sc_id, capas in capas_activas().items():
            for i in capas:
                if i == 1: continue
                btn_id = f"remove_capa_{sc_id}_{i}"
                if btn_id in input and input[btn_id]() > 0:
                    new_dict = capas_activas().copy()
                    new_dict[sc_id] = [c for c in capas if c != i]
                    capas_activas.set(new_dict)

    # ui para subir archivo
    @output
    @render.ui
    def ui_upload():    
        if input.selector_archivo() == "upload":
            return ui.input_file("epw_file", label="", accept=[".epw"], multiple=False)
        return None

    # ui de cada panel de SC
    @output 
    @render.ui
    def sc_panels():    
        sistemas = capas_activas()
        panels = []

        for sc_id in sistemas:
            panel = ui.nav_panel(
                f"SC {sc_id}",
                ui.input_numeric(
                    f"absortancia_{sc_id}",
                    "Absortancia:",
                    value=0.8,
                    min=0,
                    max=1,
                    step=0.01,
                    update_on="blur",
                ),
                ui.h5("Capas:"),
                ui.accordion(
                    ui.accordion_panel(
                    "Capa 1",
                    ui.input_select(
                        f"material_capa_{sc_id}_1", 
                        "Material:", 
                        materiales
                    ),
                    ui.input_numeric(
                        f"ancho_capa_{sc_id}_1", 
                        "Ancho (cm):", 
                        value=0.1, 
                        step=0.01, 
                        min=0.01
                    ),                  
        #            ui.input_action_button(
        #                f"remove_capa_{sc_id}_1",
        #                "Eliminar",
        #                width="100%",
        #                class_="btn-light"
        #            ) if capa_id > 1 else None
                ),
                    id=f"capas_accordion_{sc_id}",
                    open=f"Capa {max(sistemas[sc_id])}",
                    multiple=False,
                ),
                ui.input_task_button(
                    f"add_capa_{sc_id}",
                    "Agregar capa",
                    width="100%",
                    class_="btn-secondary",
                ),
            )
            panels.append(panel)

        return ui.navset_card_tab(*panels)

    #   << DataFrames >>
    @render.data_frame
    def sol_df():
        datos = soluciones_dataframe.get()
        if not datos.empty:
            display_df = datos.copy()
            display_df.insert(0, "Time", datos.index)
            return render.DataGrid(
                    display_df,
                    summary="Viendo filas {start} a {end} de {total}"
                )

        else:
            return None

    @render.data_frame
    def dia_df():
        datos = dia_promedio_dataframe.get()
        if not datos.empty:
            display_df = datos.copy()
            display_df.insert(0, "Time", datos.index)
            return render.DataGrid(
                display_df,
                summary="Viendo filas {start} a {end} de {total}"
                )

    #   << Gráficas >>
    # Temperaturas
    @render_widget
    def sol_plot():
        sol_data = soluciones_dataframe.get()
        dia_data = dia_promedio_dataframe.get()

        if dia_data.empty: return None

        if sol_data.empty:        
            # Gráfica de día promedio
            display_data = dia_data.copy()[::60]    # Cada segundo
            solucion_plot = px.scatter(
                data_frame=display_data,
                x=display_data.index,
                y=["Ta"],
                labels={'index':'Hora', 'value':'Temperatura (°C)'}
            )

        else :
            display_data=sol_data.copy()
            columnas = []
            for i in display_data.columns[1:]:
                if i.startswith("T"):
                    columnas.append(i)
            solucion_plot = px.scatter(
                data_frame=display_data,
                x=display_data.index,
                y=columnas
            )

        # Franja horizontal
        solucion_plot.add_hrect(
            y0=display_data["Tn"].mean()-display_data["DeltaTn"].mean(),
            y1=display_data["Tn"].mean()+display_data["DeltaTn"].mean(),
            fillcolor="lime",
            opacity=0.3,
            line_width=0
            )
        return solucion_plot

    # Irradiancia
    @render_widget
    def irr_plot():
        sol_data = soluciones_dataframe.get()
        dia_data = dia_promedio_dataframe.get()

        if dia_data.empty: return None

        if sol_data.empty:        
            # Gráfica solo con día promedio
            display_data = dia_data.copy()[::60]    # Cada segundo
            solucion_plot = px.scatter(
                data_frame=display_data,
                x=display_data.index,
                y=["Ig","Ib","Id"],
                labels={'index':'Hora', 'value':'Irradiancia (W/m²)'}
            )

        else :
            display_data=sol_data.copy()

            columnas = []
            for i in display_data.columns[1:]:
                if i.startswith("I"):
                    columnas.append(i)
            solucion_plot = px.scatter(
                data_frame=display_data,
                x=display_data.index,
                y=columnas
            )

        return solucion_plot

    #   << Descargas >>
    @render.download(
        filename=lambda: f"enerhabitat-meanday-{date.today().isoformat()}.csv"
    )
    def down_dia():
        down_data = dia_promedio_dataframe.get().copy()
        if down_data == None: return
        down_data.insert(0, "Time", down_data.index)
        buffer = StringIO()
        down_data.to_csv(buffer, index=False, encoding='utf-8-sig')
        buffer.seek(0)
        return buffer

    @render.download(
        filename=lambda: f"enerhabitat-{date.today().isoformat()}.csv"
    )
    def down_res():
        down_data = soluciones_dataframe.get().copy()
        if down_data == None: return
        down_data.insert(0, "Time", down_data.index)
        buffer = StringIO()
        down_data.to_csv(buffer, index=False, encoding='utf-8-sig')
        buffer.seek(0)
        return buffer

    #   << Funciones auxiliares >>
    # Regresa lista de tuplas para el sc_id
    def sistemaConstructivo(sc_id):
        return [
            (input[f"material_capa_{sc_id}_{i}"](), input[f"ancho_capa_{sc_id}_{i}"]())
            for i in ui_capas_activas().get(sc_id)
        ]

    # Creacion de accordion_panel de una capa
    def capa(sistema_id, capa_id):
        return ui.accordion_panel(
                    f"Capa {capa_id}",
                    ui.input_select(
                        f"material_capa_{sistema_id}_{capa_id}", 
                        "Material:", 
                        materiales
                    ),
                    ui.input_numeric(
                        f"ancho_capa_{sistema_id}_{capa_id}", 
                        "Ancho (cm):", 
                        value=0.1, 
                        step=0.01, 
                        min=0.01
                    ),                  
                    ui.input_action_button(
                        f"remove_capa_{sistema_id}_{capa_id}",
                        "Eliminar",
                        width="100%",
                        class_="btn-light"
                    ) if capa_id > 1 else None
                )

app = App(app_ui, server)
