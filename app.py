from htmltools.tags import footer
import plotly.express as px
import enerhabitat as eh
import pandas as pd

import os
from datetime import date

from shiny import App, ui, render, reactive
from shinywidgets import output_widget, render_widget

from utils.card import (
    init_sistemas,
    side_card,
    sc_paneles,
    build_img_uri,
    PRECARGADOS_DIR,
    MAX_CAPAS,
)

from utils.extraer import get_git_info

commit_hash, branch = get_git_info(short=True)
build_text = f"{commit_hash} ({branch})"

footer_tag = ui.tags.footer(
    ui.hr(),
    ui.tags.small(build_text),
    class_="container-fluid py-2 text-muted"
)

eh.Nx = 200

app_ui = ui.page_fluid(
    ui.modal(
        "Esta es una versión beta de la interfaz web de EnerHabitat, puede presentar fallas al usarla.",
        "Comentarios a Guillermo Barrios gbv@ier.unam.mx",
        title="EnerHabitat sigue en desarrollo.",
        easy_close=True,
        footer=footer_tag,
    ),
    ui.page_navbar(
        ui.nav_panel(
            "EnerHabitat",
            ui.page_sidebar(
                ui.sidebar(
                    side_card(),
                    id="sidebar",
                    width=350,
                    # position="right",
                ),
                ui.output_ui("ui_graficas_eh"),
            ),
        ),
        ui.nav_panel(
            "Métricas",
            ui.output_ui("ui_metricas"),
        ),
        ui.nav_panel(
            "Resultados",
            ui.output_ui("ui_dataframes"),
        ),
        title=ui.tags.img(
                src=build_img_uri("icono-EnerHabitat.png"),
                alt="EnerHabitat",
                style="height: 40px;"
            ),
    ),
    footer="Hola mundo"
)


def server(input, output, session):
    # Definición de variables "globales" para la app
    dia_promedio_dataframe = reactive.Value(pd.DataFrame())
    soluciones_dataframe = reactive.Value(pd.DataFrame())
    current_file = reactive.Value(None)

    aire_simulacion = reactive.Value(None)
    metricas = reactive.Value(pd.DataFrame())
    
    # Diccionario para datos de cada sistema constructivo
    sistemas = reactive.Value(init_sistemas())
    """
    sc_id : {
        absortancia,
        capas_activas,
        capa_abierta,
        capas: {capa_id: material, ancho}
        FD,
        FDsa,
        TR,
        ET
    }"""
    
    """
    ================================
           EnerHabitat paquete          
    ================================
    """
    # Recalcular meanDay cuando cambie el EPW o el mes
    @reactive.Effect
    def update_meanDay():
        if current_file.get() is not None:
            df = eh.meanDay(epw_file=current_file.get(), month=input.mes())
            dia_promedio_dataframe.set(df)

    # Resolver sistemas constructivos
    @reactive.Effect
    @reactive.event(input.resolver_sc) # Solo se ejecuta cuando se presiona el botón resolver_sc
    def calculate_solucion():
        num_sc = input.num_sc()
        aire = bool(int(input.aire_acondicionado()))

        # Impedir bloqueos del botón cuando falten datos o ocurra un error
        if dia_promedio_dataframe.get().empty:
            ui.notification_show(
                "Selecciona un archivo EPW y mes antes de calcular.",
                type="warning",
            )
            return
        
        cm_sistema = []
        cm_absortancia = []
        cm_FD = []
        cm_FDsa = []
        cm_TR = []
        cm_ET = []
        cm_Eenf = []
        cm_Ecal = []
        cm_Etotal = []

        with ui.Progress(min=1, max=num_sc * 2 + 2) as progreso:
            try:
                progreso.set(message="Calculando...", detail="Cargando datos", value=1)

                datos_dia_promedio = dia_promedio_dataframe.get().copy()
                resultados_df = pd.DataFrame()

                for sc_id in range(1, num_sc + 1):
                    progreso.set(detail=f"Tsa Sistema Constructivo {sc_id}", value=progreso.value + 1)

                    c_absortancia = float(input[f"absortancia_{sc_id}"]())

                    # Crear datos Tsa para cada sistema constructivo
                    Tsa_df = eh.Tsa(
                        meanDay_dataframe=datos_dia_promedio,
                        solar_absortance=c_absortancia,
                        surface_tilt=float(input.tilt()),
                        surface_azimuth=float(input.azimuth()),
                    )

                    # Obtener el sistema constructivo actual
                    sc = sistemaConstructivo(sc_id)
                    cm_sistema.append(sistemaConstructivo_str(sc_id))
                    cm_absortancia.append(c_absortancia)

                    # Resolver para este sistema constructivo
                    progreso.set(detail=f"Ti Sistema Constructivo {sc_id}", value=progreso.value + 1)

                    # Solución y métricas dependiendo de AC
                    if aire==True:
                        solve_df, Qcool, Qheat = eh.solveCS(sc, Tsa_df, AC= True)
                        cm_Eenf.append(Qcool)
                        cm_Ecal.append(Qheat)
                        cm_Etotal.append(Qcool+Qheat)
                        cm_ET.append(0)
                    else:
                        solve_df, ET = eh.solveCS(sc, Tsa_df, energia=True)
                        cm_Eenf.append(0)
                        cm_Ecal.append(0)
                        cm_Etotal.append(0)
                        cm_ET.append(ET)

                    # Crear subconjunto con Is, Tsa y Ti
                    solve_df = Tsa_df[["Tsa"]].join(solve_df, how="right")

                    # Calcular métricas
                    deltaTi = solve_df.Ti.max() - solve_df.Ti.min()

                    cm_FD.append(deltaTi/(Tsa_df.Ta.max() - Tsa_df.Ta.min()))
                    cm_FDsa.append(deltaTi/(Tsa_df.Tsa.max() - Tsa_df.Tsa.min()))

                    Tr_comp =(solve_df.Ti.idxmax() - Tsa_df.Ta.idxmax()).components
                    cm_TR.append(f"{Tr_comp.hours:02}:{Tr_comp.minutes:02}")

                    # Agregar info de Tsa solo la primera vez
                    if sc_id == 1:
                        resultados_df = Tsa_df[["Tn", "DeltaTn", "Ta", "Ig", "Ib", "Id", "Is"]]

                    # Agregar columnas con sufijo
                    solve_df = solve_df.add_suffix(f"_{sc_id}")
                    resultados_df = resultados_df.join(solve_df, how="right")

                met = {"SC\n[material : m]" : cm_sistema,
                        "a\n[-]": cm_absortancia,
                        "Eenf\n[Wh/m²]": cm_Eenf,
                        "Ecal\n[Wh/m²]": cm_Ecal,
                        "Etotal\n[Wh/m²]": cm_Etotal,
                        "FD\n[-]": cm_FD,
                        "FDsa\n[-]": cm_FDsa,
                        "TR\n[HH:MM]": cm_TR,
                        "ET\n[Wh/m²]": cm_ET
                        }
                metricas_df = pd.DataFrame(met).round(3)

                # Actualizar variables reactivas
                aire_simulacion.set(aire)
                soluciones_dataframe.set(resultados_df)
                metricas.set(metricas_df)
                progreso.set(detail="Completo :D", value=progreso.value + 1)
            except Exception as e:
                ui.notification_show(
                    f"Error al resolver los sistemas constructivos: {e}",
                    type="error",
                )

    """
    ================================
          Funciones auxiliares          
    ================================
    """
    # Regresa lista de tuplas de SC para el sc_id
    def sistemaConstructivo(sc_id):
        capas = sistemas().get(sc_id)["capas"]
        capas_activas = sistemas().get(sc_id)["capas_activas"]
        return [
            (capas[capa_id]["material"], capas[capa_id]["ancho"])
            for capa_id in range(1, capas_activas + 1)
        ]

    def sistemaConstructivo_str(sc_id):
        capas = sistemas().get(sc_id)["capas"]
        capas_activas = sistemas().get(sc_id)["capas_activas"]
        aux = []
        for capa_id in range(1, capas_activas + 1):
            material = capas[capa_id]["material"]
            ancho = capas[capa_id]["ancho"]
            aux.append(f"{material} : {ancho}")
        return "\n".join(aux)
        
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

    # Actualizar capas_activas cuando cambia el número de SC
    @reactive.Effect
    def update_sistemas():
        sc_id = int(input.sc_seleccionado().replace("SC ", ""))
        paneles_abiertos = input[f"capas_accordion_{sc_id}"]()
        current = sistemas.get().copy()

        current_open = current[sc_id]["capa_abierta"]

        if paneles_abiertos is None or len(paneles_abiertos) == 0:
            paneles_abiertos = current_open[sc_id]

        else:
            if current_open != paneles_abiertos[0]:
                current_open = paneles_abiertos[0]
                current[sc_id]["capa_abierta"] = current_open
                sistemas.set(current)

        capa_id = int(current_open.replace("capa_", ""))

        updated = False

        material_sistema = current[sc_id]["capas"][capa_id]["material"]
        ancho_sistema = current[sc_id]["capas"][capa_id]["ancho"]

        if input[f"material_capa_{sc_id}_{capa_id}"]() != material_sistema:
            current[sc_id]["capas"][capa_id]["material"] = input[f"material_capa_{sc_id}_{capa_id}"]()
            updated = True

        if input[f"ancho_capa_{sc_id}_{capa_id}"]() != ancho_sistema:
            current[sc_id]["capas"][capa_id]["ancho"] = input[f"ancho_capa_{sc_id}_{capa_id}"]()
            updated = True

        if input[f"absortancia_{sc_id}"]() != current[sc_id]["absortancia"]:
            current[sc_id]["absortancia"] = input[f"absortancia_{sc_id}"]()
            updated = True

        if updated:
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

    @reactive.Effect
    @reactive.event(input.add_capa)
    def _add_capa():
        sc_id = input.sc_seleccionado().replace("SC ", "")
        sc_id = int(sc_id)
        current = sistemas.get().copy()

        if current[sc_id]["capas_activas"] < MAX_CAPAS:
            current[sc_id]["capas_activas"] += 1
            sistemas.set(current)
    
    # Convertir numeros a subindice
    def subIndex(cadena):
        SUB = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
        cadena_mod = str(cadena).translate(SUB)
        cadena_mod.replace('_','')
        return cadena_mod
    

    """
    ********************************
            UI's y outputs          
    ********************************
    """

    # ui del contenedor de sistemas constructivos
    @output
    @render.ui
    def ui_sistemas():
        num_sistemas = input.num_sc()
        try:
            selected = input.sc_seleccionado()
        except:
            selected = f"SC {num_sistemas}"
            
        return ui.navset_card_tab(
            *sc_paneles(num_sistemas, sistemas.get()),
            id = "sc_seleccionado",
            selected=selected
            )

    # ui de métricas
    @output
    @render.ui
    def ui_metricas():
        if soluciones_dataframe.get().empty:
            return "Aún no hay métricas...\nHaz una simulación para empezar"
        
        else:
            return ui.output_data_frame("metricas_table")
    
    # ui para subir archivo
    @output
    @render.ui
    def ui_upload():
        if input.selector_archivo() == "upload":
            return ui.input_file("epw_file", label="", accept=[".epw"], multiple=False)
        return None
    
    @output
    @render.ui
    def ui_dataframes():
        if dia_promedio_dataframe.get().empty:
            return "Aún no hay datos para mostrar..."
        else:
            if soluciones_dataframe.get().empty:
                return [
                    ui.output_data_frame("dia_df"),
                    ui.download_button("down_dia", "Descargar datos", width="100%"),
                ]

            else:
                return [
                    ui.output_data_frame("sol_df"),
                    ui.download_button("down_res", "Descargar datos", width="100%"),
                ]
            
    @output
    @render.ui
    def ui_graficas_eh():
        if aire_simulacion.get():
            return [
                    ui.card(ui.card_header("Energía"), output_widget("energia_plot")),
                    ui.card(ui.card_header("Irradiancia"), output_widget("irr_plot"))
                ]
        else:
            return [
                    ui.card(ui.card_header("Temperatura"), output_widget("temperatura_plot")),
                    ui.card(ui.card_header("Irradiancia"), output_widget("irr_plot"))
                ]

    """
    ================================
        DataFrames (Data Grids)          
    ================================
    """
    
    @render.data_frame
    def metricas_table():
        current =  metricas.get().copy()
        aire = aire_simulacion.get()
        
        if aire==True:
            display_metricas_df = current[["SC\n[material : m]" ,"a\n[-]", "Eenf\n[Wh/m²]", "Ecal\n[Wh/m²]", "Etotal\n[Wh/m²]"]]
                    
        else:
            display_metricas_df = current[["SC\n[material : m]","a\n[-]","FD\n[-]","FDsa\n[-]","TR\n[HH:MM]","ET\n[Wh/m²]"]]
            
        return render.DataTable(display_metricas_df, width="100%")
    
    # DataGrid del día promedio
    @render.data_frame
    def dia_df():
        datos = dia_promedio_dataframe.get().copy()
        if not datos.empty:
            show_datos = datos[['Tn', 'DeltaTn', 'Ta', 'Ig', 'Ib', 'Id']].round(2)
            show_datos.insert(0, "Time", show_datos.index)
            return render.DataGrid(
                data=show_datos, width="100%", summary="Viendo filas {start} a {end} de {total}"
            )

    # DataGrid de la Tsa y Ti
    @render.data_frame
    def sol_df():
        datos = soluciones_dataframe.get().copy()
        if not datos.empty:
            datos = datos.round(2)
            datos.insert(0, "Time", datos.index)
            return render.DataGrid(
                data=datos, width="100%", summary="Viendo filas {start} a {end} de {total}"
            )
        else:
            return None


    """
    ================================
            Gráficas (Plotly)          
    ================================
    """
    # Energia (con AC)
    @render_widget
    def energia_plot():
        display_data =  metricas.get().copy()

        display_data.insert(0, "Sistema", display_data.index + 1)
        display_data.rename(inplace=True, columns={"Eenf\n[Wh/m²]" : "Eenf", "Ecal\n[Wh/m²]" : "Ecal", "Etotal\n[Wh/m²]" : "Etotal"})
        display_data = display_data.melt(id_vars=["Sistema", "Etotal"], value_vars=["Eenf", "Ecal"], var_name="tipo", value_name="value")

        solucion_plot = px.bar(display_data,
                            x="Sistema",
                            y="value",
                            color="tipo",
                            labels={"tipo" : "Energía", "value" : "Wh/m²"},
                            barmode="stack",
                            text_auto=True,
                            hover_data={"Etotal"},
                        )
        
        return solucion_plot
    
    # Temperaturas
    @render_widget
    def temperatura_plot():
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
                if i.startswith("T") and i != "Tn":
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
                labels={"index": "Hora", "value": "Temperatura [°C]", "variable": "Temperatura"},
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
                labels={"index": "Hora", "value": "Irradiancia [W/m²]", "variable": "Irradiancia"},
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


    """
    ================================
                Descargas          
    ================================
    """
    @render.download(
        filename=lambda: f"enerhabitat-meanday-{date.today().isoformat()}.csv"
    )
    def down_dia():
        down_data = dia_promedio_dataframe.get().copy()
        if down_data is None or down_data.empty:
            return
        down_data = down_data.round(1)
        down_data.insert(0, "Time", down_data.index)
        csv_bytes = down_data.to_csv(index=False).encode("utf-8-sig")
        yield csv_bytes

    @render.download(filename=lambda: f"enerhabitat-{date.today().isoformat()}.csv")
    def down_res():
        down_data = soluciones_dataframe.get().copy()
        if down_data is None or down_data.empty:
            return
        down_data = down_data.round(1)
        down_data.insert(0, "Time", down_data.index)
        csv_bytes = down_data.to_csv(index=False).encode("utf-8-sig")
        yield csv_bytes

app = App(app_ui, server)
