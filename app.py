import plotly.express as px
import enerhabitat as eh
import pandas as pd
import os

from datetime import date
from io import StringIO

from shiny import App, ui, render, reactive
from shinywidgets import output_widget, render_widget

from utils.card import init_sistemas, side_card, sc_paneles, PRECARGADOS_DIR, MAX_CAPAS, MAX_SC


app_ui = ui.page_fluid(
    ui.modal(
        "Esta es una versión beta de la interfaz web de EnerHabitat, no es fiable usarla",
        title="EnerHabitat sigue en desarrollo",
        easy_close=True,
        footer=None,
    ),
    ui.page_navbar(
        ui.nav_panel(
            "Resultados",
            ui.page_sidebar(
                ui.sidebar(
                    side_card(),
                    id="sidebar",
                    width=350,
                    position="right",
                ),
                ui.card(ui.card_header("Temperatura"), output_widget("sol_plot")),
                ui.card(ui.card_header("Irradiancia"), output_widget("irr_plot")),
            ),
        ),
        ui.nav_panel(
            "Datos día promedio",
            ui.output_data_frame("dia_df"),
            ui.download_button("down_dia", "Descargar datos", width="100%"),
        ),
        ui.nav_panel(
            "Datos resultados",
            ui.output_ui("ui_datos_res"),
            
        ),
        title="EnerHabitat",
        id="nav_bar",
    ),
)


def server(input, output, session):
    # Definición de variables "globales" para la app
    dia_promedio_dataframe = reactive.Value(pd.DataFrame())
    soluciones_dataframe = reactive.Value(pd.DataFrame())
    current_file = reactive.Value(None)

    # Diccionario para mantener el registro de capas por cada sistema constructivo
    sistemas = reactive.Value(init_sistemas())  
    # {sc_id : absortancia,
    #          capas_activas,
    #          capas: {capa_id: material, ancho}
    
    selected_sc = reactive.Value("SC 1")
    open_layers = reactive.Value({i: "Capa 1" for i in range(1, MAX_SC + 1)})

    """
    ==================================================
                Lo que a veces NO funciona
    ==================================================
    """
    @output
    @render.ui
    def ui_datos_res():
        if soluciones_dataframe.get().empty:
            return ui.h3("Aún no hay resultados para mostrar...")
        else:
            return [ui.output_data_frame("sol_df"),
            ui.download_button("down_res", "Descargar datos", width="100%")]

    # Actualizar capas_activas cuando cambia el número de SC
    @reactive.Effect
    def update_sistemas():
        sc_id = int(input.sc_seleccionado().replace("SC ", ""))
        paneles_abiertos = input[f"capas_accordion_{sc_id}"]()
        current_open = open_layers.get().copy()
        
        if paneles_abiertos is None or len(paneles_abiertos) == 0:
            paneles_abiertos = current_open[sc_id]
            
        else:
            if current_open[sc_id] != paneles_abiertos[0]:
                current_open[sc_id] = paneles_abiertos[0]
                open_layers.set(current_open)
            
        capa_id = int(current_open[sc_id].replace("Capa ", ""))
        current = sistemas.get().copy()

        updated = False
            
        material_sistema = current[sc_id]["capas"][capa_id]["material"]
        ancho_sistema = current[sc_id]["capas"][capa_id]["ancho"]
            
        if input[f"material_capa_{sc_id}_{capa_id}"]() != material_sistema:
            current[sc_id]["capas"][capa_id]["material"] = input[f"material_capa_{sc_id}_{capa_id}"]()
            updated = True
        
        if input[f"ancho_capa_{sc_id}_{capa_id}"]() != ancho_sistema:
            current[sc_id]["capas"][capa_id]["ancho"] = input[f"ancho_capa_{sc_id}_{capa_id}"]()
            updated = True
            
        if updated:
            sistemas.set(current)

    @reactive.Effect
    def _sync_selected_sc():
        selected_sc.set(input.sc_seleccionado())

    @reactive.Effect
    @reactive.event(input.num_sc)
    def _jump_to_new_sc():
        selected_sc.set(f"SC {input.num_sc()}")
         
    # ui del contenedor de sistemas constructivos
    @output
    @render.ui
    def ui_sistemas():
        num_sc = input.num_sc()
    
        return ui.navset_card_tab(
            *sc_paneles(num_sc, sistemas.get(), open_layers.get()),
            id="sc_seleccionado",
            selected=selected_sc.get(),
            )
    
    @reactive.Effect
    @reactive.event(input.add_capa)
    def _add_capa():   
        sc_id = input.sc_seleccionado().replace("SC ", "")
        sc_id = int(sc_id)
        current = sistemas.get().copy()
        
        if current[sc_id]["capas_activas"] < MAX_CAPAS:
            current[sc_id]["capas_activas"] += 1
            sistemas.set(current)

    @reactive.Effect
    @reactive.event(input.remove_capa)
    def _remove_capa():
        sc_id = input.sc_seleccionado().replace("SC ", "")
        sc_id = int(sc_id)
        current = sistemas.get().copy()
        if current[sc_id]["capas_activas"] > 1:
            nuevas_capas_activas = current[sc_id]["capas_activas"] - 1
            current[sc_id]["capas_activas"] = nuevas_capas_activas
            sistemas.set(current)

    #   << Funciones auxiliares >>
    # Regresa lista de tuplas para el sc_id
    def sistemaConstructivo(sc_id):
        capas = sistemas().get(sc_id)["capas"]
        capas_activas = sistemas().get(sc_id)["capas_activas"]
        return [
            (capas[capa_id]["material"], capas[capa_id]["ancho"])
            for capa_id in range(1, capas_activas+1)
        ]

    def subIndex(cadena):
        # Convertir numeros a subindice
        SUB = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
        cadena_mod = str(cadena).translate(SUB)
        cadena_mod.replace('_','')
        return cadena_mod
    
    """
    ==================================================
                    Lo que funciona
    ==================================================
    """
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

    # Manejo de EPW's
    @reactive.Effect
    def epw_precargado():
        # Manejar selección de archivo precargado
        if input.selector_archivo().startswith("precargado_"):
            file_name = input.selector_archivo().replace("precargado_", "", 1)
            file_path = os.path.join(PRECARGADOS_DIR, file_name)
            current_file.set(file_path)

    # Manejar archivo subido
    @reactive.Effect
    def epw_upload():
        if input.selector_archivo() == "upload" and input.epw_file() is not None:
            file_info = input.epw_file()[0]
            current_file.set(file_info["datapath"])

    # Recalcular meanDay cuando cambie el EPW o el mes
    @reactive.Effect
    def update_meanDay():
        if current_file.get() is not None:
            df = eh.meanDay(epw_file=current_file.get(), month=input.mes())
            dia_promedio_dataframe.set(df)

    # ui para subir archivo
    @output
    @render.ui
    def ui_upload():
        if input.selector_archivo() == "upload":
            return ui.input_file("epw_file", label="", accept=[".epw"], multiple=False)
        return None

    #   << DataFrames >>
    @render.data_frame
    def sol_df():
        datos = soluciones_dataframe.get().copy()
        datos.insert(0, "Time", datos.index)
        if not datos.empty:
            return render.DataGrid(datos, summary="Viendo filas {start} a {end} de {total}")
        else:
            return None

    @render.data_frame
    def dia_df():
        datos = dia_promedio_dataframe.get()
        if not datos.empty:
            display_df = datos.copy()
            display_df.insert(0, "Time", datos.index)
            return render.DataGrid(
                display_df, summary="Viendo filas {start} a {end} de {total}"
            )

    #   << Gráficas >>
    # Temperaturas
    @render_widget
    def sol_plot():
        sol_data = soluciones_dataframe.get()
        dia_data = dia_promedio_dataframe.get()

        if dia_data.empty:
            return None

        if sol_data.empty:
            # Gráfica de día promedio
            display_data = dia_data.copy()[::60]  # Cada segundo
            
            solucion_plot = px.scatter(
                data_frame=display_data,
                x=display_data.index,
                y=["Ta"],
                labels={"index": "Hora", "value": "°C", "variable": "Temperatura"},
            )

        else:
            display_data = sol_data.copy()
            columnas = []
            for i in display_data.columns[1:]:
                if i.startswith("T"):
                    columnas.append(i)

            # Limpieza de Tsa
            if not input.mostrar_Tsa():
                for i in columnas:
                    if i.startswith("Tsa"):
                        columnas.remove(i)

            solucion_plot = px.scatter(
                data_frame=display_data,
                x=display_data.index,
                y=columnas,
                labels={"index": "Hora", "value": "°C", "variable": "Temperatura"},
            )

        # Franja horizontal
        solucion_plot.add_hrect(
            y0=display_data["Tn"].mean() - display_data["DeltaTn"].mean(),
            y1=display_data["Tn"].mean() + display_data["DeltaTn"].mean(),
            fillcolor="lime",
            opacity=0.3,
            line_width=0,
        )
        return solucion_plot

    # Irradiancia
    @render_widget
    def irr_plot():
        sol_data = soluciones_dataframe.get()
        dia_data = dia_promedio_dataframe.get()

        if dia_data.empty:
            return None

        if sol_data.empty:
            # Gráfica solo con día promedio
            display_data = dia_data.copy()[::60]  # Cada segundo
            solucion_plot = px.scatter(
                data_frame=display_data,
                x=display_data.index,
                y=["Ig", "Ib", "Id"],
                labels={"index": "Hora", "value": "W/m²", "variable": "Irradiancia"},
            )

        else:
            display_data = sol_data.copy()

            columnas = []
            for i in display_data.columns[1:]:
                if i.startswith("I"):
                    columnas.append(i)
            solucion_plot = px.scatter(
                data_frame=display_data,
                x=display_data.index,
                y=columnas,
                labels={"index": "Hora", "value": "W/m²", "variable": "Irradiancia"},
            )

        return solucion_plot

    #   << Descargas >>
    @render.download(filename=lambda: f"enerhabitat-meanday-{date.today().isoformat()}.csv")
    def down_dia():
        down_data = dia_promedio_dataframe.get().copy()
        if down_data == None:
            return
        down_data.insert(0, "Time", down_data.index)
        buffer = StringIO()
        down_data.to_csv(buffer, index=False, encoding="utf-8-sig")
        buffer.seek(0)
        return buffer

    @render.download(filename=lambda: f"enerhabitat-{date.today().isoformat()}.csv")
    def down_res():
        down_data = soluciones_dataframe.get().copy()
        if down_data == None:
            return
        down_data.insert(0, "Time", down_data.index)
        buffer = StringIO()
        down_data.to_csv(buffer, index=False, encoding="utf-8-sig")
        buffer.seek(0)
        return buffer

   

app = App(app_ui, server)
