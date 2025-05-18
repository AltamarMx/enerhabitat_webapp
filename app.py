import plotly.express as px
import enerhabitat as eh
import os

from shiny import App, ui, render, reactive
from shinywidgets import output_widget, render_widget  

from utils.card import panel_card,PRECARGADOS_DIR

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.navset_card_tab(
            panel_card(1),
            id="cardtab_sc",           
        ),
        id="sidebar_sc",
        width=350,
        position="right"
    ),
    ui.navset_card_tab(
        ui.nav_panel(
            "Gráfica",
            output_widget("sol_plot"),
        ),
        ui.nav_panel(
            "DataFrame",
            ui.output_data_frame("sol_df")
        )
    )
)


def server(input, output, session):
    current_file = reactive.Value(None)
    
    @reactive.Calc
    def solucion():
        sol_data = eh.Tsa(
            solar_absortance = float(input.absortancia()),
            surface_tilt = float(input.tilt()), 
            surface_azimuth= float(input.azimuth()),
            month=input.mes(),
            epw_file= current_file()
            )
        
        sc = sistemaConstructivo()
        
        sol_data = eh.solveCS(sc, sol_data)
        
        return sol_data
    
    @reactive.Calc
    def sistemaConstructivo():
        return [(input.ancho_capa_1(), input.material_capa_1())]
        
        
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
            
    @output
    @render.ui
    def ui_upload():
        if input.selector_archivo() == "upload":
            return ui.input_file("epw_file",label='', accept=[".epw"], multiple=False)
        return None
    
    @render.data_frame  
    def sol_df():
        sol_data = solucion()
        return render.DataGrid(sol_data)
    
    @render_widget
    def sol_plot():
        sol_data = solucion()
        
        solucion_plot = px.scatter(
            data_frame=sol_data,
            x=sol_data.index,
            y=["Ta","Tsa","Ti"]
        )
        return solucion_plot


app = App(app_ui, server)


