import plotly.express as px
import enerhabitat as eh
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
    current_file = reactive.Value(None)

    # Lista para mantener el registro de capas existentes
    capas_activas = reactive.Value([1])  # Comienza con la capa 1

    @reactive.Calc
    def solucion():
        sol_data = eh.Tsa(
            solar_absortance=float(input.absortancia()),
            surface_tilt=float(input.tilt()),
            surface_azimuth=float(input.azimuth()),
            month=input.mes(),
            epw_file=current_file(),
        )

        sc = sistemaConstructivo()
        sol_data = eh.solveCS(sc, sol_data)
        return sol_data

    @reactive.Calc
    def sistemaConstructivo():
        return [
            (input[f"ancho_capa_{i}"](), input[f"material_capa_{i}"]())
            for i in capas_activas()
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

    # Agregar capa
    @reactive.Effect
    @reactive.event(input.add_capa)
    def _():
        nueva_capa = max(capas_activas()) + 1
        capas_activas.set(capas_activas() + [nueva_capa])

    # Eliminar capa
    @reactive.Effect
    def _():
        for i in capas_activas():
            btn_id = f"remove_capa_{i}"
            if btn_id in input and input[btn_id]() > 0:
                if len(capas_activas()) > 1:
                    # Crear nueva lista sin la capa eliminada
                    nuevas_capas = [c for c in capas_activas() if c != i]
                    capas_activas.set(nuevas_capas)
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
    def ui_capas():
        panels = []
        for i in capas_activas():
            panels.append(
                ui.accordion_panel(
                    f"Capa {i}",
                    ui.input_select(f"material_capa_{i}", "Material:", materiales),
                    ui.input_numeric(f"ancho_capa_{i}", "Ancho (mm):", value=0.1, step=0.01, min=0.01),                  
                    ui.input_action_button(
                        f"remove_capa_{i}",
                        "Eliminar",
                        width="100%",
                        class_="btn-light") if len(capas_activas()) > 1 else None
                    ),
                )
            

        return ui.accordion(
            *panels,
            id="capas_accordion",
            open=f"Capa {max(capas_activas()) if capas_activas() else '1'}",  # Abre la última capa
            multiple=False,
        )

    @render.data_frame
    def sol_df():
        sol_data = solucion()
        return render.DataGrid(sol_data)

    @render_widget
    def sol_plot():
        sol_data = solucion()

        solucion_plot = px.scatter(
            data_frame=sol_data, x=sol_data.index, y=["Ta", "Tsa", "Ti"]
        )
        return solucion_plot


app = App(app_ui, server)
