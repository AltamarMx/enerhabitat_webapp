from shiny import App, ui, render, reactive
from shinywidgets import output_widget, render_widget 

import pandas as pd

import plotly.express as px 
import plotly.graph_objects as go

import enerhabitat as eh

# Datos de ejemplo
meses = {
    "Enero": "01",
    "Febrero": "02",
    "Marzo": "03",
    "Abril": "04",
    "Mayo": "05",
    "Junio": "06",
    "Julio": "07",
    "Agosto": "08",
    "Septiembre": "09",
    "Octubre": "10",
    "Noviembre": "11",
    "Diciembre": "12"
}

materiales = {
    "Concreto",
    "Ladrillo",
    "Poliestireno",
    "Yeso",
    "Fibra de vidrio"
}

# Función para generar UI de cada capa
def capa_ui(id_capa):
    return ui.accordion_panel(
        f"Capa {id_capa}",  # Título visible
        # El ID se maneja automáticamente, no lo especificamos aquí
        ui.input_select(
            f"material_{id_capa}", 
            "Material:",
            materiales
        ),
        ui.input_numeric(
            f"espesor_{id_capa}", 
            "Espesor (mm):",
            value=100,
            min=1,
            max=1000
        ),
        ui.input_numeric(
            f"densidad_{id_capa}", 
            "Densidad (g/cm2):",
            value=0,
            min=0,
            max=1000
        ),
        ui.input_numeric(
            f"absortancia_{id_capa}", 
            "Absortancia:",
            value=0,
            min=0,
            max=1,
            step=0.001
        ),
        ui.input_numeric(
            f"conductividad_{id_capa}", 
            "Conductividad térmica (W/m·K):",
            value=0.5,
            min=0.001,
            max=10,
            step=0.01
        ),
        ui.input_numeric(
            f"capacidad_calorifica_{id_capa}", 
            "Capacidad calorífica específica (J/kg·K):",
            value=0,
            min=0,
            max=10000
        ),
        ui.input_action_button(
            f"eliminar_{id_capa}",
            "Eliminar capa",
            class_="btn-danger"
        )
    )

def crearCapas(numero_capas):
    aux=capa_ui(1)
    for i in range(numero_capas):
        aux=aux,capa_ui(i)
    return aux
        
# Función para generar UI de un SC 
def sc_ui(numero_sc):
    return ui.nav_panel(f"SC {numero_sc}",
    ui.h4("Parámetros geométricos"),
        ui.input_slider(
            f"orientacion_{numero_sc}", 
            "Orientación (Norte=0°, Sur=180°)", 
            -180, 180, 0,
            post="°"
        ),  
        ui.input_slider(
            f"inclinacion_{numero_sc}", 
            "Inclinación (Techo=0°, Muro=90°)", 
            0, 180, 90,
            post="°"
        ),
        
        ui.hr(),
        ui.h4("Datos climáticos"),
        ui.input_file(f"epw_{numero_sc}", "Archivo EPW",accept=[".epw"], multiple=False),
        ui.input_select(
            f"mes_{numero_sc}", 
            "Mes:",
            meses
        ),
        ui.hr,
        ui.h4("Sistema constructivo"),
        ui.input_numeric(
            f"num_capas_{numero_sc}", 
            "Número de capas:", 
            1, 
            min=1, 
            max=10
        ),
        
        
        
    )

"""ui.input_action_button(
            f"agregar_capa_{numero_sc}", 
            "Agregar capa"
        ),
        ui.accordion(
            crearCapas(f"{input.agregar_capa_1()}"),
            id=f"acordion_capas_{numero_sc}",  # ID del acordeón principal aquí
            # Paneles se agregarán dinámicamente
            open=False,
            multiple=False
        ),"""


def crearSC(numero_sc):
    aux=sc_ui(1)
    for i in range(1,numero_sc):
        aux=aux,sc_ui(i+1)
    return aux    
    
app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.navset_card_tab(
            crearSC(1),
            id="sistemas_constructivos",
            open=""           
        ),
        width=350,
        position="right",
        open="always"
    ),
    output_widget("grafico_TSA")
    
)

def server(input, output, session):
    @reactive.event(input.agergar_capa_1)
    def agrega():
        return f"{input.agregar_capa_1()}"
        
    @output
    @render_widget
    def grafico_TSA():
        epw = input.epw()
        cht = input.conductividad()
        sa = input.absortancia()
        inclinacion = input.inclinacion()
        azimuth = input.orientacion()
        mes = input.mes()
        año = "2025"
        
        dia=eh.calculateTsa(epw, cht, sa, inclinacion, azimuth, mes, año)
        
        df = dia.reset_index().iloc[::600]
        fig = px.line(df,x="index",y=["Tsa","Ta"])
        fig.add_trace(go.Scatter(
                                x=df["index"], 
                                y=df['Tn'] + df['DeltaTn'], 
                                mode='lines',
                                showlegend=False , 
                                line=dict(color='rgba(0,0,0,0)')
                                )
        )

        fig.add_trace(go.Scatter(
                                x=df["index"], 
                                y=df['Tn'] -df['DeltaTn'], 
                                mode='lines',
                                showlegend=False , 
                                fill='tonexty',
                                line=dict(color='rgba(0,0,0,0)'),
                                fillcolor='rgba(0,255,0,0.3)'
                                )
        )

        # Personalizar el layout

        fig.update_layout(
            yaxis_title='Temperatura (°C)',
            legend_title='',  # Quitar el título de la leyenda
            xaxis_title=''
        )
        return fig
    
    pass

app = App(app_ui, server)