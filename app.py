import plotly.express as px
import enerhabitat as eh
import pandas as pd

from shiny import App, ui, render, reactive
from shinywidgets import output_widget

from utils.card_utils import card_server, side_card
from utils.capa_utils import capa_server
from utils.download import download_server
from utils.epw_handler import epw_server
from utils.reactive_handler import reactive_server
from utils.sc_utils import sc_server, init_sistemas
from utils.ui import ui_server
from utils.sistemas import init_sistemas

MAX_SISTEMA = 5
MAX_CAPA = 10

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

    # Diccionario global con los sistemas constructivos y sus capas

    sistemas = reactive.Value(init_sistemas(MAX_SISTEMA, MAX_CAPA))

    card_server(input, output, session, sistemas)
    capa_server(input, output, session, sistemas)
    download_server(input, output, session, dia_promedio_dataframe, soluciones_dataframe)
    epw_server(input, output, session, current_file)
    reactive_server(input, output, session, current_file, dia_promedio_dataframe, sistemas)
    sc_server(input, output, session, dia_promedio_dataframe, soluciones_dataframe, sistemas)    
    ui_server(input, output, session, dia_promedio_dataframe, soluciones_dataframe)
    
    
    """
    def subIndex(cadena):
        # Convertir numeros a subindice
        SUB = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
        cadena_mod = str(cadena).translate(SUB)
        cadena_mod.replace('_','')
        return cadena_mod
    
    """
    
app = App(app_ui, server)
