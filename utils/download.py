from shiny import ui, render, reactive
import os

from datetime import date
from io import StringIO

def download_server(input, output, session, dia_promedio_dataframe, soluciones_dataframe):
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