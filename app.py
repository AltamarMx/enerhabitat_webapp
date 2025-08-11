import plotly.express as px
import enerhabitat as eh
import pandas as pd
import os

from datetime import date
from io import StringIO

from shiny import App, ui, render, reactive
from shinywidgets import output_widget, render_widget

from utils.card import side_card, sc_panel, capa_panel, capa_title, PRECARGADOS_DIR


def render_dataframe(df: pd.DataFrame | None):
    """Construye un ``DataGrid`` a partir de un ``DataFrame``.

    Inserta la columna ``Time`` al inicio con el índice del ``DataFrame`` y
    regresa un ``render.DataGrid`` con un mensaje de resumen. Si el
    ``DataFrame`` está vacío o es ``None`` se retorna ``None``.

    Parameters
    ----------
    df:
        ``DataFrame`` a mostrar.
    """

    if df is None or df.empty:
        return None

    display_df = df.copy()
    display_df.insert(0, "Time", display_df.index)

    return render.DataGrid(
        display_df, summary="Viendo filas {start} a {end} de {total}"
    )


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
            ui.output_ui("res_msg"),
            ui.output_data_frame("sol_df"),
            ui.download_button("down_res", "Descargar datos", width="100%"),
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
    capas_activas = reactive.Value({1: [1]})  # {sc_id : [capas]}
    # Estado global para valores de cada sistema constructivo
    sc_state = reactive.Value({})
    
    """
    ==================================================
                Lo que a veces NO funciona
    ==================================================
    """
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
            
    # ui de cada panel de SC
    @output
    @render.ui
    def sc_panels():
        num_sc = input.num_sc()

        # Mantener la pestaña actualmente seleccionada, siempre que exista
        selected = input.sc_seleccionado() if "sc_seleccionado" in input else None
        if selected is not None:
            try:
                sel_val = int(selected)
                if sel_val > num_sc:
                    selected = str(num_sc)
            except Exception:
                selected = str(num_sc)
        else:
            selected = str(num_sc)

        paneles = [sc_panel(sc_id, sc_state.get()) for sc_id in range(1, num_sc + 1)]

        return ui.navset_card_tab(*paneles, id="sc_seleccionado", selected=f"SC {num_sc}")
    
    # Contadores y modificación de capas
    capa_counts = {"add": reactive.Value({}), "remove": reactive.Value({})}

    def modify_capa(sc_id, cnt, action):
        """Agregar o remover capas según la acción indicada."""
        with reactive.isolate():
            current_capas = capas_activas.get().copy()

        counts = capa_counts[action]
        prev_counts = counts.get()
        capas = current_capas.get(sc_id, [])

        if cnt > prev_counts.get(sc_id, 0):
            if action == "add":
                siguiente = max(capas) + 1
                nueva = {**current_capas, sc_id: capas + [siguiente]}
                capas_activas.set(nueva)
                ui.insert_accordion_panel(
                    id=f"capas_accordion_{sc_id}",
                    panel=capa_panel(sc_id, siguiente, sc_state.get()),
                )
                ui.update_accordion(
                    id=f"capas_accordion_{sc_id}",
                    show=f"Capa {siguiente}",
                )
            elif action == "remove" and len(capas) > 1:
                eliminado = capas.pop()
                nueva = {**current_capas, sc_id: capas}
                capas_activas.set(nueva)
                ui.update_accordion(
                    id=f"capas_accordion_{sc_id}",
                    show=f"Capa {eliminado-1}",
                )
                ui.remove_accordion_panel(
                    id=f"capas_accordion_{sc_id}",
                    target=f"Capa {eliminado}",
                )

        prev_counts[sc_id] = cnt
        counts.set(prev_counts)

    # Agregar capas
    @reactive.Effect
    def _add_capa():
        with reactive.isolate():
            sc_ids = list(capas_activas.get().keys())
        for sc_id in sc_ids:
            cnt = input[f"add_capa_{sc_id}"]()
            modify_capa(sc_id, cnt, "add")

    # Eliminar capas
    @reactive.Effect
    def _remove_capa():
        with reactive.isolate():
            sc_ids = list(capas_activas.get().keys())
        for sc_id in sc_ids:
            cnt = input[f"remove_capa_{sc_id}"]()
            modify_capa(sc_id, cnt, "remove")

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

    # Actualizar títulos de las capas cuando cambien sus datos
    @reactive.Effect
    def _update_capa_titles():
        capas = capas_activas.get()
        for sc_id, lista_capas in capas.items():
            for c_id in lista_capas:
                material = input[f"material_capa_{sc_id}_{c_id}"]()
                ancho = input[f"ancho_capa_{sc_id}_{c_id}"]()
                titulo = capa_title(c_id, material, ancho)
                ui.update_accordion_panel(
                    id=f"capas_accordion_{sc_id}",
                    target=f"Capa {c_id}",
                    title=titulo,
                    value=f"Capa {c_id}",
                )

    #   << Funciones auxiliares >>
    # Regresa lista de tuplas para el sc_id
    def sistemaConstructivo(sc_id):
        return [
            (input[f"material_capa_{sc_id}_{i}"](), input[f"ancho_capa_{sc_id}_{i}"]())
            for i in capas_activas().get(sc_id)
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

    # Recalcular meanDay cuando cambie el EPW o el mes
    @reactive.Effect
    def _():
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
        return render_dataframe(soluciones_dataframe.get())

    @render.data_frame
    def dia_df():
        return render_dataframe(dia_promedio_dataframe.get())

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
        down_data = dia_promedio_dataframe.get()
        if down_data is None or down_data.empty:
            return
        down_data = down_data.copy()
        
        down_data.insert(0, "Time", down_data.index)
        buffer = StringIO()
        down_data.to_csv(buffer, index=False, encoding="utf-8-sig")
        buffer.seek(0)
        return buffer

    @output
    @render.ui
    def res_msg():
        if soluciones_dataframe.get().empty:
            return ui.p("Aún no hay datos que descargar")
        return None
        
    @output
    @render.ui
    def down_res_ui():
        if soluciones_dataframe.get().empty:
            return None
        else:
            return ui.download_button("down_res", "Descargar datos", width="100%")
    
    @render.download(filename=lambda: f"enerhabitat-{date.today().isoformat()}.csv")
    def down_res():
        down_data = soluciones_dataframe.get()
        if down_data is None or down_data.empty:
            return
        down_data = down_data.copy()
        
        down_data.insert(0, "Time", down_data.index)
        buffer = StringIO()
        down_data.to_csv(buffer, index=False, encoding="utf-8-sig")
        buffer.seek(0)
        return buffer

   

app = App(app_ui, server)
