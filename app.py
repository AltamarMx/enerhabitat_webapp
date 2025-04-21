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
def capa_ui(id_capa, numero_capa):
    return ui.accordion_panel(
        f"Capa {numero_capa}",  # Título visible
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

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.h4("Parámetros geométricos"),
        ui.input_slider(
            "orientacion", 
            "Orientación (Norte=0°, Sur=180°)", 
            -180, 180, 0,
            post="°"
        ),  
        ui.input_slider(
            "inclinacion", 
            "Inclinación (Techo=0°, Muro=90°)", 
            0, 180, 90,
            post="°"
        ),
        
        ui.hr(),
        ui.h4("Datos climáticos"),
        ui.input_file("epw", "Archivo EPW",accept=[".epw"], multiple=False),
        ui.input_select(
            "mes", 
            "Mes:",
            meses
        ),
        ui.hr,
        ui.h4("Sistema constructivo"),
        ui.input_numeric(
            "num_capas", 
            "Número de capas:", 
            1, 
            min=1, 
            max=10
        ),
        
        ui.accordion(
            id="acordion_capas",  # ID del acordeón principal aquí
            # Paneles se agregarán dinámicamente
            open=False,
            multiple=False
        ),
        
        ui.input_action_button(
            "agregar_capa", 
            "Agregar capa"
        ),
        width=350,
        position="right",
        open="always"
    ),
    output_widget("grafico_TSA")
    
)

def server(input, output, session):
    @reactive.event(input.agergar_capa)
    def agrega():
        return f"{input.agregar_capa}"
        
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
    

app = App(app_ui, server)