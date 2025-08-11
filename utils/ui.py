from shiny import ui, render, reactive
from shinywidgets import render_widget

import pandas as pd
import plotly.express as px

def ui_server(input, output, session, dia_promedio_dataframe, soluciones_dataframe):
    #   << DataFrames >>
    def render_dataframe(df: pd.DataFrame = None):
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
