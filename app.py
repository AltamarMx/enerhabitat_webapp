import plotly.express as px
import enerhabitat as eh
from shiny import App, ui, render
from shinywidgets import output_widget, render_widget  
from utils.card import panel_card

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
    @render.data_frame  
    def sol_df():
        sol_data = eh.Tsa(
        solar_absortance=0.8,
        surface_tilt=input.tilt(), 
        surface_azimuth= input.azimuth(),
        month=input.mes(),
        epw_file=input.epw_file()[0]['datapath']
        )
        return render.DataGrid(sol_data)
    
    @render_widget
    def sol_plot():
        sol_data = eh.Tsa(
        solar_absortance=0.8,
        surface_tilt=input.tilt(), 
        surface_azimuth= input.azimuth(),
        month=input.mes(),
        epw_file=input.epw_file()[0]['datapath']
        )
        
        sc = [
            (0.001,"steel"),
#           (0.1, "adobe")
#           (0.02, "brick"),
#           (0.1, "concrete"),
        ]
        
        eh.solveCS(sc, sol_data)
        
        solucion=px.scatter(
            data_frame=sol_data,
            x=sol_data.index,
            y=["Ta","Tsa","Ti"]
        )
        return solucion


app = App(app_ui, server)


